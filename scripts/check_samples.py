"""Check OCR locally; AI extraction is an explicit optional API check."""

import argparse
from pathlib import Path
from time import perf_counter

from docxtract import process_document
from docxtract.ocr import ocr_file

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract", action="store_true", help="Send sample OCR text to the AI provider (API usage).")
    parser.add_argument("--provider", choices=["gemini", "groq"], default="gemini")
    parser.add_argument("--model", default=None)
    args = parser.parse_args()
    failures = 0
    paths = [ROOT / "data/sample-image.png", *sorted((ROOT / "data/samples").glob("*"))]
    for path in paths:
        if not path.is_file():
            continue
        start = perf_counter()
        try:
            result = process_document(path, provider=args.provider, model=args.model) if args.extract else None
            text = result["text"] if result else ocr_file(path)
            if not text.strip():
                raise ValueError("OCR returned no text")
            details = f"{len(text)} text characters"
            if result:
                details += f"; {result['doc_type']}; {len(result['fields'])} extracted fields"
            print(f"OK {path.name}: {details}; {perf_counter() - start:.1f}s")
        except Exception as error:
            failures += 1
            print(f"FAIL {path.name}: {error}")
    print("This checks processing completion. AI field accuracy requires separate review.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
