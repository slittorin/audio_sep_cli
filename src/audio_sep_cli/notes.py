from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import librosa
import soundfile as sf

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def _safe_frame_length(n: int, max_frame: int = 2048, min_frame: int = 256) -> int:
    if n < min_frame:
        return 0
    frame = min(max_frame, n)
    # Use a power-of-two frame length to avoid FFT warnings.
    frame = 2 ** int(np.floor(np.log2(frame)))
    return max(min_frame, frame)

def _hz_to_note_name(f: float) -> str:
    if not np.isfinite(f) or f <= 0:
        return "NA"
    midi = 69 + 12 * math.log2(f / 440.0)
    midi_round = int(round(midi))
    name = NOTE_NAMES[midi_round % 12]
    octave = (midi_round // 12) - 1
    return f"{name}{octave}"

def estimate_pitch_note_for_wav(wav_path: Path) -> tuple[str, float]:
    y, sr = librosa.load(str(wav_path), sr=None, mono=True)
    if y.size < sr * 0.05:
        return ("NA", 0.0)
    if y.size == 0 or float(np.max(np.abs(y))) < 1e-4:
        return ("NA", 0.0)
    frame_length = _safe_frame_length(int(y.size))
    if frame_length == 0:
        return ("NA", 0.0)
    hop_length = max(1, frame_length // 4)
    f0 = librosa.yin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C7"),
        sr=sr,
        frame_length=frame_length,
        hop_length=hop_length,
    )
    voiced = np.isfinite(f0)
    voiced_ratio = float(np.mean(voiced)) if f0.size else 0.0
    if voiced_ratio < 0.25:
        return ("NA", voiced_ratio)
    f0_med = float(np.nanmedian(f0))
    return (_hz_to_note_name(f0_med), voiced_ratio)

def slice_stem_into_events(
    stem_wav: Path,
    out_dir: Path,
    prefix: str,
    stem_label: str,
    pre_s: float = 0.01,
    post_s: float = 0.6,
    min_interval_s: float = 0.08,
    delta: float = 0.15,
    max_events: int | None = None,
) -> dict:
    y, sr = librosa.load(str(stem_wav), sr=None, mono=True)

    # Separate harmonic/percussive components; detect onsets on harmonic
    y_harm, _ = librosa.effects.hpss(y)
    y_onset = y_harm

    onset_frames = librosa.onset.onset_detect(
        y=y_onset,
        sr=sr,
        units="frames",
        backtrack=False,
        pre_max=16,
        post_max=16,
        pre_avg=32,
        post_avg=32,
        delta=delta,
        wait=int(max(1, min_interval_s * sr / 512)),
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    filtered: list[float] = []
    last_t = -1e9
    for t in onset_times:
        t = float(t)
        if t - last_t >= min_interval_s:
            filtered.append(t)
            last_t = t

    if max_events is not None:
        filtered = filtered[:max_events]

    pre_n = int(round(pre_s * sr))
    post_n = int(round(post_s * sr))

    exported = 0
    paths: list[Path] = []
    for i, t in enumerate(filtered, start=1):
        center = int(round(t * sr))
        a = max(0, center - pre_n)
        b = min(len(y), center + post_n)
        seg = y[a:b]

        # Fade to reduce clicks
        if seg.size > 32:
            fade = min(128, seg.size // 8)
            w = np.ones(seg.size, dtype=np.float32)
            w[:fade] = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            w[-fade:] = np.linspace(1.0, 0.0, fade, dtype=np.float32)
            seg = seg.astype(np.float32) * w

        out_name = f"{prefix}__{stem_label}__evt-{i:04d}__t-{t:0.3f}s.wav"
        out_path = out_dir / out_name
        sf.write(out_path, seg, sr, subtype="PCM_16")
        paths.append(out_path)
        exported += 1

    return {
        "onsets": len(onset_times),
        "exported": exported,
        "paths": [str(p) for p in paths],
        "sample_rate": sr,
        "source": str(stem_wav),
    }
