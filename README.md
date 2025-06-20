# ZakaFlow – Real-Time Big Data Platform for Product Analytics

![GitHub repo size](https://img.shields.io/github/repo-size/IsaacZachary/zaka-flow)
![GitHub license](https://img.shields.io/github/license/IsaacZachary/zaka-flow)
![Issues](https://img.shields.io/github/issues/IsaacZachary/zaka-flow)
![Stars](https://img.shields.io/github/stars/IsaacZachary/zaka-flow?style=social)

ZakaFlow is a real-time data pipeline and analytics platform for simulating product interactions (like views, clicks, purchases), processing them at scale, and visualizing actionable insights. This modular project combines modern data engineering and DevOps practices using Kafka, Spark, Airflow, dbt, Docker, and Terraform.

---

## 📌 Project Objectives
- Simulate real-time user-product interactions
- Ingest data into Kafka topics
- Process data in real-time with Spark Streaming
- Orchestrate batch ETL with Airflow
- Transform and model data with dbt
- Visualize metrics and trends with dashboards
- Deploy infrastructure using Terraform on AWS

---

## 🔧 Tech Stack

| Layer        | Tools Used                                |
|--------------|---------------------------------------------|
| Ingestion    | Apache Kafka, Python Flask Producer         |
| Processing   | Apache Spark (Structured Streaming)         |
| Storage      | Hive, S3, HDFS                              |
| Orchestration| Apache Airflow                              |
| Modeling     | dbt, SQL                                    |
| Dashboards   | Apache Superset, Grafana                    |
| Infrastructure | Docker, Docker Compose, Terraform        |
| Monitoring   | Prometheus, Grafana, ELK Stack              |

---

## 🧱 Directory Structure

```bash
zaka-flow/
├── README.md
├── docker-compose.yml
├── .gitignore
├── requirements.txt
├── infra/                  # Terraform infra config
├── kafka/                 # Kafka producer and configs
├── spark/                 # PySpark stream/batch processors
├── airflow/               # DAGs for orchestration
├── dbt/                   # dbt models & config
├── dashboards/            # Superset/Grafana dashboards
├── notebooks/             # Jupyter EDA & testing
└── docs/                  # Architecture, diagrams, notes
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Git
- Spark 3.0+
- Terraform (for deployment)

### 1. Clone the Repository
```bash
git clone https://github.com/IsaacZachary/zaka-flow.git
cd zaka-flow
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Kafka + Spark + Airflow Locally
```bash
docker-compose up --build
```

### 4. Simulate Real-Time Events
```bash
python kafka/producer.py
```

### 5. Run Spark Streaming Job
```bash
spark-submit spark/stream_processor.py
```

### 6. Access Airflow UI (Optional)
Visit: [http://localhost:8081](http://localhost:8081)

---

## 📈 Example Use Cases
- Product analytics platform (views, clicks, purchases)
- Real-time sales monitoring
- ETL for e-commerce pipelines
- Training ground for DevOps, AI/ML, and MLOps engineers

---

## 🌍 Cloud Deployment (Coming Soon)
- Terraform scripts for AWS EMR + S3 + RDS
- Kubernetes support for scaling Spark workers

---

## 👨🏾‍💻 Author
**Isaac Siko Zachary**  
📫 [isaaczachary18@gmail.com](mailto:isaaczachary18@gmail.com)  
🔗 [LinkedIn](https://linkedin.com/in/isaaczachary)  
🌐 [izach.netlify.app](https://izach.netlify.app)

---

## 📜 License
[MIT License](LICENSE)

---

## 🙏 Acknowledgments
- Power Learn Project
- Cursor AI & Lovable AI (Vibe Coding Stack)
- First Basics Technologies
- Open Source Contributors

---

## 🏁 Roadmap
- [x] Kafka + Spark setup
- [x] Producer simulation script
- [x] Stream processing pipeline
- [ ] Airflow DAGs for batch ETL
- [ ] dbt model transformation
- [ ] Superset/Grafana dashboards
- [ ] Terraform for AWS infra
- [ ] Kubernetes Helm chart for deployment

---

> ⚠️ This is an open-source personal learning project. Contributions, ideas, and PRs are welcome!
