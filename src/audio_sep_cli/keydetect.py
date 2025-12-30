from pathlib import Path
import numpy as np
import librosa

KRUMHANSL_MAJOR = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
KRUMHANSL_MINOR = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def _best_key_from_chroma(chroma_mean: np.ndarray) -> str:
    chroma_mean = chroma_mean / (np.linalg.norm(chroma_mean) + 1e-9)
    maj = KRUMHANSL_MAJOR / np.linalg.norm(KRUMHANSL_MAJOR)
    minr = KRUMHANSL_MINOR / np.linalg.norm(KRUMHANSL_MINOR)
    best_score = -1e9
    best_label = "NA"
    for i in range(12):
        score_maj = float(chroma_mean @ np.roll(maj, i))
        score_min = float(chroma_mean @ np.roll(minr, i))
        if score_maj > best_score:
            best_score, best_label = score_maj, f"{NOTE_NAMES[i]}maj"
        if score_min > best_score:
            best_score, best_label = score_min, f"{NOTE_NAMES[i]}m"
    return best_label

def estimate_key_label_for_wav(wav_path: Path) -> str:
    # Mono + downsample for speed.
    y, sr = librosa.load(str(wav_path), sr=22050, mono=True)

    # Very short slices produce unreliable chroma and can trigger librosa STFT warnings.
    # If shorter than ~46ms (1024 samples @ 22050Hz), treat as unknown.
    if len(y) < 1024:
        return "NA"

    # Also avoid trying to infer a key from tiny fragments.
    if len(y) < int(sr * 0.20):  # 200ms
        return "NA"

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    return _best_key_from_chroma(chroma.mean(axis=1))
