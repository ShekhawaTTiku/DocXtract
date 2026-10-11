"""LLM-powered document classification and structured data extraction."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

# Ensure environment variables from .env are loaded
load_dotenv()

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

EXTRACTION_SYSTEM_PROMPT = """You are an expert Document Analysis and OCR Information Extraction AI.
Analyze the provided OCR text extracted from a document.

Your task:
1. Identify the exact Document Type (e.g., "Driver License", "Passport", "W2 Form", "Paystub", "Invoice", "Medical Report", "Utility Bill", "Bank Statement", "Insurance Certificate", etc.).
2. Assess extraction confidence ("High", "Medium", or "Low") based on OCR completeness and clarity.
3. Write a concise 1-sentence summary of the document contents.
4. Extract all relevant structured fields as key-value pairs. Be comprehensive: extract names, dates, identification numbers, addresses, monetary values, employer/issuer details, etc. Clean up minor OCR typos where obvious.

You MUST respond strictly with valid JSON conforming to this schema:
{
  "doc_type": "<Specific Document Type>",
  "confidence": "High" | "Medium" | "Low",
  "summary": "<1-sentence summary>",
  "fields": {
    "<Field Name>": "<Extracted Value>"
  }
}
Do not include any Markdown code fences or extra commentary outside the JSON object.
"""


def _clean_json_response(raw_text: str) -> dict[str, Any]:
    """Parse a structured AI result; invalid responses must not appear as success."""
    text = raw_text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text[3:-3].strip()
        if text.startswith("json"):
            text = text[4:].lstrip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("The AI returned an unreadable response. Try extracting the document again.") from error
    if not isinstance(data, dict):
        raise ValueError("The AI response must be a JSON object. Try extracting the document again.")
    document_type = data.get("doc_type")
    confidence = data.get("confidence")
    summary = data.get("summary")
    fields = data.get("fields")
    if not isinstance(document_type, str) or not document_type.strip():
        raise ValueError("The AI response is missing a document type. Try again.")
    if not isinstance(confidence, str) or confidence.strip().title() not in {"High", "Medium", "Low"}:
        raise ValueError("The AI response has an invalid confidence label. Try again.")
    if not isinstance(summary, str) or not isinstance(fields, dict):
        raise ValueError("The AI response must include a summary and structured fields. Try again.")
    return {
        "doc_type": document_type.strip(),
        "confidence": confidence.strip().title(),
        "summary": summary.strip(),
        "fields": fields,
    }


def extract_with_gemini(
    text: str,
    api_key: str | None = None,
    model: str = DEFAULT_GEMINI_MODEL,
) -> dict[str, Any]:
    """Extract structured data using Google Gemini API."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError(
            "Gemini API key is required. Set GEMINI_API_KEY in .env or pass it directly."
        )

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    prompt = f"{EXTRACTION_SYSTEM_PROMPT}\n\nDOCUMENT OCR TEXT:\n{text}"

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    result = _clean_json_response(response.text or "{}")
    result["provider_used"] = "Google Gemini"
    result["model_used"] = model
    return result


def extract_with_groq(
    text: str,
    api_key: str | None = None,
    model: str = DEFAULT_GROQ_MODEL,
) -> dict[str, Any]:
    """Extract structured data using Groq API."""
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError(
            "Groq API key is required. Set GROQ_API_KEY in .env or pass it directly."
        )

    from groq import Groq

    client = Groq(api_key=key)
    prompt = f"DOCUMENT OCR TEXT:\n{text}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    raw_content = response.choices[0].message.content or "{}"
    result = _clean_json_response(raw_content)
    result["provider_used"] = "Groq"
    result["model_used"] = model
    return result


def extract_document_with_llm(
    text: str,
    provider: str = "gemini",
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Unified entry point for LLM document extraction."""
    clean_provider = (provider or "gemini").strip().lower()
    if clean_provider in ("gemini", "google", "google-genai"):
        target_model = model or DEFAULT_GEMINI_MODEL
        return extract_with_gemini(text, api_key=api_key, model=target_model)
    elif clean_provider in ("groq", "llama"):
        target_model = model or DEFAULT_GROQ_MODEL
        return extract_with_groq(text, api_key=api_key, model=target_model)
    else:
        raise ValueError(
            f"Unsupported LLM provider '{provider}'. Supported: 'gemini', 'groq'."
        )
