#!/usr/bin/env python
import os
import sys
import json
import uuid
import time
import random
import signal
import logging
from datetime import datetime
from kafka import KafkaProducer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("zakaflow-producer")

# 15 Products with varied prices and categories
PRODUCTS = [
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
    {"id": "prod_12", "name": "StreamEdge Node", "category": "Networking", "price": 344.00},
    {"id": "prod_13", "name": "Log-Pipeline Light", "category": "Infrastructure", "price": 49.00},
    {"id": "prod_14", "name": "Omni Spark Accelerator", "category": "AI/ML Ops", "price": 899.00},
    {"id": "prod_15", "name": "Kubernetes Orchestrator v2", "category": "Cloud Services", "price": 599.00}
]

# 12 Locations
LOCATIONS = [
    "San Francisco, US", "Berlin, DE", "Singapore, SG", "London, UK",
    "Sydney, AU", "Tokyo, JP", "Dubai, AE", "Nairobi, KE",
    "Lagos, NG", "Johannesburg, ZA", "Toronto, CA", "Paris, FR"
]

# Event probability distribution: 60% VIEW, 30% CLICK, 10% PURCHASE
EVENT_TYPES = ["VIEW", "CLICK", "PURCHASE"]
EVENT_WEIGHTS = [0.60, 0.30, 0.10]

# Global metrics tracking
stats = {"VIEW": 0, "CLICK": 0, "PURCHASE": 0, "TOTAL": 0}
running = True

def handle_sigint(signum, frame):
    global running
    logger.info("Termination signal received. Flushing and shutting down producer...")
    running = False

signal.signal(signal.SIGINT, handle_sigint)
signal.signal(signal.SIGTERM, handle_sigint)

def generate_event():
    event_type = random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS, k=1)[0]
    product = random.choice(PRODUCTS)
    user_id = f"usr_{random.randbytes(4).hex()}"
    location = random.choice(LOCATIONS)
    
    return {
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

def get_topics(event_type):
    # Always publish to the main raw telemetry stream
    topics = ["product-events"]
    
    if event_type == "CLICK":
        topics.append("product-clicks")
    elif event_type == "PURCHASE":
        topics.append("product-purchases")
        
    return topics

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Failed to deliver message: {err}")

def main():
    global stats
    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    events_per_sec = float(os.environ.get("EVENTS_PER_SECOND", "5"))
    
    banner = """
    ==================================================
      🌊 ZakaFlow Real-Time Telemetry Event Producer 🌊
    ==================================================
      Bootstrap Servers: {}
      Target Rate:       {} events/sec
    ==================================================
    """.format(bootstrap_servers, events_per_sec)
    print(banner, flush=True)
    
    logger.info("Connecting to Kafka...")
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3
        )
        logger.info("Kafka Producer successfully initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Kafka Producer: {e}")
        sys.exit(1)
        
    last_stats_time = time.time()
    interval = 1.0 / events_per_sec
    
    while running:
        start_time = time.time()
        
        event = generate_event()
        event_type = event["event_type"]
        topics = get_topics(event_type)
        
        for topic in topics:
            try:
                producer.send(
                    topic=topic,
                    key=event["product_id"],
                    value=event
                )
            except Exception as e:
                logger.error(f"Error sending event to topic {topic}: {e}")
                
        # Track counts
        stats[event_type] += 1
        stats["TOTAL"] += 1
        
        # Log stats every 10 seconds
        now = time.time()
        if now - last_stats_time >= 10.0:
            elapsed = now - last_stats_time
            rate = stats["TOTAL"] / elapsed
            logger.info(
                f"Metrics (last {elapsed:.1f}s) | "
                f"Total Events: {stats['TOTAL']} ({rate:.1f} eps) | "
                f"Views: {stats['VIEW']} | Clicks: {stats['CLICK']} | Purchases: {stats['PURCHASE']}"
            )
            # Reset temporary window count
            stats = {"VIEW": 0, "CLICK": 0, "PURCHASE": 0, "TOTAL": 0}
            last_stats_time = now
            
        # Throttling
        execution_time = time.time() - start_time
        sleep_time = max(0.0, interval - execution_time)
        if sleep_time > 0:
            time.sleep(sleep_time)
            
    producer.flush()
    producer.close()
    logger.info("Producer stopped cleanly.")

if __name__ == "__main__":
    main()
