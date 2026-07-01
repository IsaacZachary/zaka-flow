FROM apache/airflow:2.8.1-python3.11

USER root

# Install system utilities needed by libraries
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         build-essential \
         libpq-dev \
         default-jdk \
  && apt-get autoremove -y --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME for Spark integrations
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

USER airflow

# Install Python packages required by Airflow DAGs
RUN pip install --no-cache-dir \
    kafka-python==2.0.2 \
    psycopg2-binary==2.9.9 \
    pandas==2.2.0 \
    dbt-postgres==1.7.4
