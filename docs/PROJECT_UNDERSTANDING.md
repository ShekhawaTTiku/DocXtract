# DocXtract: project understanding and improvement discussion

Reviewed on 11 October 2026 against the current working folder at `D:\projects\DocXtract`.

**Historical snapshot:** This document records the initial review before implementation. The project now uses Gemini/Groq for AI-only extraction; the keyword classifier, rule-based extractors, and fallback described below have been removed. Refer to the current README for the active workflow. Runtime/setup work is described in [RUNTIME_VERIFICATION.md](RUNTIME_VERIFICATION.md). The old rule-specific findings below describe the former implementation.

This review describes the working files, including the existing uncommitted refactor. It does not treat the older Git commit as the current application. No application changes have been made as part of this review.

## Reusable project prompt

Use the following prompt to give an assistant or contributor the current project context. Recheck the source before implementation because this is a snapshot, not a permanent specification.

---

You are helping improve DocXtract, a Python document OCR and structured-data extraction prototype. The project is located at `D:\projects\DocXtract`. Understand the existing code and preserve the user's work before making changes. The user wants to discuss possible improvements, contribute their own ideas, agree on a small final scope, and then implement that agreed scope. Do not assume that every proposed improvement has been approved.

The current product lets a user upload one document in a Streamlit interface, reads its text using local Tesseract OCR, predicts a document category using keyword scoring, extracts a small set of fields using category-specific regular expressions, and displays the fields and raw OCR text. The user can download the extracted fields as JSON. The intended benefit is reducing manual transcription of document information. Current extraction accuracy is limited; this is a prototype rather than a verified general-purpose document understanding system.

The architecture separates the interface from a reusable processing package:

- `apps/streamlit/app.py` contains the current interface, temporary upload handling, result rendering, JSON download, and session history.
- `src/docxtract/__init__.py` exports `process_document`.
- `src/docxtract/pipeline.py` orchestrates OCR, classification, and extraction.
- `src/docxtract/ocr.py` handles supported images and PDF rasterization, configures Tesseract, and reports a missing Tesseract installation.
- `src/docxtract/classification.py` defines keyword lists and selects the highest scoring category.
- `src/docxtract/extractors.py` contains the five category-specific extraction functions and their dispatch table.
- `data/samples/` holds five example documents, and `data/sample-image.png` is a generic OCR text image.
- `pyproject.toml`, `requirements.txt`, `packages.txt`, and `.devcontainer/devcontainer.json` describe package installation and development setup.

The public processing contract is `process_document(path: str | Path) -> dict[str, Any]`. Its result contains `text` (raw OCR text), `doc_type` (the category string), and `fields` (a dictionary of extracted values). Known missing fields are generally represented as `None`. Unrecognized documents receive the category `Others` and an empty field dictionary. There are no result schemas, confidence scores, validation statuses, provenance coordinates, page metadata, or processing timings in this contract.

Supported inputs are PNG, JPG/JPEG, BMP, TIF/TIFF, and PDF. PDFs are converted with `pdf2image` using Poppler, and only their first page is processed. Images are opened with Pillow and passed directly to `pytesseract.image_to_string`. There is no explicit language selection, orientation correction, deskewing, image enhancement, OCR timeout, configurable page range, or embedded PDF text extraction. There is no deliberate processing of all frames of a multipage TIFF.

Tesseract is configured at module import. `TESSERACT_CMD` takes precedence; otherwise an existing executable at `C:\Program Files\Tesseract-OCR\tesseract.exe` is used; otherwise pytesseract relies on its default command resolution. OCR validates the suffix and checks that the source file exists. A missing Tesseract executable becomes an actionable `RuntimeError`. Other OCR and PDF errors propagate to the interface, where a broad exception handler displays an error message.

Classification is deterministic substring matching on case-folded text. Each distinct configured keyword contributes one point if present anywhere. The classifier selects the category with the highest score, returns `Others` only when all scores are zero, and resolves tied scores by dictionary insertion order. That order is Driving License, Passport, W2, Paystub, Flood Certificate. Broad keywords and overlapping phrases make this an unreliable confidence measure. The UI cannot currently override the detected category.

The current extraction coverage is:

| Category | Fields |
| --- | --- |
| Driving License | DL number, DOB, Name |
| Passport | Passport number, Country, Name |
| W2 | EIN, Year, Employee Name |
| Paystub | Net Pay, Employee Name, Employer Name |
| Flood Certificate | Borrower name, Customer No, Expire date |
| Others | No structured fields |

These extractors are heavily influenced by the included examples. License rules emphasize Arizona-style D-prefixed numbers; passport country handling recognizes the United States; paystub employer extraction specifically looks for Avalon. Names often fall back to generic capitalized words, which can select headings instead of people. Dates, identifiers, and monetary values remain strings and are not semantically validated. The flood form's extracted expiry value is the form's displayed expiry label; do not automatically interpret it as a loan or property determination expiry.

The Streamlit interface immediately processes a selected file on each script run. It creates a uniquely named temporary file under `data/uploads/`, processes it, and removes it in a `finally` block after processing succeeds or fails. Original uploads are not intentionally retained. Results are shown in a two-column layout with the detected category, filename, field table, JSON download, and an expandable raw-text view. The JSON download contains only the fields, without the category or processing metadata. Fields are displayed for review but are not editable.

Recent runs are stored in `st.session_state['runs']` as filename, category, and fields. Only five are displayed, but the stored list is not capped. There are no timestamps or stable document IDs. Repeated script runs with the same selected upload cause repeated processing and duplicate history entries. There is no database-backed history, authentication, API, CLI, job queue, batch upload, or external AI service in the current working application.

Packaging uses setuptools with a `src` layout, package name `docxtract`, version `0.1.0`, and Python >=3.10. Dependencies are `pdf2image`, `Pillow`, `pytesseract`, and `streamlit`, without pinned versions. `requirements.txt` installs the local package in editable mode using `-e .`. `packages.txt` lists the Linux packages `tesseract-ocr` and `poppler-utils`. The documented launch command is `streamlit run apps/streamlit/app.py` after package installation. The Streamlit dependency is currently included in the core package's dependencies, even for consumers interested only in the processing pipeline.

The dev container uses Python 3.11 on Debian Bookworm, installs system/Python dependencies, and forwards port 8501. Its open-file and launch settings still reference the removed root-level `streamlit_app.py`. Its launch flags also explicitly disable Streamlit CORS and XSRF protection. These settings should be reviewed when improving development/deployment setup. No production deployment workflow is defined in the current folder.

The working folder is mid-refactor. Existing staged and unstaged changes reorganize the old root-level scripts and sample files, remove the Flask frontend and SQLite persistence, and introduce the current package. Git HEAD still contains the older implementation. Do not restore removed files, recreate the old database, stage unrelated changes, or commit the refactor without the user's intent. No project-specific `AGENTS.md` was found in the inspected workspace or its parent instruction locations.

The review confirmed several issues using synthetic text:

- A license containing `EXP 12/31/2030` before `DOB 01/02/1990` returned the expiry as DOB. Global replacement of uppercase O with zero changes `DOB` to `D0B`, so the labeled DOB search fails and the first date is used. The same replacement damaged the name JOHN; the output name became Smith.
- A passport with the standard MRZ prefix `P<USASMITH<<JOHN...` failed MRZ name parsing and fell back to the incorrect name Passport Usasmith. A passport number adjacent to MRZ check digits and other content was missed by the standalone nine-digit regex.
- A generic paystub with an explicit employee Jane Doe returned Pay Stub as the employee name and did not extract an employer other than Avalon.
- A generic W2 with employee Jane Doe returned Wage Tax as the employee name through its fallback.
- The single word `income` classified as Paystub; `date of birth` classified as Passport. A tied `driver license passport` input selected Driving License without surfacing ambiguity.
- Streamlit's test harness confirmed that two runs with the same selected synthetic upload performed processing twice and created two history records.

The review also confirmed that all six application/package Python source files parse, the public package imports, the synthetic OCR-to-fields pipeline returns the documented structure, the UI initializes and renders a synthetic result without exceptions, and temporary uploads are removed after processing success and failure.

End-to-end OCR accuracy on the included documents has not been verified. The review environment has the project dependencies and Poppler, but Tesseract was not found on PATH or at the configured default Windows location, and `TESSERACT_CMD` was unset. Processing an included image produced the documented missing-Tesseract error. Both sample PDFs have one page and no embedded text; they were successfully rendered for visual inspection. The samples do not exercise multipage processing. No automated test suite or CI workflow currently exists in the source tree.

Prefer improvements that address observed errors and give the user control: reliable setup, meaningful regression fixtures, robust extraction and validation, explicit handling of ambiguous classifications, document preview with editable field review, and stable processing state without duplicate runs. Multi-page PDF support and batch processing are useful extensions. Persistent history, an API, a separate frontend, or an optional AI extraction path are later possibilities whose value depends on the user's chosen product direction. Preserve the reusable pipeline boundary and the local processing path when extending the system.

Before coding, discuss the user's ideas and agree on a few concrete outcomes and acceptance criteria. Recheck the working source, keep changes focused, and distinguish runtime-verified behavior from proposed future features.

---

## Improvement options to discuss

Effort estimates below are relative, not delivery commitments. These are proposals, not an approved implementation plan.

| Improvement | Why it matters here | Relative effort |
| --- | --- | --- |
| Reliable setup and runtime checks | Detect missing OCR binaries before an upload, repair dev-container paths, and document a reproducible launch. | Small |
| Extraction correctness and validation | Fix the confirmed DOB, name, and passport MRZ errors; scope OCR character corrections to candidate identifiers; validate dates, IDs, and amounts. | Medium |
| Classification with evidence and override | Show matching signals, reject weak or tied results, and let the user select a category and rerun extraction. Scores should not be presented as calibrated probabilities. | Small-medium |
| Preview and editable review | Show the uploaded document beside fields, allow corrections, highlight missing or suspect values, and export the reviewed result. | Medium |
| Stable processing and useful session history | Use a file/content identity and explicit processing state; prevent duplicate work and entries; cap retained results; add timestamps and clear-history controls. | Small-medium |
| Measured quality and regression checks | Establish expected category/field results, synthetic error cases, and representative layout variants so fixes can be evaluated. | Medium |
| Multi-page PDFs and better OCR | Support page selection or all pages, preserve page provenance, apply targeted preprocessing, and use embedded text when trustworthy. | Medium-large |
| Batch input and richer export | Process multiple documents with per-document progress and failures; export structured JSON and tabular summaries. | Medium |
| More useful fields per category | Add fields based on the user's actual workflow, such as passport dates, W2 wages/tax, payroll period/gross pay, and flood zone/determination information. | Medium; scope dependent |
| Optional persistent history | Restore persistence deliberately with reviewed outputs, source retention choices, deletion, and a defined access model. | Medium-large |
| API and alternate frontend | Wrap the shared package in an API when another client or integration is needed; keep extraction rules independent of the UI. | Large relative to the current app |
| Optional AI-assisted extraction | Evaluate whether a model improves unseen layouts against the same fixtures; preserve review, provenance, and an explicit local/cloud choice. | Large; adds operational decisions |
| Packaging and maintenance | Add development tooling and CI, constrain dependencies appropriately, update deprecated UI arguments, and consider a UI dependency extra. | Small-medium |

A reasonable initial shortlist is: (1) runtime/setup and repeatable quality checks, (2) extraction correctness plus classification ambiguity, and (3) document preview/editable review with stable processing state. Multi-page PDF support is a useful next candidate if longer documents are central to the user's needs. The final shortlist should incorporate the user's ideas before implementation.

## Verification boundaries and source map

- Current behavior was established from every application module, configuration file, README, sample asset, and relevant Git state/history.
- Synthetic probes isolate extraction logic from OCR. They demonstrate real rule failures but do not measure accuracy on the image/PDF fixtures.
- Streamlit UI checks used mocked processing results. They verify rendering and repeated-run behavior without implying working OCR.
- The installed review environment reported Python 3.11.9, docxtract 0.1.0, Streamlit 1.65.0, pytesseract 0.3.13, pdf2image 1.17.0, and Pillow 12.3.0. These are local installed versions, not a claim about current upstream releases.
- The installed Streamlit runtime emitted a deprecation warning for `use_container_width`; it is a maintenance item, while the reviewed UI still rendered.
- The three image fixtures visually correspond to a W2, passport, and driving license. The two PDF fixtures correspond to a paystub and flood determination form. The generic image exercises ordinary OCR text. Sample details were not reproduced here.
- The source has no license declaration, and sample provenance/ground-truth expectations are not documented. Clarifying these would help if the project is published or its fixtures are expanded.
- The review added this document only. It did not change application code, install Tesseract, introduce a test suite, or commit the existing refactor.
