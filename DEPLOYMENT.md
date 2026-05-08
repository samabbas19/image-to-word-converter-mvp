# Streamlit Community Cloud Deployment

## Recommended Platform

Use Streamlit Community Cloud. It is the simplest option for this project because the app is already a Streamlit app, has a `requirements.txt`, and does not need a local GPU, Ollama, or a local database.

## Files Streamlit Cloud Needs

```text
streamlit_app.py
app.py
backend_inline.py
backend.py
diagrams.py
generate_from_image.py
latex_workflow.py
text.py
requirements.txt
.env.example
```

Do not commit `.env`, `temp/`, `output/`, `cropped_diagrams/`, `tools/`, generated DOCX files, generated PDFs, or uploaded notebook images.

## Deploy Steps

1. Push this app folder to GitHub.
2. Go to `https://share.streamlit.io`.
3. Sign in with GitHub.
4. Click **Create app**.
5. Choose **Yup, I have an app**.
6. Select the GitHub repository.
7. Set the branch to `main` or your active branch.
8. Set **Main file path** to:

```text
streamlit_app.py
```

9. Open **Advanced settings** and add secrets:

Set Python version to:

```text
3.12
```

```toml
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
```

10. Click **Deploy**.
11. Wait for the build to finish, then share the generated `streamlit.app` URL with the teacher.

## Local Test Command

```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 -m streamlit run streamlit_app.py
```

## Hosted Demo Notes

- DOCX OCR requires `GROQ_API_KEY`.
- The app does not require Ollama, a local model, local GPU, or a local database.
- Tesseract and LaTeX are optional. If unavailable in the hosted environment, the LaTeX/PDF workflow falls back to Groq vision OCR and direct image-PDF generation.
