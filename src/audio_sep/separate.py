from __future__ import annotations

from pathlib import Path
import subprocess
import time

def _dir_snapshot(d: Path) -> set[str]:
    if not d.exists():
        return set()
    return {p.name for p in d.iterdir() if p.is_dir()}

def _newest_dir_with_wavs(root: Path, before: set[str], t0: float) -> Path | None:
    if not root.exists():
        return None
    candidates: list[Path] = []
    for p in root.iterdir():
        if not p.is_dir():
            continue
        is_new = (p.name not in before) or (p.stat().st_mtime >= t0 - 1)
        if not is_new:
            continue
        if any(p.glob("*.wav")):
            candidates.append(p)
    if not candidates:
        return None
    candidates.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return candidates[0]

def run_demucs(input_wav: Path, out_dir: Path, model: str) -> Path:
    """Runs demucs and returns the directory containing the WAV stems."""
    parent_a = out_dir / "separated" / model
    parent_b = out_dir / model

    before_a = _dir_snapshot(parent_a)
    before_b = _dir_snapshot(parent_b)
    t0 = time.time()

    cmd = ["demucs", "-n", model, "--out", str(out_dir), str(input_wav)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"demucs failed:\n{p.stderr}\n\nstdout:\n{p.stdout}")

    found = _newest_dir_with_wavs(parent_a, before_a, t0)
    if found is not None:
        return found

    found = _newest_dir_with_wavs(parent_b, before_b, t0)
    if found is not None:
        return found

    for root in [parent_a, parent_b]:
        if not root.exists():
            continue
        for p2 in root.rglob("*"):
            if p2.is_dir() and p2.stat().st_mtime >= t0 - 1 and any(p2.glob("*.wav")):
                return p2

    raise RuntimeError(
        f"Expected stems folder not found. Looked under: {parent_a} and {parent_b}.\n"
        f"Hint: check where Demucs wrote output under '{out_dir}'."
    )
