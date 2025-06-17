import requests
from bs4 import BeautifulSoup
from loguru import logger
from typing import List, Dict
import json
import os
from pathlib import Path

class CloudArchitectureScraper:
    def __init__(self, sources_file: str = "sources.json"):
        self.sources_file = sources_file
        self.sources = self._load_sources()
        
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

    def scrape_source(self, source: Dict) -> None:
        """Scrape a single source and log the results."""
        try:
            logger.info(f"Scraping {source['name']} from {source['url']}")
            response = requests.get(source['url'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Basic scraping - this will need to be customized per source
            if source['type'] == 'aws':
                self._scrape_aws(soup)
            elif source['type'] == 'azure':
                self._scrape_azure(soup)
            else:
                logger.warning(f"Unknown source type: {source['type']}")
                
        except requests.RequestException as e:
            logger.error(f"Error scraping {source['name']}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error while scraping {source['name']}: {str(e)}")

    def _scrape_aws(self, soup: BeautifulSoup) -> None:
        """Scrape AWS architecture content."""
        # Find architecture patterns and solutions
        patterns = soup.find_all('div', class_='pattern')
        for pattern in patterns:
            title = pattern.find('h2')
            description = pattern.find('p')
            if title and description:
                logger.info(f"AWS Pattern: {title.text.strip()}")
                logger.info(f"Description: {description.text.strip()}\n")

    def _scrape_azure(self, soup: BeautifulSoup) -> None:
        """Scrape Azure architecture content."""
        # Find architecture patterns and solutions
        patterns = soup.find_all('article')
        for pattern in patterns:
            title = pattern.find('h1')
            description = pattern.find('p')
            if title and description:
                logger.info(f"Azure Pattern: {title.text.strip()}")
                logger.info(f"Description: {description.text.strip()}\n")

    def run(self) -> None:
        """Run the scraper for all sources."""
        logger.info("Starting cloud architecture scraping...")
        for source in self.sources:
            self.scrape_source(source)
        logger.info("Scraping completed!")

if __name__ == "__main__":
    # Configure logger
    logger.add("scraper.log", rotation="1 day", retention="7 days")
    
    # Run the scraper
    scraper = CloudArchitectureScraper()
    scraper.run() 