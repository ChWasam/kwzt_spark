#!/bin/bash


set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project namespace (update if different)
NAMESPACE="ds551-2025fall-7ae539"

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}DS551 Kafka + PySpark - OpenShift Deployment${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# Check if logged in to OpenShift
echo -e "${YELLOW}[1/10]${NC} Checking OpenShift login status..."
if ! oc whoami &> /dev/null; then
    echo -e "${RED}❌ Not logged in to OpenShift!${NC}"
    echo "Please login first with: oc login --server=<server-url> --token=<your-token>"
    exit 1
fi
echo -e "${GREEN}✅ Logged in as: $(oc whoami)${NC}"
echo ""

# Verify namespace
echo -e "${YELLOW}[2/10]${NC} Verifying project namespace..."
oc project ${NAMESPACE}
echo ""

# Deploy PersistentVolumeClaims
echo -e "${YELLOW}[3/10]${NC} Creating PersistentVolumeClaims..."
oc apply -f k8s/01-kafka-pvc.yaml
oc apply -f k8s/06-data-pvc.yaml
echo -e "${GREEN}✅ PVCs created${NC}"
echo ""

# Deploy Kafka
echo -e "${YELLOW}[4/10]${NC} Deploying Kafka broker..."
oc apply -f k8s/02-kafka-deployment.yaml
oc apply -f k8s/03-kafka-service.yaml
echo -e "${GREEN}✅ Kafka deployed${NC}"
echo ""

# Wait for Kafka to be ready
echo -e "${YELLOW}[5/10]${NC} Waiting for Kafka to be ready (this may take 1-2 minutes)..."
oc wait --for=condition=available --timeout=300s deployment/kafka
echo -e "${GREEN}✅ Kafka is ready${NC}"
echo ""

# Generate transaction data
echo -e "${YELLOW}[6/10]${NC} Generating transaction data..."
oc apply -f k8s/07-data-generator-job.yaml
echo "Waiting for data generation to complete..."
oc wait --for=condition=complete --timeout=300s job/generate-transaction-data
echo -e "${GREEN}✅ Data generated${NC}"
echo ""

# Create ImageStreams
echo -e "${YELLOW}[7/10]${NC} Creating ImageStreams..."
oc apply -f k8s/05-producer-imagestream.yaml
oc apply -f k8s/10-consumer-imagestream.yaml
echo -e "${GREEN}✅ ImageStreams created${NC}"
echo ""

# Create and start BuildConfigs
echo -e "${YELLOW}[8/10]${NC} Creating BuildConfigs and building images..."
echo "NOTE: Make sure you've updated the GitHub URL in the BuildConfigs!"
oc apply -f k8s/04-producer-buildconfig.yaml
oc apply -f k8s/09-consumer-buildconfig.yaml

echo "Starting builds..."
oc start-build kafka-producer
oc start-build kafka-consumer

echo "Waiting for builds to complete (this may take 3-5 minutes)..."
oc wait --for=condition=complete --timeout=600s build/kafka-producer-1 || true
oc wait --for=condition=complete --timeout=600s build/kafka-consumer-1 || true
echo -e "${GREEN}✅ Images built${NC}"
echo ""

# Deploy Producer and Consumer
echo -e "${YELLOW}[9/10]${NC} Deploying Producer and Consumer..."
oc apply -f k8s/08-producer-deployment.yaml
oc apply -f k8s/11-consumer-deployment.yaml
echo -e "${GREEN}✅ Producer and Consumer deployed${NC}"
echo ""

# Run EDA Job
echo -e "${YELLOW}[10/10]${NC} Running PySpark EDA job..."
oc apply -f k8s/12-eda-job.yaml
echo "Waiting for EDA job to complete (this may take 2-3 minutes)..."
oc wait --for=condition=complete --timeout=600s job/pyspark-eda || true
echo -e "${GREEN}✅ EDA job complete${NC}"
echo ""

# Display status
echo -e "${BLUE}==============================================================================${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""
echo "📊 Check the status of all resources:"
echo "  oc get all"
echo ""
echo "📝 View logs:"
echo "  oc logs deployment/kafka"
echo "  oc logs deployment/kafka-producer"
echo "  oc logs deployment/kafka-consumer"
echo "  oc logs job/pyspark-eda"
echo ""
echo "📈 View EDA results:"
echo "  oc exec -it deployment/kafka-producer -- ls -lh /data/"
echo ""
echo "🗑️  To clean up everything:"
echo "  oc delete all -l app=kafka"
echo "  oc delete all -l app=kafka-producer"
echo "  oc delete all -l app=kafka-consumer"
echo "  oc delete all -l app=pyspark-eda"
echo "  oc delete pvc --all"
echo ""
echo -e "${BLUE}==============================================================================${NC}"
