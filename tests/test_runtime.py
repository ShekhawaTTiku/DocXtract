"""Dependency failures should be actionable, including misconfigured paths."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docxtract import runtime


class RuntimeTests(unittest.TestCase):
    def test_explicit_tesseract_command_is_used(self):
        with tempfile.NamedTemporaryFile() as executable, \
             patch.dict(os.environ, {"TESSERACT_CMD": executable.name}):
            self.assertEqual(runtime.tesseract_command(), executable.name)

    @patch("docxtract.runtime._run", side_effect=FileNotFoundError)
    def test_missing_tesseract_has_setup_guidance(self, run):
        result = runtime.check_tesseract()
        self.assertFalse(result.available)
        self.assertIn("TESSERACT_CMD", result.message)

    @patch.dict(os.environ, {"TESSERACT_CMD": "missing/old-tesseract"})
    @patch("docxtract.runtime.shutil.which", return_value="working/tesseract")
    @patch("docxtract.runtime._run", side_effect=["tesseract 5", "Available languages:\neng"])
    def test_stale_override_uses_available_installation(self, run, which):
        result = runtime.check_tesseract()
        self.assertTrue(result.available)
        self.assertEqual(result.command, "working/tesseract")

    @patch("docxtract.runtime._run", side_effect=["tesseract 5", "Available languages:\neng\nosd"])
    def test_tesseract_with_english_is_ready(self, run):
        self.assertTrue(runtime.check_tesseract().available)

    @patch("docxtract.runtime._run", side_effect=["tesseract 5", "Available languages:\nosd"])
    def test_missing_english_is_not_ready(self, run):
        result = runtime.check_tesseract()
        self.assertFalse(result.available)
        self.assertIn("eng.traineddata", result.message)

    @patch("docxtract.runtime._run", side_effect=subprocess.TimeoutExpired("tesseract", 10))
    def test_hanging_executable_does_not_break_diagnostics(self, run):
        self.assertFalse(runtime.check_tesseract().available)

    @patch("docxtract.runtime._run", return_value="Poppler version 25")
    def test_explicit_poppler_path_checks_both_executables(self, run):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"POPPLER_PATH": directory}):
            self.assertTrue(runtime.check_poppler().available)
            commands = [Path(call.args[0]) for call in run.call_args_list]
            self.assertEqual(commands[0].parent, Path(directory))
            self.assertEqual(commands[1].parent, Path(directory))
            self.assertTrue(commands[0].stem == "pdfinfo")
            self.assertTrue(commands[1].stem == "pdftoppm")

    @patch("docxtract.runtime._run", side_effect=["pdfinfo 25", FileNotFoundError()])
    def test_pdfinfo_alone_is_not_sufficient(self, run):
        result = runtime.check_poppler()
        self.assertFalse(result.available)
        self.assertIn("POPPLER_PATH", result.message)

    @patch("docxtract.runtime._run", side_effect=subprocess.CalledProcessError(1, "pdfinfo"))
    def test_broken_poppler_is_not_reported_as_available(self, run):
        self.assertFalse(runtime.check_poppler().available)


if __name__ == "__main__":
    unittest.main()
