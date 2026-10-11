"""Exercise failure handling and resource cleanup without requiring OCR binaries."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image
from pdf2image.exceptions import PDFPopplerTimeoutError

from docxtract.ocr import ocr_file
from docxtract.runtime import RuntimeCheck


class OCRTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.image_path = self.root / "image.png"
        with Image.new("RGB", (10, 10), "white") as image:
            image.save(self.image_path)
        self.pdf_path = self.root / "document.pdf"
        self.pdf_path.write_bytes(b"synthetic; converter is mocked")
        patcher = patch("docxtract.ocr.check_tesseract", return_value=RuntimeCheck(True, "Ready", "tesseract"))
        self.tesseract = patcher.start()
        self.addCleanup(patcher.stop)

    def test_unsupported_file_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported file type"):
            ocr_file(self.root / "document.docx")

    def test_missing_file_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            ocr_file(self.root / "missing.png")

    def test_missing_tesseract_stops_before_ocr(self):
        self.tesseract.return_value = RuntimeCheck(False, "Install Tesseract")
        with self.assertRaisesRegex(RuntimeError, "Install Tesseract"):
            ocr_file(self.image_path)

    @patch("docxtract.ocr.check_poppler", return_value=RuntimeCheck(False, "Install Poppler"))
    @patch("docxtract.ocr.pytesseract.image_to_string", return_value="readable text")
    def test_images_work_without_poppler(self, read, poppler):
        self.assertEqual(ocr_file(self.image_path), "readable text")
        poppler.assert_not_called()
        self.assertEqual(read.call_args.kwargs["timeout"], 60)

    @patch("docxtract.ocr.check_poppler", return_value=RuntimeCheck(False, "Install Poppler"))
    def test_pdf_requires_poppler(self, poppler):
        with self.assertRaisesRegex(RuntimeError, "Install Poppler"):
            ocr_file(self.pdf_path)

    @patch("docxtract.ocr.check_poppler", return_value=RuntimeCheck(True, "Ready"))
    @patch("docxtract.ocr.poppler_path", return_value="configured/poppler")
    @patch("docxtract.ocr.convert_from_path")
    @patch("docxtract.ocr.pytesseract.image_to_string", side_effect=RuntimeError("OCR timeout"))
    def test_pdf_pages_are_closed_when_ocr_fails(self, read, convert, path, check):
        page = MagicMock()
        convert.return_value = [page]
        with self.assertRaisesRegex(RuntimeError, "OCR timeout"):
            ocr_file(self.pdf_path)
        page.close.assert_called_once()
        self.assertEqual(convert.call_args.kwargs["poppler_path"], "configured/poppler")
        self.assertEqual(convert.call_args.kwargs["timeout"], 60)

    @patch("docxtract.ocr.check_poppler", return_value=RuntimeCheck(True, "Ready"))
    @patch("docxtract.ocr.convert_from_path", side_effect=PDFPopplerTimeoutError)
    def test_pdf_conversion_timeout_has_readable_message(self, convert, check):
        with self.assertRaisesRegex(RuntimeError, "PDF conversion exceeded"):
            ocr_file(self.pdf_path)

    def test_corrupt_image_has_readable_message(self):
        self.image_path.write_bytes(b"not an image")
        with self.assertRaisesRegex(ValueError, "could not be read as an image"):
            ocr_file(self.image_path)


if __name__ == "__main__":
    unittest.main()
