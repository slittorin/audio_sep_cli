#!/usr/bin/env python
"""
Build-exe script for Windows 

Hardcoded to Python 3.11, since we otherwise get errors with some of the packages.

Note that we also bundle FFmpeg-dll:s according to dll_dir below.
"""

import subprocess
import sys
from pathlib import Path

def run(cmd):
    print(f"\n>>> Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)

def main():
    project_root = Path(__file__).parent
    cli_file = project_root / "src" / "audio_sep_cli" / "cli.py"

    if not cli_file.exists():
        raise FileNotFoundError(f"CLI file not found: {cli_file}")

    # Directory that contains the DLLs you want to bundle
    # dll_dir = project_root / "dlls"   # <-- put your DLLs here (or change path)
    dll_dir = "C:/code/tools/ffmpeg/bin/"
    if not dll_dir.exists():
        print(f"⚠️ DLL directory not found (skipping): {dll_dir}")
        dll_glob = None
    else:
        dll_glob = str(dll_dir / "*.dll")

    # 1) Install PyInstaller
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"])

    # 2) Build executable
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "audio-sep-cli",
        "--console",
    ]

    # Add DLLs into an internal folder named "dlls"
    # NOTE: On Windows, the separator is ";" between src and dest
    if dll_glob:
        cmd += ["--add-binary", f"{dll_glob};dlls"]

    cmd += [str(cli_file)]
    run(cmd)

    print("\n✅ Build complete.")
    print("Executable is located in the 'dist/' directory.")

if __name__ == "__main__":
    main()
