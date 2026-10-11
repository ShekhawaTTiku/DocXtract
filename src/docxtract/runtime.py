"""Locate and verify the external OCR tools before processing documents."""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimeCheck:
    available: bool
    message: str
    command: str | None = None


def tesseract_command() -> str:
    """Honor explicit configuration (if valid), then PATH and common Windows installs."""
    if configured := os.getenv("TESSERACT_CMD"):
        if Path(configured).is_file():
            return configured
    if command := shutil.which("tesseract"):
        return command
    candidates = [
        Path(os.path.expanduser(r"~\PythonEnvs\Tesseract-OCR\tesseract.exe")),
        Path(r"C:\Users\GIGABYTE\PythonEnvs\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    ]
    if local_app_data := os.getenv("LOCALAPPDATA"):
        candidates.append(Path(local_app_data) / "Programs/Tesseract-OCR/tesseract.exe")
    return next((str(path) for path in candidates if path.is_file()), "tesseract")


def poppler_path() -> str | None:
    """Return an explicit/fallback binary directory, or use the system PATH."""
    if configured := os.getenv("POPPLER_PATH"):
        if Path(configured).is_dir():
            return configured
    if shutil.which("pdfinfo") and shutil.which("pdftoppm"):
        return None
    user_poppler = Path(os.path.expanduser(r"~\PythonEnvs\Poppler\Library\bin"))
    if user_poppler.is_dir():
        return str(user_poppler)
    if os.name == "nt" and (local_app_data := os.getenv("LOCALAPPDATA")):
        packages = Path(local_app_data) / "Microsoft/WinGet/Packages"
        for executable in sorted(
            packages.glob("oschwartz10612.Poppler_*/poppler-*/Library/bin/pdfinfo.exe"),
            reverse=True,
        ):
            if (executable.parent / "pdftoppm.exe").is_file():
                return str(executable.parent)
    return None


def _run(command: str, *arguments: str) -> str:
    result = subprocess.run(
        [command, *arguments], capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=10, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    return (result.stdout + "\n" + result.stderr).strip()


def check_tesseract() -> RuntimeCheck:
    command = tesseract_command()
    try:
        version = _run(command, "--version").splitlines()[0]
        languages = _run(command, "--list-langs").splitlines()
        if "eng" not in {line.strip() for line in languages}:
            return RuntimeCheck(False, "Tesseract needs English language data (eng.traineddata). "
                                "Install that data and check TESSDATA_PREFIX if it is set.", command)
        return RuntimeCheck(True, version, command)
    except (OSError, subprocess.SubprocessError, IndexError):
        if os.getenv("TESSERACT_CMD"):
            return RuntimeCheck(False, f"TESSERACT_CMD points to a command that could not run: {command}. "
                                "Correct or remove this setting, then restart the app.", command)
        return RuntimeCheck(False, "Tesseract could not run. Install Tesseract OCR, then add it "
                            "to PATH or set TESSERACT_CMD to its executable. See README setup.", command)


def check_poppler() -> RuntimeCheck:
    directory = poppler_path()
    suffix = ".exe" if os.name == "nt" else ""
    commands = [str(Path(directory) / f"{name}{suffix}") if directory
                else shutil.which(name) or name for name in ("pdfinfo", "pdftoppm")]
    try:
        versions = [_run(command, "-v") for command in commands]
        return RuntimeCheck(True, versions[0].splitlines()[0], commands[0])
    except (OSError, subprocess.SubprocessError, IndexError):
        return RuntimeCheck(False, "PDF support needs Poppler. Install it and add its bin folder "
                            "to PATH, or set POPPLER_PATH to the folder containing pdfinfo and "
                            "pdftoppm. Image uploads can still be processed.", commands[0])


def check_runtime() -> dict[str, RuntimeCheck]:
    return {"tesseract": check_tesseract(), "poppler": check_poppler()}


def main() -> int:
    checks = check_runtime()
    for name, result in checks.items():
        print(f"{'OK' if result.available else 'MISSING'} {name}: {result.message}")
        if result.command:
            print(f"  Command: {result.command}")
    return 0 if all(result.available for result in checks.values()) else 1
