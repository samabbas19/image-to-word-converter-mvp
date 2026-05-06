# Environment Setup

## Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env` in the project root:

```env
GROQ_API_KEY=your_api_key_here
# Optional model override:
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

Run the app:

```bash
streamlit run app.py
```

## Deployment

Set `GROQ_API_KEY` in the hosting provider's environment-variable settings. Do not commit `.env`.

Examples:

```bash
# Heroku
heroku config:set GROQ_API_KEY=your_api_key_here

# Google Cloud Run
gcloud run deploy SERVICE_NAME --set-env-vars GROQ_API_KEY=your_api_key_here
```

## Security Practices

- Keep API keys in environment variables.
- Rotate keys when they are exposed or no longer needed.
- Use separate keys for development and production.
- Do not place uploaded user documents in public folders.
- Clear `temp/` and `cropped_diagrams/` before sharing the project folder.
- Treat generated DOCX files and exported agent traces as user data.
- Tell users that OCR and diagram analysis use a third-party Groq vision API.
- Keep the default memory model short-term unless a production privacy policy supports retention.

The code still accepts `GROK_API_KEY` for backward compatibility with the Phase 1 MVP, but new setups should use `GROQ_API_KEY`.
