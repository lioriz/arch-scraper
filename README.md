# Cloud Architecture Scraper

A Python-based scraper for collecting cloud architecture patterns and solutions from various sources, storing data in MongoDB.

## Features

- Scrapes cloud architecture patterns from multiple sources (AWS, Azure)
- Stores data in MongoDB with timestamps and metadata
- Configurable source list via JSON
- Detailed logging with file and line numbers
- Error handling and retry mechanisms
- Docker support with MongoDB container
- Data retrieval and export capabilities

## Docker Images and Playwright

- The Dockerfile uses multi-stage builds. Each service (scraper, api-server, retrieve-data, test-api) uses a specific build target.
- **Only the scraper service installs Playwright and its dependencies.** This keeps the other images smaller and faster to build.
- If you need to add browser scraping to another service, add the Playwright install steps to that build stage.

## Docker Compose Build Targets

Each service in `docker-compose.yml` specifies its build target, so you can build and run them independently and efficiently.

## Setup

### Docker Setup

1. Build and run using Docker Compose:
```bash
docker-compose up --build
```

To run in detached mode:
```bash
docker-compose up -d
```

To stop the containers:
```bash
docker-compose down
```

### Important Notes

**What happens if you run `docker-compose up` multiple times without `docker-compose down` in between:**

- **MongoDB**: Will show "service is already running" and continue using the existing container
- **Scraper**: Will create a new container each time (old ones remain stopped)
- **Retrieve-data**: Will create a new container each time (old ones remain stopped)
- **Data persistence**: MongoDB data is preserved in the volume
- **Port conflicts**: If you try to start services that are already running, Docker will show an error

**When to use `docker-compose down`:**
- Before running `docker-compose up` again to ensure clean state
- To free up system resources
- To stop all services completely
- Before making changes to docker-compose.yml

**When NOT to use `docker-compose down`:**
- If you want to keep MongoDB running between scraper runs
- If you're using the separate service approach (just use `docker-compose run --rm`)

### Running Services Separately

For better control over when each service runs:

```bash
# Start just the MongoDB database
docker-compose up -d mongodb

# Run the scraper (will exit after completion)
docker-compose run --rm scraper

# Retrieve data when needed
docker-compose run --rm retrieve-data
```

Or run specific services only:
```bash
# Start only MongoDB and scraper (skip retrieve-data)
docker-compose up --build mongodb scraper
```

## Usage

The scraper will:
1. Load sources from `sources.json` (created automatically if not exists)
2. Connect to MongoDB database
3. Scrape each source for cloud architecture patterns
4. Store results in MongoDB with metadata and timestamps
5. Log results to console

## Data Retrieval

Use the included `retrieve_data.py` script to query the MongoDB database:

### Containerized (Recommended)

```bash
# Run the retrieve-data service
docker-compose run --rm retrieve-data

# Or use the convenience script
./retrieve.sh          # Linux/Mac
```

### Direct Docker Command

```bash
# List all scraping batches
docker-compose exec scraper python retrieve_data.py
```

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

## MongoDB Data Structure

Each scraping batch is stored as a document with the following structure:

```json
{
  "_id": "MongoDB ObjectId",
  "metadata": {
    "timestamp": "ISO timestamp",
    "total_patterns": 42,
    "sources": ["AWS Architecture Center", "Azure Architecture Center"],
    "batch_id": "20250618_144235"
  },
  "architectures": [
    {
      "name": "Pattern Name",
      "type": "pattern|solution|guide|strategy",
      "source": {
        "name": "Source Name",
        "type": "aws|azure",
        "url": "https://source-url.com"
      },
      "description": "Pattern description",
      "link": "https://pattern-url.com",
      "tags": [],
      "metadata": {
        "scraped_at": "ISO timestamp"
      }
    }
  ],
  "created_at": "MongoDB Date"
}
```

## Logging

Logs are written to console with the format:
```
{time} | {file}:{line} | {level} | {message}
```

## Docker Services

The Docker Compose setup includes:
- **scraper**: Python scraper service
- **api-server**: FastAPI backend server (port 8000)
- **retrieve-data**: Data retrieval service (runs retrieve_data.py)
- **test-api**: API testing service (runs test_api.py)
- **mongodb**: MongoDB 7.0 database
- **mongodb_data**: Persistent volume for MongoDB data

## API Server

The FastAPI server provides REST endpoints to interact with the scraper and retrieve data.

### Starting the API Server

```bash
# Start all services including API server
docker-compose up -d

# Or start just the API server and MongoDB
docker-compose up -d mongodb api-server
```

### Available Endpoints

#### **Health & Info**
- `GET /` - API information and available endpoints
- `GET /health` - Health check and MongoDB connection status
- `GET /docs` - Interactive API documentation (Swagger UI)

#### **Data Retrieval**
- `GET /architectures` - Get all scraping batches with metadata
- `GET /architectures/latest` - Get the most recent batch
- `GET /architectures/{batch_id}` - Get specific batch by ID
- `GET /architectures/{batch_id}/patterns` - Get only patterns from a batch

#### **Scraping Control**
- `POST /scrape` - Trigger scraping in background
- `GET /scrape/status` - Get current scraping status
- `GET /sources` - Get available sources for scraping

### API Usage Examples

#### **Get Latest Architecture Data**
```bash
curl http://localhost:8000/architectures/latest
```

#### **Trigger Scraping**
```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"sources": ["AWS Architecture Center"]}'
```

#### **Monitor Scraping Status**
```bash
curl http://localhost:8000/scrape/status
```

#### **Get Specific Batch**
```bash
curl http://localhost:8000/architectures/20250618_165209
```

### Testing the API

Use the included test script:
```bash
# Test basic endpoints (locally)
python test_api.py

# Or test from Docker Compose
# (API server and MongoDB must be running)
docker-compose run --rm test-api
```

### API Documentation

Once the API server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Development

To modify the scraper:
1. Make your changes to the code
2. Rebuild and run the scraper:
```bash
# Rebuild and run scraper (database must be running)
docker-compose up -d mongodb
docker-compose run --rm scraper

# Or rebuild and run all services
docker-compose up --build --abort-on-container-exit ; docker-compose down
```

## Data Export

To export data from MongoDB to JSON:
```python
from retrieve_data import export_batch_to_json, connect_mongodb

client, collection = connect_mongodb()
export_batch_to_json(collection, "20250618_144235", "my_export.json")
```