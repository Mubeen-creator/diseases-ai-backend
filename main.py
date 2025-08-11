import os
from fastapi import FastAPI, Request, HTTPException, Depends
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, EmailStr
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import HumanMessage, BaseMessage, ToolMessage, AIMessage
from dotenv import load_dotenv
from pymed import PubMed
import logging
from datetime import datetime, timezone
from firebase_admin import firestore as fs
from firebase import db
from utils import hash_password, verify_password, create_access_token, get_current_user
from langgraph.prebuilt import ToolNode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

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

# --- FastAPI App & Endpoints ---
app = FastAPI(
    title="Healthcare RAG API",
    description="An API for asking health-related questions, powered by a RAG agent.",
    version="2.0.0",
)

app.add_middleware(SessionMiddleware, secret_key="your-secret-key-goes-here")

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY is not set.")

tools = [search_local_db, search_pubmed]
tool_node = ToolNode(tools)
model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("tool_node", tool_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    lambda state: "tool_node" if isinstance(state['messages'][-1], AIMessage) and state['messages'][-1].tool_calls else END,
    {"tool_node": "tool_node", END: END}
)
workflow.add_conditional_edges(
    "tool_node",
    router,
    {
        "agent": "agent",
        "end": END
    }
)
app_graph = workflow.compile()

class SignUpRequest(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    confirmPassword: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class AskRequest(BaseModel):
    query: str

@app.post("/ask")
async def ask(request: AskRequest, http_request: Request, current_user=Depends(get_current_user)):
    chat_history_list = http_request.session.get("chat_history", [])
    
    messages = []
    for msg in chat_history_list:
        if msg.get('type') == 'human':
            messages.append(HumanMessage(content=msg.get('content', '')))
        elif msg.get('type') == 'ai':
            messages.append(AIMessage(content=msg.get('content', '')))

    logger.info(f"Received query: '{request.query}' with history length: {len(messages)}")

    messages.append(HumanMessage(content=request.query))

    inputs = {"messages": messages}
    try:
        final_state = app_graph.invoke(inputs, {"recursion_limit": 15})
        answer = final_state['messages'][-1].content

        # Persist the query for analytics/history
        try:
            user_queries = db.collection("Queries").document(current_user["id"]).collection("items")
            user_queries.add({
                "query": request.query,
                "answer": answer,
                "timestamp": fs.SERVER_TIMESTAMP,
            })
        except Exception as firestore_err:
            logger.error(f"Failed to save query to Firestore: {firestore_err}")

        messages.append(AIMessage(content=answer))
        
        http_request.session["chat_history"] = [{"type": m.type, "content": m.content} for m in messages]

        logger.info(f"Generated answer: {answer}")
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/signup", response_model=TokenResponse)
async def signup(body: SignUpRequest):
    # Check passwords match
    if body.password != body.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    users_ref = db.collection("users")
    # Ensure unique email
    existing = users_ref.where("email", "==", body.email).get()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(body.password)
    user_doc = users_ref.document()
    user_data = {
        "id": user_doc.id,
        "fullName": body.fullName,
        "email": body.email,
        "password": hashed_pw,
    }
    user_doc.set(user_data)

    token = create_access_token({"id": user_doc.id, "fullName": body.fullName, "email": body.email})
    return {"access_token": token}


@app.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", body.email).get()
    if not query:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user = query[0].to_dict()
    if not verify_password(body.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_access_token({"id": user["id"], "fullName": user["fullName"], "email": user["email"]})
    return {"access_token": token}

@app.get("/me")
async def me(current_user=Depends(get_current_user)):
    return {"user": current_user}

@app.get("/")
async def root():
    return {"message": "Healthcare RAG Application is running."}



