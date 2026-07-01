#!/usr/bin/env python
import os
import sys
import logging
from urllib.parse import urlparse
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, expr, when, sum as _sum, count as _count, to_date
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("zakaflow-spark-streaming")

def parse_db_url(url):
    """Parse postgresql://user:pass@host:port/dbname into JDBC connection details"""
    parsed = urlparse(url)
    username = parsed.username
    password = parsed.password
    # JDBC format: jdbc:postgresql://host:port/dbname
    host_port = parsed.netloc.split('@')[-1]
    jdbc_url = f"jdbc:postgresql://{host_port}{parsed.path}"
    return jdbc_url, username, password

def main():
    # Environment configs
    kafka_bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    db_url = os.environ.get("DATABASE_URL", "postgresql://zakaflow_user:zakaflow_pass_2026@postgres/zakaflow")
    checkpoint_dir = os.environ.get("CHECKPOINT_DIR", "/tmp/zakaflow-checkpoint")
    
    jdbc_url, db_user, db_pass = parse_db_url(db_url)
    
    logger.info("Initializing Spark Session with Kafka & Postgres packages...")
    spark = SparkSession.builder \
        .appName("ZakaFlow-StreamProcessor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.1") \
        .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")
    
    # Event Schema definition
    event_schema = StructType([
        StructField("event_id", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("product_id", StringType(), True),
        StructField("product_name", StringType(), True),
        StructField("product_category", StringType(), True),
        StructField("product_price", DoubleType(), True),
        StructField("user_id", StringType(), True),
        StructField("location", StringType(), True),
        StructField("session_id", StringType(), True),
        StructField("timestamp", StringType(), True)
    ])
    
    logger.info(f"Subscribing to Kafka bootstrap={kafka_bootstrap} topics...")
    # Read stream from Kafka
    kafka_stream = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap) \
        .option("subscribe", "product-events,product-clicks,product-purchases") \
        .option("startingOffsets", "latest") \
        .load()
        
    # Parse the message value from binary JSON
    parsed_stream = kafka_stream.select(
        col("value").cast("string").alias("json_val"),
        col("offset").alias("kafka_offset"),
        col("partition").alias("kafka_partition"),
        col("topic").alias("kafka_topic")
    ).select(
        from_json(col("json_val"), event_schema).alias("data"),
        "kafka_offset",
        "kafka_partition",
        "kafka_topic"
    ).select(
        col("data.event_id").alias("event_id"),
        col("data.event_type").alias("event_type"),
        col("data.product_id").alias("product_id"),
        col("data.product_name").alias("product_name"),
        col("data.product_category").alias("product_category"),
        col("data.product_price").alias("product_price"),
        col("data.user_id").alias("user_id"),
        col("data.location").alias("location"),
        col("data.session_id").alias("session_id"),
        col("data.timestamp").cast(TimestampType()).alias("created_at"),
        "kafka_offset",
        "kafka_partition",
        "kafka_topic"
    )

    def write_to_postgres(batch_df, batch_id):
        """
        ForeachBatch processor that:
        1. Writes raw events to zakaflow.raw_events
        2. Aggregates micro-batch and upserts to zakaflow.product_metrics
        """
        if batch_df.isEmpty():
            return
            
        logger.info(f"Processing batch {batch_id} with {batch_df.count()} records...")
        
        # 1. Write Raw Events
        # Drop duplicates in this batch if any
        raw_events_df = batch_df.dropDuplicates(["event_id"])
        
        raw_events_df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "zakaflow.raw_events") \
            .option("user", db_user) \
            .option("password", db_pass) \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()
            
        # 2. Compute and Upsert Product Metrics for this Batch
        # Group by product and date
        aggregated_df = batch_df.withColumn("metric_date", to_date(col("created_at"))) \
            .groupBy("metric_date", "product_id", "product_name", "product_category") \
            .agg(
                _sum(when(col("event_type") == "VIEW", 1).otherwise(0)).alias("views"),
                _sum(when(col("event_type") == "CLICK", 1).otherwise(0)).alias("clicks"),
                _sum(when(col("event_type") == "PURCHASE", 1).otherwise(0)).alias("purchases"),
                _sum(when(col("event_type") == "PURCHASE", col("product_price")).otherwise(0.0)).alias("revenue")
            )
            
        # Create temp table in postgres database to perform native upsert
        temp_table = f"temp_batch_metrics_{batch_id}"
        
        aggregated_df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", temp_table) \
            .option("user", db_user) \
            .option("password", db_pass) \
            .option("driver", "org.postgresql.Driver") \
            .mode("overwrite") \
            .save()
            
        # Execute PostgreSQL native UPSERT using connection
        # Connect to DB via JDBC driver manager from python (using native pg connection helper isn't simple in Spark executor/driver context,
        # but we can do it via py4j gateway to execute executeUpdate).
        db_conn = spark._jvm.java.sql.DriverManager.getConnection(jdbc_url, db_user, db_pass)
        stmt = db_conn.createStatement()
        
        upsert_query = f"""
            INSERT INTO zakaflow.product_metrics (
                metric_date, product_id, product_name, category, 
                total_views, total_clicks, total_purchases, total_revenue, 
                click_through_rate, conversion_rate, updated_at
            )
            SELECT 
                metric_date, product_id, product_name, product_category,
                views, clicks, purchases, revenue,
                CASE WHEN views > 0 THEN clicks::decimal/views ELSE 0 END,
                CASE WHEN views > 0 THEN purchases::decimal/views ELSE 0 END,
                NOW()
            FROM {temp_table}
            ON CONFLICT (metric_date, product_id) DO UPDATE SET
                total_views = zakaflow.product_metrics.total_views + EXCLUDED.total_views,
                total_clicks = zakaflow.product_metrics.total_clicks + EXCLUDED.total_clicks,
                total_purchases = zakaflow.product_metrics.total_purchases + EXCLUDED.total_purchases,
                total_revenue = zakaflow.product_metrics.total_revenue + EXCLUDED.total_revenue,
                click_through_rate = CASE 
                    WHEN (zakaflow.product_metrics.total_views + EXCLUDED.total_views) > 0 
                    THEN (zakaflow.product_metrics.total_clicks + EXCLUDED.total_clicks)::decimal / (zakaflow.product_metrics.total_views + EXCLUDED.total_views)
                    ELSE 0 
                END,
                conversion_rate = CASE 
                    WHEN (zakaflow.product_metrics.total_views + EXCLUDED.total_views) > 0 
                    THEN (zakaflow.product_metrics.total_purchases + EXCLUDED.total_purchases)::decimal / (zakaflow.product_metrics.total_views + EXCLUDED.total_views)
                    ELSE 0 
                END,
                updated_at = NOW();
        """
        
        stmt.executeUpdate(upsert_query)
        stmt.executeUpdate(f"DROP TABLE {temp_table}")
        stmt.close()
        db_conn.close()
        logger.info(f"Successfully processed and upserted batch {batch_id}.")

    # Start the streaming query
    query = parsed_stream.writeStream \
        .foreachBatch(write_to_postgres) \
        .option("checkpointLocation", checkpoint_dir) \
        .trigger(processingTime="10 seconds") \
        .start()
        
    logger.info("Structured Streaming Query started. Awaiting termination...")
    query.awaitTermination()

if __name__ == "__main__":
    main()
