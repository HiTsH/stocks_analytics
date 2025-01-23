FROM apache/airflow:2.7.0

# Switch to root to install system dependencies
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Switch back to the airflow user to install Python packages
USER airflow
RUN pip install --no-cache-dir kafka-python psycopg2-binary

# Create directories for producers and consumers scripts
RUN mkdir -p /opt/airflow/dags/producers /opt/airflow/dags/consumers

# Copy producer and consumer scripts
COPY producer_5min/*.py /opt/airflow/dags/producers/
COPY producer_daily/*.py /opt/airflow/dags/producers/
COPY consumer_5min/*.py /opt/airflow/dags/consumers/
COPY consumer_daily/*.py /opt/airflow/dags/consumers/

# Set the working directory
WORKDIR /opt/airflow

# Initialize Airflow DB (only needed once)
RUN airflow db init && airflow db migrate

# Create Airflow User
RUN airflow users create \
    --username airflow \
    --password airflow \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email email@example.com

# Default command to run the webserver and scheduler
CMD ["bash", "-c", "airflow webserver & airflow scheduler"]