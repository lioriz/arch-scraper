FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a non-root user
RUN useradd -m scraper
RUN chown -R scraper:scraper /app
USER scraper

# Command to run the scraper
CMD ["python", "scraper.py"] 