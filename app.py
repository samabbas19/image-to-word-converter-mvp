import json
import os
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"


st.set_page_config(
    page_title="Agentic Image-to-Word Converter",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_streamlit_cloud_secrets() -> None:
    """
    Streamlit Community Cloud stores secrets in st.secrets. The backend modules
    read environment variables, so mirror configured secrets into os.environ.
    """
    for key in ("GROQ_API_KEY", "GROK_API_KEY", "GROQ_VISION_MODEL"):
        if os.getenv(key):
            continue
        try:
            value = st.secrets.get(key)
        except Exception:
            value = None
        if value:
            os.environ[key] = str(value)


load_streamlit_cloud_secrets()


@st.cache_resource(show_spinner=False)
def load_backend_tools():
    from backend_inline import assess_image_quality, build_trace_payload, process_images_to_docx

    return assess_image_quality, build_trace_payload, process_images_to_docx


@st.cache_resource(show_spinner=False)
def load_latex_converter():
    from latex_workflow import convert_images_to_latex_pdf

    return convert_images_to_latex_pdf


st.markdown(
    """
    <style>
    :root {
        --ink: #16221b;
        --muted: #66746b;
        --paper: #fbf8ee;
        --paper-2: #f3efe1;
        --panel: #fffdf8;
        --line: #ddd5bf;
        --leaf: #2f7652;
        --leaf-dark: #143325;
        --rust: #a8502d;
        --blue: #335c75;
        --amber: #d9a441;
    }

    .stApp {
        background:
            linear-gradient(90deg, rgba(47, 118, 82, 0.055) 1px, transparent 1px),
            linear-gradient(180deg, rgba(47, 118, 82, 0.045) 1px, transparent 1px),
            linear-gradient(135deg, #fbf8ee 0%, #eef4ef 47%, #f7f0df 100%);
        background-size: 40px 40px, 40px 40px, auto;
        color: var(--ink);
    }

    [data-testid="stHeader"] {
        background: rgba(251, 248, 238, 0.82);
        backdrop-filter: blur(10px);
    }

    [data-testid="stToolbar"] {
        visibility: hidden;
    }

    .block-container {
        max-width: 1180px;
        padding-top: 2.35rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, p, li, label, span {
        letter-spacing: 0;
    }

    h1 {
        color: var(--ink);
        font-family: Georgia, Cambria, serif;
        font-size: 3.15rem;
        line-height: 1;
        margin-bottom: 0.4rem;
    }

    h2, h3 {
        color: var(--ink);
        font-family: Candara, "Segoe UI", sans-serif;
        font-weight: 800;
    }

    .eyebrow {
        color: var(--rust);
        font-weight: 800;
        font-size: 0.78rem;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .lede {
        color: #47564d;
        font-size: 1.07rem;
        line-height: 1.6;
        max-width: 760px;
        margin: 0 0 1rem 0;
    }

    .hero-note {
        border-left: 5px solid var(--leaf);
        background: rgba(255, 253, 248, 0.86);
        box-shadow: 0 16px 34px rgba(40, 50, 39, 0.08);
        padding: 1rem 1.1rem;
        margin: 1.15rem 0 1.25rem;
        color: var(--ink);
    }

    .hero-note strong {
        color: var(--leaf-dark);
    }

    .desk-card {
        border: 1px solid var(--line);
        background: rgba(255, 253, 248, 0.93);
        border-radius: 8px;
        padding: 1.05rem 1.05rem 1.15rem;
        box-shadow: 0 18px 40px rgba(48, 55, 44, 0.10);
        min-height: 172px;
    }

    .empty-state {
        border: 1px dashed #b9b092;
        background: #f9f1d9;
        border-radius: 8px;
        padding: 1rem;
        color: #42351f;
        line-height: 1.55;
    }

    .quiet-note {
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.55;
    }

    .status-pill {
        display: inline-block;
        border: 1px solid #c9bea1;
        border-radius: 999px;
        padding: 0.22rem 0.62rem;
        font-size: 0.78rem;
        font-weight: 800;
        color: #213229;
        background: #f6ecd2;
        margin: 0 0.35rem 0.45rem 0;
    }

    .mapping-card {
        border-top: 3px solid var(--leaf);
        background: rgba(255, 253, 248, 0.78);
        padding: 0.8rem 0.9rem;
        border-radius: 0 0 8px 8px;
        min-height: 132px;
    }

    .mapping-card b {
        display: block;
        margin-bottom: 0.38rem;
        color: var(--leaf-dark);
    }

    .trace-step {
        border-left: 4px solid var(--blue);
        background: rgba(255, 253, 248, 0.72);
        padding: 0.55rem 0.75rem;
        margin: 0.45rem 0;
        color: var(--ink);
        font-size: 0.92rem;
        line-height: 1.45;
    }

    .requirement-grid {
        border: 1px solid var(--line);
        background: rgba(255, 253, 248, 0.72);
        border-radius: 8px;
        padding: 0.85rem;
        min-height: 128px;
    }

    .requirement-grid b {
        color: var(--leaf-dark);
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, #163626 0%, #10281d 100%);
        border-right: 1px solid #0b1f16;
    }

    [data-testid="stSidebar"] * {
        color: #f8f0d9 !important;
    }

    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] small {
        color: #c9d8ca !important;
    }

    [data-testid="stSidebar"] [data-testid="stAlert"] {
        background: #e5f3df;
        border: 1px solid #9ec296;
        border-radius: 8px;
    }

    [data-testid="stSidebar"] [data-testid="stAlert"] * {
        color: #173521 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(248, 240, 217, 0.2);
    }

    .stButton>button, .stDownloadButton>button {
        width: 100%;
        border-radius: 8px;
        border: 1px solid #1f5c3f;
        background: #2f7652;
        color: #fff;
        font-weight: 800;
        min-height: 2.8rem;
        box-shadow: 0 10px 22px rgba(47, 118, 82, 0.24);
    }

    .stButton>button:hover, .stDownloadButton>button:hover {
        border-color: #143d2b;
        background: #245e41;
        color: #fff;
    }

    .stButton>button:disabled {
        background: #ded7c5;
        color: #706b5f;
        border-color: #cfc4ac;
        box-shadow: none;
    }

    [data-testid="stFileUploader"] {
        background: transparent;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: #fffdf8 !important;
        border: 2px dashed #9eae91 !important;
        border-radius: 8px !important;
        color: var(--ink) !important;
        padding: 1rem !important;
    }

    [data-testid="stFileUploaderDropzone"] * {
        color: var(--ink) !important;
    }

    [data-testid="stFileUploaderDropzone"] button {
        background: #153826 !important;
        border: 1px solid #153826 !important;
        color: #fff7e5 !important;
        border-radius: 8px !important;
    }

    [data-testid="stFileUploaderDropzone"] button * {
        color: #fff7e5 !important;
    }

    [data-testid="stAlert"] {
        border-radius: 8px;
    }

    [data-testid="stMetricValue"] {
        color: var(--leaf);
        font-weight: 800;
    }

    [data-testid="stTabs"] button {
        color: var(--ink) !important;
        font-weight: 700;
    }

    textarea {
        background: #fffdf8 !important;
        color: var(--ink) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def safe_filename(filename):
    uploaded_path = Path(filename)
    name = uploaded_path.stem
    ext = uploaded_path.suffix
    clean_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "page"
    clean_ext = ext.lower() if ext else ".jpeg"
    return clean_name[:60] + clean_ext


def save_uploads(uploaded_files, temp_dir):
    temp_path = Path(temp_dir)
    temp_path.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for index, uploaded_file in enumerate(uploaded_files, start=1):
        filename = "{0:02d}_{1}".format(index, safe_filename(uploaded_file.name))
        path = temp_path / filename
        with open(path, "wb") as output_file:
            output_file.write(uploaded_file.getvalue())
        saved_paths.append(str(path))
    return saved_paths


def render_uploaded_preview(uploaded_file):
    try:
        image_bytes = uploaded_file.getvalue()
        with Image.open(BytesIO(image_bytes)) as image:
            image.thumbnail((1100, 1100))
            st.image(image.copy(), caption=uploaded_file.name, width="stretch")
    except Exception as error:
        st.warning("Image preview is unavailable for this file: {0}".format(error))


def show_quality_report(report):
    st.markdown(
        '<span class="status-pill">{0}</span><span class="status-pill">{1} x {2}px</span>'.format(
            report.status, report.width, report.height
        ),
        unsafe_allow_html=True,
    )
    metric_cols = st.columns(3)
    metric_cols[0].metric("Light", report.brightness)
    metric_cols[1].metric("Contrast", report.contrast)
    metric_cols[2].metric("Sharpness", report.blur_score)

    if report.issues:
        st.warning("; ".join(report.issues))
    else:
        st.success("Quality gate passed.")


def render_list(items):
    if not items:
        st.caption("None recorded.")
        return
    for item in items:
        st.markdown("- {0}".format(item))


def review_policy_value(label):
    if label.startswith("Always"):
        return "review_all"
    return "quality_gate"


with st.sidebar:
    st.markdown("### Document Agent")
    st.caption("A semi-autonomous workflow for handwritten notes.")
    include_quality_preview = st.toggle("Preview page quality", value=False)
    st.caption("Keep this off on hosted demos unless you need the quality metrics before conversion.")
    show_agent_trace = st.toggle("Show conversion trace", value=True)
    review_policy_label = st.selectbox(
        "Human review gate",
        ["Quality-based review", "Always require review"],
        index=0,
    )
    review_policy = review_policy_value(review_policy_label)

    st.divider()
    st.markdown("### Review Policy")
    st.caption("The agent can prepare a DOCX, but handwritten OCR still needs human review before submission.")

    st.divider()
    st.markdown("### Data Notice")
    st.caption(
        "Uploaded notes are processed for conversion only. Content ownership stays with the user; do not upload material you cannot process."
    )

    st.divider()
    st.markdown("### Runtime")
    api_key_ready = bool(os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY"))
    if api_key_ready:
        st.success("Groq API key detected for vision OCR.")
    else:
        st.warning("DOCX vision OCR needs GROQ_API_KEY. LaTeX/PDF can also use Tesseract or image fallback.")


st.markdown('<div class="eyebrow">Phase 2 agentic upgrade</div>', unsafe_allow_html=True)
st.title("Image-to-Word, with a reviewer at the desk")
st.markdown(
    '<p class="lede">Upload the handwritten pages, let the agent inspect the image quality, '
    "extract the notes, preserve diagrams, and mark anything that deserves a second look.</p>",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero-note"><strong>What changed from Phase 1:</strong> this version is not just a converter. '
    "It observes each page, decides whether preprocessing or review is needed, acts through OCR and diagram tools, "
    "then keeps a short run memory for transparency.</div>",
    unsafe_allow_html=True,
)

uploaded_files = st.file_uploader(
    "Add document pages",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    help="Upload one or more document page images in reading order.",
)

left_col, right_col = st.columns([1.08, 0.92], gap="large")

with left_col:
    with st.container(border=True):
        st.subheader("Pages on the desk")
        if uploaded_files:
            st.caption("{0} page(s) queued. Keep them in reading order before converting.".format(len(uploaded_files)))
            preview_tabs = st.tabs(["Page {0}".format(index) for index in range(1, len(uploaded_files) + 1)])
            for tab, uploaded_file in zip(preview_tabs, uploaded_files):
                with tab:
                    render_uploaded_preview(uploaded_file)
                    if include_quality_preview:
                        try:
                            assess_image_quality, _, _ = load_backend_tools()
                            saved_path = save_uploads([uploaded_file], TEMP_DIR / "preview")[0]
                            show_quality_report(assess_image_quality(saved_path))
                        except Exception as error:
                            st.warning("Quality preview is unavailable in this runtime: {0}".format(error))
        else:
            st.markdown(
                '<div class="empty-state"><strong>No pages uploaded yet.</strong><br>'
                "Upload notebook photos or screenshots. The agent will scan them as one document "
                "and place detected diagrams back into the DOCX.</div>",
                unsafe_allow_html=True,
            )

with right_col:
    with st.container(border=True):
        st.subheader("Conversion bench")
        ready = bool(uploaded_files) and api_key_ready
        st.markdown("#### Microsoft Word (.docx)")
        st.markdown(
            '<p class="quiet-note">The Word file contains the transformed source content only: OCR text, '
            "formatting, and detected diagram crops. Agent trace stays in the app and JSON export.</p>",
            unsafe_allow_html=True,
        )

        if st.button("Convert to MS Word (.docx)", type="primary", disabled=not ready):
            image_paths = save_uploads(uploaded_files, TEMP_DIR)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = "converted_document_{0}.docx".format(timestamp)
            output_path = str(TEMP_DIR / output_filename)

            try:
                _, build_trace_payload, process_images_to_docx = load_backend_tools()
                with st.spinner("Observing pages, extracting text, cropping diagrams, and assembling DOCX..."):
                    extracted_text, docx_path, results, memory = process_images_to_docx(
                        image_paths,
                        output_path,
                        review_policy=review_policy,
                    )

                st.session_state["docx_path"] = docx_path
                st.session_state["output_filename"] = output_filename
                st.session_state["results"] = results
                st.session_state["memory"] = memory
                st.session_state["extracted_text"] = extracted_text
                st.session_state["trace_payload"] = build_trace_payload(results, memory)
                st.success("Word conversion completed.")
            except Exception as error:
                st.error("DOCX conversion failed in this runtime: {0}".format(error))

        st.divider()
        latex_ready = bool(uploaded_files) and api_key_ready
        st.markdown("#### LaTeX PDF (.pdf)")
        st.markdown(
            '<p class="quiet-note">The LaTeX/PDF path is separate from the DOCX agentic conversion. '
            "It must complete Groq OCR/layout extraction and LaTeX compilation. If a required step fails, "
            "the app stops and shows the error instead of creating an image-only PDF.</p>",
            unsafe_allow_html=True,
        )
        if st.button("Convert to LaTeX/PDF", disabled=not latex_ready):
            for key in (
                "latex_tex_path",
                "latex_pdf_path",
                "latex_report_path",
                "latex_compile_message",
                "latex_ocr_blocks_path",
                "latex_layout_blocks_path",
            ):
                st.session_state.pop(key, None)
            latex_temp_dir = TEMP_DIR / "latex"
            latex_image_paths = save_uploads(uploaded_files, latex_temp_dir)

            try:
                convert_images_to_latex_pdf = load_latex_converter()
                with st.spinner("Extracting text/layout from the reference image and generating LaTeX/PDF..."):
                    latex_result = convert_images_to_latex_pdf(latex_image_paths, output_dir=str(OUTPUT_DIR))

                st.session_state["latex_tex_path"] = latex_result.tex_path
                st.session_state["latex_pdf_path"] = latex_result.pdf_path
                st.session_state["latex_report_path"] = latex_result.report_path
                st.session_state["latex_compile_message"] = latex_result.compile_message
                st.session_state["latex_ocr_blocks_path"] = latex_result.ocr_blocks_path
                st.session_state["latex_layout_blocks_path"] = latex_result.layout_blocks_path

                if latex_result.pdf_path:
                    st.success("OCR-based LaTeX/PDF output generated.")
                else:
                    st.info("LaTeX and processing evidence generated. {0}".format(latex_result.compile_message))
            except Exception as error:
                st.error("LaTeX/PDF conversion failed in this runtime: {0}".format(error))

        if "latex_tex_path" in st.session_state:
            latex_cols = st.columns(2)
            with open(st.session_state["latex_tex_path"], "rb") as tex_file:
                latex_cols[0].download_button(
                    "Download generated.tex",
                    data=tex_file.read(),
                    file_name="generated.tex",
                    mime="text/x-tex",
                )

            if st.session_state.get("latex_pdf_path"):
                with open(st.session_state["latex_pdf_path"], "rb") as pdf_file:
                    latex_cols[1].download_button(
                        "Download generated.pdf",
                        data=pdf_file.read(),
                        file_name="generated.pdf",
                        mime="application/pdf",
                    )
            else:
                latex_cols[1].caption("PDF was not generated because a required pipeline step failed.")

            evidence_cols = st.columns(2)
            with open(st.session_state["latex_report_path"], "rb") as report_file:
                evidence_cols[0].download_button(
                    "Download processing report",
                    data=report_file.read(),
                    file_name="processing_report.md",
                    mime="text/markdown",
                )
            with open(st.session_state["latex_ocr_blocks_path"], "rb") as ocr_file:
                evidence_cols[1].download_button(
                    "Download OCR JSON",
                    data=ocr_file.read(),
                    file_name="ocr_blocks.json",
                    mime="application/json",
                )
            with open(st.session_state["latex_layout_blocks_path"], "rb") as layout_file:
                st.download_button(
                    "Download layout JSON",
                    data=layout_file.read(),
                    file_name="layout_blocks.json",
                    mime="application/json",
                )

        if "docx_path" in st.session_state:
            with open(st.session_state["docx_path"], "rb") as docx_file:
                st.download_button(
                    "Download DOCX",
                    data=docx_file.read(),
                    file_name=st.session_state["output_filename"],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                )

            memory = st.session_state.get("memory", {})
            metrics = st.columns(4)
            metrics[0].metric("Pages", memory.get("pages_processed", 0))
            metrics[1].metric("Diagrams", memory.get("diagrams_detected", 0))
            metrics[2].metric("Review flags", memory.get("pages_requiring_review", 0))
            metrics[3].metric("Run risk", memory.get("run_risk_level", "Low"))

            if memory.get("pages_requiring_review", 0):
                st.warning("Review required for: {0}".format(", ".join(memory.get("review_pages", []))))

            if memory.get("tool_warnings", 0):
                st.error("{0} tool warning(s) were recorded in the trace.".format(memory.get("tool_warnings", 0)))

            trace_payload = st.session_state.get("trace_payload")
            if trace_payload:
                st.download_button(
                    "Download agent trace JSON",
                    data=json.dumps(trace_payload, indent=2),
                    file_name="agent_trace_{0}.json".format(memory.get("run_id", "run")),
                    mime="application/json",
                )

            with st.expander("Extracted text preview", expanded=False):
                st.text_area("OCR text", st.session_state["extracted_text"], height=280)

        elif not api_key_ready:
            st.warning("Conversion needs a Groq API key. Set GROQ_API_KEY in Streamlit secrets or local .env.")
        elif uploaded_files:
            st.info("Pages are ready. Start conversion when the order looks right.")
        else:
            st.info("Upload pages first, then the conversion button will unlock.")


if show_agent_trace and "results" in st.session_state:
    st.subheader("Agent trace")
    for index, result in enumerate(st.session_state["results"], start=1):
        with st.expander("Page {0}: {1}".format(index, result.quality.filename), expanded=index == 1):
            show_quality_report(result.quality)
            trace_cols = st.columns(4)
            trace_cols[0].metric("Status", result.status.replace("_", " "))
            trace_cols[1].metric("Risk", result.decision.risk_level)
            trace_cols[2].metric("Review", "Yes" if result.decision.human_review_required else "No")
            trace_cols[3].metric("Diagrams", len(result.diagram_data))
            st.markdown("**Autonomy:** {0}".format(result.decision.autonomy_level))
            st.markdown("**Diagram strategy:** {0}".format(result.decision.diagram_strategy))
            st.markdown(
                "**Preprocessing:** {0}".format(", ".join(result.decision.preprocessing_applied) or "None")
            )
            st.markdown("**Rationale:** {0}".format("; ".join(result.decision.rationale)))

            if result.warnings:
                st.error("; ".join(result.warnings))

            st.markdown("**Observe -> Interpret -> Decide -> Act -> Learn**")
            for step in result.trace:
                st.markdown('<div class="trace-step">{0}</div>'.format(step), unsafe_allow_html=True)

    memory = st.session_state.get("memory", {})
    with st.expander("Run memory, risk, and safety", expanded=True):
        memory_cols = st.columns(3)
        memory_cols[0].markdown("**Agent type:** {0}".format(memory.get("agent_type", "")))
        memory_cols[1].markdown("**Review policy:** {0}".format(memory.get("review_policy", "")))
        memory_cols[2].markdown("**Memory policy:** {0}".format(memory.get("memory_policy", "")))

        st.markdown("**Agentic requirements covered**")
        render_list(memory.get("agentic_requirements", []))

        st.markdown("**Safety controls**")
        render_list(memory.get("safety_controls", []))

        st.markdown("**Risk assessment**")
        for risk in memory.get("risk_register", []):
            st.markdown(
                "- **{0}**: {1} Mitigation: {2}".format(
                    risk.get("risk", ""),
                    risk.get("impact", ""),
                    risk.get("mitigation", ""),
                )
            )


st.subheader("Phase 2 agent map")
mapping = [
    ("Perception", "Checks page size, light, contrast, sharpness, OCR input, and visual regions."),
    ("Interpretation", "Turns raw image signals into ready, review recommended, or human review required."),
    ("Decision", "Chooses preprocessing, diagram extraction, review policy, and risk level."),
    ("Action", "Runs OCR, crops diagrams, builds the DOCX, and exposes the trace."),
    ("Memory", "Keeps short-term run context: pages, warnings, diagrams, risks, and review flags."),
    ("Human control", "User selects files, starts conversion, reviews flags, and accepts the DOCX."),
    ("Ethical design", "Shows uncertainty, protects content ownership, and avoids permanent user-note memory."),
    ("Safety", "Uses environment secrets, logs decisions, flags risky pages, and supports trace export."),
]
for start in range(0, len(mapping), 4):
    mapping_cols = st.columns(4)
    for column, (title, body) in zip(mapping_cols, mapping[start : start + 4]):
        column.markdown(
            '<div class="mapping-card"><b>{0}</b>{1}</div>'.format(title, body),
            unsafe_allow_html=True,
        )
