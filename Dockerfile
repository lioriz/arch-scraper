# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base
WORKDIR /app

# --- Playwright install stage ---
FROM base AS playwright-base
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN pip install --no-cache-dir playwright \
    && playwright install-deps \
    && playwright install chromium

# --- Scraper stage ---
FROM playwright-base AS scraper
WORKDIR /app
COPY --from=playwright-base /ms-playwright /ms-playwright
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scraper.py .
COPY .env .
CMD ["python", "scraper.py"]

# --- API server stage ---
FROM playwright-base AS api-server
WORKDIR /app
COPY --from=playwright-base /ms-playwright /ms-playwright
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api_server.py .
COPY scraper.py .
COPY .env .
CMD ["python", "api_server.py"]

# --- Data retriever stage (no Playwright needed) ---
FROM base AS retrieve-data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY retrieve_data.py .
COPY .env .
CMD ["python", "retrieve_data.py"]

# --- Test runner stage (no Playwright needed) ---
FROM base AS test-api
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY test_api.py .
COPY .env .
CMD ["python", "test_api.py"] 
