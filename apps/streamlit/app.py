"""Streamlit interface for AI document extraction with Gemini and Groq."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

from docxtract import process_document
from docxtract.llm_extractor import DEFAULT_GEMINI_MODEL, DEFAULT_GROQ_MODEL
from docxtract.ocr import SUPPORTED_EXTENSIONS
from docxtract.runtime import check_runtime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
ALLOWED_EXTENSIONS = sorted(extension.lstrip(".") for extension in SUPPORTED_EXTENSIONS)
GROQ_MODELS = [DEFAULT_GROQ_MODEL, "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]


@st.cache_data(ttl=30, show_spinner=False)
def runtime_status():
    return check_runtime()


def process_upload(uploaded_file, provider: str = "gemini", model: str | None = None,
                   api_key: str | None = None) -> dict[str, Any]:
    """Process a temporary upload and remove it even if writing or extraction fails."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(uploaded_file.name).suffix.lower()
    temporary = tempfile.NamedTemporaryFile(dir=UPLOAD_DIR, suffix=suffix, delete=False)
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            temporary.write(uploaded_file.getbuffer())
        return process_document(temporary_path, provider=provider, model=model, api_key=api_key)
    finally:
        temporary.close()
        temporary_path.unlink(missing_ok=True)


def export_result(filename: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "filename": filename,
        "document_type": result["doc_type"],
        "confidence": result["confidence"],
        "summary": result["summary"],
        "provider": result["provider"],
        "model": result["model"],
        "fields": result["fields"],
    }


def render_result(filename: str, result: dict[str, Any], *, history_id: int | None = None) -> None:
    export = export_result(filename, result)
    heading, download = st.columns([3, 1])
    with heading:
        if history_id is None:
            st.subheader("Extraction result")
        st.caption(f"{filename} · {result['provider']} · {result['model']}")
    with download:
        st.download_button(
            "Download JSON", data=json.dumps(export, indent=2, ensure_ascii=False),
            file_name=f"{Path(filename).stem}_extracted.json", mime="application/json",
            width="stretch", on_click="ignore", key=f"download_{history_id}",
        )

    with st.container(border=True):
        document, confidence, field_count = st.columns([2, 1, 1])
        document.metric("Document type", result["doc_type"])
        confidence.metric("Confidence", result["confidence"])
        field_count.metric("Fields extracted", len(result["fields"]))
        st.caption("Confidence reflects the AI's assessment of the readable text.")
        if result["summary"]:
            st.write(result["summary"])
        if result["fields"]:
            rows = []
            for key, value in result["fields"].items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                rows.append({"Field": str(key), "Value": "—" if value in (None, "") else str(value)})
            st.dataframe(rows, hide_index=True, width="stretch")
        else:
            st.info("The AI did not find structured fields in this document.")

    with st.expander("Document details"):
        structured, ocr = st.tabs(["Structured JSON", "OCR text"])
        with structured:
            st.json(export)
        with ocr:
            st.text(result["text"].strip())


def render_history() -> None:
    history = st.session_state.get("runs", [])
    if history:
        st.subheader("Recent extractions")
        for index, run in enumerate(history):
            result = run["result"]
            with st.expander(f"{run['filename']} · {result['doc_type']} · {result['provider']}"):
                render_result(run["filename"], result, history_id=index)


def main() -> None:
    st.set_page_config(page_title="DocXtract | AI document extraction", page_icon="📄", layout="wide")
    st.title("DocXtract")
    st.write("Extract structured information from your documents with AI.")

    # Older sessions may contain results from an extraction method that no longer exists.
    st.session_state.setdefault("runs", [])
    st.session_state["runs"] = [run for run in st.session_state["runs"] if "result" in run]
    status = runtime_status()

    with st.sidebar:
        st.header("AI settings")
        provider_label = st.selectbox("Provider", ["Google Gemini", "Groq"], key="provider_choice")
        provider = "gemini" if provider_label == "Google Gemini" else "groq"
        if provider == "gemini":
            model = st.text_input("Model", value=DEFAULT_GEMINI_MODEL, key="gemini_model").strip()
            env_key = os.getenv("GEMINI_API_KEY", "")
        else:
            model = st.selectbox("Model", GROQ_MODELS, key="groq_model")
            env_key = os.getenv("GROQ_API_KEY", "")
        with st.expander("API key", expanded=not bool(env_key)):
            if env_key:
                st.caption("A key is configured. Enter an override only if needed.")
            entered_key = st.text_input(
                "API key override" if env_key else "API key",
                type="password", key=f"{provider}_api_key",
            ).strip()
        api_key = entered_key or env_key
        if api_key:
            st.caption("API key configured")
        else:
            st.warning("Add an API key to start extracting.")

        st.divider()
        st.caption("OCR runs locally. Extracted text is sent to your selected AI provider.")
        st.caption("PDF processing uses the first page.")
        with st.expander("OCR setup"):
            for label, name in [("Image OCR", "tesseract"), ("PDF support", "poppler")]:
                check = status[name]
                if check.available:
                    st.caption(f"{label}: ready · {check.message}")
                else:
                    st.warning(check.message)
            if st.button("Check setup again"):
                runtime_status.clear()
                st.rerun()

    if not status["tesseract"].available:
        st.error(status["tesseract"].message)
    elif not status["poppler"].available:
        st.warning(status["poppler"].message)

    with st.container(border=True):
        st.subheader("Add a document")
        uploaded_file = st.file_uploader(
            "Choose a PDF or image",
            type=[extension for extension in ALLOWED_EXTENSIONS
                  if extension != "pdf" or status["poppler"].available],
            help="PNG, JPG, JPEG, BMP, TIFF or PDF. Only the first PDF page is processed.",
            disabled=not status["tesseract"].available,
        )
        pdf_ready = uploaded_file is None or Path(uploaded_file.name).suffix.lower() != ".pdf" or status["poppler"].available
        ready = bool(uploaded_file and api_key and model and status["tesseract"].available and pdf_ready)
        requested = st.button("Extract document", type="primary", disabled=not ready)
        st.caption(f"Using {provider_label} · {model or 'Choose a model'}")

    if uploaded_file is None:
        render_history()
        return
    upload_key = (
        uploaded_file.name, hashlib.sha256(uploaded_file.getbuffer()).hexdigest(), provider, model,
        hashlib.sha256(api_key.encode()).hexdigest(),
    )
    if requested and ready:
        with st.spinner(f"Extracting with {provider_label}…"):
            try:
                result = process_upload(uploaded_file, provider=provider, model=model, api_key=api_key)
            except Exception as error:
                message = str(error).replace(api_key, "[redacted]") if api_key else str(error)
                st.error(f"Extraction failed: {message}")
                st.caption("Check the connection settings or try extracting again.")
                render_history()
                return
        st.session_state["last_result"] = {"key": upload_key, "result": result}
        history = st.session_state["runs"]
        history.insert(0, {"filename": uploaded_file.name, "result": result})
        del history[5:]

    previous = st.session_state.get("last_result")
    if previous and previous["key"] == upload_key:
        render_result(uploaded_file.name, previous["result"])
    else:
        st.info("Select Extract document when your document and AI settings are ready.")
    render_history()


if __name__ == "__main__":
    main()
