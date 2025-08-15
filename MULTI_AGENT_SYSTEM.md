# Multi-Agent Healthcare Information System

## Overview

This enhanced healthcare RAG system now supports three different search strategies with multiple data sources to provide the most accurate and comprehensive health information possible.

## Available Data Sources

### 1. Local Database (`search_local_db`)
- **Source**: Local `Data.txt` file
- **Content**: Curated disease information with causes, symptoms, and treatments
- **Speed**: Fastest (local file access)
- **Use Case**: Quick lookup for common diseases

### 2. PubMed API (`search_pubmed`)
- **Source**: PubMed medical research database
- **Content**: Peer-reviewed medical research articles
- **Speed**: Medium (external API call)
- **Use Case**: Scientific research and evidence-based information

### 3. WHO API (`search_who_api`)
- **Source**: World Health Organization Global Health Observatory
- **Content**: Global health statistics, indicators, and official WHO guidance
- **Speed**: Medium (external API call)
- **Use Case**: Official health statistics and WHO recommendations

## Search Strategies

### 1. Standard Strategy (`"standard"`)
- **Workflow**: Sequential search
- **Process**: 
  1. Search local database first
  2. If not found, search PubMed
- **Pros**: Fast, efficient for common queries
- **Cons**: Limited to two sources

### 2. Enhanced Strategy (`"enhanced"`)
- **Workflow**: Intelligent search with potential parallel calls
- **Process**: 
  1. Search local database
  2. Model decides whether to call PubMed, WHO API, or both
- **Pros**: Balanced speed and accuracy
- **Cons**: May not always use all sources

### 3. Comprehensive Strategy (`"comprehensive"`) - **RECOMMENDED**
- **Workflow**: Parallel search across all sources
- **Process**: 
  1. Simultaneously search all three sources
  2. Combine results for maximum accuracy
- **Pros**: Most accurate and complete information
- **Cons**: Slightly slower due to multiple API calls

## API Usage

### Basic Query
```json
{
  "query": "What are the symptoms of diabetes?",
  "search_strategy": "comprehensive"
}
```

### Available Search Strategies
```json
{
  "query": "Tell me about malaria",
  "search_strategy": "standard"    // or "enhanced" or "comprehensive"
}
```

### Get Available Strategies
```
GET /search-strategies
```

## Implementation Details

### WHO API Integration
The WHO API integration uses the Global Health Observatory API to fetch:
- Health indicators and statistics
- Disease definitions and information
- Global health data and trends

### Parallel Processing
The comprehensive strategy executes all three searches simultaneously:
```python
# Parallel execution
local_result = search_local_db.invoke({"disease_name": search_term})
pubmed_result = search_pubmed.invoke({"query": search_term})
who_result = search_who_api.invoke({"query": search_term})
```

### Result Combination
Results from all sources are combined into a structured response:
```
LOCAL DATABASE RESULTS:
[Local database findings]

PUBMED RESEARCH RESULTS:
[Scientific research findings]

WHO (World Health Organization) RESULTS:
[Official WHO data and recommendations]

COMPREHENSIVE SUMMARY:
[Combined analysis and summary]
```

## Benefits of Multi-Agent Approach

1. **Maximum Accuracy**: Cross-referencing multiple authoritative sources
2. **Comprehensive Coverage**: Local data + research + official statistics
3. **Reliability**: Fallback sources if one fails
4. **Flexibility**: Choose strategy based on needs (speed vs accuracy)
5. **Scalability**: Easy to add more data sources

## Testing

Run the test script to verify all integrations:
```bash
python test_who_api.py
```

## Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Required for the LLM model
- No additional API keys needed for WHO API (public access)

### Dependencies
- `requests`: For WHO API calls
- `pymed`: For PubMed integration
- `langchain`: For agent orchestration

## Best Practices

1. **Use Comprehensive Strategy**: For most accurate results
2. **Handle Errors Gracefully**: Each source has error handling
3. **Monitor API Limits**: Be aware of PubMed rate limits
4. **Cache Results**: Consider caching for frequently asked questions
5. **Update Local Database**: Keep local data current

## Future Enhancements

1. **Additional APIs**: CDC, NIH, medical journals
2. **Intelligent Routing**: ML-based source selection
3. **Result Ranking**: Score and rank information by reliability
4. **Caching Layer**: Redis for frequently accessed data
5. **Real-time Updates**: Live data feeds from health organizations