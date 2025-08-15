from fastapi import FastAPI, Request, HTTPException, Depends
from starlette.middleware.sessions import SessionMiddleware
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime, timezone, timedelta
import uuid
from firebase_admin import firestore as fs
from firebase import db
from utils import hash_password, verify_password, create_access_token, get_current_user
from pydantic_validations import AskRequest, SignUpRequest, LoginRequest, TokenResponse
from tools import call_model, AgentState, router, create_enhanced_workflow, create_standard_enhanced_workflow, comprehensive_search_agent
from typing import List, Dict
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# --- FastAPI App & Endpoints ---
app = FastAPI(
    title="Healthcare RAG API",
    description="An API for asking health-related questions, powered by a RAG agent.",
    version="2.0.0",
)

# Session middleware (secure cookies)
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-goes-here")

# CORS middleware – allow frontend to call the API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000", 
        "https://*.hf.space",
        "https://*.huggingface.co",
        "https://mubeen788-healtcare-ai.hf.space",
        "*"  # Allow all origins for now - tighten in production
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Create multiple workflow options
standard_workflow = StateGraph(AgentState)
standard_workflow.add_node("agent", call_model)
standard_workflow.set_entry_point("agent")
standard_workflow.add_conditional_edges(
    "agent",
    router,
    {
        "agent": "agent",
        "end": END
    }
)
standard_app_graph = standard_workflow.compile()

# Enhanced workflows
enhanced_app_graph = create_standard_enhanced_workflow()
comprehensive_app_graph = create_enhanced_workflow()

# Default to comprehensive search for maximum accuracy
app_graph = comprehensive_app_graph

class AskRequest(BaseModel):
    query: str
    session_id: Optional[str] = Field(None, description="Existing session id; omit to start a new session")
    search_strategy: Optional[str] = Field("comprehensive", description="Search strategy: 'standard', 'enhanced', or 'comprehensive'")

@app.post("/ask")
async def ask(request: AskRequest, http_request: Request, current_user=Depends(get_current_user)):
    # Session management
    session_id = request.session_id or str(uuid.uuid4())
    
    # Load chat history from Firestore if session_id is provided
    messages = []
    if request.session_id:
        try:
            # Load existing conversation history from Firestore
            messages_ref = (
                db.collection("Sessions")
                .document(current_user["id"])
                .collection("sessions")
                .document(session_id)
                .collection("messages")
                .order_by("timestamp", direction=fs.Query.ASCENDING)
            )
            
            for doc in messages_ref.stream():
                msg_data = doc.to_dict()
                role = msg_data.get("role")
                content = msg_data.get("content", msg_data.get("query", ""))  # fallback for old format
                
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
                    
        except Exception as e:
            logger.warning(f"Could not load session history: {e}")
            # Continue with empty history if loading fails

    logger.info(f"Received query: '{request.query}' with history length: {len(messages)}")

    # Add current user message
    messages.append(HumanMessage(content=request.query))

    # Choose workflow based on search strategy
    if request.search_strategy == "standard":
        selected_graph = standard_app_graph
    elif request.search_strategy == "enhanced":
        selected_graph = enhanced_app_graph
    else:  # comprehensive (default)
        selected_graph = comprehensive_app_graph
    
    inputs = {"messages": messages}
    try:
        final_state = selected_graph.invoke(inputs, {"recursion_limit": 15})
        answer = final_state['messages'][-1].content
        
        # Save to Firestore
        try:
            session_doc_ref = (
                db.collection("Sessions")
                .document(current_user["id"])
                .collection("sessions")
                .document(session_id)
            )
            
            # Ensure session document exists with metadata
            session_doc_ref.set({
                "created": fs.SERVER_TIMESTAMP, 
                "last_activity": fs.SERVER_TIMESTAMP
            }, merge=True)

            messages_collection = session_doc_ref.collection("messages")
            
            # Save user message
            messages_collection.add({
                "content": request.query,
                "timestamp": fs.SERVER_TIMESTAMP,
                "role": "user"
            })
            
            # Save assistant message
            messages_collection.add({
                "content": answer,
                "timestamp": fs.SERVER_TIMESTAMP,
                "role": "assistant"
            })
            
            # Update session last activity
            session_doc_ref.update({"last_activity": fs.SERVER_TIMESTAMP})
            
        except Exception as firestore_err:
            logger.error(f"Failed to save messages to Firestore: {firestore_err}")

        # Update messages list for response
        messages.append(AIMessage(content=answer))
        
        # Update HTTP session for immediate access (optional, mainly for debugging)
        http_request.session["chat_history"] = [
            {"type": m.type, "content": m.content} for m in messages
        ]
        http_request.session["current_session_id"] = session_id

        logger.info(f"Generated answer: {answer}")
        return {"answer": answer, "session_id": session_id}
        
    except Exception as e:
        logger.error(f"Error during agent execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/signup", response_model=TokenResponse)
async def signup(body: SignUpRequest):
    if body.password != body.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    users_ref = db.collection("users")
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


def _group_queries_by_day(docs) -> Dict[str, List[Dict]]:
    """Helper to group query docs by relative day string."""
    today = datetime.now(timezone.utc).date()
    grouped: Dict[str, List[Dict]] = {}
    for doc in docs:
        data = doc.to_dict()
        ts = data.get("timestamp")
        if ts is None:
            continue
        if isinstance(ts, datetime):
            dt = ts.astimezone(timezone.utc)
        else:
            dt = getattr(ts, "to_datetime", lambda: ts)().astimezone(timezone.utc)
        date_only = dt.date()
        if date_only == today:
            key = "today"
        elif date_only == today - timedelta(days=1):
            key = "yesterday"
        else:
            key = date_only.isoformat()
        grouped.setdefault(key, []).append({"query": data["query"], "answer": data.get("answer"), "timestamp": dt.isoformat()})
    return grouped


@app.get("/sessions", response_model=List[Dict])
async def list_sessions(current_user=Depends(get_current_user)):
    """List all sessions for the user with last activity timestamp."""
    sessions_ref = (
        db.collection("Sessions")
        .document(current_user["id"])  # user bucket
        .collection("sessions")
    )
    sessions: List[Dict] = []
    for doc_ref in sessions_ref.list_documents():
        doc = doc_ref.get()
        data = doc.to_dict() or {}
        last_ts = data.get("last_activity")
        if isinstance(last_ts, datetime):
            last_ts = last_ts.astimezone(timezone.utc).isoformat()
        elif last_ts is not None:
            last_ts = getattr(last_ts, "to_datetime", lambda: last_ts)().astimezone(timezone.utc).isoformat()
        sessions.append({"session_id": doc.id.split("/")[-1], "last_activity": last_ts})
    return sessions


# Query history endpoints grouped by day (legacy)

@app.get("/queries", response_model=Dict[str, List[Dict]])
async def get_all_queries(current_user=Depends(get_current_user)):
    """Return all queries for the authenticated user grouped by day."""
    docs = (
        db.collection("Queries")
        .document(current_user["id"])
        .collection("items")
        .order_by("timestamp", direction=fs.Query.DESCENDING)
        .stream()
    )
    return _group_queries_by_day(docs)


# Fetch messages of a session

@app.get("/sessions/{session_id}", response_model=List[Dict])
async def get_session_messages(session_id: str, current_user=Depends(get_current_user)):
    """Get all messages for a specific session."""
    coll = (
        db.collection("Sessions")
        .document(current_user["id"])
        .collection("sessions")
        .document(session_id)
        .collection("messages")
        .order_by("timestamp", direction=fs.Query.ASCENDING)
    )
    msgs: List[Dict] = []
    for doc in coll.stream():
        d = doc.to_dict()
        ts = d.get("timestamp")
        if ts is not None:
            if isinstance(ts, datetime):
                dt = ts.astimezone(timezone.utc)
            else:
                dt = getattr(ts, "to_datetime", lambda: ts)().astimezone(timezone.utc)
            d["timestamp"] = dt.isoformat()
        
        # Ensure consistent message format
        if "content" not in d and "query" in d:
            # Handle legacy format
            d["content"] = d.get("query", "")
        
        msgs.append(d)
    return msgs

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, current_user=Depends(get_current_user)):
    """Delete a specific session and all its messages."""
    try:
        session_doc_ref = (
            db.collection("Sessions")
            .document(current_user["id"])
            .collection("sessions")
            .document(session_id)
        )
        
        # Delete all messages in the session
        messages_ref = session_doc_ref.collection("messages")
        messages = messages_ref.stream()
        
        for message in messages:
            message.reference.delete()
        
        # Delete the session document itself
        session_doc_ref.delete()
        
        return {"message": "Session deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

@app.get("/queries/{date_str}", response_model=List[Dict])
async def get_queries_by_date(date_str: str, current_user=Depends(get_current_user)):
    """Return queries for a specific date (YYYY-MM-DD)."""
    try:
        target_date = datetime.fromisoformat(date_str).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    start = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    docs = (
        db.collection("Queries")
        .document(current_user["id"])
        .collection("items")
        .where("timestamp", ">=", start)
        .where("timestamp", "<", end)
        .order_by("timestamp", direction=fs.Query.DESCENDING)
        .stream()
    )
    results: List[Dict] = []
    for doc in docs:
        data = doc.to_dict()
        ts = data.get("timestamp")
        if ts is None:
            continue
        if isinstance(ts, datetime):
            dt = ts.astimezone(timezone.utc)
        else:
            dt = getattr(ts, "to_datetime", lambda: ts)().astimezone(timezone.utc)
        data["timestamp"] = dt.isoformat()
        results.append(data)
    return results

@app.get("/")
async def root():
    return {"message": "Healthcare RAG Application is running."}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}

@app.get("/search-strategies")
async def get_search_strategies():
    """Get available search strategies and their descriptions"""
    return {
        "strategies": {
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
        },
        "default": "comprehensive",
        "recommendation": "Use 'comprehensive' for the most accurate and complete health information"
    }

@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle CORS preflight requests"""
    return {"message": "OK"}



