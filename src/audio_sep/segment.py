from pathlib import Path
import subprocess

def extract_segment_to_wav(input_file: Path, output_wav: Path, start: float, end: float | None):
    """Decode and optionally trim audio to WAV using FFmpeg."""
    cmd = ["ffmpeg", "-y"]

    if start and start > 0:
        cmd += ["-ss", str(start)]

    cmd += ["-i", str(input_file)]

    if end is not None and end > 0:
        duration = max(0.0, end - start)
        cmd += ["-t", str(duration)]

    cmd += ["-ar", "44100", "-ac", "2", "-vn", str(output_wav)]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{p.stderr}")
