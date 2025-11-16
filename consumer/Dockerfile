# Kafka Consumer Dockerfile
# Builds a lightweight Python container for receiving Kafka messages and saving to CSV

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy consumer code
COPY consumer.py .

# Run consumer with unbuffered output (-u flag)
CMD ["python", "-u", "consumer.py"]
