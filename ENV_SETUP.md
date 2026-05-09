# Environment Setup

## Local Development

Install dependencies:

```bash
py -3.12 -m pip install -r requirements.txt
```

For the image-to-LaTeX/PDF pipeline, install at least one OCR path:

```text
Recommended local OCR: install Tesseract and make sure `tesseract` is on PATH.
Fallback vision OCR: set GROQ_API_KEY.
No OCR available: the strict hosted workflow stops and shows an error instead of producing image-only output.
```

Install a LaTeX engine if you want `generated.tex` compiled directly:

```text
tectonic, pdflatex, xelatex, or lualatex
```

If no working LaTeX engine is available, the strict hosted workflow stops and shows an error. The repository includes `packages.txt` so Streamlit Cloud installs `pdflatex`.

Create `.env` in the project root:

```env
GROQ_API_KEY=your_api_key_here
# Optional model override:
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

Run the app:

```bash
py -3.12 -m streamlit run streamlit_app.py
```

## Deployment

Set `GROQ_API_KEY` in the hosting provider's environment-variable settings. Do not commit `.env`.

### Streamlit Community Cloud

Use these deployment settings:

```text
Repository: samabbas19/image-to-word-converter-mvp
Branch: main
Main file path: streamlit_app.py
```

In the Streamlit deployment **Secrets** field, add:

```toml
GROQ_API_KEY = "your_api_key_here"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
```

Set Python version to `3.12` in Advanced settings.

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
