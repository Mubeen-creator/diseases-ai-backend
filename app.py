"""
Hugging Face Spaces entry point for the Healthcare RAG API.
This file creates a Gradio interface that wraps the FastAPI application.
"""
import gradio as gr
import threading
import uvicorn
from main import app
import requests
import json
import time

# Start FastAPI server in a separate thread
def start_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

# Start the FastAPI server
fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
fastapi_thread.start()

# Wait for FastAPI to start
time.sleep(3)

# Gradio interface functions
def ask_question(question, session_id=None):
    """Ask a medical question via the API"""
    try:
        url = "http://localhost:8000/ask"
        payload = {"query": question}
        if session_id:
            payload["session_id"] = session_id
        
        # For demo purposes, we'll skip authentication
        # In production, you'd need to handle login/signup
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("answer", "No answer received"), data.get("session_id", "")
        else:
            return f"Error: {response.status_code} - {response.text}", ""
    except Exception as e:
        return f"Error connecting to API: {str(e)}", ""

def signup_user(full_name, email, password, confirm_password):
    """Sign up a new user"""
    try:
        url = "http://localhost:8000/signup"
        payload = {
            "fullName": full_name,
            "email": email,
            "password": password,
            "confirmPassword": confirm_password
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            return f"Signup successful! Token: {data.get('access_token', '')[:20]}..."
        else:
            return f"Signup failed: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

def login_user(email, password):
    """Login user"""
    try:
        url = "http://localhost:8000/login"
        payload = {
            "email": email,
            "password": password
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            return f"Login successful! Token: {data.get('access_token', '')[:20]}..."
        else:
            return f"Login failed: {response.text}"
    except Exception as e:
        return f"Error: {str(e)}"

# Create Gradio interface
with gr.Blocks(title="Healthcare RAG API", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🏥 Healthcare RAG API")
    gr.Markdown("Ask medical questions and get AI-powered answers using local database and PubMed research.")
    
    with gr.Tab("Ask Questions"):
        with gr.Row():
            with gr.Column():
                question_input = gr.Textbox(
                    label="Medical Question",
                    placeholder="e.g., What are the symptoms of diabetes?",
                    lines=3
                )
                session_input = gr.Textbox(
                    label="Session ID (optional)",
                    placeholder="Leave empty for new session"
                )
                ask_btn = gr.Button("Ask Question", variant="primary")
            
            with gr.Column():
                answer_output = gr.Textbox(
                    label="Answer",
                    lines=10,
                    interactive=False
                )
                session_output = gr.Textbox(
                    label="Session ID",
                    interactive=False
                )
        
        ask_btn.click(
            ask_question,
            inputs=[question_input, session_input],
            outputs=[answer_output, session_output]
        )
    
    with gr.Tab("Authentication"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Sign Up")
                signup_name = gr.Textbox(label="Full Name")
                signup_email = gr.Textbox(label="Email")
                signup_password = gr.Textbox(label="Password", type="password")
                signup_confirm = gr.Textbox(label="Confirm Password", type="password")
                signup_btn = gr.Button("Sign Up")
                signup_output = gr.Textbox(label="Result", interactive=False)
            
            with gr.Column():
                gr.Markdown("### Login")
                login_email = gr.Textbox(label="Email")
                login_password = gr.Textbox(label="Password", type="password")
                login_btn = gr.Button("Login")
                login_output = gr.Textbox(label="Result", interactive=False)
        
        signup_btn.click(
            signup_user,
            inputs=[signup_name, signup_email, signup_password, signup_confirm],
            outputs=signup_output
        )
        
        login_btn.click(
            login_user,
            inputs=[login_email, login_password],
            outputs=login_output
        )
    
    with gr.Tab("API Documentation"):
        gr.Markdown("""
        ## API Endpoints
        
        - **POST /ask** - Ask medical questions
        - **POST /signup** - User registration  
        - **POST /login** - User authentication
        - **GET /me** - Get current user info
        - **GET /sessions** - List user sessions
        - **GET /sessions/{session_id}** - Get session messages
        - **DELETE /sessions/{session_id}** - Delete session
        
        ## Direct API Access
        
        The FastAPI server is running on port 8000. You can access the interactive API documentation at:
        - Swagger UI: `/docs`
        - ReDoc: `/redoc`
        """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)