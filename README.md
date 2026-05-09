# Agentic Image-to-Word Converter

Phase 1 was a Streamlit MVP that converted one document image into a Word file using Groq vision OCR. Phase 2 upgrades it into a semi-autonomous document agent for handwritten notes.

## What Changed in Phase 2

- Batch conversion: upload one or more page images together and receive one combined DOCX.
- Complete agent workflow: observe image quality, interpret risk, decide preprocessing/review actions, act through OCR and diagram extraction, then summarize run memory.
- Explicit run memory: the app records pages processed, review flags, common quality risks, tool warnings, diagrams, safety controls, and the run risk level.
- Trace export: the UI can download a JSON audit trace with per-page observations, decisions, actions, warnings, and diagram coordinates.
- Safer backend: no API calls during module import, lazy Groq client creation, and clear missing-key errors.
- Better diagram handling: robust coordinate parsing, per-page crop names, and inline placement in the generated DOCX.
- Human-in-the-loop: pages with quality risks are flagged for review instead of silently trusted, and the sidebar can require review for all pages.
- Safety and legal awareness: the UI and trace export include privacy, IPR, risk, and safety controls required by the Phase 2 brief while the generated DOCX stays focused on transformed source content.
- Cleaner frontend: fixed broken character encoding, improved layout, and exposed agent trace information.

## Run Locally

```bash
py -3.12 -m pip install -r requirements.txt
```

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
# Optional override if Groq changes model access:
GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

Backward compatibility is kept for the old `GROK_API_KEY` name, but `GROQ_API_KEY` is preferred.
Use `.env.example` as the template. The real `.env` file is ignored by git and must not be committed.

Start the app:

```bash
py -3.12 -m streamlit run streamlit_app.py
```

## Free Cloud Hosting

The fastest free deployment path for this app is Streamlit Community Cloud.

Use:

```text
Repository: samabbas19/image-to-word-converter-mvp
Branch: main
Main file path: streamlit_app.py
```

In the Streamlit deployment **Secrets** field, add:

```toml
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
```

Set the Streamlit Cloud Python version to `3.12` in Advanced settings.

Do not upload `.env`. The committed `.env.example` is only a placeholder template.

`app.py` contains the real Streamlit UI. `streamlit_app.py` is a thin deployment entrypoint so local and cloud runs use the same command.

## LaTeX/PDF Study Handout Workflow

The existing DOCX conversion remains unchanged. The Streamlit interface also has a separate `Convert to LaTeX/PDF` button for producing an image-based PDF reconstruction from the uploaded reference image. This path no longer emits fixed sample chemistry notes; it analyzes the actual input image.

This workflow writes:

```text
output/generated.tex
output/generated.pdf                Created only after LaTeX compilation succeeds
output/processing_report.md
output/ocr_blocks.json
output/layout_blocks.json
output/crops/
```

The pipeline is:

```text
Input image
  -> preprocess image
  -> OCR text extraction
  -> layout/region detection
  -> classify regions as text/table/diagram/image
  -> generate LaTeX dynamically
  -> include cropped diagrams/tables when reconstruction is unreliable
  -> compile PDF with a LaTeX engine
```

The hosted Streamlit workflow uses Groq vision extraction for OCR and layout because it handles handwritten notes better than local OCR. If Groq is unavailable, returns no readable text, or reports low confidence, the app stops and shows the error instead of inventing content or producing an image-only PDF.

PDF compilation is automatic if `tectonic`, `pdflatex`, `xelatex`, or `lualatex` is on `PATH`. Streamlit Cloud installs `pdflatex` through `packages.txt`. If no LaTeX engine is available, the PDF step fails visibly instead of silently falling back to a whole-image PDF.
Generated files under `output/` and optional local compiler binaries under `tools/` are ignored by git.

To generate the LaTeX outputs without the UI:

```powershell
python generate_from_image.py --input reference.png --output output/generated.pdf
```

For strict behavior matching the hosted app, use:

```powershell
python generate_from_image.py --input reference.png --output output/generated.pdf --ocr-engine groq --no-pdf-fallback --strict
```

On Windows, the helper script accepts one or more images:

```powershell
.\scripts\build_latex.ps1 reference.png
```

## Project Structure

```text
streamlit_app.py       Streamlit Community Cloud entrypoint
app.py                  Streamlit Phase 2 interface
backend_inline.py       Agentic OCR, quality checks, DOCX generation
backend.py              Compatibility exports for older imports
diagrams.py             Diagram detection and cropping utilities
generate_from_image.py  Image-based OCR/layout to LaTeX/PDF pipeline
latex_workflow.py       Compatibility wrapper for the Streamlit LaTeX/PDF button
scripts/build_latex.ps1 Optional CLI helper for the LaTeX workflow
text.py                 Backward-compatible OCR wrapper with no import-time client
ENV_SETUP.md            Environment setup and deployment notes
DEPLOYMENT.md           Streamlit Community Cloud deployment checklist
```

Phase 2 academic deliverables are kept outside this app folder in `../Phase-2/`.

## Agent Architecture

The app is a realistic semi-autonomous agent rather than a fully autonomous system.

```text
Input images
  -> Observe: image dimensions, brightness, contrast, blur
  -> Interpret: classify quality and risk
  -> Decide: preprocessing, diagram strategy, review policy, risk level
  -> Act: OCR, diagram detection/cropping, DOCX assembly
  -> Learn: summarize pages processed, warnings, diagrams, and quality risks
  -> Human review: user previews trace, text, diagrams, and downloads editable DOCX
```

The implemented agent covers the Phase 2 agentic checklist: perception, decision-making, action/tool orchestration, short-term memory/context, autonomy-level justification, human-in-the-loop checkpoints, ethical design, risk assessment, logging, and explainability.

## Professional Practice Notes

This project handles user-provided document images, so it must treat privacy and user control as first-class requirements. The current version stores temporary files locally, keeps API keys out of source control, flags uncertain pages, avoids long-term user-note memory, and avoids claiming full automation for handwritten OCR where mistakes can affect trust.
