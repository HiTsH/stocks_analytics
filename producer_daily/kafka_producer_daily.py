import os
import requests
from kafka import KafkaProducer
import json
import logging
import psycopg2
from datetime import date, timedelta

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://www.alphavantage.co/query"
API_KEY = os.getenv("ALPHAVANTAGE_API_KEY_DAILY")
SYMBOLS = ["AAPL", "GOOGL", "MSFT"]

DB_HOST = "postgres"
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_PORT = "5432"

producer = KafkaProducer(
    bootstrap_servers='kafka:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

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

def fetch_stock_data():
    new_data_found = False  # Flag to track if new data is found

    for symbol in SYMBOLS:
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "apikey": API_KEY,
        }
        logger.info(f"Fetching data for symbol: {symbol}")
        response = requests.get(API_URL, params=params)
        response.raise_for_status()

        if response.status_code == 200:
            data = response.json()
            last_update = get_last_update(symbol)

            try:
                last_refreshed = data.get("Meta Data").get("3. Last Refreshed")
            except AttributeError:
                last_refreshed = date.today() - timedelta(days=1)
                logger.info(f"Setting last refreshed date for symbol {symbol} to {last_refreshed}")

            if last_refreshed != last_update:
                logger.info(f"New data found for symbol: {symbol}")
                producer.send("stock_prices_daily", data)
                new_data_found = True
            else:
                logger.info(f"Data for symbol {symbol} is already up-to-date.")
        else:
            logger.error(f"Failed to fetch data for {symbol}. Status Code: {response.status_code}, Response: {response.text}")

    if not new_data_found:
        logger.info("No new data found for any symbol. Closing producer.")

fetch_stock_data()
logger.info("Producer executed.")
producer.close()
