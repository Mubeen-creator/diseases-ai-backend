from fastapi import FastAPI, Request, HTTPException, Depends
from starlette.middleware.sessions import SessionMiddleware
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
import logging
from datetime import datetime, timezone, timedelta
from firebase_admin import firestore as fs
from firebase import db
from utils import hash_password, verify_password, create_access_token, get_current_user
from pydantic_validations import AskRequest, SignUpRequest, LoginRequest, TokenResponse
from tools import call_model, AgentState, router
from typing import List, Dict



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()



# --- FastAPI App & Endpoints ---
app = FastAPI(
    title="Healthcare RAG API",
    description="An API for asking health-related questions, powered by a RAG agent.",
    version="2.0.0",
)

app.add_middleware(SessionMiddleware, secret_key="your-secret-key-goes-here")

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    router,
    {
        "agent": "agent",
        "end": END
    }
)
app_graph = workflow.compile()

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



