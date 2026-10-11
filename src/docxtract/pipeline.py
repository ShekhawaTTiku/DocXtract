"""Reusable document-processing entry point for UI and future API layers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .llm_extractor import extract_document_with_llm
from .ocr import ocr_file


def process_document(
    path: str | Path,
    provider: str = "gemini",
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Read a document locally and extract its type and fields with the selected AI.

    OCR and provider errors propagate to the caller so they can be retried.
    """
    text = ocr_file(path)
    if not text.strip():
        raise ValueError("No readable text was found. Try a clearer image or PDF.")
    result = extract_document_with_llm(text=text, provider=provider, api_key=api_key, model=model)
    return {
        "text": text,
        "doc_type": result["doc_type"],
        "confidence": result["confidence"],
        "summary": result["summary"],
        "fields": result["fields"],
        "provider": result["provider_used"],
        "model": result["model_used"],
    }
