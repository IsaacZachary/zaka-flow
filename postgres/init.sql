-- =============================================================
-- ZakaFlow – PostgreSQL Initialisation Script
-- Runs automatically on first container start via
-- /docker-entrypoint-initdb.d/init.sql
-- =============================================================

-- ─────────────────────────────────────────────
-- SCHEMA
-- ─────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS zakaflow;

-- ─────────────────────────────────────────────
-- TABLE: zakaflow.raw_events
-- Stores every event consumed from Kafka before
-- any transformation or aggregation.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zakaflow.raw_events (
    id                 SERIAL          PRIMARY KEY,
    event_id           VARCHAR(36)     UNIQUE NOT NULL,
    event_type         VARCHAR(20)     NOT NULL,
    product_id         VARCHAR(50),
    product_name       VARCHAR(200),
    product_category   VARCHAR(100),
    product_price      DECIMAL(10, 2),
    user_id            VARCHAR(50),
    location           VARCHAR(100),
    session_id         VARCHAR(36),
    created_at         TIMESTAMP       DEFAULT NOW(),
    kafka_offset       BIGINT,
    kafka_partition    INT,
    kafka_topic        VARCHAR(100)
);

-- ─────────────────────────────────────────────
-- TABLE: zakaflow.product_metrics
-- Daily aggregated metrics per product, written
-- by Spark streaming / batch jobs.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zakaflow.product_metrics (
    id                  SERIAL          PRIMARY KEY,
    metric_date         DATE            NOT NULL,
    product_id          VARCHAR(50),
    product_name        VARCHAR(200),
    category            VARCHAR(100),
    total_views         INT             DEFAULT 0,
    total_clicks        INT             DEFAULT 0,
    total_purchases     INT             DEFAULT 0,
    total_revenue       DECIMAL(12, 2)  DEFAULT 0,
    click_through_rate  DECIMAL(5, 4),
    conversion_rate     DECIMAL(5, 4),
    updated_at          TIMESTAMP       DEFAULT NOW(),
    UNIQUE (metric_date, product_id)
);

-- ─────────────────────────────────────────────
-- TABLE: zakaflow.pipeline_runs
-- Audit log written by Airflow DAGs to track
-- every pipeline execution.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zakaflow.pipeline_runs (
    id                  SERIAL      PRIMARY KEY,
    run_id              VARCHAR(36),
    dag_id              VARCHAR(200),
    status              VARCHAR(50),
    started_at          TIMESTAMP,
    finished_at         TIMESTAMP,
    records_processed   BIGINT,
    error_message       TEXT
);

-- ─────────────────────────────────────────────
-- TABLE: zakaflow.kafka_topic_stats
-- Periodic snapshot of Kafka topic message counts
-- recorded by a monitoring job.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zakaflow.kafka_topic_stats (
    id             SERIAL      PRIMARY KEY,
    topic_name     VARCHAR(100),
    message_count  BIGINT      DEFAULT 0,
    last_offset    BIGINT      DEFAULT 0,
    recorded_at    TIMESTAMP   DEFAULT NOW()
);

-- ─────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────

-- raw_events – fast lookup by event type (view / click / purchase)
CREATE INDEX IF NOT EXISTS idx_raw_events_event_type
    ON zakaflow.raw_events (event_type);

-- raw_events – range queries on ingestion time
CREATE INDEX IF NOT EXISTS idx_raw_events_created_at
    ON zakaflow.raw_events (created_at);

-- raw_events – filter / join on product
CREATE INDEX IF NOT EXISTS idx_raw_events_product_id
    ON zakaflow.raw_events (product_id);

-- product_metrics – most queries filter or partition by date
CREATE INDEX IF NOT EXISTS idx_product_metrics_metric_date
    ON zakaflow.product_metrics (metric_date);

-- ─────────────────────────────────────────────
-- SEED DATA: zakaflow.pipeline_runs
-- Representative rows so dashboards and tests
-- have data immediately after first boot.
-- ─────────────────────────────────────────────
INSERT INTO zakaflow.pipeline_runs
    (run_id, dag_id, status, started_at, finished_at, records_processed, error_message)
VALUES
    (
        'a1b2c3d4-0001-4e5f-9a8b-111111111111',
        'zakaflow_kafka_ingest_dag',
        'success',
        NOW() - INTERVAL '3 days' + INTERVAL '0 hours',
        NOW() - INTERVAL '3 days' + INTERVAL '0 hours 4 minutes 12 seconds',
        82450,
        NULL
    ),
    (
        'a1b2c3d4-0002-4e5f-9a8b-222222222222',
        'zakaflow_spark_transform_dag',
        'success',
        NOW() - INTERVAL '3 days' + INTERVAL '0 hours 5 minutes',
        NOW() - INTERVAL '3 days' + INTERVAL '0 hours 18 minutes 33 seconds',
        82450,
        NULL
    ),
    (
        'a1b2c3d4-0003-4e5f-9a8b-333333333333',
        'zakaflow_metrics_aggregate_dag',
        'success',
        NOW() - INTERVAL '3 days' + INTERVAL '0 hours 20 minutes',
        NOW() - INTERVAL '3 days' + INTERVAL '0 hours 22 minutes 7 seconds',
        1024,
        NULL
    ),
    (
        'b2c3d4e5-0004-4e5f-9a8b-444444444444',
        'zakaflow_kafka_ingest_dag',
        'success',
        NOW() - INTERVAL '2 days' + INTERVAL '0 hours',
        NOW() - INTERVAL '2 days' + INTERVAL '0 hours 3 minutes 58 seconds',
        91200,
        NULL
    ),
    (
        'b2c3d4e5-0005-4e5f-9a8b-555555555555',
        'zakaflow_spark_transform_dag',
        'success',
        NOW() - INTERVAL '2 days' + INTERVAL '0 hours 5 minutes',
        NOW() - INTERVAL '2 days' + INTERVAL '0 hours 19 minutes 45 seconds',
        91200,
        NULL
    ),
    (
        'b2c3d4e5-0006-4e5f-9a8b-666666666666',
        'zakaflow_metrics_aggregate_dag',
        'success',
        NOW() - INTERVAL '2 days' + INTERVAL '0 hours 21 minutes',
        NOW() - INTERVAL '2 days' + INTERVAL '0 hours 23 minutes 10 seconds',
        1156,
        NULL
    ),
    (
        'c3d4e5f6-0007-4e5f-9a8b-777777777777',
        'zakaflow_kafka_ingest_dag',
        'failed',
        NOW() - INTERVAL '1 day' + INTERVAL '0 hours',
        NOW() - INTERVAL '1 day' + INTERVAL '0 hours 1 minute 5 seconds',
        0,
        'KafkaTimeoutException: Failed to connect to broker kafka:9092 after 60 s'
    ),
    (
        'c3d4e5f6-0008-4e5f-9a8b-888888888888',
        'zakaflow_kafka_ingest_dag',
        'success',
        NOW() - INTERVAL '1 day' + INTERVAL '1 hour',
        NOW() - INTERVAL '1 day' + INTERVAL '1 hour 4 minutes 30 seconds',
        78900,
        NULL
    ),
    (
        'c3d4e5f6-0009-4e5f-9a8b-999999999999',
        'zakaflow_spark_transform_dag',
        'success',
        NOW() - INTERVAL '1 day' + INTERVAL '1 hour 5 minutes',
        NOW() - INTERVAL '1 day' + INTERVAL '1 hour 17 minutes 52 seconds',
        78900,
        NULL
    ),
    (
        'c3d4e5f6-0010-4e5f-9a8b-aaaaaaaaaaaa',
        'zakaflow_metrics_aggregate_dag',
        'success',
        NOW() - INTERVAL '1 day' + INTERVAL '1 hour 19 minutes',
        NOW() - INTERVAL '1 day' + INTERVAL '1 hour 21 minutes 18 seconds',
        998,
        NULL
    ),
    (
        'd4e5f6a7-0011-4e5f-9a8b-bbbbbbbbbbbb',
        'zakaflow_kafka_ingest_dag',
        'success',
        NOW() - INTERVAL '4 hours',
        NOW() - INTERVAL '4 hours' + INTERVAL '4 minutes 2 seconds',
        103750,
        NULL
    ),
    (
        'd4e5f6a7-0012-4e5f-9a8b-cccccccccccc',
        'zakaflow_spark_transform_dag',
        'success',
        NOW() - INTERVAL '4 hours' + INTERVAL '5 minutes',
        NOW() - INTERVAL '4 hours' + INTERVAL '21 minutes 44 seconds',
        103750,
        NULL
    ),
    (
        'd4e5f6a7-0013-4e5f-9a8b-dddddddddddd',
        'zakaflow_metrics_aggregate_dag',
        'success',
        NOW() - INTERVAL '4 hours' + INTERVAL '23 minutes',
        NOW() - INTERVAL '4 hours' + INTERVAL '25 minutes 5 seconds',
        1380,
        NULL
    );

-- ─────────────────────────────────────────────
-- SEED DATA: zakaflow.kafka_topic_stats
-- ─────────────────────────────────────────────
INSERT INTO zakaflow.kafka_topic_stats
    (topic_name, message_count, last_offset, recorded_at)
VALUES
    ('product-events',    356300, 356299, NOW() - INTERVAL '4 hours' + INTERVAL '26 minutes'),
    ('product-clicks',    142120, 142119, NOW() - INTERVAL '4 hours' + INTERVAL '26 minutes'),
    ('product-purchases',  18440,  18439, NOW() - INTERVAL '4 hours' + INTERVAL '26 minutes');

-- ─────────────────────────────────────────────
-- SEED DATA: zakaflow.product_metrics
-- Three days of sample metrics for five products
-- ─────────────────────────────────────────────
INSERT INTO zakaflow.product_metrics
    (metric_date, product_id, product_name, category,
     total_views, total_clicks, total_purchases, total_revenue,
     click_through_rate, conversion_rate, updated_at)
VALUES
    -- Day -3
    (CURRENT_DATE - 3, 'PROD-001', 'Wireless Noise-Cancelling Headphones', 'Electronics',  4200, 840,  62, 9610.38, 0.2000, 0.0738, NOW() - INTERVAL '3 days' + INTERVAL '23 minutes'),
    (CURRENT_DATE - 3, 'PROD-002', 'Running Shoes Pro X',                  'Footwear',     3100, 527,  98, 7742.02, 0.1700, 0.1859, NOW() - INTERVAL '3 days' + INTERVAL '23 minutes'),
    (CURRENT_DATE - 3, 'PROD-003', 'Organic Green Tea (100 bags)',         'Groceries',    1850, 296,  74,  885.26, 0.1600, 0.2500, NOW() - INTERVAL '3 days' + INTERVAL '23 minutes'),
    (CURRENT_DATE - 3, 'PROD-004', 'Ergonomic Office Chair',              'Furniture',    2700, 486, 109,43164.91, 0.1800, 0.2243, NOW() - INTERVAL '3 days' + INTERVAL '23 minutes'),
    (CURRENT_DATE - 3, 'PROD-005', 'Smart Fitness Tracker Band',          'Electronics',  5100,1122,  88, 5278.72, 0.2200, 0.0784, NOW() - INTERVAL '3 days' + INTERVAL '23 minutes'),
    -- Day -2
    (CURRENT_DATE - 2, 'PROD-001', 'Wireless Noise-Cancelling Headphones', 'Electronics',  4520, 950,  71,11006.29, 0.2102, 0.0747, NOW() - INTERVAL '2 days' + INTERVAL '23 minutes'),
    (CURRENT_DATE - 2, 'PROD-002', 'Running Shoes Pro X',                  'Footwear',     3380, 608, 112, 8853.28, 0.1799, 0.1842, NOW() - INTERVAL '2 days' + INTERVAL '23 minutes'),
    (CURRENT_DATE - 2, 'PROD-003', 'Organic Green Tea (100 bags)',         'Groceries',    1920, 326,  82,  979.78, 0.1698, 0.2515, NOW() - INTERVAL '2 days' + INTERVAL '23 minutes'),
    (CURRENT_DATE - 2, 'PROD-004', 'Ergonomic Office Chair',              'Furniture',    2850, 541, 118,46757.82, 0.1898, 0.2181, NOW() - INTERVAL '2 days' + INTERVAL '23 minutes'),
    (CURRENT_DATE - 2, 'PROD-005', 'Smart Fitness Tracker Band',          'Electronics',  5340,1228,  94, 5637.26, 0.2300, 0.0766, NOW() - INTERVAL '2 days' + INTERVAL '23 minutes'),
    -- Day -1
    (CURRENT_DATE - 1, 'PROD-001', 'Wireless Noise-Cancelling Headphones', 'Electronics',  4780,1050,  79,12249.21, 0.2196, 0.0752, NOW() - INTERVAL '1 day'  + INTERVAL '22 minutes'),
    (CURRENT_DATE - 1, 'PROD-002', 'Running Shoes Pro X',                  'Footwear',     3620, 688, 129,10203.71, 0.1900, 0.1876, NOW() - INTERVAL '1 day'  + INTERVAL '22 minutes'),
    (CURRENT_DATE - 1, 'PROD-003', 'Organic Green Tea (100 bags)',         'Groceries',    2010, 361,  90, 1075.50, 0.1796, 0.2493, NOW() - INTERVAL '1 day'  + INTERVAL '22 minutes'),
    (CURRENT_DATE - 1, 'PROD-004', 'Ergonomic Office Chair',              'Furniture',    2940, 588, 124,49157.76, 0.2000, 0.2109, NOW() - INTERVAL '1 day'  + INTERVAL '22 minutes'),
    (CURRENT_DATE - 1, 'PROD-005', 'Smart Fitness Tracker Band',          'Electronics',  5590,1285, 103, 6175.89, 0.2299, 0.0802, NOW() - INTERVAL '1 day'  + INTERVAL '22 minutes');

-- ─────────────────────────────────────────────
-- Confirm completion
-- ─────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE 'ZakaFlow schema initialised successfully at %', NOW();
END $$;
