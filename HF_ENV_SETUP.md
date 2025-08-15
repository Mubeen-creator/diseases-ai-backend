# Hugging Face Spaces Environment Variables Setup

## Required Environment Variables

Set these in your Hugging Face Space settings (Settings > Variables and secrets):

### 1. Google API Key
```
GOOGLE_API_KEY=AIzaSyDlyPhUwiBtA17-A0rzRxdWkjj4k9_w2Lg
```

### 2. Firebase Service Account (CRITICAL)
Convert your serviceAccountKey.json to a single line:

**On Windows (PowerShell):**
```powershell
Get-Content serviceAccountKey.json | ConvertFrom-Json | ConvertTo-Json -Compress
```

**On Mac/Linux:**
```bash
cat serviceAccountKey.json | jq -c .
```

Then set:
```
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"diseases-ai",...}
```

### 3. JWT Secret
```
JWT_SECRET_KEY=fjhru9f84hjwh92348fuehf89324f8ehfuh923huewfhqwiefhe
```

### 4. Firebase Config (Optional - already in your code)
```
FIREBASE_PROJECT_ID=diseases-ai
FIREBASE_API_KEY=AIzaSyAHXwjuzgCuuJzyOegW0guBuaNJswJPvdw
FIREBASE_AUTH_DOMAIN=diseases-ai.firebaseapp.com
FIREBASE_STORAGE_BUCKET=diseases-ai.firebasestorage.app
FIREBASE_MESSAGING_SENDER_ID=693142618858
FIREBASE_APP_ID=1:693142618858:web:3318684922ef62a8294d93
```

## Important Notes

1. **Never commit your actual API keys to git**
2. **The service account JSON must be on a single line**
3. **Test the deployment with the Gradio interface first**
4. **Your space URL will be: https://your-username-healthcare-rag-api.hf.space**