import os
import json
import psycopg2
from kafka import KafkaConsumer
import logging

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
DB_HOST = "postgres"
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_PORT = "5432"

def process_and_store(data):
    try:
        with psycopg2.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        ) as conn:
            cursor = conn.cursor()

            time_series = data.get("Time Series (5min)")
            symbol = data.get("Meta Data").get("2. Symbol")

            for timestamp, value in time_series.items():
                raw_data = {timestamp: value}
                open_price = round(float(value.get("1. open")), 2)
                high_price = round(float(value.get("2. high")), 2)
                low_price = round(float(value.get("3. low")), 2)
                close_price = round(float(value.get("4. close")), 2)
                volume = int(value.get("5. volume"))

                raw_data_json = json.dumps(raw_data)

                # Insert into raw table
                cursor.execute(
                    '''
                    INSERT INTO raw.stock_prices_5min (symbol, timestamp, open_price, high_price, low_price, close_price, volume, raw_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timestamp) DO NOTHING
                    ''',
                    (symbol, timestamp, open_price, high_price, low_price, close_price, volume, raw_data_json)
                )
                logger.info(f"Inserted 5min data for symbol: {symbol}, timestamp: {timestamp} in RAW TABLE")

                # Insert into staging table
                cursor.execute(
                    '''
                    INSERT INTO staging.stock_prices_5min (symbol, timestamp, open_price, high_price, low_price, close_price, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timestamp) DO NOTHING
                    ''',
                    (symbol, timestamp, open_price, high_price, low_price, close_price, volume)
                )
                logger.info(f"Inserted 5min data for symbol: {symbol}, timestamp: {timestamp} in STAGING TABLE")

            conn.commit()
            logger.info(f"Processed data for symbol: {symbol}")
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Error while connecting to PostgreSQL: {error}")

def main():
    consumer = KafkaConsumer(
        "stock_prices_5min",
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="stock_pipeline_5min"
    )

    try:
        for message in consumer:
            process_and_store(message.value)
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user.")
    finally:
        consumer.close()
        logger.info("Consumer closed.")

if __name__ == "__main__":
    main()