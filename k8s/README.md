# Kubernetes YAML Files for OpenShift Deployment

## Overview
This directory contains all Kubernetes/OpenShift manifests needed to deploy the Kafka + PySpark assignment to NERC OpenShift.

## Resource Summary

**Total Resource Usage:**
- **CPU**: 1.5 cores (requests), 3 cores (limits)
- **Memory**: 6Gi (requests), 9Gi (limits)
- **Storage**: 7Gi (5Gi Kafka + 2Gi data)
- **PVCs**: 2

**Fits within NERC quota:**
- ✅ CPU: 3 cores max
- ✅ Memory: 12Gi max
- ✅ Storage: 20Gi max
- ✅ PVCs: 4 max

---

## YAML Files (in correct deployment order)

**IMPORTANT:** Deploy in this exact order for successful deployment.

### Phase 1: Storage (PVCs First)
1. **`01-kafka-pvc.yaml`** - PersistentVolumeClaim for Kafka data (5Gi, RWO)
2. **`06-data-pvc.yaml`** - PersistentVolumeClaim for transaction CSV files (2Gi, RWO)

### Phase 2: Kafka Service & Data Generation
3. **`03-kafka-service.yaml`** - Kafka service (ClusterIP, port 9092)
   - **Must create BEFORE Kafka deployment** (service name used in Kafka config)
4. **`07-data-generator-job.yaml`** - Job to generate 100K transaction records
   - Resources: 250m-500m CPU, 512Mi-1Gi RAM
   - Outputs: `/data/transactions.csv` (9.24 MB)
   - Time: ~30-60 seconds
5. **`02-kafka-deployment.yaml`** - Kafka broker deployment (KRaft mode, 1 replica)
   - Resources: 500m-1000m CPU, 2-3Gi RAM
   - **Critical Config:** `KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093` (uses service name, not localhost)
   - Time: ~1-2 minutes to start

### Phase 3: Producer Build & Deploy
6. **`05-producer-imagestream.yaml`** - ImageStream for producer (must create before BuildConfig)
7. **`04-producer-buildconfig.yaml`** - BuildConfig for producer image
   - Builds from Git repository `producer/` directory
   - Update Git URL before deploying!
   - Build time: ~2-3 minutes
8. **`08-producer-deployment.yaml`** - Producer **Job** (despite filename)
   - **Type:** Job (one-time execution, not continuous)
   - Resources: 250m-500m CPU, 512Mi-1Gi RAM
   - Reads `/data/transactions.csv` and sends to Kafka topic `transactions`
   - **Behavior:** Sends 20 batches (5000 records each) = 100K total, then stops
   - Time: ~3-4 minutes

### Phase 4: Consumer Build & Deploy
9. **`10-consumer-imagestream.yaml`** - ImageStream for consumer (must create before BuildConfig)
10. **`09-consumer-buildconfig.yaml`** - BuildConfig for consumer image
    - Builds from Git repository `consumer/` directory
    - Update Git URL before deploying!
    - Build time: ~2-3 minutes
11. **`11-consumer-deployment.yaml`** - Consumer **Job** (despite filename)
    - **Type:** Job (one-time execution, batch processing, NOT continuous)
    - Resources: 100m-500m CPU, 512Mi-1Gi RAM
    - Receives from Kafka and writes to `/data/received_transactions.csv`
    - **Behavior:** Receives 100K messages then stops (MAX_MESSAGES=100000, consumer_timeout_ms=60000)
    - Time: ~10-12 minutes

### Phase 5: EDA Build & Deploy (Custom PySpark Image)
12. **`13-eda-imagestream.yaml`** - ImageStream for custom PySpark image
13. **`14-eda-buildconfig.yaml`** - BuildConfig for custom PySpark image
    - Builds from Git repository `eda/` directory
    - **Custom Dockerfile:** Includes Spark 3.5.0 + Java 17 + pre-configured Hadoop
    - **Solves:** OpenShift random UID + Hadoop authentication issues
    - Update Git URL before deploying!
    - Build time: ~5-10 minutes (downloads ~400MB Spark tarball)
14. **`12-eda-job.yaml`** - PySpark EDA Job
    - **Type:** Job (one-time execution)
    - Resources: 500m-1500m CPU, 2-4Gi RAM
    - Uses custom image: `pyspark-eda-custom:latest`
    - Performs analysis and generates 3 visualization plots
    - Outputs:
      - `/data/plot_revenue_by_category.png` (80KB)
      - `/data/plot_payment_methods.png` (71KB)
      - `/data/plot_top_cities.png` (49KB)
    - Time: ~60-90 seconds

---

## Deployment Instructions

### Prerequisites
1. Access to NERC OpenShift
2. `oc` CLI installed and configured
3. Project namespace: `ds551-2025fall-7ae539`
4. GitHub repository with code pushed

### Quick Deployment (Recommended)
```bash
# Make deploy script executable
chmod +x ../deploy.sh

# Run deployment script
../deploy.sh
```

### Manual Deployment (Correct Order)

```bash
# 1. Login to OpenShift
oc login --server=<server-url> --token=<your-token>
oc project ds551-2025fall-7ae539

# PHASE 1: Create PVCs (Storage First)
oc apply -f 01-kafka-pvc.yaml
oc apply -f 06-data-pvc.yaml

# PHASE 2: Kafka Service & Data Generation
oc apply -f 03-kafka-service.yaml           # Service BEFORE deployment
oc apply -f 07-data-generator-job.yaml      # Generate data
oc wait --for=condition=complete --timeout=300s job/generate-transaction-data

oc apply -f 02-kafka-deployment.yaml        # Kafka deployment
oc wait --for=condition=available --timeout=300s deployment/kafka

# PHASE 3: Producer Build & Deploy
oc apply -f 05-producer-imagestream.yaml    # ImageStream first
oc apply -f 04-producer-buildconfig.yaml    # BuildConfig second
oc start-build kafka-producer               # Start build
oc logs -f bc/kafka-producer                # Monitor build (~2-3 min)

oc apply -f 08-producer-deployment.yaml     # Deploy producer job
oc logs -f job/kafka-producer               # Monitor producer (~3-4 min)

# PHASE 4: Consumer Build & Deploy
oc apply -f 10-consumer-imagestream.yaml    # ImageStream first
oc apply -f 09-consumer-buildconfig.yaml    # BuildConfig second
oc start-build kafka-consumer               # Start build
oc logs -f bc/kafka-consumer                # Monitor build (~2-3 min)

oc apply -f 11-consumer-deployment.yaml     # Deploy consumer job
oc logs -f job/kafka-consumer               # Monitor consumer (~10-12 min)

# PHASE 5: EDA Build & Deploy
oc apply -f 13-eda-imagestream.yaml         # ImageStream first
oc apply -f 14-eda-buildconfig.yaml         # BuildConfig second
oc start-build pyspark-eda-custom           # Start build
oc logs -f bc/pyspark-eda-custom            # Monitor build (~5-10 min)

oc apply -f 12-eda-job.yaml                 # Deploy EDA job
oc logs -f job/pyspark-eda                  # Monitor EDA (~60-90 sec)

# Download plots
mkdir -p ../plots
oc run data-accessor --image=busybox --restart=Never --overrides='{
  "spec": {
    "containers": [{
      "name": "busybox",
      "image": "busybox",
      "command": ["sleep", "3600"],
      "volumeMounts": [{"name": "data", "mountPath": "/data"}]
    }],
    "volumes": [{
      "name": "data",
      "persistentVolumeClaim": {"claimName": "transaction-data-pvc"}
    }]
  }
}'
oc wait --for=condition=ready pod/data-accessor --timeout=60s
oc cp data-accessor:/data/plot_revenue_by_category.png ../plots/
oc cp data-accessor:/data/plot_payment_methods.png ../plots/
oc cp data-accessor:/data/plot_top_cities.png ../plots/
oc delete pod data-accessor
```

**Total Time:** ~30-40 minutes (including builds)

---

## Verification Commands

```bash
# Check all resources
oc get all

# Check PVCs
oc get pvc

# Check pod status
oc get pods

# View logs
oc logs deployment/kafka
oc logs job/kafka-producer        # Producer is a Job
oc logs job/kafka-consumer        # Consumer is a Job
oc logs job/pyspark-eda

# Check generated data (use completed pod name)
oc get pods | grep kafka-consumer  # Find the completed pod name
oc exec -it kafka-consumer-xxxxx -- ls -lh /data/

# View EDA plots (if you want to download them)
POD=$(oc get pods -l app=pyspark-eda -o jsonpath='{.items[0].metadata.name}')
oc cp $POD:/data/plot_revenue_by_category.png ./plot_revenue_by_category.png
oc cp $POD:/data/plot_payment_methods.png ./plot_payment_methods.png
oc cp $POD:/data/plot_top_cities.png ./plot_top_cities.png
```

---

## Troubleshooting

### Producer/Consumer not starting
```bash
# Check if images built successfully
oc get builds

# Check build logs
oc logs build/kafka-producer-1
oc logs build/kafka-consumer-1

# Restart builds if needed
oc start-build kafka-producer
oc start-build kafka-consumer
```

### Kafka not ready
```bash
# Check Kafka logs
oc logs deployment/kafka

# Check if PVC is bound
oc get pvc kafka-data-pvc

# Describe deployment for events
oc describe deployment kafka
```

### Data generation failed
```bash
# Check job logs
oc logs job/generate-transaction-data

# Check if PVC is bound
oc get pvc transaction-data-pvc

# Recreate job if needed
oc delete job generate-transaction-data
oc apply -f 07-data-generator-job.yaml
```

### EDA job failed
```bash
# Check job logs
oc logs job/pyspark-eda

# Check if data file exists (use completed pod name)
oc get pods | grep kafka-consumer
oc exec -it kafka-consumer-xxxxx -- ls -lh /data/

# Recreate job if needed
oc delete job pyspark-eda
oc apply -f 12-eda-job.yaml
```

---

## Cleanup

```bash
# Delete all resources
oc delete all -l app=kafka
oc delete all -l app=kafka-producer
oc delete all -l app=kafka-consumer
oc delete all -l app=pyspark-eda
oc delete all -l app=data-generator

# Delete PVCs (this will delete all data!)
oc delete pvc kafka-data-pvc
oc delete pvc transaction-data-pvc

# Delete ImageStreams and BuildConfigs
oc delete imagestream kafka-producer kafka-consumer
oc delete buildconfig kafka-producer kafka-consumer
```

---

## Important Notes

1. **GitHub URL**: Update the Git repository URL in:
   - `04-producer-buildconfig.yaml`
   - `09-consumer-buildconfig.yaml`

   Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username.

2. **Namespace**: All image references use:
   ```
   image-registry.openshift-image-registry.svc:5000/ds551-2025fall-7ae539/<image-name>:latest
   ```

   If your namespace is different, update the deployment YAML files.

3. **Resource Limits**: All resources are configured to fit within your quota:
   - CPU: 3 cores total
   - Memory: 12Gi total
   - Storage: 20Gi total

4. **Data Size**: The data generator creates 100K records (vs 1M locally) to ensure:
   - Faster generation time
   - Lower storage usage
   - Faster EDA processing

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenShift Cluster                        │
│                                                             │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │   Kafka PVC  │        │  Data PVC    │                  │
│  │   (5Gi)      │        │  (2Gi)       │                  │
│  └──────┬───────┘        └───────┬──────┘                  │
│         │                        │                         │
│  ┌──────▼───────┐        ┌───────▼──────────┐              │
│  │   Kafka      │        │  Data Generator  │              │
│  │  Deployment  │        │     (Job)        │              │
│  │  (1 replica) │        │  Generates CSV   │              │
│  └──────┬───────┘        └───────┬──────────┘              │
│         │                        │                         │
│  ┌──────▼───────┐                │                         │
│  │   Kafka      │                │                         │
│  │   Service    │◄───────────────┘                         │
│  │  (kafka:9092)│                                          │
│  └──────┬───────┘                                          │
│         │                                                  │
│    ┌────▼────┐                                             │
│    │         │                                             │
│┌───▼────┐ ┌──▼──────────┐ ┌────────────┐                  │
││Producer│ │  Consumer   │ │ PySpark EDA│                   │
││  Job   │ │    Job      │ │   (Job)    │                   │
││        │ │             │ │            │                   │
││Sends   │ │Receives     │ │  Analyzes  │                   │
││20 batch│ │100K msgs    │ │   Data &   │                   │
││then    │ │then stops   │ │  Creates   │                   │
││stops   │ │             │ │  Plots     │                   │
│└────────┘ └─────────────┘ └────────────┘                   │
│                                                             │
│  Architecture Pattern (Batch Processing):                  │
│  - Producer: Job (sends 20 batches, stops)                 │
│  - Consumer: Job (receives 100K messages, stops)           │
│  - Kafka: Deployment (persistent broker)                   │
└─────────────────────────────────────────────────────────────┘
```

---

**Questions?** Check the main README.md or contact the course TA.
