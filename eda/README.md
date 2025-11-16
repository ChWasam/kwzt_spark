# Custom PySpark EDA Docker Image

This directory contains a custom Docker image for running PySpark EDA jobs in OpenShift.

## Problem Solved

The standard `jupyter/pyspark-notebook` and `bitnami/spark` images have Hadoop authentication issues when running with OpenShift's random UID security model. This custom image:

- Pre-configures Hadoop to disable Kerberos authentication
- Uses `RawLocalFileSystem` to bypass user authentication checks
- Supports OpenShift's arbitrary UID assignment
- Includes all necessary Python packages (pyspark, pandas, matplotlib, seaborn)

## Files

- **Dockerfile**: Custom image definition
  - Base: `python:3.11-slim-bookworm`
  - Installs: OpenJDK 17, Apache Spark 3.5.0, Python packages
  - Pre-configures: Hadoop core-site.xml for simple authentication
  - Supports: OpenShift random UIDs via entrypoint script

- **eda_analysis.py**: PySpark EDA script
  - Loads CSV data from `/data/received_transactions.csv`
  - Performs analysis: category sales, payment methods, top cities
  - Generates matplotlib visualizations saved to `/data/`
  - Hardcoded Spark configs to bypass Hadoop authentication

## Building Locally (Optional)

```bash
cd eda/
docker build -t pyspark-eda-custom:latest .
docker run --rm -v $(pwd)/test-data:/data pyspark-eda-custom:latest
```

## Deploying to OpenShift

```bash
# 1. Create ImageStream
oc apply -f k8s/13-eda-imagestream.yaml

# 2. Create BuildConfig
oc apply -f k8s/14-eda-buildconfig.yaml

# 3. Start build (builds from GitHub, takes ~5-10 minutes)
oc start-build pyspark-eda-custom

# 4. Monitor build
oc logs -f bc/pyspark-eda-custom

# 5. Verify image is ready
oc get is pyspark-eda-custom

# 6. Run the EDA job
oc apply -f k8s/12-eda-job.yaml

# 7. Monitor job
oc logs -f job/pyspark-eda

# 8. Download generated plots
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
```

## Key Configurations

### Hadoop core-site.xml (baked into image)
```xml
<configuration>
  <property>
    <name>hadoop.security.authentication</name>
    <value>simple</value>
  </property>
  <property>
    <name>hadoop.security.authorization</name>
    <value>false</value>
  </property>
  <property>
    <name>fs.file.impl</name>
    <value>org.apache.hadoop.fs.RawLocalFileSystem</value>
  </property>
</configuration>
```

### Spark Configuration (in eda_analysis.py)
```python
spark = (SparkSession.builder
    .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.RawLocalFileSystem")
    .config("spark.hadoop.hadoop.security.authentication", "simple")
    .config("spark.hadoop.hadoop.security.authorization", "false")
    .config("spark.authenticate", "false")
    .getOrCreate())
```

## Deployment Results

Successfully deployed and tested on OpenShift with the following results:

**Analysis Summary:**
- Total Transactions: 100,000
- Total Revenue: $89,599,149.32
- Average Transaction: $895.99

**Top Product Category by Revenue:**
- Electronics: $30,230,238.29 (9,928 transactions)

**Payment Method Distribution:**
- Credit Card: 20,122 transactions
- PayPal: 20,096 transactions
- Debit Card: 20,029 transactions
- Google Pay: 19,901 transactions
- Apple Pay: 19,852 transactions

**Top City by Revenue:**
- Chicago: $6,186,490.45 (6,838 transactions)

**Generated Visualizations:**
- `plot_revenue_by_category.png` (80KB)
- `plot_payment_methods.png` (71KB)
- `plot_top_cities.png` (49KB)

**Build Time:** ~5-10 minutes
**Job Execution Time:** ~60 seconds (for 100K records)

## OpenShift UID Handling

The Dockerfile includes an entrypoint script that adds the random OpenShift UID to `/etc/passwd` at runtime:

```bash
#!/bin/bash
if ! whoami &> /dev/null; then
  if [ -w /etc/passwd ]; then
    echo "spark:x:$(id -u):0:spark user:${HOME}:/sbin/nologin" >> /etc/passwd
  fi
fi
exec "$@"
```

This ensures Hadoop's `UnixLoginModule` can find a username for the random UID.

## Troubleshooting

**Build fails:**
- Check GitHub URL in `k8s/14-eda-buildconfig.yaml`
- Ensure `eda/` directory is pushed to Git
- Check build logs: `oc logs -f bc/pyspark-eda-custom`

**Job fails to start:**
- Verify image exists: `oc get is pyspark-eda-custom`
- Check image pull policy is `Always`
- Verify PVC exists: `oc get pvc transaction-data-pvc`

**Hadoop authentication error:**
- This should NOT happen with this custom image
- If it does, check that core-site.xml was created correctly
- Verify HADOOP_CONF_DIR points to `/opt/spark/conf/hadoop-conf`

**Data file not found:**
- Ensure consumer job completed: `oc get job kafka-consumer`
- Check file exists: `oc exec -it <consumer-pod> -- ls -lh /data/`
