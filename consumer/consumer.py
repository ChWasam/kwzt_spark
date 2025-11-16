import csv
import json
import os
import sys
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Configuration from environment variables
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'transactions')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'transaction-consumer-group')
OUTPUT_FILE = os.getenv('OUTPUT_FILE', '/data/received_transactions.csv')
MAX_MESSAGES = int(os.getenv('MAX_MESSAGES', 0))  # 0 = no limit (consume until timeout)

print("=" * 80)
print(" KAFKA CONSUMER - Transaction Data Receiver")
print("=" * 80)
print(f"Kafka Broker: {KAFKA_BROKER}")
print(f"Topic: {KAFKA_TOPIC}")
print(f"Consumer Group: {KAFKA_GROUP_ID}")
print(f"Output File: {OUTPUT_FILE}")
print(f"Max Messages: {MAX_MESSAGES if MAX_MESSAGES > 0 else 'No limit (continuous waiting)'}")
print("=" * 80)


def create_consumer():
    """Create and configure Kafka consumer"""
    print("\n Connecting to Kafka broker...")

    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BROKER,
            group_id=KAFKA_GROUP_ID,
            auto_offset_reset='earliest',      # Start from beginning if no offset
            enable_auto_commit=True,           # Auto-commit offsets
            auto_commit_interval_ms=5000,      # Commit every 5 seconds
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            consumer_timeout_ms=60000,         # Wait up to 60 seconds between messages
        )

        print(f" Successfully connected to Kafka!")
        print(f" Subscribed to topic: {KAFKA_TOPIC}")
        return consumer

    except Exception as e:
        print(f" Failed to connect to Kafka: {e}")
        sys.exit(1)


def consume_messages():
    """Main function to consume messages from Kafka and save to CSV"""

    # Create Kafka consumer
    consumer = create_consumer()

    print(f"\n Opening output file: {OUTPUT_FILE}")

    # CSV fieldnames (same as producer)
    fieldnames = [
        "timestamp", "transaction_id", "customer_id", "product_category",
        "product_price", "quantity", "total_amount", "payment_method",
        "city", "country"
    ]

    message_count = 0
    batch_count = 0

    try:
        # Open CSV file for writing
        with open(OUTPUT_FILE, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            print("\n Listening for messages...")
            if MAX_MESSAGES > 0:
                print(f"(Will stop after {MAX_MESSAGES:,} messages)\n")
            else:
                print("(Continuous mode - waiting indefinitely for messages)\n")

            # Consume messages
            for message in consumer:
                try:
                    # Extract record from message
                    record = message.value
                    key = message.key

                    # Write to CSV
                    writer.writerow(record)
                    message_count += 1

                    # Log progress every 10,000 messages
                    if message_count % 10000 == 0:
                        batch_count += 1
                        print(f"Batch #{batch_count}: Received {message_count:,} messages so far...")

                    # Check if we've reached the maximum number of messages
                    if MAX_MESSAGES > 0 and message_count >= MAX_MESSAGES:
                        print(f"\n Reached maximum message limit ({MAX_MESSAGES:,} messages)")
                        print(" Stopping consumer...")
                        break

                except Exception as e:
                    print(f" Error processing message: {e}")

            print("\n" + "=" * 80)
            print(" CONSUMPTION COMPLETE!")
            print("=" * 80)
            print(f" Total messages received: {message_count:,}")
            print(f" Saved to: {OUTPUT_FILE}")
            print("=" * 80)

    except KeyboardInterrupt:
        print("\n  Consumption interrupted by user")

    except Exception as e:
        print(f"\n Error during consumption: {e}")

    finally:
        # Close consumer
        print("\n Closing Kafka consumer...")
        consumer.close()
        print(" Consumer closed successfully")

    return message_count


if __name__ == "__main__":
    consume_messages()
