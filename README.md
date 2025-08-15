---
title: Healthcare AI
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# Healthcare RAG API

A FastAPI-based healthcare question-answering system powered by RAG (Retrieval-Augmented Generation) using Google Gemini AI, local medical database, and PubMed integration.

## Features

- 🤖 AI-powered medical question answering
- 📚 Local medical database search
- 🔬 PubMed research integration
- 👤 User authentication and session management
- 💾 Firebase integration for data persistence
- 🔒 Secure JWT-based authentication

## API Endpoints

- `POST /ask` - Ask medical questions
- `POST /signup` - User registration
- `POST /login` - User authentication
- `GET /me` - Get current user info
- `GET /sessions` - List user sessions
- `GET /sessions/{session_id}` - Get session messages
- `DELETE /sessions/{session_id}` - Delete session

## Environment Variables

Make sure to set the following environment variables in your Hugging Face Space:

- `GOOGLE_API_KEY` - Google Gemini API key
- `FIREBASE_SERVICE_ACCOUNT_JSON` - Firebase service account JSON (as string)
- `JWT_SECRET_KEY` - JWT secret key
- Other Firebase configuration variables

## Usage

The API is automatically deployed and accessible via the Hugging Face Spaces interface.