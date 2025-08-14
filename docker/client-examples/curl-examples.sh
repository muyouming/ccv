#!/bin/bash

# CCV Text Detection API - cURL Examples

API_URL="http://localhost:8080"

echo "1. Health Check"
curl -X GET "$API_URL/health"
echo -e "\n"

echo "2. Process sample image"
curl -X GET "$API_URL/sample"
echo -e "\n"

echo "3. Upload and process an image"
# Replace 'path/to/image.jpg' with actual image path
curl -X POST "$API_URL/detect" \
  -F "file=@path/to/image.jpg" \
  -F "min_height=10" \
  -F "min_area=100"
echo -e "\n"

echo "4. Get result by ID"
# Replace 'result-id' with actual result ID from previous response
curl -X GET "$API_URL/results/result-id"