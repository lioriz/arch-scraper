# Cloud Architecture Scraper

A Python-based scraper for collecting cloud architecture patterns and solutions from various sources.

## Features

- Scrapes cloud architecture patterns from multiple sources (AWS, Azure)
- Configurable source list via JSON
- Detailed logging with rotation
- Error handling and retry mechanisms

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the scraper:
```bash
python scraper.py
```

The scraper will:
1. Load sources from `sources.json` (created automatically if not exists)
2. Scrape each source for cloud architecture patterns
3. Log results to both console and `scraper.log`

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
- `scraper.log` file (rotates daily, retains for 7 days)