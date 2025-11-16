## Project Overview

This project demonstrates a complete end-to-end data pipeline using Apache Kafka for streaming and Apache PySpark for distributed data analysis, deployed on OpenShift (NERC cluster).

### Architecture

```
Data Generator (Job) → CSV → Producer (Job) → Kafka (Deployment)
    → Consumer (Job) → CSV → PySpark EDA (Job) → Visualizations
```

**Key Learning Points:**
- Kafka streaming with producer/consumer pattern
- Batch processing in Kubernetes (Jobs vs Deployments)
- PySpark distributed data analysis
- OpenShift deployment & troubleshooting
- Custom Docker images for complex dependencies

### Technology Stack

- **Streaming:** Apache Kafka 3.5.0 (KRaft mode)
- **Analytics:** Apache Spark 3.5.0 with PySpark
- **Orchestration:** OpenShift/Kubernetes
- **Languages:** Python 3.11
- **Data:** 100K synthetic e-commerce transactions
- **Visualizations:** Matplotlib, Seaborn

---

## Quick Start

### Local Development (Docker Compose)

```bash
# 1. Generate data
python generate_data.py

# 2. Start all services
docker-compose up -d

# 3. Monitor logs
docker-compose logs -f producer
docker-compose logs -f consumer

# 4. Run EDA in Jupyter
# Open http://localhost:8888
# Run eda.ipynb

# 5. Cleanup
docker-compose down
```

### OpenShift Deployment

**Full deployment with correct order:**

```bash
# Login
oc login --server=https://api.edu.nerc.mghpcc.org:6443 --token=YOUR_TOKEN
oc project ds551-2025fall-7ae539

# PHASE 1: PVCs
oc apply -f k8s/01-kafka-pvc.yaml
oc apply -f k8s/06-data-pvc.yaml

# PHASE 2: Kafka & Data
oc apply -f k8s/03-kafka-service.yaml
oc apply -f k8s/07-data-generator-job.yaml
oc wait --for=condition=complete --timeout=300s job/generate-transaction-data
oc apply -f k8s/02-kafka-deployment.yaml
oc wait --for=condition=available --timeout=300s deployment/kafka

# PHASE 3: Producer
oc apply -f k8s/05-producer-imagestream.yaml
oc apply -f k8s/04-producer-buildconfig.yaml
oc start-build kafka-producer
oc apply -f k8s/08-producer-deployment.yaml

# PHASE 4: Consumer
oc apply -f k8s/10-consumer-imagestream.yaml
oc apply -f k8s/09-consumer-buildconfig.yaml
oc start-build kafka-consumer
oc apply -f k8s/11-consumer-deployment.yaml

# PHASE 5: EDA (Custom PySpark Image)
oc apply -f k8s/13-eda-imagestream.yaml
oc apply -f k8s/14-eda-buildconfig.yaml
oc start-build pyspark-eda-custom
oc apply -f k8s/12-eda-job.yaml

# Download results
mkdir -p plots
```

**Total Time:** ~30-40 minutes (including builds)

---

## Project Structure

```
.
├── producer/                   # Kafka producer (sends CSV to Kafka)
│   ├── producer.py
│   ├── Dockerfile
│   └── requirements.txt
├── consumer/                   # Kafka consumer (receives from Kafka, writes CSV)
│   ├── consumer.py
│   ├── Dockerfile
│   └── requirements.txt
├── eda/                        # PySpark EDA analysis
│   ├── eda_analysis.py        # Standalone PySpark script
│   ├── Dockerfile             # Custom image (Spark 3.5.0 + Hadoop config)
│   ├── README.md              # Technical documentation
│   └── DEPLOY_CUSTOM_EDA.md   # Deployment guide
├── k8s/                        # Kubernetes YAML manifests
│   ├── 01-kafka-pvc.yaml      # Kafka storage (5Gi)
│   ├── 02-kafka-deployment.yaml
│   ├── 03-kafka-service.yaml
│   ├── 04-producer-buildconfig.yaml
│   ├── 05-producer-imagestream.yaml
│   ├── 06-data-pvc.yaml       # Data storage (2Gi)
│   ├── 07-data-generator-job.yaml
│   ├── 08-producer-deployment.yaml  # Actually a Job
│   ├── 09-consumer-buildconfig.yaml
│   ├── 10-consumer-imagestream.yaml
│   ├── 11-consumer-deployment.yaml  # Actually a Job
│   ├── 12-eda-job.yaml
│   ├── 13-eda-imagestream.yaml
│   ├── 14-eda-buildconfig.yaml
│   └── README.md
├── plots/                      # Generated visualizations
│   ├── plot_revenue_by_category.png
│   ├── plot_payment_methods.png
│   └── plot_top_cities.png
├── generate_data.py            # Data generator script
├── docker-compose.yml          # Local development setup
└── README.md                   # This file
```

---


## Key Features & Challenges Solved

### ✅ Apache Kafka in KRaft Mode
- No Zookeeper dependency (modern Kafka 3.5.0)
- Critical fix: `KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093` (service name, not localhost)

### ✅ Batch Processing Pattern
- Producer & Consumer are **Jobs** (not Deployments)
- Producer: Sends 20 batches (100K records) then stops
- Consumer: Receives 100K messages then stops
- Educational purpose: Learn job patterns in Kubernetes

### ✅ Custom PySpark Image for OpenShift
**Major Challenge:** Standard PySpark images fail on OpenShift due to Hadoop authentication

**Error:**
```
org.apache.hadoop.security.KerberosAuthException:
javax.security.auth.login.LoginException: NullPointerException: invalid null input
```

**Root Cause:** OpenShift random UIDs (e.g., 1001520000) don't exist in `/etc/passwd`

**Solution:** Created custom Docker image (`eda/Dockerfile`) that:
1. Pre-configures Hadoop core-site.xml (disables authentication)
2. Uses RawLocalFileSystem (bypasses permission checks)
3. Entrypoint script adds OpenShift UID to /etc/passwd at runtime

**Result:** Successful PySpark execution in 60 seconds!

### ✅ Complete Data Pipeline
- **Input:** 100,000 synthetic transactions (9.24 MB CSV)
- **Processing:** Kafka streaming + PySpark distributed analysis
- **Output:** 3 visualizations + analysis summary
- **Revenue Analyzed:** $89.6 million across 10 product categories

---

## Results

### Analysis Summary
- **Total Transactions:** 100,000
- **Total Revenue:** $89,599,149.32
- **Average Transaction:** $895.99

### Top Insights
- **Top Category:** Electronics ($30.2M in revenue, 9,928 transactions)
- **Top Payment Method:** Credit Card (20,122 transactions)
- **Top City:** Chicago ($6.2M revenue, 6,838 transactions)

### Generated Visualizations
1. `plot_revenue_by_category.png` (80KB) - Bar chart of revenue by product category
2. `plot_payment_methods.png` (71KB) - Transaction distribution by payment method
3. `plot_top_cities.png` (49KB) - Top 10 cities by revenue

---

## All Errors Encountered & Fixed

### ERROR 1: Kafka Controller Voters (localhost vs service name)
**Fix:** Changed `1@localhost:9093` → `1@kafka:9093`
**Commit:** d5ad233

### ERROR 2: PySpark Hadoop Authentication (Major)
**Attempts:** Environment vars, bitnami image, fsGroup - all failed
**Fix:** Custom Docker image with pre-configured Hadoop
**Commits:** 31982ee, 44e277c

### ERROR 3: Dockerfile Heredoc Syntax
**Fix:** Replaced heredoc with echo commands
**Commit:** 44e277c

### ERROR 4: OpenShift fsGroup Security
**Fix:** Removed fsGroup, used HOME=/tmp instead

### ERROR 5: Node Selector Pods Pending
**Fix:** Removed all node selectors


---

## Performance Metrics

| Component | Build Time | Run Time | Resources |
|-----------|------------|----------|-----------|
| Kafka Deployment | - | 1-2 min | 500m-1000m CPU, 2-3Gi RAM |
| Data Generator | - | 30-60 sec | 250m-500m CPU, 512Mi-1Gi RAM |
| Producer Build | 2-3 min | - | - |
| Producer Job | - | 3-4 min | 250m-500m CPU, 512Mi-1Gi RAM |
| Consumer Build | 2-3 min | - | - |
| Consumer Job | - | 10-12 min | 100m-500m CPU, 512Mi-1Gi RAM |
| PySpark Build | 5-10 min | - | - |
| PySpark Job | - | 60-90 sec | 500m-1500m CPU, 2-4Gi RAM |
| **Total** | **~12-18 min** | **~18-22 min** | **Fits in 3 CPU / 12Gi quota** |

---

## Resource Limits

**OpenShift Namespace Quota:**
- CPU: 3 cores max
- Memory: 12Gi max
- Storage: 20Gi max

**Total Usage:**
- CPU Requests: 1.2 cores ✅
- Memory Requests: 4.5Gi ✅
- Storage: 7Gi (5Gi Kafka + 2Gi data) ✅

---

## Common Commands

### Monitoring
```bash
# Check all resources
oc get all,pvc,bc,is

# View logs
oc logs deployment/kafka
oc logs job/kafka-producer
oc logs job/kafka-consumer
oc logs job/pyspark-eda

# Check builds
oc get builds
oc logs build/kafka-producer-1
```

### Troubleshooting
```bash
# Restart build
oc start-build kafka-producer

# Check data files
oc get pods | grep kafka-consumer
oc exec -it <consumer-pod> -- ls -lh /data/

# Check quota
oc describe quota
```

### Cleanup
```bash
# Delete all (keep PVCs)
oc delete job --all
oc delete deployment kafka
oc delete svc kafka
oc delete bc,is --all

# Complete cleanup (WARNING: deletes data!)
oc delete all --all
oc delete bc,is --all
oc delete pvc --all
```

---

## Prerequisites

### Software
- Docker & Docker Compose (local development)
- OpenShift CLI (`oc`) v4.x
- Python 3.11+
- Git

### OpenShift Access
- NERC OpenShift cluster access
- Project namespace: `ds551-2025fall-7ae539`
- Login token from OpenShift console

### GitHub
- Repository with code pushed
- Update Git URLs in BuildConfigs:
  - `k8s/04-producer-buildconfig.yaml`
  - `k8s/09-consumer-buildconfig.yaml`
  - `k8s/14-eda-buildconfig.yaml`

---

## Learning Outcomes

1. **Kafka Streaming Architecture**
   - Producer/Consumer pattern
   - Topic-based messaging
   - KRaft mode (no Zookeeper)

2. **Kubernetes Patterns**
   - Jobs vs Deployments
   - PersistentVolumeClaims
   - ImageStreams & BuildConfigs

3. **OpenShift Specifics**
   - Random UID security model
   - Security Context Constraints
   - Internal image registry

4. **PySpark**
   - Distributed DataFrame operations
   - Data aggregation & analysis
   - Matplotlib/Seaborn integration

5. **DevOps & Debugging**
   - Container builds from Git
   - Log analysis
   - Resource quota management
   - Systematic troubleshooting

---

## References

- **Apache Kafka:** https://kafka.apache.org/documentation/
- **Apache Spark:** https://spark.apache.org/docs/latest/
- **OpenShift:** https://docs.openshift.com/
- **Kubernetes:** https://kubernetes.io/docs/

---

**🎯 Success! Complete end-to-end deployment with comprehensive documentation.**
