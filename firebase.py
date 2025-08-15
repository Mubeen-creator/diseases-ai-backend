"""Firebase initialization helper.

This module initialises the Firebase Admin SDK and exposes the Firestore
client instance via the `db` variable so it can be imported anywhere in the
project:

    from firebase import db

The Admin SDK will look for credentials in the environment.  You can either
set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable or place a
`serviceAccount.json` file in your project root and set that path instead.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv

# Ensure .env is loaded before reading any environment variables.
load_dotenv()

import firebase_admin
from firebase_admin import credentials, firestore
import json

# Re-use the same Firebase app across hot-reloads / multiple imports.
if not firebase_admin._apps:
    # For Vercel deployment, try to get service account from environment variable first
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or os.getenv("FIREBASE_SERVICE_ACCOUNT")
    service_account_b64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_B64")
    
    if service_account_json:
        # Parse the JSON string from environment variable
        try:
            service_account_info = json.loads(service_account_json)
            cred = credentials.Certificate(service_account_info)
        except json.JSONDecodeError:
            # Fallback to file path if JSON parsing fails
            cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                cred = credentials.ApplicationDefault()
    elif service_account_b64:
        # Decode base64 encoded service account
        try:
            import base64
            decoded_json = base64.b64decode(service_account_b64).decode('utf-8')
            service_account_info = json.loads(decoded_json)
            cred = credentials.Certificate(service_account_info)
        except Exception:
            # Fallback to file path if base64 decoding fails
            cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                cred = credentials.ApplicationDefault()
    else:
        # Prefer explicit service-account json if provided, otherwise fall back to
        # application-default credentials (useful on GCP / Cloud Run etc.)
        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            cred = credentials.ApplicationDefault()

    firebase_admin.initialize_app(cred)

# Firestore client – importable from other modules.
db = firestore.client()

