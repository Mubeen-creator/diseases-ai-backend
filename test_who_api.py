#!/usr/bin/env python3
"""
Test script for WHO API integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools import search_who_api, search_pubmed, search_local_db

def test_who_api():
    """Test the WHO API search functionality"""
    print("Testing WHO API integration...")
    
    test_queries = [
        "diabetes",
        "malaria",
        "tuberculosis",
        "covid-19",
        "heart disease"
    ]
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Testing query: {query}")
        print(f"{'='*50}")
        
        try:
            result = search_who_api.invoke({"query": query})
            print(f"WHO API Result:\n{result}")
        except Exception as e:
            print(f"Error testing WHO API with query '{query}': {e}")

def test_comprehensive_search():
    """Test the new comprehensive search agent that provides unified answers"""
    print("\n" + "="*60)
    print("COMPREHENSIVE SEARCH TEST - UNIFIED ANSWERS")
    print("="*60)
    
    test_queries = [
        "what are the symptoms of strep throat?",
        "what causes diabetes?",
        "how is malaria treated?",
        "what are the symptoms of migraine?"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        
        try:
            from tools import comprehensive_search_agent, AgentState
            from langchain_core.messages import HumanMessage
            
            state = {'messages': [HumanMessage(content=query)]}
            result = comprehensive_search_agent(state)
            
            if result['messages']:
                answer = result['messages'][0].content
                print(f"Answer: {answer}")
            else:
                print("No answer generated")
                
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "="*50)

if __name__ == "__main__":
    print("Healthcare RAG - Multi-Source API Test")
    print("=" * 50)
    
    # Test WHO API
    test_who_api()
    
    # Test comprehensive search
    test_comprehensive_search()
    
    print("\n" + "="*50)
    print("Testing completed!")