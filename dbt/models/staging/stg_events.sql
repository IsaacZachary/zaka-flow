{{ config(materialized='view') }}

WITH source_events AS (
    SELECT * 
    FROM {{ source('zakaflow', 'raw_events') }}
)

SELECT
    event_id,
    event_type,
    product_id,
    product_name,
    product_category,
    product_price,
    user_id,
    location,
    session_id,
    created_at AS event_timestamp,
    DATE(created_at) AS event_date,
    EXTRACT(HOUR FROM created_at) AS event_hour,
    
    -- Helper booleans for aggregates
    CASE WHEN event_type = 'VIEW' THEN 1 ELSE 0 END AS is_view,
    CASE WHEN event_type = 'CLICK' THEN 1 ELSE 0 END AS is_click,
    CASE WHEN event_type = 'PURCHASE' THEN 1 ELSE 0 END AS is_purchase

FROM source_events
WHERE event_id IS NOT NULL
