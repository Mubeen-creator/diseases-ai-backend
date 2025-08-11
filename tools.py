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

# --- Graph Workflow ---


api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set.")

tools = [search_local_db, search_pubmed]
tool_node = ToolNode(tools)
model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


def call_model(state: AgentState):
    """Invokes the model to decide the next action."""
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}


def router(state: AgentState) -> str:
    """Routes the workflow based on the last message from a tool execution."""
    last_message = state['messages'][-1]
    if isinstance(last_message, ToolMessage):
        if "not found in the local data" in last_message.content:
            return "agent"
        else:
            return "end"
    return "end"
