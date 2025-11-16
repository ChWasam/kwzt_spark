import csv
import json
import os
import sys
import time
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configuration from environment variables
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'transactions')
DATA_FILE = os.getenv('DATA_FILE', '/data/transactions.csv')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 10000))
BATCH_DELAY = int(os.getenv('BATCH_DELAY', 5))
MAX_BATCHES = int(os.getenv('MAX_BATCHES', 0))  # 0 = no limit (process all data)

print("=" * 80)
print("KAFKA PRODUCER - Transaction Data Streamer")
print("=" * 80)
print(f" Kafka Broker: {KAFKA_BROKER}")
print(f" Topic: {KAFKA_TOPIC}")
print(f" Data File: {DATA_FILE}")
print(f" Batch Size: {BATCH_SIZE:,} records")
print(f"⏱  Batch Delay: {BATCH_DELAY} seconds")
print(f" Max Batches: {MAX_BATCHES if MAX_BATCHES > 0 else 'No limit (all data)'}")
print("=" * 80)


def create_producer():
    """Create and configure Kafka producer"""
    print("\n Connecting to Kafka broker...")

    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',                    # Wait for all replicas to acknowledge
            retries=3,                     # Retry failed sends
            max_in_flight_requests_per_connection=5,
            compression_type='gzip',       # Compress messages
            linger_ms=10,                  # Batch messages for 10ms
            batch_size=16384,              # 16KB batch size
        )

        print(" Successfully connected to Kafka!")
        return producer

    except Exception as e:
        print(f" Failed to connect to Kafka: {e}")
        sys.exit(1)


def send_batch(producer, batch, batch_number):
    """Send a batch of records to Kafka"""
    print(f"\n Sending batch #{batch_number} ({len(batch)} records)...")

    success_count = 0
    error_count = 0

    for record in batch:
        try:
            # Use transaction_id as the key for partitioning
            key = record['transaction_id']

            # Send to Kafka
            future = producer.send(KAFKA_TOPIC, key=key, value=record)

            # Optional: Wait for acknowledgment (can be async for better performance)
            # future.get(timeout=10)

            success_count += 1

        except KafkaError as e:
            print(f" Error sending record: {e}")
            error_count += 1

    # Flush to ensure all messages are sent
    producer.flush()

    print(f" Batch #{batch_number} complete: {success_count} sent, {error_count} errors")
    return success_count, error_count


def stream_data():
    """Main function to stream data from CSV to Kafka"""

    # Check if data file exists
    if not os.path.exists(DATA_FILE):
        print(f" Error: Data file not found: {DATA_FILE}")
        sys.exit(1)

    # Create Kafka producer
    producer = create_producer()

    print(f"\n Reading data from: {DATA_FILE}")
    print(f" Starting data stream...\n")

    total_sent = 0
    total_errors = 0
    batch_number = 0
    batch = []

    try:
        with open(DATA_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            for record in reader:
                batch.append(record)

                # When batch is full, send it
                if len(batch) >= BATCH_SIZE:
                    batch_number += 1
                    sent, errors = send_batch(producer, batch, batch_number)
                    total_sent += sent
                    total_errors += errors

                    # Clear batch
                    batch = []

                    # Check if we've reached the maximum number of batches
                    if MAX_BATCHES > 0 and batch_number >= MAX_BATCHES:
                        print(f"\n Reached maximum batch limit ({MAX_BATCHES} batches)")
                        print(" Stopping producer...")
                        break

                    # Wait before sending next batch (simulate real-time streaming)
                    if BATCH_DELAY > 0:
                        print(f"Waiting {BATCH_DELAY} seconds before next batch...")
                        time.sleep(BATCH_DELAY)

            # Send remaining records in the last batch (only if we haven't hit the limit)
            if batch and (MAX_BATCHES == 0 or batch_number < MAX_BATCHES):
                batch_number += 1
                sent, errors = send_batch(producer, batch, batch_number)
                total_sent += sent
                total_errors += errors

        print("\n" + "=" * 80)
        print(" DATA STREAMING COMPLETE!")
        print("=" * 80)
        print(f" Total batches: {batch_number}")
        print(f" Total records sent: {total_sent:,}")
        print(f" Total errors: {total_errors:,}")
        print(f" Topic: {KAFKA_TOPIC}")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n  Streaming interrupted by user")

    except Exception as e:
        print(f"\n Error during streaming: {e}")

    finally:
        # Close producer
        print("\n Closing Kafka producer...")
        producer.close()
        print(" Producer closed successfully")


if __name__ == "__main__":
    stream_data()
