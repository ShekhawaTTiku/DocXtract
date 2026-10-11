<div align="center">

# 📄 DocXtract

### Local OCR and AI-Powered Structured Document Extraction

*Read an image or PDF locally with Tesseract, send the extracted text to Google Gemini or Groq, and review structured fields in a Streamlit app.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![OCR](https://img.shields.io/badge/OCR-Tesseract-4C8C4A?style=for-the-badge)](https://tesseract-ocr.github.io/)
[![AI Providers](https://img.shields.io/badge/AI-Gemini%20%7C%20Groq-6C63FF?style=for-the-badge)](#-provider-configuration)

**[Overview](#-overview) · [Workflow](#-how-it-works) · [Installation](#-installation) · [Usage](#-usage)**

</div>

---

## ✨ Overview

**DocXtract** extracts document text locally with Tesseract OCR, then uses a selected AI provider to classify the document and return a short summary and structured key-value fields. The Streamlit interface displays the result and lets you review the OCR text and download JSON. The reusable `docxtract` package can also be called directly from Python.

| 📥 Input | 🔎 OCR | 🤖 Extraction | 📤 Result |
|:---:|:---:|:---:|:---:|
| Images or PDF documents | Local Tesseract OCR | Google Gemini or Groq | Type, summary, confidence label, fields, and JSON |

Supported image formats are PNG, JPG/JPEG, BMP, TIF, and TIFF. For PDFs, the current OCR pipeline processes **the first page only**.

---

## 🚀 Features

- 🖼️ Extract text from common image files and first-page PDF scans.
- 🧠 Select Google Gemini or Groq, a model, and an API key in the Streamlit sidebar.
- 🧾 Classify the document and extract a concise summary and structured fields.
- ✅ Validate that the provider response has the expected JSON shape before showing success.
- 📋 Review OCR text and structured JSON under **Document details**.
- 📥 Download the extraction result as JSON.
- 🧰 Check Tesseract and Poppler readiness before processing.
- 🧩 Call the processing pipeline from Python without using the Streamlit frontend.
- 🧹 Remove temporary uploaded files after processing and retain up to five recent results in the current Streamlit session.

---

## 🔄 How It Works

```text
Upload an image or PDF
          │
          ▼
Check local OCR prerequisites
          │
          ▼
Run Tesseract OCR locally
(English language data)
          │
          ▼
Send OCR text to the selected provider
(Gemini or Groq)
          │
          ▼
Validate the JSON response
          │
          ▼
Review fields, summary, and confidence
          │
          ▼
Download structured JSON
```

The source document is read locally. Its **OCR text** is sent to the selected AI provider for extraction. There is no automatic provider fallback: failures are surfaced in the interface so the user can retry or select another provider.

---

## 📋 Output Fields

Each extraction returns a JSON object with:

| Field | Description |
|---|---|
| `doc_type` | Model-identified document category, such as invoice, passport, or utility bill. |
| `confidence` | Model-assessed label: `High`, `Medium`, or `Low`. It is not a benchmarked probability of correctness. |
| `summary` | One-sentence summary of the document. |
| `fields` | Key-value fields inferred from the OCR text. |
| `provider` / `model` | Provider and model used for the request. |

The full OCR text is also returned by `process_document` and can be inspected in the app. Review extracted values against the original document before relying on them.

---

## ⚙️ Requirements

- **Python 3.10 or newer** (the project was locally verified with Python 3.11).
- **Tesseract OCR**, including English (`eng`) language data.
- **Poppler** for PDF rendering (`pdfinfo` and `pdftoppm`). Image extraction can run without Poppler.
- A Google Gemini or Groq API key and internet access for AI extraction.

Python dependencies are declared in `pyproject.toml` and installed through `requirements.txt`. Tesseract and Poppler are separate system programs, not Python packages.

---

## 📦 Installation

### 1. Clone and Install Python Dependencies

```bash
git clone https://github.com/ShekhawaTTiku/DocXtract.git
cd DocXtract
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, the virtual-environment Python can be used directly:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Install OCR System Tools

**Windows (WinGet):**

```powershell
winget install --id UB-Mannheim.TesseractOCR --exact --source winget
winget install --id oschwartz10612.Poppler --exact --source winget
```

**Debian / Ubuntu:**

```bash
sudo apt-get install tesseract-ocr poppler-utils
```

**macOS (Homebrew):**

```bash
brew install tesseract poppler
```

Tesseract must include its English language data. Tesseract and Poppler binaries should be available on `PATH`, or use the optional environment variables below.

### 3. Configure an AI Provider

Copy `.env.example` to `.env` and add at least one provider key:

```dotenv
GEMINI_API_KEY=your-gemini-key
GROQ_API_KEY=your-groq-key
```

Alternatively, enter the key for the selected provider in the app sidebar. Keep `.env` private and do not commit API keys.

### 4. Check the OCR Setup

```bash
python -m docxtract
```

This reports whether Tesseract and Poppler can be found. Use the environment's Python executable if the virtual environment is not activated.

If the tools are installed in nonstandard locations, set:

```powershell
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
$env:POPPLER_PATH = 'C:\tools\poppler\Library\bin'
```

---

## ▶️ Usage

### Streamlit App

From the repository root:

```bash
python -m streamlit run apps/streamlit/app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.

1. Select **Gemini** or **Groq** and choose a model.
2. Enter the selected provider's API key if it is not configured in `.env`.
3. Upload an image or PDF.
4. Press **Extract document** to send the OCR text to the provider.
5. Review the document type, summary, confidence label, and fields.
6. Open **Document details** to inspect OCR text and JSON, or download the JSON result.

Changing provider settings does not trigger an API request by itself. Extraction happens when you press the button.

### Python Package

The reusable pipeline accepts a document path and provider selection:

```python
from docxtract import process_document

result = process_document(
    "data/samples/Doc1.jpg",
    provider="gemini",  # or "groq"
)

print(result["doc_type"])
print(result["fields"])
```

You can provide `api_key=` and `model=` explicitly. Without an explicit API key, the package reads the selected provider's key from environment variables. The function returns OCR text, document type, confidence label, summary, fields, provider, and model. OCR and provider errors are raised to the caller.

---

## 📁 Project Structure

```text
DocXtract/
├── apps/
│   └── streamlit/app.py        # Streamlit frontend
├── src/docxtract/
│   ├── ocr.py                  # Image and first-page PDF OCR
│   ├── llm_extractor.py        # Gemini/Groq calls and JSON validation
│   ├── pipeline.py             # Reusable process_document() API
│   ├── runtime.py              # Tesseract and Poppler detection
│   └── __main__.py             # python -m docxtract diagnostics
├── data/samples/               # Example image and PDF inputs
├── data/uploads/               # Temporary uploads; ignored by Git
├── scripts/check_samples.py    # Local OCR / optional AI smoke check
├── tests/                      # Runtime, OCR, pipeline, and UI checks
├── docs/                       # Project and runtime notes
├── .env.example
├── pyproject.toml
└── requirements.txt
```

---

## 🧪 Verification

Run the local regression suite and dependency checks from the repository root:

```bash
python -m unittest discover -s tests -v
python -m pip check
```

Check the included sample files with local OCR:

```bash
python scripts/check_samples.py
```

To also send sample OCR text to an AI provider, use `--extract --provider groq` or `--provider gemini`. This makes provider requests and may incur API usage. The sample check reports completion and timing; it does not measure field-level accuracy.

---

## ⚠️ Limitations

| Area | Current limitation |
|---|---|
| OCR | Accuracy depends on scan quality, orientation, language data, and Tesseract. |
| PDF pages | Only the first page of a PDF is processed. |
| AI output | Fields can be missing or incorrect; the confidence label is model-assessed, not a measured accuracy score. |
| Provider calls | OCR text is sent to the chosen external provider; internet access and a valid API key are required. There is no automatic fallback. |
| Native tools | PDF support depends on Poppler. Without it, image uploads remain available but PDFs are disabled. |
| Persistence | Recent extraction history exists only in the current Streamlit session; there is no persistent database or API. |
| Timeouts | OCR and PDF conversion are limited to 60 seconds. Large or complex documents may need preprocessing. |

---

## 🛣️ Future Improvements

- 📚 Support multi-page PDFs with per-page review.
- 🌐 Add language selection and multilingual OCR options.
- 🔄 Offer an explicit retry with a different provider when extraction fails.
- 🗃️ Add an opt-in persistent history store with clear retention controls.
- 📏 Evaluate field-level accuracy on a documented sample set.
- 🧰 Add batch processing while preserving per-document review and error reporting.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| **Python** | OCR, extraction pipeline, and app logic |
| **Tesseract / pytesseract** | Local English OCR |
| **Poppler / pdf2image** | Render the first PDF page for OCR |
| **Pillow** | Image loading |
| **Streamlit** | Upload, extraction, review, and download UI |
| **Google GenAI** | Gemini structured extraction |
| **Groq** | Groq-hosted model structured extraction |
| **python-dotenv** | Local provider and OCR configuration |

---

## 👤 Maintainer

**Digvijay Singh Shekhawat**

[![GitHub](https://img.shields.io/badge/GitHub-@ShekhawaTTiku-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ShekhawaTTiku)

---

<div align="center">

*Built with 🔎 Tesseract OCR, 🤖 AI, and 🖥️ Streamlit.*

</div>
