# Environment Setup Guide

## Local Development

1. **Install dependencies:**
   ```bash
   pip install python-dotenv groq
   ```

2. **Create a `.env` file** in the project root with your API key:
   ```
   GROK_API_KEY=your_api_key_here
   ```

3. **Run your application:**
   ```bash
   python text.py
   ```

## Cloud Deployment

When deploying as a service on the cloud, you need to set environment variables through your cloud provider's interface instead of using a `.env` file.

### Common Cloud Platforms:

#### **AWS (Elastic Beanstalk, Lambda, ECS)**
- Go to your service configuration
- Add environment variable: `GROK_API_KEY` = `your_api_key_here`
- For Lambda: Configuration → Environment variables
- For Elastic Beanstalk: Configuration → Software → Environment properties

#### **Google Cloud (Cloud Run, App Engine, Cloud Functions)**
- Use the `gcloud` CLI or Console
- Example for Cloud Run:
  ```bash
  gcloud run deploy SERVICE_NAME --set-env-vars GROK_API_KEY=your_api_key_here
  ```
- Or in `app.yaml` for App Engine:
  ```yaml
  env_variables:
    GROK_API_KEY: 'your_api_key_here'
  ```

#### **Azure (App Service, Functions)**
- Portal → Your App → Configuration → Application settings
- Add new setting: `GROK_API_KEY` = `your_api_key_here`

#### **Heroku**
- Dashboard → Your App → Settings → Config Vars
- Or via CLI:
  ```bash
  heroku config:set GROK_API_KEY=your_api_key_here
  ```

#### **Railway / Render / Fly.io**
- Go to your project settings
- Add environment variable in the dashboard

## Security Best Practices

✅ **DO:**
- Use environment variables for all secrets
- Keep `.env` file in `.gitignore`
- Use different API keys for development and production
- Rotate API keys periodically

❌ **DON'T:**
- Commit `.env` files to version control
- Hardcode API keys in source code
- Share API keys in chat/email
- Use production keys in development

## Verifying Setup

Your code is already configured correctly! It uses:
```python
from dotenv import load_dotenv
import os

load_dotenv()
groq_key = os.getenv("GROK_API_KEY")
```

This will:
- Load from `.env` file in local development
- Use cloud environment variables in production automatically
