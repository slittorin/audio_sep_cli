#!/usr/bin/env python
"""
Bootstrap script for Windows (Python 3.11):

Equivalent steps:
  python -m venv .venv
  .\.venv\Scripts\activate
  pip install -U pip setuptools wheel
  pip install torchcodec
  pip install -e .

Run (recommended):
  py -3.11 build.py
(or ensure your `python` is 3.11)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
VENV_PY = VENV_DIR / "Scripts" / "python.exe"


def run(cmd: list[str]) -> None:
    print(f"\n>> {' '.join(cmd)}")
    subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        check=True,
        stdin=subprocess.DEVNULL,  # prevents waiting for input
    )


def ensure_py311() -> None:
    if sys.version_info[:2] != (3, 11):
        raise SystemExit(
            f"This script must be run with Python 3.11. "
            f"Current: {sys.version_info.major}.{sys.version_info.minor}\n\n"
            f"Tip: run:  py -3.11 build.py"
        )


def ensure_venv() -> None:
    if VENV_PY.exists():
        return
    run([sys.executable, "-m", "venv", str(VENV_DIR)])


def pip_install(*args: str) -> None:
    # Always use venv python, so we don't depend on "activate" in the parent shell.
    run([str(VENV_PY), "-m", "pip", "install", *args])


def main() -> None:
    ensure_py311()
    ensure_venv()

    # Upgrade core packaging tools
    pip_install("-U", "pip", "setuptools", "wheel")

    # Install required package(s)
    pip_install("torchcodec")

    # Install current project in editable mode
    pip_install("-e", ".")

    print("\n✅ Done. Virtual environment is ready and project installed (editable).")
    print(f"Activate in PowerShell:\n  {VENV_DIR}\\Scripts\\Activate.ps1")


if __name__ == "__main__":
    main()
