#!/bin/bash

# ZakaFlow – Quick Start Script
# Starts the full data pipeline stack locally

set -e

echo ""
echo "🌊 =================================================="
echo "   ZakaFlow – Real-Time Big Data Pipeline"
echo "   Starting full stack..."
echo "   =================================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install Docker Desktop first."
    echo "   https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found."
    exit 1
fi

echo "✅ Docker found: $(docker --version)"
echo "✅ Docker Compose: $(docker compose version)"
echo ""

# Create required directories
mkdir -p airflow/logs airflow/dags airflow/dbt
mkdir -p postgres
mkdir -p api

# Set permissions for Airflow
export AIRFLOW_UID=$(id -u 2>/dev/null || echo 50000)

echo "🚀 Starting services..."
echo "   This will take 2-3 minutes on first run (pulling images)"
echo ""

docker compose up -d --build

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 15

echo ""
echo "🎉 =================================================="
echo "   ZakaFlow Stack is LIVE!"
echo ""
echo "   📊 Dashboard:      http://localhost:3030"
echo "   🔌 API:            http://localhost:8000"
echo "   ✈️  Airflow:        http://localhost:8081"
echo "      Username: admin | Password: admin"
echo "   🔥 Spark Master:   http://localhost:8090"
echo "   🐘 PostgreSQL:     localhost:5432"
echo "      DB: zakaflow | User: zakaflow_user"
echo ""
echo "   To start producing events:"
echo "   docker exec -it \$(docker ps -qf name=kafka) bash"
echo "   OR run: python kafka/producer.py"
echo ""
echo "   To stop: docker compose down"
echo "   To stop + delete data: docker compose down -v"
echo "   =================================================="
