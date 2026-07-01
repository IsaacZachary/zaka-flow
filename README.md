# ZakaFlow 🌊

> **Real-Time Big Data Pipeline & Analytics Platform**
> Built with Kafka · Spark · Airflow · dbt · PostgreSQL · FastAPI

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](docker-compose.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](requirements.txt)

---

## 🏗️ Architecture

```
[Kafka Producer (Python)]
         │  generates product events (VIEW · CLICK · PURCHASE)
         ▼
[Apache Kafka]  ──── 3 topics ────────────────────────┐
         │                                              │
         ▼                                             │
[Spark Structured Streaming]                          │
         │  parses + writes to DB in real-time        │
         ▼                                             │
[PostgreSQL]  ◄── [Spark Batch ETL (hourly)] ◄── [Airflow DAG]
         │
         ▼
[dbt Models]  (staging → marts)
         │
         ▼
[FastAPI Backend]  (/api/metrics · /api/events · WebSocket)
         │
         ▼
[ZakaFlow Dashboard]  (real-time UI · Vercel-deployable)
```

---

## 🚀 Quick Start (Local Docker)

**Prerequisites:** Docker Desktop installed

```bash
# Clone
git clone https://github.com/IsaacZachary/zaka-flow.git
cd zaka-flow

# Start everything (first run takes ~3 min to pull images)
bash start.sh

# OR manually:
docker compose up -d --build
```

**Access the stack:**

| Service | URL | Credentials |
|---|---|---|
| 📊 Dashboard | http://localhost:3030 | - |
| 🔌 API | http://localhost:8000 | - |
| ✈️ Airflow | http://localhost:8081 | admin / admin |
| 🔥 Spark UI | http://localhost:8090 | - |
| 🐘 PostgreSQL | localhost:5432 | zakaflow_user / zakaflow_pass_2026 |

---

## 📂 Project Structure

```
zaka-flow/
├── docker-compose.yml        # Full stack orchestration
├── start.sh                  # Quick start script
├── requirements.txt          # Python dependencies
│
├── kafka/
│   ├── producer.py           # Event simulator & Kafka producer
│   └── topics_config.sh      # Topic creation script
│
├── spark/
│   ├── stream_processor.py   # PySpark Structured Streaming
│   └── batch_etl.py          # PySpark batch aggregation ETL
│
├── airflow/
│   ├── Dockerfile            # Custom Airflow image
│   └── dags/
│       └── etl_pipeline.py   # Main orchestration DAG
│
├── dbt/
│   ├── dbt_project.yml       # dbt project config
│   ├── profiles.yml          # DB connection profile
│   └── models/
│       ├── staging/
│       │   └── stg_events.sql
│       └── marts/
│           ├── product_metrics_daily.sql
│           └── funnel_analysis.sql
│
├── api/
│   ├── main.py               # FastAPI backend
│   ├── Dockerfile            # API container
│   └── requirements.txt      # API dependencies
│
├── postgres/
│   └── init.sql              # DB schema + seed data
│
├── dashboards/
│   └── index.html            # Live analytics dashboard
│
├── infra/                    # Terraform (AWS deployment)
├── notebooks/                # Jupyter EDA
└── docs/                     # Architecture diagrams
```

---

## 🔧 Running Individual Components

### Start Kafka Producer
```bash
# Inside Docker
docker compose exec kafka-producer python /app/kafka/producer.py

# Locally (requires Kafka running)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092 EVENTS_PER_SECOND=10 python kafka/producer.py
```

### Run Spark Streaming Job
```bash
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.1 \
  spark/stream_processor.py
```

### Run Batch ETL (specific date)
```bash
spark-submit spark/batch_etl.py --date 2026-07-01
```

### Run dbt Models
```bash
cd dbt
dbt run --profiles-dir . --target dev
dbt test --profiles-dir .
```

### API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Service health check |
| `GET /api/metrics` | Live KPI metrics |
| `GET /api/events?limit=50` | Recent events |
| `GET /api/analytics` | Conversion funnel + top products |
| `GET /api/pipeline` | Pipeline stage health |
| `GET /api/kafka/topics` | Kafka topic stats |
| `WS  /ws/events` | Live event WebSocket stream |

---

## 🌍 Deploy to Cloud

### Dashboard → Vercel
```bash
# The dashboards/ folder is a static site
vercel deploy dashboards/
```

### Full Stack → VPS (Docker)
```bash
# SSH into your VPS
ssh root@your-vps-ip

# Clone and start
git clone https://github.com/IsaacZachary/zaka-flow.git
cd zaka-flow
docker compose up -d --build
```

### Infrastructure → AWS (Terraform)
```bash
cd infra
terraform init
terraform plan
terraform apply
```

---

## 📊 Data Models

### `raw_events` (streaming sink)
| Column | Type | Description |
|---|---|---|
| event_id | VARCHAR | Unique event UUID |
| event_type | VARCHAR | VIEW / CLICK / PURCHASE |
| product_name | VARCHAR | Product name |
| product_category | VARCHAR | Category |
| product_price | DECIMAL | Price in USD |
| user_id | VARCHAR | Anonymous user ID |
| location | VARCHAR | City, Country |
| created_at | TIMESTAMP | Event time |

### `product_metrics` (dbt mart)
Aggregated daily metrics per product with CTR and conversion rate.

### `funnel_analysis` (dbt mart)
Daily conversion funnel: views → clicks → purchases.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Ingestion** | Apache Kafka + Python Producer |
| **Stream Processing** | Apache Spark Structured Streaming |
| **Batch ETL** | PySpark + Airflow |
| **Data Modeling** | dbt (PostgreSQL) |
| **Storage** | PostgreSQL 15 |
| **API** | FastAPI + asyncpg |
| **Dashboard** | Vanilla HTML/CSS/JS + Chart.js |
| **Infrastructure** | Docker Compose + Terraform (AWS) |
| **Monitoring** | Airflow UI + Spark UI + Custom Dashboard |

---

## 👨🏾‍💻 Author

**Isaac Siko Zachary** — Data Engineer
- 📧 isaaczachary18@gmail.com
- 🔗 [LinkedIn](https://linkedin.com/in/isaaczachary)
- 🌐 [izach.netlify.app](https://izach.netlify.app)

---

## 📜 License

MIT License — see [LICENSE](LICENSE)
