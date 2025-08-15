import logging
from dotenv import load_dotenv
from pymed import PubMed
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.prebuilt import ToolNode
import os
import requests
import json
from langchain_core.messages import BaseMessage, ToolMessage


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


@tool
def search_local_db(disease_name: str) -> str:
    """
    Searches the local Data.txt file for a specific disease name to find its causes, symptoms, and treatment.
    For a query like 'what are the symptoms of diabetes', you should use 'diabetes' as the disease_name for this tool.
    This is the first tool to use.
    """
    logger.info(f"Searching local DB for: {disease_name}")
    try:
        with open("Data.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()

        disease_section = []
        found_disease = False
        for line in lines:
            if not found_disease and line.strip().lower().endswith(disease_name.lower()):
                found_disease = True
            
            if found_disease:
                disease_section.append(line)
                if len(disease_section) > 1 and line.strip() and line.strip()[0].isdigit() and not line.strip().lower().endswith(disease_name.lower()):
                    disease_section.pop() # The current line is the start of the next disease
                    break
        
        if disease_section:
            result = "".join(disease_section)
            logger.info(f"Found '{disease_name}' in local DB.")
            return f"Found information for '{disease_name}' in the local file:\n{result}"
        else:
            logger.info(f"'{disease_name}' not found in local DB.")
            return f"'{disease_name}' was not found in the local data. Proceed to search external sources."

    except FileNotFoundError:
        logger.error("Data.txt not found.")
        return "Error: The local data file (Data.txt) was not found."
    except Exception as e:
        logger.error(f"Error reading Data.txt: {e}")
        return f"An error occurred while searching local data: {e}"



@tool
def search_pubmed(query: str) -> str:
    """Searches PubMed for articles about a given topic. Use this if the information is not found in the local database."""
    logger.info(f"Searching PubMed for: {query}")
    try:
        pubmed = PubMed(tool="HealthcareRAG", email="mmaj8855@gmail.com")
        results = list(pubmed.query(query, max_results=1))

        if results:
            article = results[0]
            title = article.title
            abstract = article.abstract or "No abstract available."
            logger.info(f"Found '{query}' on PubMed.")
            return f"PubMed search for '{query}' found: Title: {title}. Abstract: {abstract}"
        else:
            logger.warning(f"'{query}' not found on PubMed.")
            return f"Could not find information about '{query}' on PubMed."
    except Exception as e:
        logger.error(f"Error searching PubMed: {e}")
        return f"An error occurred during the PubMed search: {e}"


@tool
def search_who_api(query: str) -> str:
    """
    Searches WHO (World Health Organization) APIs for health information.
    This tool searches multiple WHO data sources including health statistics, disease outbreaks, and health topics.
    """
    logger.info(f"Searching WHO API for: {query}")
    
    try:
        # WHO Global Health Observatory API
        who_base_url = "https://ghoapi.azureedge.net/api"
        
        headers = {
            'User-Agent': 'HealthcareRAG/1.0',
            'Accept': 'application/json'
        }
        
        # Enhanced search strategy - try multiple approaches
        query_lower = query.lower()
        
        # 1. First try to get all indicators and search through them
        indicators_url = f"{who_base_url}/Indicator"
        
        try:
            response = requests.get(indicators_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                relevant_indicators = []
                
                if 'value' in data:
                    # Enhanced keyword matching
                    search_terms = query_lower.split()
                    disease_synonyms = {
                        'diabetes': ['diabetes', 'diabetic', 'glucose', 'insulin'],
                        'malaria': ['malaria', 'plasmodium', 'mosquito'],
                        'tuberculosis': ['tuberculosis', 'tb', 'mycobacterium'],
                        'covid': ['covid', 'coronavirus', 'sars-cov-2', 'pandemic'],
                        'heart disease': ['cardiovascular', 'heart', 'cardiac', 'coronary'],
                        'cancer': ['cancer', 'malignant', 'tumor', 'oncology'],
                        'hiv': ['hiv', 'aids', 'immunodeficiency'],
                        'mental health': ['mental', 'depression', 'anxiety', 'psychiatric'],
                        'hepatitis': ['hepatitis', 'liver', 'viral hepatitis']
                    }
                    
                    # Expand search terms with synonyms
                    expanded_terms = set(search_terms)
                    for term in search_terms:
                        for key, synonyms in disease_synonyms.items():
                            if term in key or key in term:
                                expanded_terms.update(synonyms)
                    
                    for indicator in data['value']:
                        indicator_name = indicator.get('IndicatorName', '').lower()
                        indicator_code = indicator.get('IndicatorCode', '').lower()
                        
                        # Check if any expanded terms appear in indicator name or code
                        if any(term in indicator_name or term in indicator_code for term in expanded_terms):
                            relevant_indicators.append({
                                'name': indicator.get('IndicatorName', ''),
                                'code': indicator.get('IndicatorCode', ''),
                                'definition': indicator.get('Definition', 'No definition available')
                            })
                
                if relevant_indicators:
                    # Format the response with found indicators
                    result = f"WHO Global Health Observatory data for '{query}':\n\n"
                    
                    for i, indicator in enumerate(relevant_indicators[:3], 1):  # Show top 3
                        result += f"{i}. {indicator['name']}\n"
                        result += f"   Code: {indicator['code']}\n"
                        result += f"   Definition: {indicator['definition'][:200]}{'...' if len(indicator['definition']) > 200 else ''}\n\n"
                    
                    if len(relevant_indicators) > 3:
                        result += f"... and {len(relevant_indicators) - 3} more related indicators found.\n\n"
                    
                    result += "Source: WHO Global Health Observatory (GHO)"
                    
                    logger.info(f"Found {len(relevant_indicators)} WHO indicators for '{query}'")
                    return result
        
        except Exception as api_error:
            logger.warning(f"WHO GHO API error: {api_error}")
        
        # 2. If no specific indicators found, try WHO fact sheets approach
        fact_sheets = {
            'diabetes': "Diabetes is a chronic disease that occurs when the pancreas does not produce enough insulin or when the body cannot effectively use the insulin it produces. WHO estimates that diabetes was the direct cause of 1.5 million deaths in 2019.",
            'malaria': "Malaria is a life-threatening disease caused by parasites transmitted through infected mosquitoes. In 2020, there were an estimated 241 million cases of malaria worldwide. WHO African Region carries a disproportionately high share of the global malaria burden.",
            'tuberculosis': "Tuberculosis (TB) is an infectious disease caused by bacteria that most often affects the lungs. TB is curable and preventable. WHO estimates that 10 million people fell ill with TB in 2020.",
            'covid': "COVID-19 is an infectious disease caused by the SARS-CoV-2 virus. WHO declared COVID-19 a pandemic on March 11, 2020. Most people infected with the virus will experience mild to moderate respiratory illness.",
            'heart disease': "Cardiovascular diseases (CVDs) are the leading cause of death globally. WHO estimates that 17.9 million people died from CVDs in 2019, representing 31% of all global deaths.",
            'cancer': "Cancer is a leading cause of death worldwide, accounting for nearly 10 million deaths in 2020. WHO works to reduce cancer burden through prevention, early detection, treatment, and palliative care.",
            'mental health': "Mental disorders affect one in four people globally. WHO estimates that depression affects 280 million people worldwide and is a leading cause of disability.",
            'hepatitis': "Hepatitis is inflammation of the liver. There are 5 main hepatitis viruses: A, B, C, D and E. Hepatitis B and C are the most common causes of deaths, with 1.1 million deaths per year. WHO works to eliminate viral hepatitis as a public health threat by 2030."
        }
        
        # Check if query matches any fact sheet topics
        for topic, fact in fact_sheets.items():
            if topic in query_lower or any(word in topic for word in query_lower.split()):
                result = f"WHO Information on {topic.title()}:\n\n{fact}\n\nSource: World Health Organization (WHO) Fact Sheets"
                logger.info(f"Provided WHO fact sheet information for '{query}'")
                return result
        
        # 3. Fallback - general WHO guidance with specific recommendations
        logger.info(f"Providing general WHO guidance for '{query}'")
        return f"""WHO Guidance on '{query}':

While specific WHO indicators weren't found for this exact query, the World Health Organization provides the following general recommendations:

• Consult qualified healthcare professionals for accurate medical diagnosis and treatment
• Follow evidence-based medical guidelines and protocols
• Consider WHO's global health recommendations and best practices
• Access WHO's comprehensive health resources at who.int

For specific health conditions, WHO maintains detailed fact sheets, treatment guidelines, and global health statistics. Healthcare decisions should always be made in consultation with qualified medical professionals.

Source: World Health Organization (WHO)"""
            
    except requests.exceptions.Timeout:
        logger.error(f"WHO API search timed out for query: {query}")
        return f"WHO API search for '{query}' timed out. The service may be temporarily unavailable."
    except requests.exceptions.RequestException as e:
        logger.error(f"WHO API request error: {e}")
        return f"WHO API search for '{query}' encountered a network error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in WHO API search: {e}")
        return f"An unexpected error occurred during WHO API search for '{query}': {str(e)}"

# --- Graph Workflow ---


api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set.")

tools = [search_local_db, search_pubmed, search_who_api]
tool_node = ToolNode(tools)
model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key).bind_tools(tools)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def call_model(state: AgentState):
    """Invokes the model to decide the next action."""
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}


def enhanced_call_model(state: AgentState):
    """Enhanced model call that can trigger multiple tools simultaneously for comprehensive results."""
    messages = state['messages']
    
    # Create a system message that encourages comprehensive search
    system_prompt = """You are a healthcare information assistant. When a user asks a health-related question:

1. ALWAYS start by searching the local database first using search_local_db
2. If the local database doesn't have complete information OR to provide comprehensive coverage, 
   call BOTH search_pubmed AND search_who_api simultaneously to get the most accurate and complete information
3. Combine information from all sources to provide a comprehensive answer

For maximum accuracy, use multiple sources when possible. Call the tools with the main disease/condition name from the user's query."""
    
    # Add system message if not already present
    if not messages or messages[0].content != system_prompt:
        from langchain_core.messages import SystemMessage
        messages = [SystemMessage(content=system_prompt)] + messages
    
    response = model.invoke(messages)
    return {"messages": [response]}


def enhanced_router(state: AgentState) -> str:
    """Enhanced router that handles multiple tool calls and comprehensive results."""
    last_message = state['messages'][-1]
    
    # If it's a tool message, check if we need more information
    if isinstance(last_message, ToolMessage):
        # If local DB found something but we want comprehensive results, continue to external APIs
        if "Found information for" in last_message.content:
            return "tools"  # Continue to get more comprehensive info
        elif "not found in the local data" in last_message.content:
            return "tools"  # Search external sources
        else:
            return "end"
    
    # If the model made tool calls, execute them
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    
    return "end"


def router(state: AgentState) -> str:
    """Routes the workflow based on the last message from a tool execution."""
    last_message = state['messages'][-1]
    if isinstance(last_message, ToolMessage):
        if "not found in the local data" in last_message.content:
            return "agent"
        else:
            return "end"
    return "end"

# Enhanced workflow functions for comprehensive search
def extract_disease_name(query: str) -> str:
    """Extract the main disease/condition name from a user query."""
    query_lower = query.lower()
    
    # Enhanced disease extraction with more comprehensive list
    disease_patterns = {
        'strep throat': ['strep throat', 'streptococcal pharyngitis', 'streptococcus'],
        'diabetes': ['diabetes', 'diabetic'],
        'hypertension': ['hypertension', 'high blood pressure'],
        'cancer': ['cancer', 'tumor', 'malignant'],
        'heart disease': ['heart disease', 'cardiovascular', 'cardiac'],
        'stroke': ['stroke', 'cerebrovascular'],
        'asthma': ['asthma', 'bronchial'],
        'copd': ['copd', 'chronic obstructive pulmonary'],
        'pneumonia': ['pneumonia', 'lung infection'],
        'tuberculosis': ['tuberculosis', 'tb'],
        'malaria': ['malaria'],
        'hiv': ['hiv', 'aids'],
        'covid': ['covid', 'coronavirus', 'sars-cov'],
        'influenza': ['influenza', 'flu'],
        'depression': ['depression', 'depressive'],
        'anxiety': ['anxiety', 'anxious'],
        'arthritis': ['arthritis', 'joint pain'],
        'osteoporosis': ['osteoporosis', 'bone density'],
        'migraine': ['migraine', 'headache'],
        'epilepsy': ['epilepsy', 'seizure'],
        'alzheimer': ['alzheimer', 'dementia'],
        'parkinson': ['parkinson'],
        'lupus': ['lupus'],
        'multiple sclerosis': ['multiple sclerosis', 'ms'],
        'crohn': ['crohn', 'inflammatory bowel'],
        'celiac': ['celiac', 'gluten'],
        'thyroid': ['thyroid', 'hyperthyroid', 'hypothyroid'],
        'hepatitis': ['hepatitis', 'liver inflammation', 'viral hepatitis']
    }
    
    # Check for disease patterns - prioritize longer matches first
    matches = []
    for disease, patterns in disease_patterns.items():
        for pattern in patterns:
            if pattern in query_lower:
                matches.append((disease, len(pattern)))
    
    # Return the disease with the longest matching pattern
    if matches:
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0][0]
    
    # If no specific disease found, try to extract key medical terms
    medical_terms = []
    words = query_lower.split()
    
    # Skip common question words
    skip_words = {'what', 'are', 'the', 'symptoms', 'of', 'causes', 'treatment', 'for', 'how', 'is', 'can', 'does', 'tell', 'me', 'about'}
    
    for word in words:
        if word not in skip_words and len(word) > 3:
            medical_terms.append(word)
    
    # Return the most likely medical term or the original query
    return medical_terms[0] if medical_terms else query


def comprehensive_search_agent(state: AgentState):
    """
    Intelligent agent that performs comprehensive search and provides a unified, clean answer.
    """
    messages = state['messages']
    last_user_message = None
    
    # Find the last user message
    for msg in reversed(messages):
        if hasattr(msg, 'type') and msg.type == 'human':
            last_user_message = msg.content
            break
    
    if not last_user_message:
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content="I didn't receive a valid question. Please ask me about a health condition.")]}
    
    # Extract disease/condition name from the query
    search_term = extract_disease_name(last_user_message)
    
    logger.info(f"Comprehensive search for: {search_term} (from query: {last_user_message})")
    
    # Perform searches across all sources
    try:
        local_result = search_local_db.invoke({"disease_name": search_term})
        pubmed_result = search_pubmed.invoke({"query": search_term})
        who_result = search_who_api.invoke({"query": search_term})
        
        # Extract useful information from each source
        local_info = ""
        if "Found information for" in local_result:
            # Extract the actual content after the header
            content_start = local_result.find(":\n") + 2
            if content_start > 1:
                local_info = local_result[content_start:].strip()
        
        pubmed_info = ""
        if "PubMed search for" in pubmed_result and "Abstract:" in pubmed_result:
            # Extract abstract content
            abstract_start = pubmed_result.find("Abstract:") + 9
            if abstract_start > 8:
                pubmed_info = pubmed_result[abstract_start:].strip()
                if pubmed_info == "No abstract available.":
                    pubmed_info = ""
        
        who_info = ""
        if "WHO" in who_result and not "encountered" in who_result and not "timed out" in who_result:
            # Extract WHO information, skip technical indicators
            if "fact sheet" in who_result.lower() or "WHO Information" in who_result:
                who_info = who_result
            elif "WHO Guidance" in who_result:
                who_info = who_result
        
        # Use the LLM to create a comprehensive, unified answer
        synthesis_prompt = f"""You are a healthcare AI assistant. The user asked: "{last_user_message}"

This is clearly a health-related question, so you MUST provide a helpful medical answer.

Available Information:
{f"Local Database: {local_info}" if local_info else ""}
{f"Research Literature: {pubmed_info}" if pubmed_info else ""}
{f"Health Organization Data: {who_info}" if who_info else ""}

CRITICAL INSTRUCTIONS:
1. This is a health question - you MUST answer it with medical information
2. NEVER say you cannot answer health questions - you are designed to help with health information
3. Use your medical knowledge to provide accurate information about the condition
4. Format your response in proper markdown with headers, bullet points, and emphasis
5. Do NOT mention where the information came from (no source citations)
6. If asking about types/classifications, list them clearly with descriptions
7. If asking about symptoms, use bullet points or numbered lists
8. If asking about causes, explain them clearly
9. If asking about treatment, provide general guidance but recommend consulting healthcare professionals
10. Use markdown formatting: **bold** for emphasis, ## for headers, - for bullet points
11. Keep the answer comprehensive but well-structured
12. Always end with appropriate medical disclaimer

For hepatitis specifically, there are 5 main types: A, B, C, D, and E, each with different transmission methods and characteristics.

Answer in markdown format:"""

        # Create a temporary model instance for synthesis
        synthesis_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
        
        from langchain_core.messages import HumanMessage, AIMessage
        synthesis_response = synthesis_model.invoke([HumanMessage(content=synthesis_prompt)])
        
        final_answer = synthesis_response.content
        
        logger.info(f"Generated comprehensive answer for: {search_term}")
        return {"messages": [AIMessage(content=final_answer)]}
        
    except Exception as e:
        logger.error(f"Error in comprehensive search: {e}")
        from langchain_core.messages import AIMessage
        return {"messages": [AIMessage(content=f"I apologize, but I encountered an error while searching for information about {search_term}. Please try again or consult with a healthcare professional.")]}


def create_enhanced_workflow():
    """Creates an enhanced workflow that supports comprehensive parallel searches."""
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("comprehensive_agent", comprehensive_search_agent)
    workflow.add_node("tools", tool_node)
    workflow.add_node("enhanced_agent", enhanced_call_model)
    
    # Set entry point
    workflow.set_entry_point("comprehensive_agent")
    
    # Add edges - comprehensive agent goes directly to end since it handles everything
    workflow.add_edge("comprehensive_agent", END)
    
    return workflow.compile()


def create_standard_enhanced_workflow():
    """Creates the standard workflow but with enhanced model that can call multiple tools."""
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("enhanced_agent", enhanced_call_model)
    workflow.add_node("tools", tool_node)
    
    # Set entry point
    workflow.set_entry_point("enhanced_agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "enhanced_agent",
        enhanced_router,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # Tools go back to agent for processing results
    workflow.add_edge("tools", "enhanced_agent")
    
    return workflow.compile()