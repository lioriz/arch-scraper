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
import openai
from dotenv import load_dotenv

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Load .env file for OpenAI API key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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
        # No batch saving, handled per-architecture in scrape_source
        pass

    async def scrape_source(self, source: Dict, page) -> None:
        try:
            logger.info(f"Scraping {source['name']} from {source['url']}")
            await page.goto(source['url'], wait_until='networkidle')
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(5000)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # Find all architecture links (adjust selector as needed)
            arch_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "architecture" in href and href.startswith("http"):
                    arch_links.append(href)
                elif "architecture" in href:
                    from urllib.parse import urljoin
                    arch_links.append(urljoin(source["url"], href))

            logger.info(f"Found {len(arch_links)} architecture links.")

            for arch_url in arch_links:
                try:
                    await page.goto(arch_url, wait_until='networkidle')
                    await page.wait_for_load_state('domcontentloaded')
                    await page.wait_for_timeout(3000)
                    arch_content = await page.content()
                    arch_soup = BeautifulSoup(arch_content, 'html.parser')
                    for tag in arch_soup(["script", "style", "nav", "footer", "header", "aside"]):
                        tag.decompose()
                    main_content = arch_soup.get_text(separator="\n", strip=True)
                    arch_data = extract_architecture_with_openai(main_content, arch_url, source['name'])
                    if arch_data:
                        if 'timestamp' not in arch_data:
                            from datetime import datetime
                            arch_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
                        self.collection.insert_one(arch_data)
                        logger.info(f"Inserted architecture: {arch_data.get('title', 'N/A')} from {arch_url}")
                    else:
                        logger.error(f"OpenAI extraction failed for {arch_url}")
                except Exception as e:
                    logger.error(f"Error scraping architecture page {arch_url}: {str(e)}")
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

def extract_architecture_with_openai(raw_html, url, provider):
    prompt = f"""
    Extract a cloud architecture from the following HTML/text and return a JSON object in this format:
    {{
      "title": "...",
      "description": "...",
      "provider": "{provider}",
      "scraped_from_url": "{url}",
      "timestamp": "<current UTC ISO timestamp>",
      "tags": [...],
      "resources": [...],
      "relationships": [...]
    }}
    Only include fields you can infer. If a field is missing, leave it out.
    If the provided HTML/text is not a cloud architecture, return None.
    HTML/text:
    {raw_html}
    """
    client = openai.OpenAI()  # Uses OPENAI_API_KEY from env
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1500,
    )
    content = response.choices[0].message.content
    try:
        return json.loads(content)
    except Exception:
        return None

if __name__ == "__main__":
    # Configure simple stdout logger
    logger.remove()  # Remove default handler
    logger.add(sys.stdout, format="{time} | {file}:{line} | {level} | {message}")
    
    # Run the scraper
    asyncio.run(CloudArchitectureScraper().run()) 
    logger.info("Process completed, exiting...")
    