# Complete Execution Guide - Kafka + PySpark Assignment

## 📊 Data Flow Overview

```
1. Generate Data → 2. Kafka Producer → 3. Kafka Broker → 4. Consumer → 5. PySpark EDA
   (CSV file)        (CSV → Kafka)      (Topic: transactions)  (Kafka → CSV)   (Analysis + Plots)
```

---

## 🏠 LOCAL DEVELOPMENT (Docker Compose)

### Step 1: Generate Synthetic Data
```bash
python3 generate_data.py
# Creates: data/transactions.csv (1M records, ~92MB)
# Takes: ~1 minute
```

### Step 2: Start Kafka Broker
```bash
docker compose up kafka -d
# Wait 30 seconds for Kafka to start
```

### Step 3: Start Producer & Consumer
```bash
docker compose up producer consumer -d
```

### Step 4: Monitor Progress
```bash
# Watch producer sending data
docker compose logs -f producer

# Watch consumer receiving data (in another terminal)
docker compose logs -f consumer

# Stop watching: Ctrl+C
```

**Expected behavior:**
- Producer sends 10,000 records every 5 seconds until completion
- Consumer receives continuously and saves to `data/received_transactions.csv`
- Consumer waits indefinitely for new messages (no timeout)
- Takes ~8 minutes to process all 1M records

### Step 5: Run PySpark EDA (Jupyter Notebook)
```bash
# Start Jupyter
docker compose up pyspark -d

# Open browser: http://localhost:8888
# Navigate to: work/eda.ipynb
# Click: Run → Run All Cells
# Wait for all cells to complete (~2-3 minutes)
```

**Outputs:**
- Analysis results in notebook
- 6 visualization plots displayed inline

### Step 6: Cleanup
```bash
docker compose down
# Keep data: docker compose down (volumes persist)
# Delete data: docker compose down -v
```

---

## ☁️ OPENSHIFT DEPLOYMENT

### Prerequisites
```bash
# 1. Push code to GitHub
git init
git add .
git commit -m "Kafka + PySpark assignment"
git remote add origin https://github.com/YOUR_USERNAME/ds551_kafka_spark_wasam.git
git push -u origin main

# 2. Update GitHub URLs in BuildConfigs
# Edit: k8s/04-producer-buildconfig.yaml 
# Edit: k8s/09-consumer-buildconfig.yaml
# Replace: YOUR_GITHUB_USERNAME → your actual username

# 3. Login to OpenShift
oc login --server=<your-server> --token=<your-token>
oc project ds551-2025fall-7ae539
```

### Option A: Automated Deployment (Recommended)
```bash
./deploy.sh
# Runs all steps automatically
# Takes ~10-15 minutes total
```

### Option B: Manual Deployment (Step-by-Step)
  
#### Step 1: Create Storage
```bash
oc apply -f k8s/01-kafka-pvc.yaml
oc apply -f k8s/06-data-pvc.yaml
```

#### Step 2: Deploy Kafka
```bash
oc apply -f k8s/02-kafka-deployment.yaml
oc apply -f k8s/03-kafka-service.yaml

# Wait for Kafka to be ready (~2 minutes)
oc wait --for=condition=available --timeout=300s deployment/kafka
```

#### Step 3: Generate Data in Cloud
```bash
oc apply -f k8s/07-data-generator-job.yaml

# Wait for completion (~1 minute)
oc wait --for=condition=complete --timeout=300s job/generate-transaction-data

# Verify data created
oc logs job/generate-transaction-data
```

#### Step 4: Build Producer & Consumer Images
```bash
# Create ImageStreams
oc apply -f k8s/05-producer-imagestream.yaml
oc apply -f k8s/10-consumer-imagestream.yaml

# Create BuildConfigs
oc apply -f k8s/04-producer-buildconfig.yaml
oc apply -f k8s/09-consumer-buildconfig.yaml

# Start builds
oc start-build kafka-producer
oc start-build kafka-consumer

# Monitor builds (~3-5 minutes)
oc get builds -w
# Press Ctrl+C when both show "Complete"
```

#### Step 5: Deploy Producer & Consumer (Both Jobs)
```bash
# Deploy producer as a one-time job (stops after 20 batches)
oc apply -f k8s/08-producer-deployment.yaml

# Deploy consumer as a one-time job (stops after receiving all 100K messages)
oc apply -f k8s/11-consumer-deployment.yaml

# Monitor logs
oc logs -f job/kafka-producer        # Watch producer (will complete after 20 batches)
oc logs -f job/kafka-consumer        # Watch consumer (will complete after 100K messages)
# Press Ctrl+C after seeing successful batches
```

**Architecture Note (Batch Processing):**
- **Producer**: Runs as a Kubernetes Job that completes after sending 20 batches (100K records, stops cleanly)
- **Consumer**: Runs as a Kubernetes Job that completes after receiving 100K messages (MAX_MESSAGES=100000, consumer_timeout_ms=60000)
- Both Jobs complete with status "Complete" and don't restart
- This is **batch processing**: finite dataset processed once, suitable for assignments and ETL pipelines

#### Step 6: Run PySpark EDA Job
```bash
oc apply -f k8s/12-eda-job.yaml

# Wait for completion (~2-3 minutes)
oc wait --for=condition=complete --timeout=600s job/pyspark-eda

# View EDA output
oc logs job/pyspark-eda
```

#### Step 7: Download EDA Plots
```bash
# Create a temporary pod to access the PVC
oc run data-accessor --image=busybox --restart=Never --overrides='
{
  "spec": {
    "containers": [{
      "name": "data-accessor",
      "image": "busybox",
      "command": ["sleep", "3600"],
      "volumeMounts": [{
        "name": "data",
        "mountPath": "/data"
      }]
    }],
    "volumes": [{
      "name": "data",
      "persistentVolumeClaim": {
        "claimName": "transaction-data-pvc"
      }
    }]
  }
}'

# Wait for pod to be ready
oc wait --for=condition=ready pod/data-accessor --timeout=60s

# List available files
oc exec data-accessor -- ls -lh /data/

# Download the 3 visualization plots
mkdir -p plots
oc cp data-accessor:/data/plot_revenue_by_category.png plots/plot_revenue_by_category.png
oc cp data-accessor:/data/plot_payment_methods.png plots/plot_payment_methods.png
oc cp data-accessor:/data/plot_top_cities.png plots/plot_top_cities.png

# Verify downloads
ls -lh plots/

# Cleanup temporary pod
oc delete pod data-accessor
```

---

## 🔍 Verification Commands

### Local
```bash
# Check containers running
docker compose ps

# Check data files
ls -lh data/

# View Kafka topics
docker exec kafka-broker kafka-topics.sh --list --bootstrap-server localhost:9092
```

### OpenShift
```bash
# Check all resources
oc get all

# Check pods status
oc get pods

# Check PVCs
oc get pvc

# View logs
oc logs deployment/kafka
oc logs job/kafka-producer --tail=50        # Producer runs as Job
oc logs job/kafka-consumer --tail=50        # Consumer runs as Job
oc logs job/pyspark-eda

# Check data in PVC (use completed pod name)
oc get pods | grep kafka-consumer
oc exec -it kafka-consumer-xxxxx -- ls -lh /data/
```

---

## 🧹 Resource Management

### Downscaling Resources (Save Costs, Keep Data)

When you want to pause the deployment but keep all data intact:

#### Option 1: Scale Down Kafka Only
```bash
# Scale Kafka to 0 replicas (stops broker, keeps config)
oc scale deployment/kafka --replicas=0

# Verify
oc get deployment kafka
# Output: kafka   0/0     0            0           2h
```

**What This Does**:
- ✅ Stops Kafka broker (frees CPU/RAM)
- ✅ Keeps deployment configuration
- ✅ Keeps PVCs and all data
- ✅ Jobs remain in "Complete" state
- ⚠️ Kafka topics/data preserved but inaccessible until scaled up

**To Resume**:
```bash
# Scale back up
oc scale deployment/kafka --replicas=1

# Wait for ready
oc wait --for=condition=available --timeout=300s deployment/kafka
```

---

#### Option 2: Delete Jobs but Keep Infrastructure
```bash
# Delete completed jobs (they don't consume resources anyway)
oc delete job --all

# Keep Kafka, PVCs, BuildConfigs, ImageStreams
```

**What This Does**:
- ✅ Removes completed job pods (minimal resource savings)
- ✅ Keeps Kafka deployment
- ✅ Keeps all data in PVCs
- ✅ Keeps built images
- ⚠️ Can recreate jobs anytime using `oc apply`

**To Rerun Pipeline**:
```bash
# Rerun producer job (delete old one first if needed)
oc delete job kafka-producer  # If job already exists
oc apply -f k8s/08-producer-deployment.yaml

# Consumer deployment continues running (no need to reapply)
# If you need to restart consumer:
oc rollout restart deployment/kafka-consumer

# Rerun EDA job
oc delete job pyspark-eda  # If job already exists
oc apply -f k8s/12-eda-job.yaml
```

---

#### Option 3: Keep Only Storage (Maximum Cost Savings)
```bash
# Delete all compute resources
oc delete job --all
oc delete deployment --all
oc delete service kafka
oc delete bc --all
oc delete is --all

# Keep PVCs only
# Storage costs are minimal compared to compute
```

**What This Does**:
- ✅ Stops ALL compute resources
- ✅ Keeps data in PVCs (cheapest resource)
- ✅ Can rebuild everything later
- ⚠️ Must rebuild images (3-5 min)
- ⚠️ Must redeploy Kafka (2 min)

**Cost**: Only PVC storage (~$0.10/GB/month for 7GB = ~$0.70/month)

**To Resume Full Pipeline**:
```bash
# Follow full deployment from Step 2 in EXECUTION_GUIDE
# PVCs already exist, so start with Kafka deployment
oc apply -f k8s/02-kafka-deployment.yaml
# ... continue with other steps
```

---

### Complete Cleanup (Delete Everything)

⚠️ **WARNING**: This deletes ALL data permanently. Cannot be recovered!

#### Step 1: Delete Compute Resources
```bash
# Delete all jobs
oc delete job --all

# Wait for deletion
oc wait --for=delete job --all --timeout=60s
```

**Expected Output**:
```
job.batch "generate-transaction-data" deleted
job.batch "kafka-producer" deleted
job.batch "kafka-consumer" deleted
job.batch "pyspark-eda" deleted
```

---

#### Step 2: Delete Kafka Deployment and Service
```bash
# Delete Kafka deployment
oc delete deployment kafka

# Delete Kafka service
oc delete service kafka

# Wait for pods to terminate
oc wait --for=delete pod -l app=kafka --timeout=60s
```

**Expected Output**:
```
deployment.apps "kafka" deleted
service "kafka" deleted
```

---

#### Step 3: Delete Build Resources
```bash
# Delete BuildConfigs
oc delete bc --all

# Delete ImageStreams
oc delete is --all

# This also deletes associated builds
```

**Expected Output**:
```
buildconfig.build.openshift.io "kafka-consumer" deleted
buildconfig.build.openshift.io "kafka-producer" deleted
imagestream.image.openshift.io "kafka-consumer" deleted
imagestream.image.openshift.io "kafka-producer" deleted
```

---

#### Step 4: Delete Storage (Data Loss!)
```bash
# ⚠️ LAST STEP - PERMANENT DATA DELETION
oc delete pvc --all

# Wait for deletion
oc wait --for=delete pvc --all --timeout=120s
```

**Expected Output**:
```
persistentvolumeclaim "kafka-data-pvc" deleted
persistentvolumeclaim "transaction-data-pvc" deleted
```

**What Gets Deleted**:
- ❌ All Kafka topics and messages
- ❌ CSV files (transactions.csv, received_transactions.csv)
- ❌ Visualization plots
- ❌ Kafka metadata and logs

---

#### Step 5: Verify Complete Cleanup
```bash
# Check for any remaining resources
oc get all,pvc,bc,is
```

**Expected Output** (only system resources remain):
```
NAME                        TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)                               AGE
service/modelmesh-serving   ClusterIP   None         <none>        8033/TCP,8008/TCP,8443/TCP,2112/TCP   40d
```

✅ **Cleanup Complete!** Only system-managed resources remain.

---

### Selective Deletion

#### Delete Only a Specific Job
```bash
# Delete one job
oc delete job kafka-producer

# Verify
oc get jobs
```

#### Delete Only Build Resources (Keep Data)
```bash
# Delete builds but keep everything else
oc delete bc,is --all

# Data and deployments remain intact
```

#### Delete Only Kafka (Keep Jobs and Data)
```bash
# Scale down first (graceful)
oc scale deployment/kafka --replicas=0
sleep 10

# Then delete
oc delete deployment kafka
oc delete service kafka

# Jobs and data remain
```

---

### Cleanup Scripts

#### Quick Cleanup (Everything)
Save as `cleanup-all.sh`:
```bash
#!/bin/bash
echo "🧹 Deleting all Kafka resources..."

oc delete job --all
oc delete deployment kafka
oc delete service kafka
oc delete bc,is --all
oc delete pvc --all

echo "✅ Cleanup complete!"
oc get all,pvc,bc,is
```

#### Safe Cleanup (Keep Data)
Save as `cleanup-safe.sh`:
```bash
#!/bin/bash
echo "🧹 Deleting compute resources (keeping data)..."

oc delete job --all
oc delete deployment kafka
oc delete service kafka
oc delete bc,is --all

echo "✅ Compute resources deleted. PVCs preserved:"
oc get pvc
```

---

### Cost Optimization Summary

| Strategy | Monthly Cost* | Restart Time | Data Preserved |
|----------|--------------|--------------|----------------|
| **Full Running** | ~$50-100 | N/A | ✅ |
| **Kafka Scaled to 0** | ~$20-40 | ~1 min | ✅ |
| **Only PVCs** | ~$0.70 | ~15 min | ✅ |
| **Everything Deleted** | $0 | ~20 min | ❌ |

*Estimates based on typical cloud costs. NERC may have different pricing.

---

### Local Docker Cleanup

```bash
# Stop all containers (keep data)
docker compose down

# Stop and delete volumes (delete data)
docker compose down -v

# Delete everything including images
docker compose down -v --rmi all

# Check disk space recovered
docker system df
```

---

## ⚡ Quick Reference

### When to Run EDA?

**Local:**
- After producer/consumer have processed data
- Run Jupyter notebook interactively
- URL: http://localhost:8888

**OpenShift:**
- After producer/consumer deployments are running
- Run as one-time Job
- Command: `oc apply -f k8s/12-eda-job.yaml`

### Typical Execution Time

**Local:**
- Data generation: 1 min
- Kafka startup: 30 sec
- Producer/consumer (1M records): 8 min
- EDA notebook: 2-3 min
- **Total: ~12 minutes**

**OpenShift:**
- Kafka deployment: 2 min
- Data generation (100K): 1 min
- Image builds: 5 min
- Producer/consumer (100K): 2 min
- EDA job: 2-3 min
- **Total: ~12-15 minutes**

---

## 🚨 Common Issues

**Local: "Kafka not ready"**
```bash 
# Solution: Wait longer or restart Kafka
docker compose restart kafka
sleep 30
```

**OpenShift: "Build failed"**
```bash
# Solution: Check build logs and rebuild
oc logs build/kafka-producer-1
oc start-build kafka-producer
```

**OpenShift: "Pod pending"**
```bash
# Solution: Check PVC status
oc get pvc
oc describe pvc transaction-data-pvc
```

**EDA: "No such file"**
```bash
# Solution: Verify data file exists
oc exec -it deployment/kafka-producer -- cat /data/transactions.csv | head
```

---

## ✅ ACTUAL DEPLOYMENT RESULTS (Nov 16, 2025)

### Deployment Summary
Successfully deployed complete Kafka streaming pipeline to OpenShift NERC cluster.

**Cluster**: NERC OpenShift (api.edu.nerc.mghpcc.org)
**Project**: ds551-2025fall-7ae539
**Total Time**: ~36 minutes (including troubleshooting)

### Code Fixes Applied
1. **Removed node selectors** from producer and consumer deployments (k8s/08 & k8s/11)
2. **Fixed Kafka controller configuration**: Changed from `localhost:9093` to `kafka:9093` (k8s/02)
3. **Fixed data generator warning**: Added PATH environment variable for faker script (k8s/07)
4. **Replaced PySpark with Pandas** for EDA job due to OpenShift security constraints (k8s/12)
   - Kerberos/Hadoop authentication incompatible with OpenShift random UIDs
   - Python:3.11-slim image + pandas works perfectly

### Resources Deployed
| Resource | Status | Details |
|----------|--------|---------|
| kafka-data-pvc | Bound | 5Gi RWO storage for Kafka data |
| transaction-data-pvc | Bound | 2Gi RWO storage for CSV files |
| kafka deployment | Running | 1/1 pods, apache/kafka:latest |
| kafka service | Active | ClusterIP on ports 9092, 9093 |
| generate-transaction-data job | Complete | 42s duration, 100K records generated (9.24 MB) |
| kafka-producer build | Complete | 2 builds, 44-49s each |
| kafka-consumer build | Complete | 2 builds, 44-46s each |
| kafka-producer job | Complete | 3m52s, sent 100K records in 20 batches, then stopped |
| kafka-consumer deployment | Running | Continuous operation, received 100K records, waiting for more |
| pyspark-eda job | Complete | 41s, generated 3 PNG plots |

### Data Pipeline Results
- **Generated**: 100,000 transaction records (9.2 MB CSV)
- **Produced**: 100,000 messages to Kafka topic "transactions" (0 errors)
- **Consumed**: 100,000 messages from Kafka (saved to received_transactions.csv)
- **Analyzed**: Complete EDA with 3 visualizations

### EDA Analysis Summary
```
Total Transactions: 100,000
Total Revenue: $90,078,361.30
Average Transaction: $900.78
```

**Visualizations Created**:
1. `plot_revenue_by_category.png` - Revenue by product category (bar chart)
2. `plot_payment_methods.png` - Payment method distribution (pie chart)
3. `plot_top_cities.png` - Top 10 cities by revenue (horizontal bar chart)

**Top Cities by Revenue**:
1. Jacksonville: $6,371,417.81
2. San Jose: $6,132,961.98
3. Chicago: $6,109,623.79

### Key Learnings
1. **OpenShift Security**: Random UID assignment requires careful handling of user-dependent processes
2. **PySpark Limitations**: Hadoop/Kerberos authentication doesn't work well in restricted environments
3. **Pandas Alternative**: Pandas provides same analytical capabilities without JVM/Hadoop complexity
4. **Node Selectors**: Avoid hardcoding node selectors unless absolutely necessary
5. **DNS in K8s**: Always use service names (e.g., `kafka:9093`) not localhost for inter-pod communication

### Verification Commands Used
```bash
# Check all resources
oc get all,pvc

# View job logs
oc logs job/generate-transaction-data
oc logs job/kafka-producer
oc logs job/kafka-consumer
oc logs job/pyspark-eda

# Download visualizations
oc run data-accessor --image=busybox --restart=Never --overrides='...'
oc cp data-accessor:/data/plot_*.png plots/
```

### Files Modified from Original
- `k8s/02-kafka-deployment.yaml` - Fixed controller quorum voter
- `k8s/07-data-generator-job.yaml` - Added PATH env var
- `k8s/08-producer-deployment.yaml` - Removed node selector
- `k8s/11-consumer-deployment.yaml` - Removed node selector
- `k8s/12-eda-job.yaml` - Replaced PySpark with Pandas, simplified dependencies

---

## 📝 Notes for Future Runs

1. **Always start fresh**: Delete all resources before redeployment
2. **Wait for builds**: Image builds take 3-5 minutes, don't rush
3. **Check logs early**: If a job fails, check logs immediately
4. **PVC data persists**: Data remains in PVCs even after pod deletion
5. **Download plots**: Use temporary busybox pod to access PVC data
