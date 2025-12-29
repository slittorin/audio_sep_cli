from __future__ import annotations

from pathlib import Path
import numpy as np
import librosa
import soundfile as sf

def _safe_stft_mag(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Return (magnitude_spectrogram, freqs, n_fft) with n_fft chosen to avoid librosa warnings."""
    n = int(y.size)
    if n <= 0:
        return np.zeros((0, 0), dtype=np.float32), np.array([], dtype=np.float32), 0
    max_nfft = min(2048, n)
    p = 2 ** int(np.floor(np.log2(max(256, max_nfft))))
    n_fft = int(min(max_nfft, p))
    n_fft = max(256, min(n_fft, n))
    hop = max(64, n_fft // 8)
    S = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop, center=False))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    return S, freqs, n_fft

def _classify_hit(y: np.ndarray, sr: int) -> str:
    """Heuristic classifier: kick/snare/hat/other."""
    if y.size == 0:
        return "other"

    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=256))
    if S.size == 0:
        return "other"

    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    band_low = (freqs >= 20) & (freqs < 150)
    band_mid = (freqs >= 150) & (freqs < 2000)
    band_high = (freqs >= 2000) & (freqs < 12000)

    low_e = float(S[band_low, :].mean()) if band_low.any() else 0.0
    mid_e = float(S[band_mid, :].mean()) if band_mid.any() else 0.0
    high_e = float(S[band_high, :].mean()) if band_high.any() else 0.0

    centroid = float(librosa.feature.spectral_centroid(S=S, sr=sr).mean())

    if high_e > (mid_e * 1.2) and centroid > 3500:
        return "hat"
    if low_e > (mid_e * 0.9) and centroid < 1200:
        return "kick"
    if mid_e >= max(low_e, high_e) and 900 <= centroid <= 3500:
        return "snare"
    return "other"

def slice_and_classify_drum_hits(
    drums_wav: Path,
    out_dir: Path,
    pre_s: float = 0.03,
    post_s: float = 0.25,
    min_interval_s: float = 0.06,
    prefix: str = "track",
) -> dict:
    """Detect onsets, slice hits, classify them, and write WAVs."""
    y, sr = librosa.load(str(drums_wav), sr=None, mono=True)

    onset_frames = librosa.onset.onset_detect(
        y=y,
        sr=sr,
        backtrack=False,
        units="frames",
        pre_max=8,
        post_max=8,
        pre_avg=16,
        post_avg=16,
        delta=0.2,
        wait=int(max(1, min_interval_s * sr / 512)),
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    filtered = []
    last_t = -1e9
    for t in onset_times:
        t = float(t)
        if t - last_t >= min_interval_s:
            filtered.append(t)
            last_t = t

    pre_n = int(round(pre_s * sr))
    post_n = int(round(post_s * sr))

    counts = {"kick": 0, "snare": 0, "hat": 0, "other": 0}
    exported = 0

    for i, t in enumerate(filtered, start=1):
        center = int(round(t * sr))
        a = max(0, center - pre_n)
        b = min(len(y), center + post_n)
        hit = y[a:b]

        if hit.size > 32:
            fade = min(64, hit.size // 8)
            w = np.ones(hit.size, dtype=np.float32)
            w[:fade] = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            w[-fade:] = np.linspace(1.0, 0.0, fade, dtype=np.float32)
            hit = hit.astype(np.float32) * w

        label = _classify_hit(hit, sr)
        counts[label] = counts.get(label, 0) + 1
        exported += 1

        out_name = f"{prefix}__drums__hit-{i:04d}__t-{t:0.3f}s__{label}.wav"
        sf.write(out_dir / out_name, hit, sr, subtype="PCM_16")

    return {
        "onsets": len(onset_times),
        "exported": exported,
        "counts": counts,
        "sample_rate": sr,
        "source": str(drums_wav),
    }
