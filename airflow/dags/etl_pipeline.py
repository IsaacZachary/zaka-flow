import os
import logging
from datetime import datetime, timedelta
import psycopg2
from kafka import KafkaAdminClient
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zakaflow-airflow-dag")

# Env configurations
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://zakaflow_user:zakaflow_pass_2026@postgres/zakaflow")

default_args = {
    'owner': 'zakaflow',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False
}

def check_kafka_health_fn():
    logger.info(f"Checking Kafka health on {KAFKA_BOOTSTRAP_SERVERS}...")
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
            request_timeout_ms=5000
        )
        topics = admin.list_topics()
        logger.info(f"Kafka is healthy. Available topics: {topics}")
        admin.close()
    except Exception as e:
        logger.error(f"Kafka health check failed: {e}")
        raise

def check_db_health_fn():
    logger.info("Checking database connection...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        
        # Check if raw_events table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'zakaflow' AND table_name = 'raw_events'
            );
        """)
        exists = cursor.fetchone()[0]
        if not exists:
            raise ValueError("Table 'zakaflow.raw_events' does not exist in database!")
            
        logger.info("Database is healthy, connection established, schema verified.")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise

def compute_funnel_metrics_fn(ds, **kwargs):
    logger.info(f"Computing daily conversion funnel metrics for {ds}...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Create funnel metrics table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zakaflow.funnel_metrics (
                metric_date DATE PRIMARY KEY,
                total_views INT DEFAULT 0,
                total_clicks INT DEFAULT 0,
                total_purchases INT DEFAULT 0,
                view_to_click_pct DECIMAL(5,2),
                click_to_purchase_pct DECIMAL(5,2),
                overall_conversion_pct DECIMAL(5,2),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Fetch views, clicks, purchases
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN event_type = 'VIEW' THEN 1 ELSE 0 END), 0) as views,
                COALESCE(SUM(CASE WHEN event_type = 'CLICK' THEN 1 ELSE 0 END), 0) as clicks,
                COALESCE(SUM(CASE WHEN event_type = 'PURCHASE' THEN 1 ELSE 0 END), 0) as purchases
            FROM zakaflow.raw_events
            WHERE DATE(created_at) = %s::date;
        """, (ds,))
        
        row = cursor.fetchone()
        views = row[0] or 0
        clicks = row[1] or 0
        purchases = row[2] or 0
        
        v2c = (clicks / views * 100) if views > 0 else 0.0
        c2p = (purchases / clicks * 100) if clicks > 0 else 0.0
        conv = (purchases / views * 100) if views > 0 else 0.0
        
        logger.info(f"Funnel Stats for {ds}: Views={views}, Clicks={clicks}, Purchases={purchases}")
        
        cursor.execute("""
            INSERT INTO zakaflow.funnel_metrics (
                metric_date, total_views, total_clicks, total_purchases,
                view_to_click_pct, click_to_purchase_pct, overall_conversion_pct, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (metric_date) DO UPDATE SET
                total_views = EXCLUDED.total_views,
                total_clicks = EXCLUDED.total_clicks,
                total_purchases = EXCLUDED.total_purchases,
                view_to_click_pct = EXCLUDED.view_to_click_pct,
                click_to_purchase_pct = EXCLUDED.click_to_purchase_pct,
                overall_conversion_pct = EXCLUDED.overall_conversion_pct,
                updated_at = NOW();
        """, (ds, views, clicks, purchases, v2c, c2p, conv))
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Successfully calculated and stored funnel metrics.")
    except Exception as e:
        logger.error(f"Error computing funnel metrics: {e}")
        raise

def cleanup_old_events_fn(**kwargs):
    logger.info("Running raw event table data retention pruning (older than 90 days)...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM zakaflow.raw_events WHERE created_at < NOW() - INTERVAL '90 days';")
        deleted = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Successfully pruned {deleted} old raw events from database.")
    except Exception as e:
        logger.error(f"Pruning job failed: {e}")
        raise

def notify_success_fn(ds, **kwargs):
    logger.info(f"🚀 ZakaFlow pipeline run for {ds} finished successfully!")

with DAG(
    dag_id='zakaflow_etl_pipeline',
    default_args=default_args,
    description='ZakaFlow main batch ingestion & aggregation ETL orchestration pipeline',
    schedule_interval='@hourly',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['zakaflow', 'etl', 'production']
) as dag:

    check_kafka = PythonOperator(
        task_id='check_kafka_health',
        python_callable=check_kafka_health_fn
    )

    check_db = PythonOperator(
        task_id='check_db_health',
        python_callable=check_db_health_fn
    )

    # Spark batch execution
    run_spark_batch = BashOperator(
        task_id='run_spark_batch',
        bash_command=(
            "spark-submit "
            "--master spark://spark-master:7077 "
            "--packages org.postgresql:postgresql:42.7.1 "
            "/opt/airflow/spark/batch_etl.py "
            "--date {{ ds }}"
        ),
        env={
            'DATABASE_URL': DATABASE_URL,
            'SPARK_HOME': '/usr/local/spark' # local environment config
        }
    )

    # dbt models compilation and run
    # dbt profile is set up to read from env vars
    run_dbt_models = BashOperator(
        task_id='run_dbt_models',
        bash_command=(
            "cd /opt/airflow/dbt && "
            "dbt run --profiles-dir . --project-dir . --target dev"
        ),
        env={
            'DBT_HOST': 'postgres',
            'DBT_USER': 'zakaflow_user',
            'DBT_PASSWORD': 'zakaflow_pass_2026',
            'DBT_DBNAME': 'zakaflow'
        }
    )

    compute_funnel = PythonOperator(
        task_id='compute_funnel_metrics',
        python_callable=compute_funnel_metrics_fn
    )

    cleanup_events = PythonOperator(
        task_id='cleanup_old_events',
        python_callable=cleanup_old_events_fn
    )

    notify_success = PythonOperator(
        task_id='notify_success',
        python_callable=notify_success_fn
    )

    # DAG Dependency Flow
    [check_kafka, check_db] >> run_spark_batch >> run_dbt_models >> compute_funnel >> cleanup_events >> notify_success
