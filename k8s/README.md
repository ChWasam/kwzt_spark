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

## YAML Files (in deployment order)

### 1. Storage
- **`01-kafka-pvc.yaml`** - PersistentVolumeClaim for Kafka data (5Gi)
- **`06-data-pvc.yaml`** - PersistentVolumeClaim for transaction CSV files (2Gi)

### 2. Kafka Broker
- **`02-kafka-deployment.yaml`** - Kafka broker deployment (KRaft mode, 1 replica)
  - Resources: 500m-1 CPU, 2-3Gi RAM
- **`03-kafka-service.yaml`** - Kafka service (ClusterIP, port 9092)

### 3. Data Generation
- **`07-data-generator-job.yaml`** - Job to generate 100K transaction records
  - Resources: 250m-500m CPU, 512Mi-1Gi RAM
  - Outputs: `/data/transactions.csv`

### 4. Producer
- **`04-producer-buildconfig.yaml`** - BuildConfig for producer image
  - Builds from Git repository
  - Context: `producer/` directory
- **`05-producer-imagestream.yaml`** - ImageStream for producer
- **`08-producer-deployment.yaml`** - Producer deployment (1 replica)
  - Resources: 250m-500m CPU, 512Mi-1Gi RAM
  - Reads CSV and sends to Kafka topic `transactions`

### 5. Consumer
- **`09-consumer-buildconfig.yaml`** - BuildConfig for consumer image
  - Builds from Git repository
  - Context: `consumer/` directory
- **`10-consumer-imagestream.yaml`** - ImageStream for consumer
- **`11-consumer-deployment.yaml`** - Consumer Job (despite filename)
  - **Type**: Job (one-time execution, batch processing)
  - Resources: 100m-500m CPU, 512Mi-1Gi RAM
  - Receives from Kafka and writes to `/data/received_transactions.csv`
  - **Behavior**: Receives 100K messages then stops (MAX_MESSAGES=100000, consumer_timeout_ms=60000)

### 6. EDA (Exploratory Data Analysis)
- **`12-eda-job.yaml`** - PySpark EDA job
  - Resources: 500m-1 CPU, 3-4Gi RAM
  - Performs analysis and generates visualizations
  - Outputs:
    - `/data/plot_revenue_by_category.png`
    - `/data/plot_payment_methods.png`
    - `/data/plot_top_cities.png`

### 7. Combined
- **`all-resources.yaml`** - All resources in one file (for convenience)

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

### Manual Deployment
```bash
# 1. Login to OpenShift
oc login --server=<server-url> --token=<your-token>

# 2. Switch to your project
oc project ds551-2025fall-7ae539

# 3. Create PVCs
oc apply -f 01-kafka-pvc.yaml
oc apply -f 06-data-pvc.yaml

# 4. Deploy Kafka
oc apply -f 02-kafka-deployment.yaml
oc apply -f 03-kafka-service.yaml

# Wait for Kafka to be ready
oc wait --for=condition=available --timeout=300s deployment/kafka

# 5. Generate data
oc apply -f 07-data-generator-job.yaml
oc wait --for=condition=complete --timeout=300s job/generate-transaction-data

# 6. Create ImageStreams and BuildConfigs
oc apply -f 05-producer-imagestream.yaml
oc apply -f 10-consumer-imagestream.yaml
oc apply -f 04-producer-buildconfig.yaml
oc apply -f 09-consumer-buildconfig.yaml

# 7. Start builds
oc start-build kafka-producer
oc start-build kafka-consumer

# Wait for builds to complete
oc logs -f bc/kafka-producer
oc logs -f bc/kafka-consumer

# 8. Deploy Producer and Consumer
oc apply -f 08-producer-deployment.yaml
oc apply -f 11-consumer-deployment.yaml

# 9. Run EDA
oc apply -f 12-eda-job.yaml
oc wait --for=condition=complete --timeout=600s job/pyspark-eda
```

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
