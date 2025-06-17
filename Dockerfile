FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its dependencies
RUN playwright install-deps && \
    playwright install chromium

# Copy the rest of the application
COPY . .

# Command to run the scraper
CMD ["python", "scraper.py"] 