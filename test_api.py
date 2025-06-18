#!/usr/bin/env python3
"""
Test script to demonstrate the Cloud Architecture Scraper API usage.
"""

import requests
import json
import time
from typing import Dict, Any

# API base URL
API_BASE_URL = "http://api-server:8000"

def safe_json(response):
    try:
        return response.json()
    except Exception:
        return response.text

def test_api_endpoints():
    """Test all API endpoints."""
    
    print("🚀 Testing Cloud Architecture Scraper API")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Health Check")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {safe_json(response)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Get available sources
    print("\n2. Available Sources")
    try:
        response = requests.get(f"{API_BASE_URL}/sources")
        print(f"Status: {response.status_code}")
        sources = safe_json(response)
        if isinstance(sources, list):
            for source in sources:
                print(f"  - {source.get('name', 'N/A')} ({source.get('type', 'N/A')})")
        else:
            print(f"Response: {sources}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Get all batches
    print("\n3. All Scraping Batches")
    try:
        response = requests.get(f"{API_BASE_URL}/architectures")
        print(f"Status: {response.status_code}")
        batches = safe_json(response)
        if isinstance(batches, list):
            print(f"Found {len(batches)} batches:")
            for batch in batches:
                metadata = batch.get('metadata', {})
                print(f"  - {metadata.get('batch_id', 'N/A')} ({metadata.get('total_patterns', 0)} patterns)")
        else:
            print(f"Response: {batches}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Get latest batch
    print("\n4. Latest Batch")
    try:
        response = requests.get(f"{API_BASE_URL}/architectures/latest")
        print(f"Status: {response.status_code}")
        latest = safe_json(response)
        if isinstance(latest, dict) and 'metadata' in latest:
            metadata = latest.get('metadata', {})
            print(f"Batch ID: {metadata.get('batch_id', 'N/A')}")
            print(f"Total Patterns: {metadata.get('total_patterns', 0)}")
            print(f"Sources: {', '.join(metadata.get('sources', []))}")
            print(f"Timestamp: {metadata.get('timestamp', 'N/A')}")
        else:
            print(f"Response: {latest}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 5: Get scraping status
    print("\n5. Scraping Status")
    try:
        response = requests.get(f"{API_BASE_URL}/scrape/status")
        print(f"Status: {response.status_code}")
        status = safe_json(response)
        if isinstance(status, dict):
            print(f"Current Status: {status.get('status', 'N/A')}")
            print(f"Message: {status.get('message', 'N/A')}")
        else:
            print(f"Response: {status}")
    except Exception as e:
        print(f"Error: {e}")

def trigger_scraping_and_monitor():
    """Trigger scraping and monitor the progress."""
    
    print("\n🔄 Triggering Scraping and Monitoring")
    print("=" * 50)
    
    # Step 1: Trigger scraping
    print("\n1. Triggering scraping...")
    try:
        response = requests.post(f"{API_BASE_URL}/scrape", json={})
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {result}")
        
        if response.status_code == 200:
            # Step 2: Monitor progress
            print("\n2. Monitoring scraping progress...")
            for i in range(30):  # Monitor for up to 30 seconds
                time.sleep(2)
                status_response = requests.get(f"{API_BASE_URL}/scrape/status")
                status = status_response.json()
                print(f"Status: {status.get('status')} - {status.get('message')}")
                
                if status.get('status') in ['completed', 'failed']:
                    break
            
            # Step 3: Get latest batch after completion
            if status.get('status') == 'completed':
                print("\n3. Getting latest batch after scraping...")
                latest_response = requests.get(f"{API_BASE_URL}/architectures/latest")
                if latest_response.status_code == 200:
                    latest = latest_response.json()
                    metadata = latest.get('metadata', {})
                    print(f"New Batch ID: {metadata.get('batch_id', 'N/A')}")
                    print(f"Total Patterns: {metadata.get('total_patterns', 0)}")
                    
                    # Get first few patterns
                    patterns = latest.get('architectures', [])
                    print(f"\nFirst 3 patterns:")
                    for i, pattern in enumerate(patterns[:3], 1):
                        print(f"  {i}. {pattern.get('name', 'N/A')} ({pattern.get('type', 'N/A')})")
        
    except Exception as e:
        print(f"Error: {e}")

def test_specific_batch(batch_id: str):
    """Test retrieving a specific batch."""
    
    print(f"\n📋 Testing Specific Batch: {batch_id}")
    print("=" * 50)
    
    # Get batch details
    try:
        response = requests.get(f"{API_BASE_URL}/architectures/{batch_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            batch = response.json()
            metadata = batch.get('metadata', {})
            print(f"Batch ID: {metadata.get('batch_id', 'N/A')}")
            print(f"Total Patterns: {metadata.get('total_patterns', 0)}")
            print(f"Sources: {', '.join(metadata.get('sources', []))}")
            print(f"Timestamp: {metadata.get('timestamp', 'N/A')}")
            
            # Get patterns only
            patterns_response = requests.get(f"{API_BASE_URL}/architectures/{batch_id}/patterns")
            if patterns_response.status_code == 200:
                patterns = patterns_response.json()
                print(f"\nPatterns ({len(patterns)}):")
                for i, pattern in enumerate(patterns[:5], 1):  # Show first 5
                    print(f"  {i}. {pattern.get('name', 'N/A')} ({pattern.get('type', 'N/A')})")
                if len(patterns) > 5:
                    print(f"  ... and {len(patterns) - 5} more")
        else:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test basic endpoints
    test_api_endpoints()
    
    # Uncomment to test scraping (this will take some time)
    # trigger_scraping_and_monitor()
    
    # Uncomment to test specific batch (replace with actual batch ID)
    # test_specific_batch("20250618_165209")
    
    print("\n✅ API testing completed!")
    print("\n📖 API Documentation available at: http://api-server:8000/docs") 