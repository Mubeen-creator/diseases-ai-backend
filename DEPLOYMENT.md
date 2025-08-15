# Deployment to Hugging Face Spaces

## Prerequisites

1. Create a Hugging Face account at https://huggingface.co
2. Have your Firebase service account JSON ready
3. Have your Google Gemini API key ready

## Steps to Deploy

### 1. Create a New Space

1. Go to https://huggingface.co/new-space
2. Choose a name for your space (e.g., `healthcare-rag-api`)
3. Select **Gradio** as the SDK
4. Set visibility to Public or Private as needed
5. Click "Create Space"

### 2. Upload Files

Upload all the files from the `healtcare-backend` directory to your space:

- `app.py` (main entry point)
- `main.py` (FastAPI application)
- `tools.py` (RAG tools)
- `utils.py` (utilities)
- `firebase.py` (Firebase setup)
- `pydantic_validations.py` (validation models)
- `requirements.txt` (dependencies)
- `Data.txt` (local medical database)
- `README.md` (documentation)

### 3. Set Environment Variables

In your Hugging Face Space settings, add these environment variables:

**Required:**

- `GOOGLE_API_KEY` = Your Google Gemini API key
- `FIREBASE_SERVICE_ACCOUNT_JSON` = Your Firebase service account JSON (as a single line string)
- `JWT_SECRET_KEY` = A secure random string for JWT signing

**Firebase Config (if needed):**

- `FIREBASE_API_KEY` = Your Firebase API key
- `FIREBASE_AUTH_DOMAIN` = Your Firebase auth domain
- `FIREBASE_PROJECT_ID` = Your Firebase project ID
- `FIREBASE_STORAGE_BUCKET` = Your Firebase storage bucket
- `FIREBASE_MESSAGING_SENDER_ID` = Your Firebase messaging sender ID
- `FIREBASE_APP_ID` = Your Firebase app ID

### 4. Deploy

Once you upload the files and set the environment variables, Hugging Face Spaces will automatically build and deploy your application.

### 5. Access Your API

Your API will be available at:

- Gradio Interface: `https://your-username-space-name.hf.space`
- FastAPI Docs: `https://your-username-space-name.hf.space/docs` (may not work directly due to port routing)

## Important Notes

1. **Firebase Service Account**: Convert your `serviceAccountKey.json` to a single-line string:

   ```bash
   cat serviceAccountKey.json | jq -c . | tr -d '\n'
   ```

2. **API Access**: The Gradio interface provides a user-friendly way to test the API. For direct API access from your frontend, use the space URL.

3. **CORS**: The API is configured to accept requests from Hugging Face domains and localhost.

4. **Rate Limits**: Be aware of Hugging Face Spaces resource limits and Google API quotas.

## Troubleshooting

- Check the logs in your Hugging Face Space for any errors
- Ensure all environment variables are set correctly
- Verify your Firebase service account has the necessary permissions
- Test the API endpoints using the Gradio interface first
