from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from datetime import datetime, timedelta

## Uncomment the below code block and set SMTP configs
##  to activate the config for Email Notification
## Config Email Notidication
# from airflow.utils.email import send_email
# import smtplib

# smtp_host = "your-smtp-host"
# smtp_port = 587
# smtp_user = "your-email@example.com"
# smtp_password = "your-password"

# try:
#     server = smtplib.SMTP(smtp_host, smtp_port)
#     server.starttls()
#     server.login(smtp_user, smtp_password)
#     print("SMTP connection successful!")
# except Exception as e:
#     print(f"SMTP connection failed: {e}")
# finally:
#     server.quit()

# def send_email_notification(context):
#     subject = "Airflow Task Failed"
#     body = f"""
#     Task {context['task_instance'].task_id} failed in DAG {context['dag'].dag_id}.
#     Execution Time: {context['execution_date']}
#     Log URL: {context['task_instance'].log_url}
#     """
#     send_email(to=["your-email@example.com"], subject=subject, html_content=body)

default_args = {
    'owner': 'airflow',
    'start_date': datetime.today(),
    # Turn to True if you want to receive an email when the task fails
    'email_on_failure': False,
    'email_on_retry': False,
    # Uncomment if you want to add a callback when the task fails
    # 'on_failure_callback': send_email_notification,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Load SQL queries from files
with open('/opt/airflow/dags/sql/intraday_query.sql', 'r') as file:
    intraday_sql = file.read()

with open('/opt/airflow/dags/sql/daily_query.sql', 'r') as file:
    daily_sql = file.read()

# DAG for 5-minute data (runs hourly)
with DAG(
    dag_id='stock_price_pipeline_intraday',
    default_args=default_args,
    description='DAG for 5-minute data (runs hourly)',
    schedule_interval='@hourly',
) as dag_intraday:
    start_producer_intraday_task = BashOperator(
        task_id='start_producer_intraday',
        bash_command='docker exec producer-5min python kafka_producer_5min.py',
    )

    start_consumer_intraday_task = BashOperator(
        task_id='start_consumer_intraday',
        bash_command='docker exec consumer-5min python kafka_consumer_5min.py',
    )
    
    analytics_intraday_task = SQLExecuteQueryOperator(
        task_id='update_stock_analytics_intraday',
        conn_id='postgres_default',
        sql=intraday_sql,
    )

    start_producer_intraday_task >> start_consumer_intraday_task >> analytics_intraday_task


# DAG for daily data (runs daily)
with DAG(
    dag_id='stock_price_pipeline_daily',
    default_args=default_args,
    description='DAG for daily data (runs daily)',
    schedule_interval='@daily',
) as dag_daily:
    start_producer_daily_task = BashOperator(
        task_id='start_producer_daily',
        bash_command='docker exec producer-daily python kafka_producer_daily.py',
    )

    start_consumer_daily_task = BashOperator(
        task_id='start_consumer_daily',
        bash_command='docker exec consumer-daily python kafka_consumer_daily.py',
    )

    analytics_daily_task = SQLExecuteQueryOperator(
        task_id='update_stock_analytics_daily',
        conn_id='postgres_default',
        sql=daily_sql,
    )

    start_producer_daily_task >> start_consumer_daily_task >> analytics_daily_task