"""AI-only UI tests use synthetic results and never call cloud providers."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

from docxtract.runtime import RuntimeCheck

APP = Path(__file__).resolve().parents[1] / "apps/streamlit/app.py"
READY = {name: RuntimeCheck(True, "Ready") for name in ("tesseract", "poppler")}
RESULT = {
    "text": "Synthetic invoice text", "doc_type": "Invoice", "confidence": "High",
    "summary": "Synthetic invoice", "fields": {"Total": "123.45"},
    "provider": "Google Gemini", "model": "test-model",
}


class Upload:
    name = "synthetic.png"

    def __init__(self, content=b"synthetic"):
        self.content = content

    def getbuffer(self):
        return self.content


def extract_button(app):
    return next(button for button in app.button if button.label == "Extract document")


class AppTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        environment = patch.dict(os.environ, {"GEMINI_API_KEY": "synthetic-key", "GROQ_API_KEY": "synthetic-key"})
        environment.start()
        self.addCleanup(environment.stop)

    @patch("docxtract.runtime.check_runtime", return_value=READY)
    @patch("docxtract.process_document", return_value=RESULT)
    def test_explicit_extraction_and_rerun_reuse(self, process, checks):
        upload = Upload()
        with patch("streamlit.file_uploader", return_value=upload):
            app = AppTest.from_file(str(APP)).run()
            process.assert_not_called()
            self.assertEqual(len(app.radio), 0)
            extract_button(app).click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(process.call_count, 1)
            self.assertEqual(len(app.session_state["runs"]), 1)
            self.assertEqual(app.session_state["last_result"]["result"], RESULT)
            app.run()
            self.assertEqual(process.call_count, 1)
            upload.content = b"changed document"
            app.run()
            self.assertEqual(process.call_count, 1)
            extract_button(app).click().run()
            self.assertEqual(process.call_count, 2)
            self.assertEqual(len(app.session_state["runs"]), 2)

    @patch("docxtract.runtime.check_runtime", return_value=READY)
    @patch("docxtract.process_document", return_value=RESULT)
    def test_provider_and_full_key_change_require_explicit_extraction(self, process, checks):
        with patch("streamlit.file_uploader", return_value=Upload()):
            app = AppTest.from_file(str(APP)).run()
            key_input = next(item for item in app.text_input if item.key == "gemini_api_key")
            key_input.set_value("shared-prefix-key-one").run()
            extract_button(app).click().run()
            key_input = next(item for item in app.text_input if item.key == "gemini_api_key")
            key_input.set_value("shared-prefix-key-two").run()
            self.assertEqual(process.call_count, 1)
            self.assertFalse(any(item.value == "Extraction result" for item in app.subheader))
            extract_button(app).click().run()
            self.assertEqual(process.call_count, 2)
            self.assertEqual(process.call_args.kwargs["api_key"], "shared-prefix-key-two")
            app.selectbox[0].select("Groq").run()
            self.assertEqual(process.call_count, 2)
            extract_button(app).click().run()
            self.assertEqual(process.call_args.kwargs["provider"], "groq")
            self.assertEqual(len(app.exception), 0)

    @patch("docxtract.runtime.check_runtime", return_value=READY)
    @patch("docxtract.process_document", return_value=RESULT)
    def test_history_is_bounded(self, process, checks):
        upload = Upload()
        with patch("streamlit.file_uploader", return_value=upload):
            app = AppTest.from_file(str(APP)).run()
            for index in range(7):
                upload.content = str(index).encode()
                app.run()
                extract_button(app).click().run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(len(app.session_state["runs"]), 5)

    @patch("docxtract.process_document")
    def test_missing_tesseract_disables_upload_and_extraction(self, process):
        status = {**READY, "tesseract": RuntimeCheck(False, "Install Tesseract")}
        with patch("docxtract.runtime.check_runtime", return_value=status), patch("streamlit.file_uploader", return_value=Upload()) as uploader:
            app = AppTest.from_file(str(APP)).run()
            self.assertTrue(uploader.call_args.kwargs["disabled"])
            self.assertTrue(extract_button(app).disabled)
            self.assertIn("Install Tesseract", app.error[0].value)
            process.assert_not_called()

    @patch("docxtract.process_document", return_value=RESULT)
    def test_missing_poppler_keeps_image_processing_available(self, process):
        status = {**READY, "poppler": RuntimeCheck(False, "Install Poppler")}
        with patch("docxtract.runtime.check_runtime", return_value=status), patch("streamlit.file_uploader", return_value=Upload()) as uploader:
            app = AppTest.from_file(str(APP)).run()
            self.assertNotIn("pdf", uploader.call_args.kwargs["type"])
            self.assertFalse(extract_button(app).disabled)
            extract_button(app).click().run()
            self.assertEqual(len(app.exception), 0)
            process.assert_called_once()

    @patch("docxtract.runtime.check_runtime", return_value=READY)
    @patch("docxtract.process_document")
    def test_missing_key_disables_extraction(self, process, checks):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}), patch("streamlit.file_uploader", return_value=Upload()):
            app = AppTest.from_file(str(APP)).run()
            self.assertTrue(extract_button(app).disabled)
            process.assert_not_called()

    @patch("docxtract.runtime.check_runtime", return_value=READY)
    @patch("docxtract.process_document", side_effect=[ValueError("Provider unavailable"), RESULT])
    def test_provider_failure_has_no_result_and_can_be_retried(self, process, checks):
        with patch("streamlit.file_uploader", return_value=Upload()):
            app = AppTest.from_file(str(APP)).run()
            extract_button(app).click().run()
            self.assertIn("Provider unavailable", app.error[0].value)
            self.assertEqual(app.session_state["runs"], [])
            self.assertEqual(len(app.metric), 0)
            extract_button(app).click().run()
            self.assertEqual(process.call_count, 2)
            self.assertEqual(len(app.session_state["runs"]), 1)
            self.assertEqual(len(app.exception), 0)

    def test_temporary_upload_cleanup_and_export(self):
        spec = importlib.util.spec_from_file_location("docxtract_ui_test", APP)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory, patch.object(module, "UPLOAD_DIR", Path(directory)):
            for fail in (False, True):
                def process(path, **settings):
                    self.assertTrue(path.exists())
                    self.assertEqual(settings["provider"], "groq")
                    if fail:
                        raise ValueError("processing failed")
                    return RESULT
                with patch.object(module, "process_document", side_effect=process):
                    if fail:
                        with self.assertRaises(ValueError):
                            module.process_upload(Upload(), provider="groq")
                    else:
                        module.process_upload(Upload(), provider="groq")
                self.assertEqual(list(Path(directory).iterdir()), [])
            with patch.object(Upload, "getbuffer", side_effect=OSError("write failed")), self.assertRaises(OSError):
                module.process_upload(Upload())
            self.assertEqual(list(Path(directory).iterdir()), [])
        exported = module.export_result("synthetic.png", RESULT)
        self.assertEqual(exported["provider"], "Google Gemini")
        self.assertEqual(exported["model"], "test-model")
        self.assertEqual(exported["fields"], RESULT["fields"])
        self.assertNotIn("api_key", exported)


if __name__ == "__main__":
    unittest.main()
