FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY kafka_consumer_5min.py ./
CMD ["python", "kafka_consumer_5min.py"]
