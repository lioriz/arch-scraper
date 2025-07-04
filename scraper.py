import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict, Any
import json
import os
from pathlib import Path
from datetime import datetime
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

class CloudArchitectureScraper:
    def __init__(self, sources_file: str = "sources.json"):
        self.sources_file = sources_file
        self.sources = self._load_sources()
        self.architectures = []
        self.mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password@localhost:27017/arch_scraper?authSource=admin')
        self.mongo_client = None
        self.db = None
        self.collection = None
        # Do not connect to MongoDB here

    def _connect_mongodb(self):
        """Connect to MongoDB database."""
        if self.mongo_client and self.collection:
            return  # Already connected
        try:
            self.mongo_client = MongoClient(self.mongodb_uri)
            # Test the connection
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client.arch_scraper
            self.collection = self.db.architectures
            logger.info("Connected to MongoDB successfully")
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise

    def _load_sources(self) -> List[Dict]:
        """Load sources from the sources file."""
        if not os.path.exists(self.sources_file):
            logger.warning(f"Sources file {self.sources_file} not found. Creating default sources.")
            default_sources = [
                {
                    "name": "AWS Architecture Center",
                    "url": "https://aws.amazon.com/architecture/",
                    "type": "aws"
                },
                {
                    "name": "Azure Architecture Center",
                    "url": "https://learn.microsoft.com/en-us/azure/architecture/",
                    "type": "azure"
                }
            ]
            with open(self.sources_file, 'w') as f:
                json.dump(default_sources, f, indent=4)
            return default_sources
        
        with open(self.sources_file, 'r') as f:
            return json.load(f)

    def _save_architectures(self):
        """Save architectures to MongoDB database."""
        if not self.architectures:
            logger.warning("No architectures to save")
            return
            
        logger.info("Attempting to save to MongoDB...")
        try:
            self._connect_mongodb()
            
            # Create a batch document with metadata
            batch_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_patterns": len(self.architectures),
                    "sources": [source["name"] for source in self.sources],
                    "batch_id": datetime.now().strftime("%Y%m%d_%H%M%S")
                },
                "architectures": self.architectures,
                "created_at": datetime.now()
            }
            
            # Insert the batch into MongoDB
            result = self.collection.insert_one(batch_data)
            logger.info(f"Saved {len(self.architectures)} architecture patterns to MongoDB with batch_id: {batch_data['metadata']['batch_id']}")
            logger.info(f"MongoDB document ID: {result.inserted_id}")
            
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
            logger.warning("Falling back to JSON file saving...")
            
            # Fallback to JSON file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/architectures_{timestamp}.json"
            
            output_data = {
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "total_patterns": len(self.architectures),
                    "sources": [source["name"] for source in self.sources]
                },
                "architectures": self.architectures
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.architectures)} architecture patterns to {output_file}")

    async def scrape_source(self, source: Dict, page) -> None:
        """Scrape a single source and log the results."""
        try:
            logger.info(f"Scraping {source['name']} from {source['url']}")
            await page.goto(source['url'], wait_until='networkidle')
            
            # Wait for content to load with increased timeout
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(5000)  # Additional wait for dynamic content
            
            # Get the page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Log the page title for debugging
            title = soup.find('title')
            if title:
                logger.info(f"Page title: {title.text.strip()}")
            
            # Basic scraping - this will need to be customized per source
            if source['type'] == 'aws':
                await self._scrape_aws(soup, source)
            elif source['type'] == 'azure':
                await self._scrape_azure(soup, source)
            else:
                logger.warning(f"Unknown source type: {source['type']}")
                
        except Exception as e:
            logger.error(f"Error scraping {source['name']}: {str(e)}")

    async def _scrape_aws(self, soup: BeautifulSoup, source: Dict) -> None:
        """Scrape AWS architecture content."""
        # Try multiple selectors for AWS patterns
        patterns = []
        
        # Try different possible selectors
        selectors = [
            'div[class*="aws-card"]',
            'div[class*="card"]',
            'div[class*="pattern"]',
            'div[class*="solution"]',
            'article',
            'div[class*="architecture"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                patterns.extend(elements)
                logger.info(f"Found {len(elements)} elements with selector: {selector}")
        
        if not patterns:
            logger.warning("No patterns found in AWS")
            return

        for pattern in patterns:
            title = pattern.find(['h1', 'h2', 'h3', 'h4', 'h5'])
            description = pattern.find('p')
            link = pattern.find('a')
            
            if title:
                architecture = {
                    "name": title.text.strip(),
                    "type": "pattern",
                    "source": {
                        "name": source["name"],
                        "type": source["type"],
                        "url": source["url"]
                    },
                    "description": description.text.strip() if description else None,
                    "link": link.get('href') if link else None,
                    "tags": [],
                    "metadata": {
                        "scraped_at": datetime.now().isoformat()
                    }
                }
                
                # Add tags based on content
                if "solution" in str(pattern).lower():
                    architecture["type"] = "solution"
                if "guide" in str(pattern).lower():
                    architecture["type"] = "guide"
                if "strategy" in str(pattern).lower():
                    architecture["type"] = "strategy"
                
                self.architectures.append(architecture)
                logger.info(f"AWS Pattern: {architecture['name']}")
                if description:
                    logger.info(f"Description: {architecture['description']}\n")

    async def _scrape_azure(self, soup: BeautifulSoup, source: Dict) -> None:
        """Scrape Azure architecture content."""
        # Try multiple selectors for Azure patterns
        patterns = []
        
        # Try different possible selectors
        selectors = [
            'div[class*="card"]',
            'div[class*="article"]',
            'div[class*="pattern"]',
            'div[class*="solution"]',
            'article',
            'div[class*="architecture"]'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                patterns.extend(elements)
                logger.info(f"Found {len(elements)} elements with selector: {selector}")
        
        if not patterns:
            logger.warning("No patterns found in Azure")
            return

        for pattern in patterns:
            title = pattern.find(['h1', 'h2', 'h3', 'h4', 'h5'])
            description = pattern.find('p')
            link = pattern.find('a')
            
            if title:
                architecture = {
                    "name": title.text.strip(),
                    "type": "pattern",
                    "source": {
                        "name": source["name"],
                        "type": source["type"],
                        "url": source["url"]
                    },
                    "description": description.text.strip() if description else None,
                    "link": link.get('href') if link else None,
                    "tags": [],
                    "metadata": {
                        "scraped_at": datetime.now().isoformat()
                    }
                }
                
                # Add tags based on content
                if "solution" in str(pattern).lower():
                    architecture["type"] = "solution"
                if "guide" in str(pattern).lower():
                    architecture["type"] = "guide"
                if "strategy" in str(pattern).lower():
                    architecture["type"] = "strategy"
                
                self.architectures.append(architecture)
                logger.info(f"Azure Pattern: {architecture['name']}")
                if description:
                    logger.info(f"Description: {architecture['description']}\n")

    def _close_mongodb(self):
        """Close MongoDB connection."""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")

    async def run(self) -> None:
        """Run the scraper for all sources."""
        logger.info("Starting cloud architecture scraping...")
        logger.info(f"Sources: {self.sources}")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                for source in self.sources:
                    logger.info(f"Source: {source}")
                    await self.scrape_source(source, page)
                
                await browser.close()
            
            # Save the collected architectures
            self._save_architectures()
            logger.info("Scraping completed!")
            
        finally:
            # Close MongoDB connection
            self._close_mongodb()

if __name__ == "__main__":
    # Configure simple stdout logger
    logger.remove()  # Remove default handler
    logger.add(sys.stdout, format="{time} | {file}:{line} | {level} | {message}")
    
    # Run the scraper
    asyncio.run(CloudArchitectureScraper().run()) 
    logger.info("Process completed, exiting...")
    