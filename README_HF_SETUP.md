# Hugging Face Spaces Setup for FastAPI

## Important Configuration Steps

### 1. Space Configuration
When creating or editing your Hugging Face Space:

1. Go to your space settings
2. Change the **SDK** from "Gradio" to "Docker" or "Static"
3. Set the **App File** to `app.py`
4. Save the configuration

### 2. Alternative: Use Dockerfile
If the above doesn't work, create a `Dockerfile`:

```dockerfile
FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
```

### 3. Environment Variables
Make sure these are set in your Space settings:

- `GOOGLE_API_KEY`
- `FIREBASE_SERVICE_ACCOUNT_JSON`
- `JWT_SECRET_KEY`

### 4. Test Endpoints
After deployment, test these URLs:

- Health check: `https://your-space-name.hf.space/health`
- API docs: `https://your-space-name.hf.space/docs`
- Root: `https://your-space-name.hf.space/`

## Current Issue
The Space is currently configured as a Gradio app, which means it's serving the Gradio interface instead of the FastAPI endpoints directly. This causes CORS issues when trying to access the API from your frontend.

## Solution
Change the Space SDK to "Docker" or "Static" to serve the FastAPI app directly.