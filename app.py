"""
Hugging Face Spaces entry point for the Healthcare RAG API.
This file runs the FastAPI application directly on Hugging Face Spaces.
"""
from main import app
import os

# For Hugging Face Spaces, we need to expose the FastAPI app directly
# The app will be served by the Spaces infrastructure
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

# Export the app for Hugging Face Spaces
application = app

