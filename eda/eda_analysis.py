#!/usr/bin/env python3
"""
PySpark EDA for Transaction Data
Optimized for OpenShift with Hadoop authentication disabled
"""

import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as spark_sum, count, avg

print("="*80)
print(" PySpark EDA Job - Transaction Analysis")
print("="*80)

# Verify input file exists
INPUT_FILE = "/data/received_transactions.csv"
if not os.path.exists(INPUT_FILE):
    print(f"ERROR: Input file not found: {INPUT_FILE}")
    sys.exit(1)

print(f"\nInput file found: {INPUT_FILE}")
print(f"File size: {os.path.getsize(INPUT_FILE) / 1024 / 1024:.2f} MB")

# Create SparkSession with security disabled
print("\nInitializing Spark Session...")
spark = (SparkSession.builder
    .appName("Transaction EDA - OpenShift")
    .master("local[2]")
    .config("spark.driver.host", "localhost")
    .config("spark.driver.bindAddress", "0.0.0.0")
    .config("spark.ui.enabled", "false")
    .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse")
    .config("spark.local.dir", "/tmp")
    # Hadoop security bypass configurations
    .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.RawLocalFileSystem")
    .config("spark.hadoop.hadoop.security.authentication", "simple")
    .config("spark.hadoop.hadoop.security.authorization", "false")
    .config("spark.authenticate", "false")
    .config("spark.hadoop.fs.defaultFS", "file:///")
    # Use pre-configured Hadoop config
    .config("spark.hadoop.hadoop.conf.dir", "/opt/spark/conf/hadoop-conf")
    .getOrCreate())

spark.sparkContext.setLogLevel("ERROR")
print("Spark Session initialized successfully!")

# Load data
print(f"\nLoading data from {INPUT_FILE}...")
try:
    df = spark.read.csv(INPUT_FILE, header=True, inferSchema=True)
    total_records = df.count()
    print(f"Data loaded successfully: {total_records:,} records")
    print(f"Schema:")
    df.printSchema()
except Exception as e:
    print(f"ERROR loading data: {e}")
    spark.stop()
    sys.exit(1)

# Analysis 1: Sales by Product Category
print("\n" + "="*80)
print(" ANALYSIS 1: Sales by Product Category")
print("="*80)
category_sales = (df.groupBy("product_category")
    .agg(
        count("transaction_id").alias("num_transactions"),
        spark_sum("total_amount").alias("total_revenue")
    )
    .orderBy(col("total_revenue").desc()))

category_pd = category_sales.toPandas()
print(category_pd.to_string(index=False))

# Analysis 2: Payment Methods
print("\n" + "="*80)
print(" ANALYSIS 2: Payment Method Distribution")
print("="*80)
payment_analysis = (df.groupBy("payment_method")
    .agg(count("transaction_id").alias("num_transactions"))
    .orderBy(col("num_transactions").desc()))

payment_pd = payment_analysis.toPandas()
print(payment_pd.to_string(index=False))

# Analysis 3: Top 10 Cities by Revenue
print("\n" + "="*80)
print(" ANALYSIS 3: Top 10 Cities by Revenue")
print("="*80)
city_revenue = (df.groupBy("city")
    .agg(
        count("transaction_id").alias("num_transactions"),
        spark_sum("total_amount").alias("total_revenue")
    )
    .orderBy(col("total_revenue").desc())
    .limit(10))

city_pd = city_revenue.toPandas()
print(city_pd.to_string(index=False))

# Generate visualizations
print("\n" + "="*80)
print(" GENERATING VISUALIZATIONS")
print("="*80)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Plot 1: Revenue by Category
plt.figure(figsize=(12, 6))
cat_sorted = category_pd.sort_values('total_revenue', ascending=False)
plt.bar(cat_sorted['product_category'], cat_sorted['total_revenue'], color='teal')
plt.xlabel('Product Category')
plt.ylabel('Total Revenue ($)')
plt.title('Total Revenue by Product Category')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plot1 = '/data/plot_revenue_by_category.png'
plt.savefig(plot1, dpi=150, bbox_inches='tight')
plt.close()
print(f"✓ Saved: {plot1}")

# Plot 2: Payment Methods
plt.figure(figsize=(10, 8))
plt.pie(payment_pd['num_transactions'],
        labels=payment_pd['payment_method'],
        autopct='%1.1f%%',
        startangle=90)
plt.title('Payment Method Distribution')
plt.tight_layout()
plot2 = '/data/plot_payment_methods.png'
plt.savefig(plot2, dpi=150)
plt.close()
print(f"✓ Saved: {plot2}")

# Plot 3: Top 10 Cities
plt.figure(figsize=(12, 8))
plt.barh(city_pd['city'], city_pd['total_revenue'], color='coral')
plt.xlabel('Total Revenue ($)')
plt.ylabel('City')
plt.title('Top 10 Cities by Revenue')
plt.tight_layout()
plot3 = '/data/plot_top_cities.png'
plt.savefig(plot3, dpi=150, bbox_inches='tight')
plt.close()
print(f"✓ Saved: {plot3}")

# Calculate summary statistics
total_revenue = df.agg(spark_sum("total_amount")).collect()[0][0] or 0.0
avg_transaction = df.agg(avg("total_amount")).collect()[0][0] or 0.0

print("\n" + "="*80)
print(" ANALYSIS SUMMARY")
print("="*80)
print(f" Total Transactions : {total_records:,}")
print(f" Total Revenue      : ${total_revenue:,.2f}")
print(f" Average Transaction: ${avg_transaction:,.2f}")
print("="*80)
print(" EDA Complete! All outputs saved to /data/")

# Cleanup
spark.stop()
print("Spark session stopped. Job completed successfully.")
