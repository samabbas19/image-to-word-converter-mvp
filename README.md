# Agentic Image-to-Word Converter

Phase 1 was a Streamlit MVP that converted one document image into a Word file using Groq vision OCR. Phase 2 upgrades it into a semi-autonomous document agent for handwritten notes.

## What Changed in Phase 2

- Batch conversion: upload `1.jpeg`, `2.jpeg`, and `3.jpeg` together and receive one combined DOCX.
- Complete agent workflow: observe image quality, interpret risk, decide preprocessing/review actions, act through OCR and diagram extraction, then summarize run memory.
- Explicit run memory: the app records pages processed, review flags, common quality risks, tool warnings, diagrams, safety controls, and the run risk level.
- Trace export: the UI can download a JSON audit trace with per-page observations, decisions, actions, warnings, and diagram coordinates.
- Safer backend: no API calls during module import, lazy Groq client creation, and clear missing-key errors.
- Better diagram handling: robust coordinate parsing, per-page crop names, and inline placement in the generated DOCX.
- Human-in-the-loop: pages with quality risks are flagged for review instead of silently trusted, and the sidebar can require review for all pages.
- Safety and legal awareness: the UI and generated DOCX include privacy, IPR, risk, and safety controls required by the Phase 2 brief.
- Cleaner frontend: fixed broken character encoding, improved layout, and exposed agent trace information.

## Run Locally

```bash
pip install -r requirements.txt
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
streamlit run app.py
```

## LaTeX/PDF Study Handout Workflow

The existing DOCX conversion remains unchanged. The Streamlit interface now also has a separate `Convert to LaTeX/PDF` button for producing a clean chemistry study handout from the same uploaded notebook images.

This workflow writes:

```text
output/latex/notes.tex
output/latex/notes.pdf              Created only when a LaTeX engine is available
output/latex/processing_report.md
```

The final `notes.tex` and optional `notes.pdf` contain only student-facing study material. Ambiguous handwriting, assumptions, questionable reactions, and PDF compilation notes are written only to `processing_report.md`.

PDF compilation is automatic if `tectonic`, `pdflatex`, `xelatex`, or `lualatex` is on `PATH`. Without one of those tools, the app still generates `notes.tex` and `processing_report.md`.
Generated files under `output/` and optional local compiler binaries under `tools/` are ignored by git.

To generate the LaTeX outputs without the UI on Windows:

```powershell
.\scripts\build_latex.ps1
```

## Project Structure

```text
app.py                  Streamlit Phase 2 interface
backend_inline.py       Agentic OCR, quality checks, DOCX generation
backend.py              Compatibility exports for older imports
diagrams.py             Diagram detection and cropping utilities
latex_workflow.py       Independent LaTeX/PDF study handout generator
scripts/build_latex.ps1 Optional CLI helper for the LaTeX workflow
text.py                 Backward-compatible OCR wrapper with no import-time client
ENV_SETUP.md            Environment setup and deployment notes
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
