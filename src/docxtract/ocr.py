"""Local OCR support for image files and PDFs."""

from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPopplerTimeoutError
from PIL import Image, UnidentifiedImageError
from pytesseract import TesseractNotFoundError

from .runtime import check_poppler, check_tesseract, poppler_path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf"}
OCR_TIMEOUT_SECONDS = 60
PDF_TIMEOUT_SECONDS = 60


def ocr_file(path: str | Path) -> str:
    """Return OCR text from an image or the first page of a PDF."""
    source = Path(path)
    extension = source.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type {extension or '(no extension)'}. Supported: {supported}")
    if not source.is_file():
        raise FileNotFoundError(f"Document not found: {source}")

    tesseract = check_tesseract()
    if not tesseract.available:
        raise RuntimeError(tesseract.message)
    pytesseract.pytesseract.tesseract_cmd = tesseract.command

    try:
        if extension == ".pdf":
            poppler = check_poppler()
            if not poppler.available:
                raise RuntimeError(poppler.message)
            pages = convert_from_path(
                str(source), first_page=1, last_page=1,
                poppler_path=poppler_path(), timeout=PDF_TIMEOUT_SECONDS,
            )
            if not pages:
                raise ValueError("The PDF has no pages to process.")
            try:
                return pytesseract.image_to_string(pages[0], lang="eng", timeout=OCR_TIMEOUT_SECONDS)
            finally:
                for page in pages:
                    page.close()

        with Image.open(source) as image:
            return pytesseract.image_to_string(image, lang="eng", timeout=OCR_TIMEOUT_SECONDS)
    except TesseractNotFoundError as error:
        raise RuntimeError("Tesseract is unavailable. Run python -m docxtract to check setup.") from error
    except PDFInfoNotInstalledError as error:
        raise RuntimeError("Poppler is unavailable. Run python -m docxtract to check setup.") from error
    except PDFPopplerTimeoutError as error:
        raise RuntimeError("PDF conversion exceeded 60 seconds. Try a smaller PDF.") from error
    except UnidentifiedImageError as error:
        raise ValueError("This file could not be read as an image. Try another image or export it again.") from error

