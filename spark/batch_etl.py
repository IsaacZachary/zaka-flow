#!/usr/bin/env python
import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, sum as _sum, count as _count, to_date

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("zakaflow-spark-batch")

def parse_db_url(url):
    parsed = urlparse(url)
    username = parsed.username
    password = parsed.password
    host_port = parsed.netloc.split('@')[-1]
    jdbc_url = f"jdbc:postgresql://{host_port}{parsed.path}"
    return jdbc_url, username, password

def main():
    parser = argparse.ArgumentParser(description="ZakaFlow Batch ETL Spark Job")
    parser.add_argument(
        "--date", 
        type=str, 
        default=(datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d"),
        help="Target date for ETL (YYYY-MM-DD format). Defaults to yesterday."
    )
    args = parser.parse_args()
    
    target_date_str = args.date
    try:
        # Validate format
        datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        logger.error(f"Invalid date format: {target_date_str}. Use YYYY-MM-DD.")
        sys.exit(1)
        
    db_url = os.environ.get("DATABASE_URL", "postgresql://zakaflow_user:zakaflow_pass_2026@postgres/zakaflow")
    jdbc_url, db_user, db_pass = parse_db_url(db_url)
    
    logger.info(f"Starting batch ETL for date: {target_date_str}...")
    
    spark = SparkSession.builder \
        .appName("ZakaFlow-BatchETL") \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.1") \
        .getOrCreate()
        
    # Read raw_events for the targeted date
    # In postgres, raw_events.created_at is a timestamp, we filter by cast as date
    logger.info("Reading raw events from Postgres...")
    raw_events_df = spark.read \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", "zakaflow.raw_events") \
        .option("user", db_user) \
        .option("password", db_pass) \
        .option("driver", "org.postgresql.Driver") \
        .load()
        
    # Filter for target date
    day_events_df = raw_events_df.filter(to_date(col("created_at")) == target_date_str)
    
    total_records = day_events_df.count()
    logger.info(f"Total raw events found for {target_date_str}: {total_records}")
    
    if total_records == 0:
        logger.warning(f"No events found for {target_date_str}. Exiting.")
        spark.stop()
        sys.exit(0)
        
    # Compute product level aggregates
    logger.info("Computing product performance metrics...")
    aggregated_df = day_events_df.groupBy("product_id", "product_name", "product_category") \
        .agg(
            _sum(when(col("event_type") == "VIEW", 1).otherwise(0)).alias("views"),
            _sum(when(col("event_type") == "CLICK", 1).otherwise(0)).alias("clicks"),
            _sum(when(col("event_type") == "PURCHASE", 1).otherwise(0)).alias("purchases"),
            _sum(when(col("event_type") == "PURCHASE", col("product_price")).otherwise(0.0)).alias("revenue")
        )
        
    # Write aggregated metrics to temp table in PostgreSQL
    temp_table = f"temp_batch_etl_{target_date_str.replace('-', '_')}"
    
    aggregated_df.write \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", temp_table) \
        .option("user", db_user) \
        .option("password", db_pass) \
        .option("driver", "org.postgresql.Driver") \
        .mode("overwrite") \
        .save()
        
    # Native UPSERT query
    logger.info("Upserting metrics to product_metrics...")
    db_conn = spark._jvm.java.sql.DriverManager.getConnection(jdbc_url, db_user, db_pass)
    stmt = db_conn.createStatement()
    
    upsert_query = f"""
        INSERT INTO zakaflow.product_metrics (
            metric_date, product_id, product_name, category, 
            total_views, total_clicks, total_purchases, total_revenue, 
            click_through_rate, conversion_rate, updated_at
        )
        SELECT 
            '{target_date_str}'::date, product_id, product_name, product_category,
            views, clicks, purchases, revenue,
            CASE WHEN views > 0 THEN clicks::decimal/views ELSE 0 END,
            CASE WHEN views > 0 THEN purchases::decimal/views ELSE 0 END,
            NOW()
        FROM {temp_table}
        ON CONFLICT (metric_date, product_id) DO UPDATE SET
            total_views = EXCLUDED.total_views,
            total_clicks = EXCLUDED.total_clicks,
            total_purchases = EXCLUDED.total_purchases,
            total_revenue = EXCLUDED.total_revenue,
            click_through_rate = EXCLUDED.click_through_rate,
            conversion_rate = EXCLUDED.conversion_rate,
            updated_at = NOW();
    """
    
    stmt.executeUpdate(upsert_query)
    stmt.executeUpdate(f"DROP TABLE {temp_table}")
    stmt.close()
    
    # Log summary stats
    # 1. Total revenue
    total_revenue = aggregated_df.select(_sum("revenue")).collect()[0][0] or 0.0
    # 2. Total views & purchases for overall conversion rate
    totals = aggregated_df.agg(_sum("views"), _sum("purchases")).collect()[0]
    total_views = totals[0] or 0
    total_purchases = totals[1] or 0
    overall_conv = (total_purchases / total_views * 100) if total_views > 0 else 0.0
    
    # 3. Top 5 products by revenue
    top_products = aggregated_df.orderBy(col("revenue").desc()).limit(5).collect()
    
    logger.info("==================================================")
    logger.info(f"   Batch ETL Summary for {target_date_str}")
    logger.info("==================================================")
    logger.info(f"   Raw Events Processed: {total_records}")
    logger.info(f"   Total Views:          {total_views}")
    logger.info(f"   Total Purchases:      {total_purchases}")
    logger.info(f"   Total Revenue:        ${total_revenue:.2f}")
    logger.info(f"   Conversion Rate:      {overall_conv:.2f}%")
    logger.info("--------------------------------------------------")
    logger.info("   Top 5 Products by Revenue:")
    for idx, row in enumerate(top_products, 1):
        logger.info(f"   {idx}. {row['product_name']} ({row['product_category']}) - ${row['revenue']:.2f}")
    logger.info("==================================================")
    
    db_conn.close()
    spark.stop()
    logger.info("ETL batch job completed successfully.")

if __name__ == "__main__":
    main()
