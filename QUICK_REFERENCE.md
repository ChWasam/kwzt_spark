# Quick Reference Guide
## Kafka + PySpark Pipeline on OpenShift

**For:** Quick deployment without reading full documentation

---

## Prerequisites Check

```bash
# 1. Login to OpenShift
oc login --server=https://api.edu.nerc.mghpcc.org:6443 --token=YOUR_TOKEN
oc project ds551-2025fall-7ae539

# 2. Verify quota
oc describe quota
# Should have: CPU 3 cores, Memory 12Gi, Storage 20Gi

# 3. Update GitHub URLs in:
# - k8s/04-producer-buildconfig.yaml (line 16)
# - k8s/09-consumer-buildconfig.yaml (line 16)
# - k8s/14-eda-buildconfig.yaml (line 16)
```

---

## Deployment (5 Phases) - Copy & Paste

### Phase 1: Storage (30 seconds)
```bash
oc apply -f k8s/01-kafka-pvc.yaml
oc apply -f k8s/06-data-pvc.yaml
oc get pvc  # Verify both are "Bound"
```

### Phase 2: Kafka & Data (2-3 minutes)
```bash
oc apply -f k8s/03-kafka-service.yaml
oc apply -f k8s/07-data-generator-job.yaml
oc wait --for=condition=complete --timeout=300s job/generate-transaction-data
oc apply -f k8s/02-kafka-deployment.yaml
oc wait --for=condition=available --timeout=300s deployment/kafka
```

### Phase 3: Producer (5-7 minutes)
```bash
oc apply -f k8s/05-producer-imagestream.yaml
oc apply -f k8s/04-producer-buildconfig.yaml
oc start-build kafka-producer
# Wait for build: oc get builds (should show "Complete")
oc apply -f k8s/08-producer-deployment.yaml
# Monitor: oc logs -f job/kafka-producer
```

### Phase 4: Consumer (12-15 minutes)
```bash
oc apply -f k8s/10-consumer-imagestream.yaml
oc apply -f k8s/09-consumer-buildconfig.yaml
oc start-build kafka-consumer
# Wait for build: oc get builds (should show "Complete")
oc apply -f k8s/11-consumer-deployment.yaml
# Monitor: oc logs -f job/kafka-consumer
```

### Phase 5: EDA (6-12 minutes)
```bash
oc apply -f k8s/13-eda-imagestream.yaml
oc apply -f k8s/14-eda-buildconfig.yaml
oc start-build pyspark-eda-custom
# Wait for build (~5-10 min): oc logs -f bc/pyspark-eda-custom
oc apply -f k8s/12-eda-job.yaml
# Monitor: oc logs -f job/pyspark-eda
```

**Total Time:** ~30-40 minutes

---

## Download Plots

```bash
mkdir -p plots

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

oc cp data-accessor:/data/plot_revenue_by_category.png ./plots/
oc cp data-accessor:/data/plot_payment_methods.png ./plots/
oc cp data-accessor:/data/plot_top_cities.png ./plots/

oc delete pod data-accessor

ls -lh plots/  # Verify 3 PNG files downloaded
```

---

## Verification Commands

```bash
# Check everything is running/completed
oc get all,pvc

# Should see:
# - deployment/kafka: READY 1/1
# - job/generate-transaction-data: COMPLETIONS 1/1
# - job/kafka-producer: COMPLETIONS 1/1
# - job/kafka-consumer: COMPLETIONS 1/1
# - job/pyspark-eda: COMPLETIONS 1/1
# - pvc/kafka-data-pvc: Bound
# - pvc/transaction-data-pvc: Bound

# Check final results
oc logs job/pyspark-eda | tail -20
# Should show: Total Transactions: 100,000
#              Total Revenue: $89,599,149.32
```

---

## Common Issues & Quick Fixes

### Build Failed
```bash
oc get builds
oc logs build/<build-name>  # Check error
oc start-build <name>  # Retry
```

### Pod Stuck in Pending
```bash
oc describe pod <pod-name>  # Check events
# Common: Image not ready → Wait for build to complete
```

### Job Failed
```bash
oc logs job/<job-name>  # Check error logs
oc delete job <job-name>  # Delete failed job
oc apply -f k8s/<XX-job.yaml>  # Recreate
```

### Kafka Won't Start
```bash
oc logs deployment/kafka
# Common error: Controller quorum voters
# Fix: Ensure k8s/02-kafka-deployment.yaml has:
# KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9093 (not localhost)
```

### PySpark Hadoop Error
```bash
# Error: "KerberosAuthException" or "NullPointerException"
# Fix: Ensure using custom image:
oc get is pyspark-eda-custom  # Verify image exists
# k8s/12-eda-job.yaml must use:
# image: ...pyspark-eda-custom:latest
```

---

## Cleanup

### Keep Data, Remove Compute
```bash
oc delete job --all
oc delete deployment kafka
oc delete svc kafka
oc delete bc,is --all
# PVCs remain (data persists)
```

### Complete Cleanup (WARNING: Deletes ALL data)
```bash
oc delete all --all
oc delete bc,is --all
oc delete pvc --all
```

---

## Expected Results

### Data Pipeline
- **Input:** 100,000 transactions (9.24 MB)
- **Output:** 3 visualization plots (200KB total)

### Analysis Summary
- Total Revenue: $89,599,149.32
- Average Transaction: $895.99
- Top Category: Electronics ($30.2M)
- Top Payment: Credit Card (20,122 transactions)
- Top City: Chicago ($6.2M)

### Files Generated
1. `/data/transactions.csv` - Original data (9.24 MB)
2. `/data/received_transactions.csv` - Consumed data (9.24 MB)
3. `/data/plot_revenue_by_category.png` (80KB)
4. `/data/plot_payment_methods.png` (71KB)
5. `/data/plot_top_cities.png` (49KB)

---

## Full Documentation

- **Complete Guide:** `docs/COMPLETE_DEPLOYMENT_GUIDE.md` (all errors + solutions)
- **Success Summary:** `DEPLOYMENT_SUCCESS.md`
- **Project Docs:** `CLAUDE.md`
- **Main README:** `README.md`
- **Kubernetes:** `k8s/README.md`
- **Custom Image:** `eda/README.md`

---

**Need Help?** Check `docs/COMPLETE_DEPLOYMENT_GUIDE.md` for detailed troubleshooting.
