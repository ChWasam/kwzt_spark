FROM python:3.11-slim-bookworm

# Metadata
LABEL maintainer="Your Name"
LABEL description="Custom PySpark image for OpenShift with Hadoop authentication disabled"

# Set environment variables
ENV SPARK_VERSION=3.5.0 \
    HADOOP_VERSION=3 \
    SPARK_HOME=/opt/spark \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH=$PATH:/opt/spark/bin:/opt/spark/sbin \
    PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip \
    SPARK_NO_DAEMONIZE=true

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Download and install Apache Spark
RUN curl -fsSL https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    -o /tmp/spark.tgz \
    && tar -xzf /tmp/spark.tgz -C /opt/ \
    && mv /opt/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_HOME} \
    && rm /tmp/spark.tgz

# Create Hadoop configuration directory
RUN mkdir -p ${SPARK_HOME}/conf/hadoop-conf

# Pre-configure Hadoop to disable Kerberos authentication
RUN echo '<?xml version="1.0"?>' > ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '<configuration>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '  <property>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '    <name>hadoop.security.authentication</name>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '    <value>simple</value>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '  </property>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '  <property>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '    <name>hadoop.security.authorization</name>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '    <value>false</value>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '  </property>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '  <property>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '    <name>fs.file.impl</name>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '    <value>org.apache.hadoop.fs.RawLocalFileSystem</value>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '  </property>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml && \
    echo '</configuration>' >> ${SPARK_HOME}/conf/hadoop-conf/core-site.xml

# Install Python packages
RUN pip install --no-cache-dir \
    pyspark==${SPARK_VERSION} \
    pandas \
    matplotlib \
    seaborn

# Create application directory
RUN mkdir -p /app /tmp/spark-warehouse /tmp/spark-events

# Copy the EDA script
COPY eda_analysis.py /app/

# Set up for OpenShift arbitrary UID support
# Create directories that need to be writable
RUN mkdir -p /tmp /opt/spark/work /opt/spark/logs \
    && chmod -R 777 /tmp /opt/spark/work /opt/spark/logs /app

# Create a script to add the OpenShift random UID to /etc/passwd at runtime
RUN echo '#!/bin/bash\n\
if ! whoami &> /dev/null; then\n\
  if [ -w /etc/passwd ]; then\n\
    echo "${USER_NAME:-spark}:x:$(id -u):0:${USER_NAME:-spark} user:${HOME}:/sbin/nologin" >> /etc/passwd\n\
  fi\n\
fi\n\
exec "$@"' > /usr/local/bin/uid_entrypoint.sh \
    && chmod +x /usr/local/bin/uid_entrypoint.sh

# Set working directory
WORKDIR /app

# Use the UID entrypoint to handle OpenShift random UIDs
ENTRYPOINT ["/usr/local/bin/uid_entrypoint.sh"]

# Default command
CMD ["python", "/app/eda_analysis.py"]
