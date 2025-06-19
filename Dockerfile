# syntax=docker/dockerfile:1

# Base stage: Python + pip only
FROM python:3.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Playwright base stage (for scraper and api-server only) ---
FROM python:3.11-slim AS playwright-base
WORKDIR /app
RUN pip install playwright && playwright install-deps && playwright install chromium
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Scraper stage ---
FROM playwright-base AS scraper
WORKDIR /app
COPY scraper.py .
COPY .env .
COPY requirements.txt .
CMD ["python", "scraper.py"]

# --- API server stage ---
FROM playwright-base AS api-server
WORKDIR /app
COPY api_server.py .
COPY scraper.py .
COPY .env .
COPY requirements.txt .
CMD ["python", "api_server.py"]

# --- Data retriever stage (no Playwright needed) ---
FROM base AS retrieve-data
WORKDIR /app
COPY retrieve_data.py .
COPY .env .
COPY requirements.txt .
CMD ["python", "retrieve_data.py"]

# --- Test runner stage (no Playwright needed) ---
FROM base AS test-api
WORKDIR /app
COPY test_api.py .
COPY .env .
COPY requirements.txt .
CMD ["python", "test_api.py"] 