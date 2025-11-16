"""
Synthetic E-commerce Transaction Data Generator
Generates 1,000,000 transaction records for Kafka streaming and PySpark EDA

Author: DS551 Assignment
Date: 2025-11-14
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
NUM_RECORDS = 1_000_000
OUTPUT_FILE = "data/transactions.csv"

# Data generation parameters
PRODUCT_CATEGORIES = [
    "Electronics", "Clothing", "Home & Garden", "Sports & Outdoors",
    "Books", "Toys & Games", "Health & Beauty", "Food & Beverage",
    "Automotive", "Office Supplies"
]

PAYMENT_METHODS = ["Credit Card", "Debit Card", "PayPal", "Apple Pay", "Google Pay"]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose",
    "Austin", "Jacksonville", "Fort Worth", "Columbus", "Indianapolis",
    "Charlotte", "San Francisco", "Seattle", "Denver", "Boston",
    "Miami", "Atlanta", "Detroit", "Portland", "Las Vegas"
]

COUNTRIES = ["USA"]  # Can expand if needed


def generate_timestamp(start_date, end_date):
    """Generate random timestamp between start and end dates"""
    time_delta = end_date - start_date
    random_seconds = random.randint(0, int(time_delta.total_seconds()))
    return start_date + timedelta(seconds=random_seconds)


def generate_transaction():
    """Generate a single transaction record"""
    # Generate timestamp (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    timestamp = generate_timestamp(start_date, end_date)

    # Generate transaction details
    transaction_id = f"TXN{random.randint(100000000, 999999999)}"
    customer_id = f"CUST{random.randint(10000, 99999)}"
    product_category = random.choice(PRODUCT_CATEGORIES)

    # Price varies by category
    if product_category == "Electronics":
        product_price = round(random.uniform(50, 2000), 2)
    elif product_category == "Clothing":
        product_price = round(random.uniform(15, 300), 2)
    elif product_category == "Books":
        product_price = round(random.uniform(5, 50), 2)
    else:
        product_price = round(random.uniform(10, 500), 2)

    quantity = random.randint(1, 5)
    total_amount = round(product_price * quantity, 2)
    payment_method = random.choice(PAYMENT_METHODS)
    city = random.choice(CITIES)
    country = random.choice(COUNTRIES)

    return {
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "product_category": product_category,
        "product_price": product_price,
        "quantity": quantity,
        "total_amount": total_amount,
        "payment_method": payment_method,
        "city": city,
        "country": country
    }


def main():
    """Generate synthetic transaction data"""
    print(f" Starting synthetic data generation...")
    print(f" Target records: {NUM_RECORDS:,}")
    print(f" Output file: {OUTPUT_FILE}")
    print()

    # Create data directory if it doesn't exist
    Path("data").mkdir(exist_ok=True)

    # Generate data
    fieldnames = [
        "timestamp", "transaction_id", "customer_id", "product_category",
        "product_price", "quantity", "total_amount", "payment_method",
        "city", "country"
    ]

    with open(OUTPUT_FILE, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Generate records with progress reporting
        for i in range(1, NUM_RECORDS + 1):
            transaction = generate_transaction()
            writer.writerow(transaction)

            # Progress update every 100k records
            if i % 100_000 == 0:
                print(f"Generated {i:,} records ({i/NUM_RECORDS*100:.0f}% complete)")

    # Get file size
    file_size_mb = Path(OUTPUT_FILE).stat().st_size / (1024 * 1024)

    print()
    print(f" Data generation complete!")
    print(f" File: {OUTPUT_FILE}")
    print(f" Size: {file_size_mb:.2f} MB")
    print(f" Total records: {NUM_RECORDS:,}")
    print()
    print("Sample data (first 3 rows):")
    print("-" * 80)

    # Display sample
    with open(OUTPUT_FILE, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            if i < 3:
                print(row)

    print("-" * 80)
    print("✨ Ready for Kafka streaming!")


if __name__ == "__main__":
    main()
