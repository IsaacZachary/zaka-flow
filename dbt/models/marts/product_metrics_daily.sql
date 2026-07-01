{{ config(materialized='table') }}

WITH stg_events AS (
    SELECT * 
    FROM {{ ref('stg_events') }}
)

SELECT
    event_date,
    product_id,
    product_name,
    product_category AS category,
    SUM(is_view) AS total_views,
    SUM(is_click) AS total_clicks,
    SUM(is_purchase) AS total_purchases,
    SUM(CASE WHEN is_purchase = 1 THEN product_price ELSE 0.0 END) AS total_revenue,
    
    -- Click through rate (clicks / views)
    CASE 
        WHEN SUM(is_view) > 0 THEN ROUND(SUM(is_click)::DECIMAL / SUM(is_view), 4)
        ELSE 0.0 
    END AS click_through_rate,
    
    -- Conversion rate (purchases / views)
    CASE 
        WHEN SUM(is_view) > 0 THEN ROUND(SUM(is_purchase)::DECIMAL / SUM(is_view), 4)
        ELSE 0.0
    END AS conversion_rate

FROM stg_events
GROUP BY event_date, product_id, product_name, product_category
ORDER BY event_date DESC, total_revenue DESC
