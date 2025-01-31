import os
import requests
from kafka import KafkaProducer
import json
import logging
import psycopg2
from datetime import date, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API CONSTANTS
API_URL = "https://www.alphavantage.co/query"
API_KEY = os.getenv("ALPHAVANTAGE_API_KEY_DAILY")
SYMBOLS = ["AAPL", "GOOGL", "MSFT"]

# DB CONSTANTS
DB_HOST = "postgres"
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_PORT = "5432"

# Validate API Key
if not API_KEY:
    logger.error("ALPHAVANTAGE_API_KEY_DAILY environment variable is not set.")
    exit(1)

# Kafka Producer Configuration
producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

message_counter = 0

def get_last_update(symbol):
    """Get the latest date for a specific symbol from the database."""
    try:
        with psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        ) as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT date 
                FROM staging.stock_prices_daily
                WHERE symbol = %s
                ORDER BY date DESC
                LIMIT 1
                ''',
                (symbol,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error fetching last update for symbol {symbol}: {e}")
        return None

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_stock_data():
    for symbol in SYMBOLS:
        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": API_KEY,
            }
            logger.info(f"Fetching data for symbol: {symbol}")
            response = requests.get(API_URL, params=params)

            # Check for HTTP errors per symbol without raising an exception
            if response.status_code != 200:
                logger.error(f"Failed to fetch data for {symbol}. Status Code: {response.status_code}, Response: {response.text}")
                continue

            data = response.json()

            # Check for API errors and rate limit messages per symbol
            if "Error Message" in data:
                logger.error(f"API Error for symbol {symbol}: {data['Error Message']}")
                continue

            if "Note" in data:
                logger.error(f"API Rate Limit for symbol {symbol}: {data['Note']}")
                continue

            # Check if the response contains the necessary data
            meta_data = data.get("Meta Data")
            time_series = data.get("Time Series (Daily)")
            if not meta_data and not time_series:
                if "Time Series (Daily)" in data and "Meta Data" in data:
                    logger.error(f"Meta Data or Time Series (Daily) is missing in the response: {data}")
                    continue

            last_refreshed = date.fromisoformat(meta_data.get("3. Last Refreshed"))
            last_update = get_last_update(symbol) or (last_refreshed - timedelta(days=1))
            
            for date_str, value in time_series.items():
                date_dt = date.fromisoformat(date_str)
                if not last_update or date_dt > last_update:
                    message = {"symbol": symbol, "date": date_str, "data": {date_str: value}}
                    producer.send('stock_prices_daily', message)
                    logger.info(f"Sent data for symbol: {symbol}, date: {date_str}")
                    global message_counter
                    message_counter += 1
            
            logger.info(f"Processed messages for symbol: {symbol}: {message_counter}")

        except Exception as e:
            logger.error(f"Error processing symbol {symbol}: {e}")

fetch_stock_data()

# Flush all messages and close the producer
try:
    # Send terminate message
    producer.send('stock_prices_daily', {'terminate': True})
    logger.info("Flushing kafka producer...")
    producer.flush()

    # Log Kafka producer metrics
    metrics = producer.metrics()
    messages_sent = metrics.get('producer-metrics', {}).get('record-send-total', message_counter)
    record_errors = metrics.get('producer-metrics', {}).get('record-error-total', 0)
    request_latency = metrics.get('producer-metrics', {}).get('request-latency-avg', 0)
    logger.info(f"Messages sent: {messages_sent}")
    logger.info(f"Record errors: {record_errors}")
    logger.info(f"Average request latency: {request_latency}")

except Exception as e:
    logger.error(f"Error flushing kafka producer: {e}")

finally:
    logger.info("Closing kafka producer...")
    producer.close()
    logger.info("Producer executed and closed successfully.")
