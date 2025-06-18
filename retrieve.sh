#!/bin/bash

# Script to run the retrieve-data service
# Build the retrieve-data service for first run or on changes
# Usage: ./retrieve.sh

echo "Running retrieve-data service..."
docker-compose build retrieve-data 
docker-compose run --rm retrieve-data 