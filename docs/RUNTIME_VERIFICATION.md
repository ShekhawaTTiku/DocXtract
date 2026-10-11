# Runtime reliability baseline

Verified on 11 October 2026 on Windows with Python 3.11.9.

## Current AI-only update

The application now extracts exclusively with Gemini/Groq. The former keyword/regex implementation and fallback have been removed. The UI uses explicit extraction requests, displays structured fields and document metadata, and keeps OCR/JSON details available in expanders. All 31 current automated tests pass using synthetic AI responses. Live provider requests were not required for these regression checks. The sample script now checks OCR locally by default; `--extract` explicitly enables AI requests. The sample category/field counts below belong to the earlier local extraction baseline.

## Changes

- Installed Tesseract 5.4.0.20240606 with English language data.
- Installed standalone Poppler 25.07.0 through WinGet.
- Added tool discovery, executable checks, language-data checks, and `python -m docxtract` diagnostics.
- Added startup guidance to Streamlit, with image processing still available if only Poppler is missing.
- Added `POPPLER_PATH` support and Windows installation fallbacks.
- Corrected the development-container paths, made setup fail when installation/checks fail, and restored Streamlit's default CORS/XSRF settings.
- Pinned the four direct Python dependencies to the locally tested versions.
- Added 60-second OCR/rendering timeouts and PDF image cleanup.
- Reused the current upload's result across Streamlit reruns, bounded session history to five entries, and updated deprecated width arguments.
- Added regression tests, a sample smoke-check script, and installation/troubleshooting instructions.
- Corrected a stale user-level `TESSERACT_CMD` override and restarted the existing server with the installed executable. The former server inherited a different obsolete executable path, which was absent from fresh-process test environments.
- Invalid Tesseract overrides now identify the configured command and advise correcting/removing the setting and restarting, rather than only suggesting installation.

## Real sample processing

The sample check was run with PATH restricted to Windows system folders. Tesseract and standalone Poppler were found through the application's Windows installation fallbacks. This verifies that processing does not depend on Codex's bundled Poppler.

| Input | Detected category | OCR characters | Populated fields | Result |
| --- | --- | ---: | ---: | --- |
| sample-image.png | Others | 286 | 0/0 | Passed |
| Doc1.jpg | W2 | 1,220 | 1/3 | Passed |
| Doc2.jpg | Passport | 171 | 2/3 | Passed |
| Doc3.png | Driving License | 201 | 3/3 | Passed |
| Doc4.pdf | Paystub | 809 | 3/3 | Passed |
| Doc5.pdf | Flood Certificate | 2,287 | 1/3 | Passed |

All six produced non-empty OCR text without processing exceptions. The detected categories agree with the visually reviewed sample categories. Populated fields can still contain incorrect values; the accuracy problems documented in the initial project review remain a separate improvement area.

## Automated checks

- 23 regression tests passed for runtime errors, stale overrides, language data, image-only operation, timeouts, corrupt images, resource cleanup, UI retries, result reuse, and bounded history.
- Streamlit's test harness processed actual image and PDF uploads through real OCR and rendered result tables without errors; temporary uploads were removed.
- Editable package installation succeeded and `pip check` reported no broken requirements.
- Git whitespace checks passed.
- The project server on `http://localhost:8501` returned HTTP 200 for its page and health endpoint. After correcting the stale override, it was restarted using this project's Python environment. A live browser check confirmed no startup error and an enabled upload control.

## Limits

- This baseline verifies local Windows processing. The development-container configuration was corrected but the container was not rebuilt in this session.
- PDF processing remains limited to the first page.
- No extraction-accuracy target is claimed. Low OCR quality and brittle extraction rules still affect results.
- Direct dependencies are pinned; this is not a full transitive dependency lock.

Run `python -m docxtract`, `python -m unittest discover -s tests -v`, and `python scripts/check_samples.py` to reproduce the checks after activating the project's environment.
