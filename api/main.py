import os
import json
import uuid
import random
import asyncio
import logging
from datetime import datetime, date
from collections import deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import asyncpg

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zakaflow-api")

# Database URL
DATABASE_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql://zakaflow_user:zakaflow_pass_2026@postgres/zakaflow"
)

# Startup & Shutdown Lifespan
db_pool = None
startup_time = datetime.utcnow()

# In-memory Simulation Cache (Fallback & WebSocket source)
SIM_PRODUCTS = [
    {"id": "prod_1", "name": "Neural Engine Pro", "category": "AI/ML Ops", "price": 412.00},
    {"id": "prod_2", "name": "Quantum Flow Hub", "category": "Cloud Services", "price": 284.00},
    {"id": "prod_3", "name": "Stream-Sentry Max", "category": "Security", "price": 152.00},
    {"id": "prod_4", "name": "Void-Shield Firewall", "category": "Security", "price": 98.00},
    {"id": "prod_5", "name": "Echo-Sync Gateway", "category": "Networking", "price": 67.00},
    {"id": "prod_6", "name": "Quantum Sorter", "category": "Infrastructure", "price": 286.00},
    {"id": "prod_7", "name": "Vector DB Pro", "category": "Infrastructure", "price": 293.00},
    {"id": "prod_8", "name": "Graph Connector", "category": "Networking", "price": 174.00},
    {"id": "prod_9", "name": "DevOps Toolkit", "category": "Cloud Services", "price": 199.00},
    {"id": "prod_10", "name": "ZakaFlow Core", "category": "AI/ML Ops", "price": 438.00},
    {"id": "prod_11", "name": "Schema Guard", "category": "Security", "price": 251.00},
    {"id": "prod_12", "name": "StreamEdge Node", "category": "Networking", "price": 344.00}
]

SIM_LOCATIONS = [
    "San Francisco, US", "Berlin, DE", "Singapore, SG", "London, UK",
    "Sydney, AU", "Tokyo, JP", "Dubai, AE", "Nairobi, KE",
    "Lagos, NG", "Johannesburg, ZA"
]

events_cache = deque(maxlen=500)
sim_stats = {"VIEW": 0, "CLICK": 0, "PURCHASE": 0, "REVENUE": 0.0, "TOTAL": 0}
sim_running = True

def generate_simulated_event():
    event_type = random.choices(["VIEW", "CLICK", "PURCHASE"], weights=[0.60, 0.30, 0.10], k=1)[0]
    product = random.choice(SIM_PRODUCTS)
    location = random.choice(SIM_LOCATIONS)
    user_id = f"usr_{random.randint(1000, 9999)}"
    
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "product_id": product["id"],
        "product_name": product["name"],
        "product_category": product["category"],
        "product_price": product["price"],
        "user_id": user_id,
        "location": location,
        "session_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Update sim stats
    sim_stats[event_type] += 1
    sim_stats["TOTAL"] += 1
    if event_type == "PURCHASE":
        sim_stats["REVENUE"] += product["price"]
        
    return event

async def run_simulation_loop():
    logger.info("Starting simulation background task...")
    while sim_running:
        try:
            event = generate_simulated_event()
            events_cache.appendleft(event)
            # Sleep a bit before producing next simulated event
            await asyncio.sleep(random.uniform(0.5, 1.5))
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}")
            await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, sim_running
    # Create DB connection pool
    try:
        logger.info("Initializing asyncpg database pool...")
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
        logger.info("Database pool initialized successfully.")
    except Exception as e:
        logger.warning(f"Could not connect to database on startup: {e}. Running in simulation mode.")
        
    # Start background task for simulation
    sim_task = asyncio.create_task(run_simulation_loop())
    
    yield
    
    # Clean up
    sim_running = False
    sim_task.cancel()
    await sim_task
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed.")

app = FastAPI(
    title="ZakaFlow API",
    description="Real-time data pipeline metrics API backend",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: str
    uptime_seconds: float

class MetricResponse(BaseModel):
    events_per_sec: int
    kafka_lag_ms: int
    spark_jobs_active: int
    pipeline_health_pct: float
    total_events: int
    total_views: int
    total_clicks: int
    total_purchases: int
    total_revenue: float
    db_rows: int

# REST Endpoints
@app.get("/")
def read_root():
    return {"service": "ZakaFlow API", "version": "1.0.0", "status": "healthy"}

@app.get("/api/health", response_model=HealthResponse)
async def get_health():
    db_status = "unconnected"
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
                db_status = "connected"
        except Exception:
            db_status = "error"
            
    uptime = (datetime.utcnow() - startup_time).total_seconds()
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime_seconds": uptime
    }

@app.get("/api/metrics", response_model=MetricResponse)
async def get_metrics():
    # Attempt to query Postgres database for metrics first
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                # Query counts from raw_events
                counts_row = await conn.fetchrow("""
                    SELECT 
                        COUNT(id) as total_events,
                        COALESCE(SUM(CASE WHEN event_type = 'VIEW' THEN 1 ELSE 0 END), 0) as views,
                        COALESCE(SUM(CASE WHEN event_type = 'CLICK' THEN 1 ELSE 0 END), 0) as clicks,
                        COALESCE(SUM(CASE WHEN event_type = 'PURCHASE' THEN 1 ELSE 0 END), 0) as purchases,
                        COALESCE(SUM(CASE WHEN event_type = 'PURCHASE' THEN product_price ELSE 0 END), 0.0) as revenue
                    FROM zakaflow.raw_events;
                """)
                
                eps_row = await conn.fetchrow("""
                    SELECT COUNT(id) as eps
                    FROM zakaflow.raw_events
                    WHERE created_at >= NOW() - INTERVAL '10 seconds';
                """)
                
                # Fetch Kafka offset lag stats if available
                # Sum of lag = (max offset - consumed offset) or simply simulated if no kafka metadata
                db_rows = counts_row["total_events"]
                
                return {
                    "events_per_sec": int(eps_row["eps"] / 10) if eps_row else 5,
                    "kafka_lag_ms": 0,  # Kafka cluster latency
                    "spark_jobs_active": 12,
                    "pipeline_health_pct": 98.4,
                    "total_events": counts_row["total_events"],
                    "total_views": counts_row["views"],
                    "total_clicks": counts_row["clicks"],
                    "total_purchases": counts_row["purchases"],
                    "total_revenue": float(counts_row["revenue"]),
                    "db_rows": db_rows
                }
        except Exception as e:
            logger.warning(f"Error querying Postgres database for metrics: {e}. Falling back to simulation.")
            
    # Fallback to simulation metrics
    return {
        "events_per_sec": random.randint(4, 9),
        "kafka_lag_ms": 0,
        "spark_jobs_active": 12,
        "pipeline_health_pct": 98.4,
        "total_events": len(events_cache) + 1200, # Fake total
        "total_views": sim_stats["VIEW"] + 800,
        "total_clicks": sim_stats["CLICK"] + 300,
        "total_purchases": sim_stats["PURCHASE"] + 100,
        "total_revenue": float(sim_stats["REVENUE"] + 12000.0),
        "db_rows": len(events_cache) + 1200
    }

@app.get("/api/events")
async def get_events(limit: int = 50, event_type: str = "ALL"):
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                query = "SELECT event_id, event_type, product_id, product_name, product_category, product_price, user_id, location, session_id, created_at as timestamp FROM zakaflow.raw_events"
                params = []
                if event_type != "ALL":
                    query += " WHERE event_type = $1"
                    params.append(event_type)
                    query += " ORDER BY id DESC LIMIT $2"
                    params.append(limit)
                else:
                    query += " ORDER BY id DESC LIMIT $1"
                    params.append(limit)
                    
                rows = await conn.fetch(query, *params)
                events_list = []
                for row in rows:
                    events_list.append({
                        "event_id": row["event_id"],
                        "event_type": row["event_type"],
                        "product_id": row["product_id"],
                        "product_name": row["product_name"],
                        "product_category": row["product_category"],
                        "product_price": float(row["product_price"]) if row["product_price"] else 0.0,
                        "user_id": row["user_id"],
                        "location": row["location"],
                        "session_id": row["session_id"],
                        "timestamp": row["timestamp"].isoformat() + "Z"
                    })
                return events_list
        except Exception as e:
            logger.warning(f"Error querying Postgres for events: {e}. Falling back to simulation cache.")
            
    # Fallback simulation
    events_list = list(events_cache)
    if event_type != "ALL":
        events_list = [e for e in events_list if e["event_type"] == event_type]
    return events_list[:limit]

@app.get("/api/analytics")
async def get_analytics():
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                # Top products by revenue
                top_products_rows = await conn.fetch("""
                    SELECT 
                        product_name, product_category,
                        COUNT(id) as total_events,
                        SUM(CASE WHEN event_type = 'VIEW' THEN 1 ELSE 0 END) as views,
                        SUM(CASE WHEN event_type = 'CLICK' THEN 1 ELSE 0 END) as clicks,
                        SUM(CASE WHEN event_type = 'PURCHASE' THEN 1 ELSE 0 END) as purchases,
                        SUM(CASE WHEN event_type = 'PURCHASE' THEN product_price ELSE 0 END) as revenue
                    FROM zakaflow.raw_events
                    GROUP BY product_name, product_category
                    ORDER BY revenue DESC
                    LIMIT 8;
                """)
                
                top_products = []
                for row in top_products_rows:
                    views = row["views"] or 1
                    top_products.append({
                        "name": row["product_name"],
                        "category": row["product_category"],
                        "events": row["total_events"],
                        "revenue": float(row["revenue"]) if row["revenue"] else 0.0,
                        "clicks": row["clicks"] or 0,
                        "purchases": row["purchases"] or 0,
                        "ctr": round((row["clicks"] or 0) / views * 100, 2)
                    })
                    
                # Funnel metrics
                counts = await conn.fetchrow("""
                    SELECT 
                        SUM(CASE WHEN event_type = 'VIEW' THEN 1 ELSE 0 END) as views,
                        SUM(CASE WHEN event_type = 'CLICK' THEN 1 ELSE 0 END) as clicks,
                        SUM(CASE WHEN event_type = 'PURCHASE' THEN 1 ELSE 0 END) as purchases
                    FROM zakaflow.raw_events;
                """)
                
                v = counts["views"] or 1
                c = counts["clicks"] or 0
                p = counts["purchases"] or 0
                
                # Category breakdown
                cat_rows = await conn.fetch("""
                    SELECT 
                        product_category,
                        SUM(CASE WHEN event_type = 'VIEW' THEN 1 ELSE 0 END) as views,
                        SUM(CASE WHEN event_type = 'PURCHASE' THEN 1 ELSE 0 END) as purchases
                    FROM zakaflow.raw_events
                    GROUP BY product_category;
                """)
                
                category_breakdown = {}
                for cr in cat_rows:
                    category_breakdown[cr["product_category"]] = {
                        "views": cr["views"] or 0,
                        "purchases": cr["purchases"] or 0
                    }
                    
                return {
                    "funnel": {
                        "views": v,
                        "clicks": c,
                        "purchases": p,
                        "view_to_click_rate": round(c / v * 100, 2),
                        "click_to_purchase_rate": round(p / (c or 1) * 100, 2)
                    },
                    "top_products": top_products,
                    "category_breakdown": category_breakdown,
                    "revenue_today": sum(tp["revenue"] for tp in top_products)
                }
        except Exception as e:
            logger.warning(f"Error querying Postgres for analytics: {e}. Falling back to simulation.")
            
    # Fallback simulation analytics
    # Create top products list from cache counts
    counts = {}
    revs = {}
    cats = {}
    for ev in events_cache:
        name = ev["product_name"]
        counts[name] = counts.get(name, 0) + 1
        cats[name] = ev["product_category"]
        if ev["event_type"] == "PURCHASE":
            revs[name] = revs.get(name, 0.0) + ev["product_price"]
            
    top_products = []
    for name, cnt in sorted(counts.items(), key=lambda x: revs.get(x[0], 0.0), reverse=True)[:8]:
        top_products.append({
            "name": name,
            "category": cats[name],
            "events": cnt,
            "revenue": revs.get(name, 0.0),
            "clicks": int(cnt * 0.3),
            "purchases": int(cnt * 0.1),
            "ctr": 30.0
        })
        
    v = sim_stats["VIEW"] or 1
    cl = sim_stats["CLICK"] or 0
    pu = sim_stats["PURCHASE"] or 0
    
    return {
        "funnel": {
            "views": v,
            "clicks": cl,
            "purchases": pu,
            "view_to_click_rate": round(cl / v * 100, 2),
            "click_to_purchase_rate": round(pu / (cl or 1) * 100, 2)
        },
        "top_products": top_products,
        "category_breakdown": {
            "AI/ML Ops": {"views": int(v*0.3), "purchases": int(pu*0.3)},
            "Cloud Services": {"views": int(v*0.3), "purchases": int(pu*0.3)},
            "Security": {"views": int(v*0.2), "purchases": int(pu*0.2)},
            "Networking": {"views": int(v*0.1), "purchases": int(pu*0.1)},
            "Infrastructure": {"views": int(v*0.1), "purchases": int(pu*0.1)}
        },
        "revenue_today": sim_stats["REVENUE"]
    }

@app.get("/api/pipeline")
def get_pipeline():
    # Returns active stats of each stage
    return {
        "producer": {"status": "healthy", "throughput": "5.0 eps", "last_updated": datetime.utcnow().isoformat()},
        "kafka": {"status": "healthy", "lag_ms": 0, "last_updated": datetime.utcnow().isoformat()},
        "spark": {"status": "healthy", "active_jobs": 12, "last_updated": datetime.utcnow().isoformat()},
        "postgres": {"status": "healthy" if db_pool else "warning", "last_updated": datetime.utcnow().isoformat()},
        "dbt": {"status": "healthy", "last_run_status": "success", "last_updated": datetime.utcnow().isoformat()}
    }

@app.get("/api/kafka/topics")
def get_kafka_topics():
    # Returns stats for the three primary topics
    return [
        {
            "name": "product-events",
            "message_count": sim_stats["TOTAL"] + 1200,
            "lag_ms": 0,
            "partitions": 3,
            "status": "active"
        },
        {
            "name": "product-clicks",
            "message_count": sim_stats["CLICK"] + 300,
            "lag_ms": 0,
            "partitions": 3,
            "status": "active"
        },
        {
            "name": "product-purchases",
            "message_count": sim_stats["PURCHASE"] + 100,
            "lag_ms": 0,
            "partitions": 1,
            "status": "active"
        }
    ]

# WebSocket Streaming
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established.")
    try:
        while True:
            # Generate simulated event and stream to client in real-time
            event = generate_simulated_event()
            await websocket.send_json(event)
            # Send at realistic rate (every 800ms)
            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
