{{ config(materialized='table') }}

WITH stg_events AS (
    SELECT * 
    FROM {{ ref('stg_events') }}
)

SELECT
    event_date,
    COUNT(event_id) AS total_events,
    SUM(is_view) AS total_views,
    SUM(is_click) AS total_clicks,
    SUM(is_purchase) AS total_purchases,
    SUM(CASE WHEN is_purchase = 1 THEN product_price ELSE 0.0 END) AS total_revenue,
    
    -- Funnel rates
    CASE 
        WHEN SUM(is_view) > 0 THEN ROUND(SUM(is_click)::DECIMAL / SUM(is_view) * 100, 2)
        ELSE 0.0
    END AS view_to_click_rate,
    
    CASE 
        WHEN SUM(is_click) > 0 THEN ROUND(SUM(is_purchase)::DECIMAL / SUM(is_click) * 100, 2)
        ELSE 0.0
    END AS click_to_purchase_rate,
    
    CASE 
        WHEN SUM(is_view) > 0 THEN ROUND(SUM(is_purchase)::DECIMAL / SUM(is_view) * 100, 2)
        ELSE 0.0
    END AS overall_conversion_rate

FROM stg_events
GROUP BY event_date
ORDER BY event_date DESC
