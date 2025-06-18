#!/usr/bin/env python3
"""
Script to retrieve architecture data from MongoDB.
"""

import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from datetime import datetime
import json

def connect_mongodb():
    """Connect to MongoDB database."""
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://admin:password@localhost:27017/arch_scraper?authSource=admin')
    
    try:
        client = MongoClient(mongodb_uri)
        # Test the connection
        client.admin.command('ping')
        db = client.arch_scraper
        collection = db.architectures
        print("Connected to MongoDB successfully")
        return client, collection
    except ConnectionFailure as e:
        print(f"Failed to connect to MongoDB: {e}")
        return None, None
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None, None

def list_all_batches(collection):
    """List all scraping batches with metadata."""
    try:
        batches = collection.find({}, {"metadata": 1, "created_at": 1, "_id": 1})
        
        print("\n=== All Scraping Batches ===")
        for batch in batches:
            metadata = batch.get('metadata', {})
            print(f"Batch ID: {metadata.get('batch_id', 'N/A')}")
            print(f"MongoDB ID: {batch['_id']}")
            print(f"Timestamp: {metadata.get('timestamp', 'N/A')}")
            print(f"Total Patterns: {metadata.get('total_patterns', 0)}")
            print(f"Sources: {', '.join(metadata.get('sources', []))}")
            print(f"Created At: {batch.get('created_at', 'N/A')}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error listing batches: {e}")

def get_batch_details(collection, batch_id=None, mongo_id=None):
    """Get detailed information about a specific batch."""
    try:
        if batch_id:
            batch = collection.find_one({"metadata.batch_id": batch_id})
        elif mongo_id:
            from bson import ObjectId
            batch = collection.find_one({"_id": ObjectId(mongo_id)})
        else:
            print("Please provide either batch_id or mongo_id")
            return
            
        if not batch:
            print("Batch not found")
            return
            
        print(f"\n=== Batch Details ===")
        print(f"Batch ID: {batch['metadata']['batch_id']}")
        print(f"MongoDB ID: {batch['_id']}")
        print(f"Timestamp: {batch['metadata']['timestamp']}")
        print(f"Total Patterns: {batch['metadata']['total_patterns']}")
        print(f"Sources: {', '.join(batch['metadata']['sources'])}")
        print(f"Created At: {batch['created_at']}")
        
        print(f"\n=== Architecture Patterns ({len(batch['architectures'])}) ===")
        for i, arch in enumerate(batch['architectures'], 1):
            print(f"{i}. {arch['name']}")
            print(f"   Type: {arch['type']}")
            print(f"   Source: {arch['source']['name']}")
            if arch.get('description'):
                print(f"   Description: {arch['description'][:100]}...")
            if arch.get('link'):
                print(f"   Link: {arch['link']}")
            print()
            
    except Exception as e:
        print(f"Error getting batch details: {e}")

def export_batch_to_json(collection, batch_id, output_file=None):
    """Export a batch to JSON file."""
    try:
        batch = collection.find_one({"metadata.batch_id": batch_id})
        if not batch:
            print("Batch not found")
            return
            
        if not output_file:
            output_file = f"data/export_{batch_id}.json"
            
        # Convert ObjectId to string for JSON serialization
        batch['_id'] = str(batch['_id'])
        batch['created_at'] = batch['created_at'].isoformat()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(batch, f, indent=2, ensure_ascii=False)
            
        print(f"Batch exported to {output_file}")
        
    except Exception as e:
        print(f"Error exporting batch: {e}")

def main():
    """Main function to demonstrate data retrieval."""
    client, collection = connect_mongodb()
    if collection is None:
        print("No collection found")
        return
        
    try:
        # List all batches
        list_all_batches(collection)
        
        # Get the most recent batch
        latest_batch = collection.find_one(sort=[("created_at", -1)])
        if latest_batch:
            batch_id = latest_batch['metadata']['batch_id']
            print(f"\nGetting details for latest batch: {batch_id}")
            get_batch_details(collection, batch_id=batch_id)
            
            # Export to JSON
            export_batch_to_json(collection, batch_id)
        else:
            print("No latest batch found")
        
    finally:
        if client:
            client.close()
            print("MongoDB connection closed")

if __name__ == "__main__":
    main() 