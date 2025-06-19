# syntax=docker/dockerfile:1

# Base stage
FROM python:3.11-slim AS base
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

FROM base AS playwright
RUN pip install playwright && playwright install-deps && playwright install chromium

# Scraper stage
FROM playwright AS scraper
CMD ["python", "scraper.py"]

# API server stage
FROM playwright AS api-server
CMD ["python", "api_server.py"]

# Data retriever stage
FROM base AS retrieve-data
CMD ["python", "retrieve_data.py"]

# Test runner stage
FROM base AS test-api
CMD ["python", "test_api.py"] 