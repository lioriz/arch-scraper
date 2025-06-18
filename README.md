# Cloud Architecture Scraper

A Python-based scraper for collecting cloud architecture patterns and solutions from various sources.

## Features

- Scrapes cloud architecture patterns from multiple sources (AWS, Azure)
- Configurable source list via JSON
- Detailed logging with rotation
- Error handling and retry mechanisms
- Docker support for easy deployment

## Setup

### Option 1: Local Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the scraper:
```bash
python scraper.py
```

### Option 2: Docker Setup

1. Build and run using Docker Compose:
```bash
docker-compose up --build
```

To run in detached mode:
```bash
docker-compose up -d
```

To stop the container:
```bash
docker-compose down
```

## Usage

The scraper will:
1. Load sources from `sources.json` (created automatically if not exists)
2. Scrape each source for cloud architecture patterns
3. Log results to both console and `logs/scraper.log`

## Configuration

Sources can be configured in `sources.json`. The default configuration includes:
- AWS Architecture Center
- Azure Architecture Center

Add or modify sources by editing the JSON file with the following structure:
```json
[
    {
        "name": "Source Name",
        "url": "https://source-url.com",
        "type": "source_type"
    }
]
```

## Logging

Logs are written to:
- Console output
- `logs/scraper.log` file (rotates daily, retains for 7 days)

## Docker Volumes

The following directories are mounted as volumes in Docker:
- `./logs:/app/logs` - Contains the log files
- `./sources.json:/app/sources.json` - Contains the source configuration

## Development

To modify the scraper:
1. Make your changes to the code
2. Rebuild the Docker container:
```bash
docker-compose up --build --abort-on-container-exit ; docker-compose down
```