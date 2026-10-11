"""AI-only processing must report failures without producing substitute fields."""

import inspect
import json
import unittest
from unittest.mock import patch

from docxtract.llm_extractor import _clean_json_response
from docxtract.pipeline import process_document

AI_RESULT = {
    "doc_type": "Invoice", "confidence": "High", "summary": "An invoice for services.",
    "fields": {"Total": "123.45"}, "provider_used": "Groq", "model_used": "test-model",
}


class PipelineTests(unittest.TestCase):
    @patch("docxtract.pipeline.ocr_file", return_value="Invoice Total 123.45")
    @patch("docxtract.pipeline.extract_document_with_llm", return_value=AI_RESULT)
    def test_ocr_text_and_settings_are_forwarded_to_ai(self, extract, ocr):
        result = process_document("document.png", provider="groq", model="test-model", api_key="test-key")
        extract.assert_called_once_with(text="Invoice Total 123.45", provider="groq", model="test-model", api_key="test-key")
        self.assertEqual(result["fields"], AI_RESULT["fields"])
        self.assertEqual(result["provider"], "Groq")
        self.assertNotIn("mode", inspect.signature(process_document).parameters)

    @patch("docxtract.pipeline.ocr_file", return_value="Invoice")
    @patch("docxtract.pipeline.extract_document_with_llm", side_effect=RuntimeError("Provider unavailable"))
    def test_provider_failure_propagates_without_fallback(self, extract, ocr):
        with self.assertRaisesRegex(RuntimeError, "Provider unavailable"):
            process_document("document.png")

    @patch("docxtract.pipeline.ocr_file", return_value=" \n ")
    @patch("docxtract.pipeline.extract_document_with_llm")
    def test_empty_ocr_does_not_send_an_ai_request(self, extract, ocr):
        with self.assertRaisesRegex(ValueError, "No readable text"):
            process_document("document.png")
        extract.assert_not_called()


class ResponseTests(unittest.TestCase):
    def test_structured_result_and_markdown_wrapping(self):
        payload = {k: v for k, v in AI_RESULT.items() if k not in {"provider_used", "model_used"}}
        for text in [json.dumps(payload), "```json\n" + json.dumps(payload) + "\n```"]:
            self.assertEqual(_clean_json_response(text), payload)

    def test_invalid_json_and_invalid_shapes_are_errors(self):
        payload = {k: v for k, v in AI_RESULT.items() if k not in {"provider_used", "model_used"}}
        cases = ["not json", "[]", "{}", json.dumps({**payload, "fields": "text"}),
                 json.dumps({**payload, "confidence": "certain"}),
                 json.dumps({**payload, "doc_type": ""})]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                _clean_json_response(text)

    def test_nested_fields_and_empty_fields_are_supported(self):
        for fields in [{}, {"Items": [{"Amount": 123.45}], "Paid": False}]:
            payload = {"doc_type": "Invoice", "confidence": "medium", "summary": "", "fields": fields}
            result = _clean_json_response(json.dumps(payload))
            self.assertEqual(result["fields"], fields)
            self.assertEqual(result["confidence"], "Medium")
