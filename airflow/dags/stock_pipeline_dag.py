from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.utils.email import send_email
from datetime import datetime, timedelta
import subprocess


def send_email_notification(context):
    subject = "Airflow Task Failed"
    body = f"""
    Task {context['task_instance'].task_id} failed in DAG {context['dag'].dag_id}.
    Execution Time: {context['execution_date']}
    Log URL: {context['task_instance'].log_url}
    """
    send_email(to=["your_email@example.com"], subject=subject, html_content=body)


def start_producer():
    subprocess.run(
        ["python", "/opt/airflow/dags/producer/kafka_producer.py"], 
        check=True,
        text=True,
        capture_output=True,
    )


def start_consumer():
    subprocess.run(
        ["python", "/opt/airflow/dags/consumer/kafka_consumer.py"], 
        check=True,
        text=True,
        capture_output=True,
    )

default_args = {
    'owner': 'airflow',
    'start_date': datetime.today(),
    'email_on_failure': True,
    'on_failure_callback': send_email_notification,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='stock_price_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
) as dag:
    producer_task = PythonOperator(
        task_id='start_producer',
        python_callable=start_producer,
    )

    consumer_task = PythonOperator(
        task_id='start_consumer',
        python_callable=start_consumer,
    )
    
    analytics_intraday_task = SQLExecuteQueryOperator(
        task_id='update_stock_analytics_intraday',
        postgres_conn_id='postgres_default',
        sql="""
        INSERT INTO final.intraday_analytics (
    symbol, timestamp, open, high, low, close, volume, prev_close, price_change_pct, vwap, last_refreshed
)
        SELECT
            symbol,
            timestamp,
            open,
            high,
            low,
            close,
            volume::BIGINT,
            LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp) AS prev_close,
            ROUND(((close - LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp)) / 
                NULLIF(LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp), 0)) * 100, 2) AS price_change_pct,
            ROUND(SUM(close * volume) OVER (PARTITION BY symbol, DATE(timestamp)) / 
                NULLIF(SUM(volume) OVER (PARTITION BY symbol, DATE(timestamp)), 0), 2) AS vwap,
            timestamp AS last_refreshed
        FROM staging.stock_prices_5min
        ON CONFLICT (symbol, timestamp) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            prev_close = EXCLUDED.prev_close,
            price_change_pct = EXCLUDED.price_change_pct,
            vwap = EXCLUDED.vwap,
            last_refreshed = EXCLUDED.last_refreshed;
        """,
    )

    analytics_daily_task = SQLExecuteQueryOperator(
        task_id='update_stock_analytics_daily',
        postgres_conn_id='postgres_default',
        sql="""
        INSERT INTO final.daily_analytics (
    symbol, date, open, high, low, close, volume, price_change_pct_daily, moving_avg_50d, moving_avg_200d, volume_avg_20d, last_refreshed
)
        SELECT
            symbol,
            date,
            open,
            high,
            low,
            close,
            volume::BIGINT,
            ROUND(((close - LAG(close) OVER (PARTITION BY symbol ORDER BY date)) / 
                NULLIF(LAG(close) OVER (PARTITION BY symbol ORDER BY date), 0)) * 100, 2) AS price_change_pct_daily,
            ROUND(AVG(close) OVER (
                PARTITION BY symbol 
                ORDER BY date 
                ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
            ), 2) AS moving_avg_50d,
            ROUND(AVG(close) OVER (
                PARTITION BY symbol 
                ORDER BY date 
                ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
            ), 2) AS moving_avg_200d,
            ROUND(AVG(volume) OVER (
                PARTITION BY symbol 
                ORDER BY date 
                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
            ), 2) AS volume_avg_20d,
            CURRENT_TIMESTAMP AS last_refreshed
        FROM staging.stock_prices_daily
        ON CONFLICT (symbol, date) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            price_change_pct_daily = EXCLUDED.price_change_pct_daily,
            moving_avg_50d = EXCLUDED.moving_avg_50d,
            moving_avg_200d = EXCLUDED.moving_avg_200d,
            volume_avg_20d = EXCLUDED.volume_avg_20d,
            last_refreshed = EXCLUDED.last_refreshed;
        """,
    )

    producer_task >> consumer_task >> [analytics_intraday_task, analytics_daily_task]
