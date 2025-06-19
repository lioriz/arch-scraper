#!/usr/bin/env python3
"""
FastAPI backend server for the Cloud Architecture Scraper.
Provides endpoints to retrieve scraped architectures and trigger scraping.
"""

import os
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from loguru import logger
import sys

# Import the scraper
from scraper import CloudArchitectureScraper

# Configure logger
logger.remove()
logger.add(sys.stdout, format="{time} | {file}:{line} | {level} | {message}")

# Initialize FastAPI app
app = FastAPI(
    title="Cloud Architecture Scraper API",
    description="API for retrieving and triggering cloud architecture scraping",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password@localhost:27017/arch_scraper?authSource=admin')
mongo_client = None
db = None
collection = None

# Pydantic models
class ArchitecturePattern(BaseModel):
    name: str
    type: str
    source: Dict[str, str]
    description: Optional[str] = None
    link: Optional[str] = None
    tags: List[str] = []
    metadata: Dict[str, str]

class BatchMetadata(BaseModel):
    timestamp: str
    total_patterns: int
    sources: List[str]
    batch_id: str

class BatchResponse(BaseModel):
    _id: str
    metadata: BatchMetadata
    architectures: List[ArchitecturePattern]
    created_at: datetime

class ScrapingStatus(BaseModel):
    status: str
    message: str
    batch_id: Optional[str] = None
    total_patterns: Optional[int] = None
    timestamp: Optional[str] = None

class ScrapingRequest(BaseModel):
    sources: Optional[List[str]] = Field(default=None, description="List of source names to scrape. If None, scrapes all sources.")

# Global variable to track scraping status
scraping_in_progress = False
last_scraping_result = None

def connect_mongodb():
    """Connect to MongoDB database."""
    global mongo_client, db, collection
    try:
        mongo_client = MongoClient(mongodb_uri)
        # Test the connection
        mongo_client.admin.command('ping')
        db = mongo_client.arch_scraper
        collection = db.architectures
        logger.info("Connected to MongoDB successfully")
        return True
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialize MongoDB connection on startup."""
    if not connect_mongodb():
        logger.error("Failed to connect to MongoDB on startup")

@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown."""
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed")

async def run_scraper_background(sources: Optional[List[str]] = None):
    """Run the scraper in the background."""
    global scraping_in_progress, last_scraping_result
    
    try:
        scraping_in_progress = True
        logger.info("Starting background scraping...")
        
        # Initialize scraper
        scraper = CloudArchitectureScraper()
        
        # Filter sources if specified
        if sources:
            scraper.sources = [s for s in scraper.sources if s["name"] in sources]
            logger.info(f"Filtered sources to: {[s['name'] for s in scraper.sources]}")
        
        # Run the scraper
        await scraper.run()
        
        # Get the latest batch
        if collection is not None:
            latest_batch = collection.find_one(sort=[("created_at", -1)])
            if latest_batch:
                last_scraping_result = {
                    "status": "completed",
                    "batch_id": latest_batch["metadata"]["batch_id"],
                    "total_patterns": latest_batch["metadata"]["total_patterns"],
                    "timestamp": latest_batch["metadata"]["timestamp"]
                }
                logger.info(f"Scraping completed successfully: {last_scraping_result}")
            else:
                last_scraping_result = {
                    "status": "completed",
                    "message": "Scraping completed but no data found"
                }
        else:
            last_scraping_result = {
                "status": "completed",
                "message": "Scraping completed but MongoDB not available"
            }
            
    except Exception as e:
        logger.error(f"Error during background scraping: {e}")
        last_scraping_result = {
            "status": "failed",
            "message": f"Scraping failed: {str(e)}"
        }
    finally:
        scraping_in_progress = False

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Cloud Architecture Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "GET /architectures": "Retrieve all architecture batches",
            "GET /architectures/{batch_id}": "Retrieve specific batch",
            "GET /architectures/latest": "Retrieve latest batch",
            "POST /scrape": "Trigger scraping",
            "GET /scrape/status": "Get scraping status"
        }
    }

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint."""
    try:
        if collection is not None:
            return {"status": "healthy", "mongodb": "connected"}
        else:
            return {"status": "unhealthy", "mongodb": "disconnected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "error", "mongodb": "error", "detail": str(e)}

@app.get("/architectures", response_model=List[BatchResponse])
async def get_all_batches():
    """Retrieve all scraping batches with metadata."""
    if collection is None:
        return []
    try:
        batches = list(collection.find().sort("created_at", -1))
        for batch in batches:
            batch["_id"] = str(batch["_id"])
        return batches
    except Exception as e:
        logger.error(f"Error retrieving all batches: {e}")
        return []

@app.get("/architectures/latest")
async def get_latest_batch():
    """Retrieve the most recent scraping batch."""
    if collection is None:
        return {"error": "MongoDB not connected"}
    try:
        latest_batch = collection.find_one(sort=[("created_at", -1)])
    except Exception as e:
        logger.error(f"Error retrieving latest batch: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving latest batch: {str(e)}")
    if not latest_batch:
        raise HTTPException(status_code=404, detail="No batches found")
    latest_batch["_id"] = str(latest_batch["_id"])
    return latest_batch

@app.get("/architectures/{batch_id}", response_model=BatchResponse)
async def get_batch_by_id(batch_id: str):
    """Retrieve a specific batch by batch_id."""
    if collection is None:
        raise HTTPException(status_code=500, detail="MongoDB not connected")
    
    try:
        batch = collection.find_one({"metadata.batch_id": batch_id})
    except Exception as e:
        logger.error(f"Error retrieving batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batch: {str(e)}")
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    # Convert ObjectId to string for JSON serialization
    batch["_id"] = str(batch["_id"])
    
    return batch

@app.get("/architectures/{batch_id}/patterns")
async def get_patterns_by_batch_id(batch_id: str):
    """Retrieve only the architecture patterns from a specific batch."""
    if collection is None:
        raise HTTPException(status_code=500, detail="MongoDB not connected")
    
    try:
        batch = collection.find_one({"metadata.batch_id": batch_id}, {"architectures": 1})
    except Exception as e:
        logger.error(f"Error retrieving patterns for batch {batch_id}: {e}")
        raise HTTPException(status_code=500,  detail=f"Error retrieving patterns: {str(e)}")
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    
    return batch["architectures"]

@app.post("/scrape", response_model=ScrapingStatus)
async def trigger_scraping(request: ScrapingRequest, background_tasks: BackgroundTasks):
    """Trigger scraping in the background."""
    global scraping_in_progress
    
    if scraping_in_progress:
        raise HTTPException(status_code=409, detail="Scraping already in progress")
    
    # Add scraping task to background tasks
    background_tasks.add_task(run_scraper_background, request.sources)
    
    return ScrapingStatus(
        status="started",
        message="Scraping started in background"
    )

@app.get("/scrape/status", response_model=ScrapingStatus)
async def get_scraping_status():
    """Get the current status of scraping."""
    global scraping_in_progress, last_scraping_result
    
    if scraping_in_progress:
        return ScrapingStatus(
            status="in_progress",
            message="Scraping is currently running"
        )
    
    if last_scraping_result:
        return ScrapingStatus(
            status=last_scraping_result["status"],
            message=last_scraping_result.get("message", ""),
            batch_id=last_scraping_result.get("batch_id"),
            total_patterns=last_scraping_result.get("total_patterns"),
            timestamp=last_scraping_result.get("timestamp")
        )
    
    return ScrapingStatus(
        status="idle",
        message="No scraping has been performed yet"
    )

@app.get("/sources", response_model=List[Dict[str, str]])
async def get_available_sources():
    """Get list of available sources for scraping."""
    try:
        scraper = CloudArchitectureScraper()
        return scraper.sources
    except Exception as e:
        logger.error(f"Error retrieving sources: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving sources: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 