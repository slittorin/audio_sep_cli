import subprocess
import sys
from pathlib import Path

def run(cmd):
    print(f"\n>>> Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)

def main():
    # Ensure we run from project root
    project_root = Path(__file__).parent
    cli_file = project_root / "src" / "audio_sep" / "cli.py"

    if not cli_file.exists():
        raise FileNotFoundError(f"CLI file not found: {cli_file}")

    # 1. Install PyInstaller
    run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"])

    # 2. Build executable
    run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "audio-sep",
        "--console",
        str(cli_file)
    ])

    print("\n✅ Build complete.")
    print("Executable is located in the 'dist/' directory.")

if __name__ == "__main__":
    main()
