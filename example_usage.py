#!/usr/bin/env python3
"""
Example usage of the multi-agent healthcare information system
"""

import requests
import json

# API base URL (adjust if running on different host/port)
BASE_URL = "http://localhost:8000"

def test_search_strategies():
    """Test different search strategies"""
    
    # Sample query
    query = "What are the symptoms of diabetes?"
    
    # Test data for different strategies
    test_cases = [
        {
            "name": "Standard Strategy",
            "data": {
                "query": query,
                "search_strategy": "standard"
            }
        },
        {
            "name": "Enhanced Strategy", 
            "data": {
                "query": query,
                "search_strategy": "enhanced"
            }
        },
        {
            "name": "Comprehensive Strategy",
            "data": {
                "query": query,
                "search_strategy": "comprehensive"
            }
        }
    ]
    
    print("Healthcare RAG - Multi-Agent System Demo")
    print("=" * 50)
    print(f"Query: {query}")
    print("=" * 50)
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}:")
        print("-" * 30)
        
        try:
            # Note: This would require authentication in a real scenario
            # For demo purposes, showing the request structure
            print("Request payload:")
            print(json.dumps(test_case['data'], indent=2))
            print("\n[This would make an API call to /ask endpoint]")
            
        except Exception as e:
            print(f"Error: {e}")

def show_available_strategies():
    """Show available search strategies"""
    print("\nAvailable Search Strategies:")
    print("=" * 40)
    
    strategies = {
        "standard": {
            "description": "Sequential search: Local DB first, then PubMed if not found",
            "sources": ["Local Database", "PubMed"],
            "speed": "Fast",
            "accuracy": "Good"
        },
        "enhanced": {
            "description": "Intelligent search with potential parallel API calls",
            "sources": ["Local Database", "PubMed", "WHO API"],
            "speed": "Medium", 
            "accuracy": "Better"
        },
        "comprehensive": {
            "description": "Parallel search across all sources for maximum accuracy",
            "sources": ["Local Database", "PubMed", "WHO API"],
            "speed": "Medium",
            "accuracy": "Best"
        }
    }
    
    for strategy, details in strategies.items():
        print(f"\n{strategy.upper()}:")
        print(f"  Description: {details['description']}")
        print(f"  Sources: {', '.join(details['sources'])}")
        print(f"  Speed: {details['speed']}")
        print(f"  Accuracy: {details['accuracy']}")

def example_api_calls():
    """Show example API call structures"""
    print("\nExample API Calls:")
    print("=" * 30)
    
    examples = [
        {
            "endpoint": "POST /ask",
            "description": "Ask a health question with comprehensive search",
            "payload": {
                "query": "What are the causes of hypertension?",
                "search_strategy": "comprehensive"
            }
        },
        {
            "endpoint": "POST /ask", 
            "description": "Quick search using standard strategy",
            "payload": {
                "query": "Tell me about malaria symptoms",
                "search_strategy": "standard"
            }
        },
        {
            "endpoint": "GET /search-strategies",
            "description": "Get available search strategies",
            "payload": None
        }
    ]
    
    for example in examples:
        print(f"\n{example['endpoint']}:")
        print(f"  {example['description']}")
        if example['payload']:
            print("  Payload:")
            print(json.dumps(example['payload'], indent=4))

if __name__ == "__main__":
    # Show available strategies
    show_available_strategies()
    
    # Show example API calls
    example_api_calls()
    
    # Test search strategies (demo)
    test_search_strategies()
    
    print("\n" + "=" * 50)
    print("Multi-Agent System Benefits:")
    print("• Maximum accuracy through multiple authoritative sources")
    print("• Flexible search strategies based on speed vs accuracy needs")
    print("• Comprehensive health information from local data, research, and WHO")
    print("• Reliable fallback sources if one API fails")
    print("• Easy to extend with additional health data sources")
    print("=" * 50)