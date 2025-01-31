import os
import json
import pandas as pd
from kafka import KafkaConsumer
import logging
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from tenacity import retry, stop_after_attempt, wait_exponential

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
DB_HOST = "postgres"
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_PORT = "5432"
SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def process_and_store(data):
    if "Error Message" in data:
        logger.error(f"API Error: {data.get('Error Message')}")
        return
    if "Note" in data:
        logger.error(f"API Rate Limit: {data.get('Note')}")
        return

    symbol = data.get("symbol")
    time_series = data.get("data")
    if not symbol or not time_series:
        logger.error("Invalid message format: missing symbol or data.")
        return

    processed_data = []
    for timestamp, value in time_series.items():
        raw_data = {timestamp: value}
        open_price = round(float(value.get("1. open")), 2)
        high_price = round(float(value.get("2. high")), 2)
        low_price = round(float(value.get("3. low")), 2)
        close_price = round(float(value.get("4. close")), 2)
        volume = int(value.get("5. volume"))

        raw_data_json = json.dumps(raw_data)

        processed_data.append({
            'symbol': symbol,
            'timestamp': timestamp,
            'open_price': open_price,
            'high_price': high_price,
            'low_price': low_price,
            'close_price': close_price,
            'volume': volume,
            'raw_data': raw_data_json
        })

    df = pd.DataFrame(processed_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    try:
        engine = create_engine(SQLALCHEMY_DATABASE_URI)

        # Insert data in raw tables
        df_raw = df[['symbol', 'timestamp', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'raw_data']]
        df_raw.to_sql('stock_prices_5min', engine, schema='raw', if_exists='append', index=False, method='multi')
        logger.info(f"Inserted {len(df_raw)} rows into raw table for symbol: {symbol}")

        # Insert data in staging tables
        df_staging = df[['symbol', 'timestamp', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']]
        df_staging.to_sql('stock_prices_5min', engine, schema='staging', if_exists='append', index=False, method='multi')
        logger.info(f"Inserted {len(df_staging)} rows into staging table for symbol: {symbol}")
    
    except Exception as e:
        logger.error(f"Error processing data for {symbol}: {e}")
        return

def main():
    consumer = KafkaConsumer(
        "stock_prices_5min",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id="stock_pipeline_5min",
    )

    message_count = 0

    try:
        for message in consumer:
            if message.value.get("terminate"):
                logger.info(f"Received termination signal: {message.value}. Closing consumer.")
                break
            
            process_and_store(message.value)
            message_count += 1
            consumer.commit()

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
    
    finally:
        logger.info("Consumer closing...")
        consumer.close()
        logger.info(f"Consumer closed. Total messages processed: {message_count}")

if __name__ == "__main__":
    main()
