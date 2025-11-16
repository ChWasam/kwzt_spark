# Deploying Custom PySpark EDA Image to OpenShift

This guide walks through deploying the custom PySpark EDA solution that fixes Hadoop authentication issues in OpenShift.

## What We Built

### Problem
- Standard Spark images (`jupyter/pyspark-notebook`, `bitnami/spark`) fail with Kerberos authentication errors in OpenShift
- OpenShift runs containers with random UIDs (e.g., 1001520000) that don't exist in `/etc/passwd`
- Hadoop's `UnixLoginModule` cannot find user information and throws `NullPointerException`

### Solution
Custom Docker image with:
- **Pre-configured Hadoop**: `core-site.xml` baked into image with authentication disabled
- **OpenShift UID support**: Entrypoint script adds random UID to `/etc/passwd` at runtime
- **RawLocalFileSystem**: Bypasses user permission checks
- **All dependencies included**: PySpark, pandas, matplotlib, seaborn

## Files Created

```
eda/
├── Dockerfile              # Custom image definition
├── eda_analysis.py        # PySpark EDA script
└── README.md              # Documentation

k8s/
├── 12-eda-job.yaml        # Updated job (now uses custom image)
├── 13-eda-imagestream.yaml # ImageStream for custom image
└── 14-eda-buildconfig.yaml # BuildConfig to build from GitHub
```

## Prerequisites

Before deploying, ensure:

1. **Git repository is updated** with the new `eda/` directory
   ```bash
   git add eda/ k8s/12-eda-job.yaml k8s/13-eda-imagestream.yaml k8s/14-eda-buildconfig.yaml
   git commit -m "Add custom PySpark EDA image for OpenShift"
   git push origin main
   ```

2. **Consumer job has completed** and data file exists
   ```bash
   oc get job kafka-consumer
   # Should show "1/1" completions
   ```

3. **OpenShift is logged in**
   ```bash
   oc whoami
   # Should show your username
   ```

## Deployment Steps

### Step 1: Create ImageStream

```bash
oc apply -f k8s/13-eda-imagestream.yaml
```

Expected output:
```
imagestream.image.openshift.io/pyspark-eda-custom created
```

Verify:
```bash
oc get is pyspark-eda-custom
```

### Step 2: Create BuildConfig

```bash
oc apply -f k8s/14-eda-buildconfig.yaml
```

Expected output:
```
buildconfig.build.openshift.io/pyspark-eda-custom created
```

Verify:
```bash
oc get bc pyspark-eda-custom
```

### Step 3: Start the Build

```bash
oc start-build pyspark-eda-custom
```

Expected output:
```
build.build.openshift.io/pyspark-eda-custom-1 started
```

### Step 4: Monitor the Build

```bash
oc logs -f bc/pyspark-eda-custom
```

The build will:
1. Clone your GitHub repository
2. Download Python base image
3. Install OpenJDK 17
4. Download Apache Spark 3.5.0 (~400MB)
5. Install Python packages
6. Create Hadoop configuration
7. Build final image

**Expected duration:** 5-10 minutes (depending on network speed)

Check build status:
```bash
oc get builds
```

Should eventually show:
```
NAME                     TYPE     FROM   STATUS     STARTED          DURATION
pyspark-eda-custom-1     Docker   Git    Complete   5 minutes ago    8m23s
```

### Step 5: Verify Image is Ready

```bash
oc get is pyspark-eda-custom
```

Should show:
```
NAME                  IMAGE REPOSITORY                                                              TAGS     UPDATED
pyspark-eda-custom    image-registry.openshift-image-registry.svc:5000/.../pyspark-eda-custom      latest   5 minutes ago
```

### Step 6: Delete Old Failed Jobs (if any)

```bash
oc delete job pyspark-eda --ignore-not-found=true
```

### Step 7: Deploy the EDA Job

```bash
oc apply -f k8s/12-eda-job.yaml
```

Expected output:
```
job.batch/pyspark-eda created
```

### Step 8: Monitor the Job

```bash
oc logs -f job/pyspark-eda
```

Expected output:
```
================================================================================
 PySpark EDA Job - Transaction Analysis
================================================================================

Input file found: /data/received_transactions.csv
File size: 9.30 MB

Initializing Spark Session...
Spark Session initialized successfully!

Loading data from /data/received_transactions.csv...
Data loaded successfully: 100,000 records
Schema:
root
 |-- transaction_id: string (nullable = true)
 |-- timestamp: timestamp (nullable = true)
 |-- customer_id: string (nullable = true)
 |-- product_id: string (nullable = true)
 |-- product_category: string (nullable = true)
 |-- quantity: integer (nullable = true)
 |-- price: double (nullable = true)
 |-- total_amount: double (nullable = true)
 |-- payment_method: string (nullable = true)
 |-- city: string (nullable = true)
 |-- country: string (nullable = true)

================================================================================
 ANALYSIS 1: Sales by Product Category
================================================================================
product_category  num_transactions  total_revenue
     Electronics            10123    1234567.89
     ...

================================================================================
 ANALYSIS 2: Payment Method Distribution
================================================================================
payment_method  num_transactions
   Credit Card            45678
   ...

================================================================================
 ANALYSIS 3: Top 10 Cities by Revenue
================================================================================
       city  num_transactions  total_revenue
   New York              5432    678901.23
   ...

================================================================================
 GENERATING VISUALIZATIONS
================================================================================
✓ Saved: /data/plot_revenue_by_category.png
✓ Saved: /data/plot_payment_methods.png
✓ Saved: /data/plot_top_cities.png

================================================================================
 ANALYSIS SUMMARY
================================================================================
 Total Transactions : 100,000
 Total Revenue      : $12,345,678.90
 Average Transaction: $123.46
================================================================================

✅ EDA Complete! All outputs saved to /data/

Spark session stopped. Job completed successfully.
```

### Step 9: Check Job Completion

```bash
oc get job pyspark-eda
```

Should show:
```
NAME           COMPLETIONS   DURATION   AGE
pyspark-eda    1/1           2m15s      3m
```

## Downloading the Generated Plots

```bash
# Create temporary pod with data volume access
oc run data-accessor --image=busybox --restart=Never --overrides='{
  "spec": {
    "containers": [{
      "name": "data-accessor",
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

# Wait for pod to be ready
oc wait --for=condition=ready pod/data-accessor --timeout=60s

# Create local plots directory
mkdir -p plots

# Download plots
oc cp data-accessor:/data/plot_revenue_by_category.png ./plots/
oc cp data-accessor:/data/plot_payment_methods.png ./plots/
oc cp data-accessor:/data/plot_top_cities.png ./plots/

# Cleanup
oc delete pod data-accessor

# View plots
open plots/plot_revenue_by_category.png
open plots/plot_payment_methods.png
open plots/plot_top_cities.png
```

## Troubleshooting

### Build Fails with "repository not found"

Check GitHub URL in `k8s/14-eda-buildconfig.yaml`:
```bash
grep "uri:" k8s/14-eda-buildconfig.yaml
```

Should match your GitHub repository. Update if needed:
```yaml
source:
  git:
    uri: https://github.com/YOUR_USERNAME/YOUR_REPO.git  # Update this
    ref: main
```

### Build Fails with "Dockerfile not found"

Ensure the `eda/` directory is pushed to GitHub:
```bash
git status
git add eda/
git commit -m "Add custom PySpark EDA image"
git push origin main
```

### Job Pod Won't Start

Check image reference:
```bash
oc describe job pyspark-eda | grep Image:
```

Should show:
```
Image: image-registry.openshift-image-registry.svc:5000/ds551-2025fall-7ae539/pyspark-eda-custom:latest
```

### Still Getting Hadoop Authentication Errors

This should NOT happen with the custom image. If it does:

1. Check that the build completed successfully:
   ```bash
   oc get builds
   ```

2. Verify core-site.xml was created in the image:
   ```bash
   oc run test-image --rm -it --image=image-registry.openshift-image-registry.svc:5000/ds551-2025fall-7ae539/pyspark-eda-custom:latest --command -- cat /opt/spark/conf/hadoop-conf/core-site.xml
   ```

3. Check Spark configuration in logs:
   ```bash
   oc logs job/pyspark-eda | grep -i hadoop
   ```

### Data File Not Found

Ensure consumer job completed:
```bash
oc get job kafka-consumer
```

Check file exists:
```bash
oc get pods | grep kafka-consumer
oc exec -it kafka-consumer-XXXXX -- ls -lh /data/received_transactions.csv
```

## Cleanup

To remove everything and start fresh:

```bash
# Delete job
oc delete job pyspark-eda

# Delete build config and image stream
oc delete bc pyspark-eda-custom
oc delete is pyspark-eda-custom

# Delete all builds
oc delete builds -l buildconfig=pyspark-eda-custom
```

## Next Steps

1. Update your project documentation (README.md, CLAUDE.md) with this solution
2. Commit and push all changes to GitHub
3. Consider using this pattern for other Spark jobs in OpenShift
4. Document lessons learned about OpenShift security contexts

## Key Learnings

1. **OpenShift Security Model**: Random UIDs require special handling in containers
2. **Hadoop Configuration**: Can be pre-baked into Docker images for consistency
3. **Custom Images**: Provide better control than trying to patch public images at runtime
4. **BuildConfigs**: OpenShift's native way to build images from Git repositories
5. **RawLocalFileSystem**: Key to bypassing Hadoop's user permission checks

This solution demonstrates a production-ready approach to running Spark workloads in OpenShift!
