# DocXtract

DocXtract extracts structured data with Google Gemini or Groq after reading documents locally with Tesseract OCR. Streamlit provides the frontend, and the reusable processing package can also be called by another application.

## Current workflow

```text
Document upload → Extract document → Tesseract OCR → Gemini / Groq → Review fields and download JSON
```

The processing package is under `src/docxtract/`:

- `ocr.py` reads image formats and the first page of PDFs with Tesseract.
- `llm_extractor.py` uses Google Gemini or Groq to classify documents and extract structured fields, then validates the response shape.
- `pipeline.py` exposes `process_document(path, provider="gemini"|"groq", api_key=None, model=None)`.
- `runtime.py` locates and checks Tesseract, English language data, and Poppler.

The Streamlit frontend lives in `apps/streamlit/app.py`. Choose a provider and model, upload a document, and press **Extract document**. Changing settings does not send a request; extraction happens only when the button is pressed. The result includes type, summary, model-assessed confidence, fields, and provider/model details, with OCR text and structured JSON available under **Document details**. Current results and five recent extractions are kept in the Streamlit session. Uploads are removed after processing; there is no persistent database.

Extraction uses AI only. Provider failures are shown as errors and can be retried; there is no alternate extraction method or automatic fallback. Tesseract OCR remains a prerequisite for both providers.

## Project layout

```text
DocXtract/
├── apps/
│   └── streamlit/          # Current frontend
├── data/
│   ├── samples/            # Example documents
│   └── uploads/            # Temporary uploads; ignored by Git
├── src/
│   └── docxtract/          # Reusable OCR and extraction backend package
├── .devcontainer/          # Development container configuration
├── scripts/               # Real-document smoke check
├── tests/                 # Runtime, OCR failure, and UI regression checks
├── pyproject.toml
└── requirements.txt
```

For a future separate frontend/backend implementation, add the API or service layer alongside the shared `src/docxtract` package, and keep frontend code under `apps/`.

## Setup

Use Python 3.10 or newer (verified locally with Python 3.11). OCR/UI dependencies are pinned, while the AI SDK and dotenv dependencies use minimum versions. Transitive dependencies are resolved by pip.

Copy `.env.example` to `.env` and add `GEMINI_API_KEY`, `GROQ_API_KEY`, or both. Alternatively, enter a key in the sidebar's **API key** section. An API key for the selected provider and an internet connection are required. The original document is read locally; its OCR text is sent to the selected provider for extraction. `.env` is ignored by Git.

On Windows, run these commands from the repository root. Activation is optional when using the environment's Python directly:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
winget install --id UB-Mannheim.TesseractOCR --exact --source winget
winget install --id oschwartz10612.Poppler --exact --source winget
.\.venv\Scripts\python.exe -m docxtract
```

Tesseract is a separate program from the Python `pytesseract` package. Its Windows installer is linked from the [Tesseract installation documentation](https://tesseract-ocr.github.io/tessdoc/Installation.html). The Poppler package uses the [Poppler Windows distribution](https://github.com/oschwartz10612/poppler-windows).

On macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Debian / Ubuntu:
sudo apt-get install tesseract-ocr poppler-utils
# macOS alternative: brew install tesseract poppler
python -m docxtract
```

The OCR system tools must also be installed:

- **Tesseract OCR** needs English (`eng`) language data. Put it on `PATH`, or set `TESSERACT_CMD` to its executable path. Common Windows installation locations are also detected.
- **Poppler** needs both `pdfinfo` and `pdftoppm`. Put its binary folder on `PATH`, or set `POPPLER_PATH` to that folder. Standard per-user WinGet installations are detected if the commands are absent from the current `PATH`.

For a custom installation, set these in the terminal used to launch the app (replace the Poppler example with the actual folder):

```powershell
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
$env:POPPLER_PATH = 'C:\tools\poppler\Library\bin'
.\.venv\Scripts\python.exe -m docxtract
```

`python -m docxtract` prints the selected commands and readiness status, and exits with code 1 if either tool is unavailable. Explicit environment settings take precedence, so correct or remove stale overrides. After installing tools or changing persistent environment variables, reopen the terminal/app if needed. The UI's **Check setup again** button refreshes diagnostics without waiting for its 30-second cache.

The development container installs the Linux tools and Python dependencies, checks them, and launches the current Streamlit entry point on port 8501.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run apps/streamlit/app.py
```

With an activated environment on any platform, use `python -m streamlit run apps/streamlit/app.py`. Open the local URL printed in the terminal, normally `http://localhost:8501`. Stop the server with Ctrl+C.

Supported upload formats are PNG, JPG/JPEG, BMP, TIF/TIFF, and PDF. PDF OCR currently processes only the first page.

The app checks its tools before accepting documents. Missing Tesseract disables processing with setup guidance; missing Poppler disables PDF uploads while keeping image uploads available. OCR and PDF rendering each have a 60-second timeout. Invalid inputs produce an error in the app, and temporary uploads are cleaned up after processing errors.

## Verify the installation

From the repository root, using the environment's Python:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/check_samples.py
.\.venv\Scripts\python.exe -m pip check
```

The regression tests cover OCR failures, cleanup, explicit requests, provider failures without fallback, response validation, settings/key changes, retries, and bounded history. They use synthetic AI responses and do not require native tools, API keys, or paid requests.

The sample check requires the OCR tools and reads all six inputs locally by default. To deliberately test AI extraction as well, run `python scripts/check_samples.py --extract --provider groq` (or `gemini`), optionally adding `--model MODEL_NAME`. The `--extract` option sends sample OCR text to that provider and may incur API usage. It prints counts and timing without printing field values. This checks completion rather than field accuracy. See `docs/RUNTIME_VERIFICATION.md` for the local OCR baseline and current AI-only regression checks.

## Current limitations

- AI can return missing or incorrect fields, especially when OCR text is incomplete. Confidence is a model-reported label, not a measured accuracy score.
- AI extraction requires provider credentials and network access; request errors are surfaced for retry.
- Extracted values should be reviewed before being used for important decisions.
- OCR depends on locally installed Tesseract and Poppler binaries.
- There is no persistent processing history or API yet.

## Sample documents

Example inputs are in `data/samples/`. They are included as development fixtures; avoid adding real sensitive documents to source control.

## License

No license is currently specified.
