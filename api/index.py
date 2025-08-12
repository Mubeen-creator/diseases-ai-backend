"""Vercel serverless function entry point for FastAPI app."""
import os
import sys

# Add the parent directory to the Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Vercel expects a handler function
def handler(request, response):
    return app(request, response)

# For Vercel's ASGI support
app = app