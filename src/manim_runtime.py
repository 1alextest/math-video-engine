"""Detect Manim CLI availability for scene rendering."""

import os
import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _venv_manim_paths():
    if os.name == "nt":
        yield _PROJECT_ROOT / ".venv" / "Scripts" / "manim.exe"
    yield _PROJECT_ROOT / ".venv" / "bin" / "manim"


def resolve_manim_executable() -> str | None:
    """Return a Manim CLI path if found on PATH or in the project venv."""
    found = shutil.which("manim")
    if found:
        return found
    for path in _venv_manim_paths():
        if path.is_file():
            return str(path)
    return None


def is_manim_available() -> bool:
    return resolve_manim_executable() is not None


def manim_unavailable_reason() -> str | None:
    """Human-readable reason when Manim cannot run, else None."""
    if is_manim_available():
        return None
    if os.name == "nt":
        return (
            "Manim is not installed on this machine. On Windows, run the app with Docker "
            "(.\\restart.ps1) or install Manim + Visual C++ Build Tools in .venv."
        )
    return "Manim CLI not found on PATH. Install manim in the project venv or use Docker."


def manim_status_for_api() -> dict:
    exe = resolve_manim_executable()
    return {
        "manim_available": exe is not None,
        "manim_executable": exe,
        "manim_hint": manim_unavailable_reason(),
        "render_backend": "local" if exe else "unavailable",
    }
