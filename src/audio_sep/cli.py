"""
audio-sep CLI

Version history (high level):
0.1 - First version from ChatGPT
0.2 - Vibe coding to fix errors with conversion
0.3 - Vibe coding to fix errors with two working-dirs for isolating stems.
0.4 - Vibe coding to add:
      Text output from the script that outlines the different stems/sounds that are isolated.
	  Drum-stem onset detection + hit slicing + classification (kick/snare/hat).
	  Keyboard as a stem: requires instrument separation / instrument recognition beyond the standard 4-stem Demucs output.

Notes:
- "Keyboard" stem: use Demucs 6-stem model (htdemucs_6s) which adds piano and guitar sources.
"""
from pathlib import Path
import uuid
import typer
from rich import print

from . import __version__
from .segment import extract_segment_to_wav
from .separate import run_demucs
from .keydetect import estimate_key_label_for_wav
from .drums import slice_and_classify_drum_hits
from .notes import slice_stem_into_events, estimate_pitch_note_for_wav

app = typer.Typer(add_completion=False, no_args_is_help=True)

SUPPORTED_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".wma", ".aiff", ".aif"}

def _version_callback(value: bool):
    if value:
        print(f"audio-sep {__version__}")
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    # If no subcommand is provided, these args/options apply to the default 'separate' action.
    input_file: Path | None = typer.Argument(None, help="Audio file to process (default action: separate)."),
    out_dir: Path = typer.Option(Path("out"), "--out", "-o"),
    start: float = typer.Option(0.0, "--start", help="Start time in seconds"),
    end: float = typer.Option(None, "--end", help="End time in seconds (optional)"),
    model: str = typer.Option("htdemucs", "--model", help="Demucs model name (try htdemucs_6s for piano/guitar)"),
    stems_only: bool = typer.Option(False, "--stems-only", help="Only write stems (skip drum hit slicing)."),
    drum_hits: bool = typer.Option(False, "--drum-hits/--no-drum-hits", help="Slice drum stem into hits and classify."),
    hit_pre: float = typer.Option(0.03, "--hit-pre", help="Seconds before onset to include in a hit."),
    hit_post: float = typer.Option(0.25, "--hit-post", help="Seconds after onset to include in a hit."),
    hit_min_interval: float = typer.Option(0.06, "--hit-min-interval", help="Minimum interval between onsets (seconds)."),
    note_slices: bool = typer.Option(False, "--note-slices/--no-note-slices", help="Slice tonal stems into event WAVs (note/chord/phrase)."),
    note_stems: str = typer.Option("bass,guitar,piano,vocals,other", "--note-stems", help="Comma-separated stems to slice when --note-slices is enabled."),
    note_pre: float = typer.Option(0.01, "--note-pre", help="Seconds before onset to include in a slice."),
    note_post: float = typer.Option(0.60, "--note-post", help="Seconds after onset to include in a slice."),
    note_min_interval: float = typer.Option(0.08, "--note-min-interval", help="Minimum interval between onsets for tonal slicing (seconds)."),
    note_delta: float = typer.Option(0.15, "--note-delta", help="Onset detector sensitivity for tonal slicing (higher=less sensitive)."),
    note_max_events: int | None = typer.Option(None, "--note-max-events", help="Limit number of slices per stem (for testing)."),
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit.", callback=_version_callback),
):
    # If no subcommand was invoked, run default action.
    if ctx.invoked_subcommand is None:
        if input_file is None:
            # no_args_is_help=True will show help
            return
        separate(
            input_file=input_file,
            out_dir=out_dir,
            start=start,
            end=end,
            model=model,
            stems_only=stems_only,
            drum_hits=drum_hits,
            hit_pre=hit_pre,
            hit_post=hit_post,
            hit_min_interval=hit_min_interval,
            note_slices=note_slices,
            note_stems=note_stems,
            note_pre=note_pre,
            note_post=note_post,
            note_min_interval=note_min_interval,
            note_delta=note_delta,
            note_max_events=note_max_events,
        )

@app.command()
def separate(
    input_file: Path = typer.Argument(..., exists=True, readable=True),
    out_dir: Path = typer.Option(Path("out"), "--out", "-o"),
    start: float = typer.Option(0.0, "--start", help="Start time in seconds"),
    end: float = typer.Option(None, "--end", help="End time in seconds (optional)"),
    model: str = typer.Option("htdemucs", "--model", help="Demucs model name (try htdemucs_6s for piano/guitar)"),
    stems_only: bool = typer.Option(False, "--stems-only", help="Only write stems (skip drum hit slicing)."),
    drum_hits: bool = typer.Option(False, "--drum-hits/--no-drum-hits", help="Slice drum stem into hits and classify."),
    hit_pre: float = typer.Option(0.03, "--hit-pre", help="Seconds before onset to include in a hit."),
    hit_post: float = typer.Option(0.25, "--hit-post", help="Seconds after onset to include in a hit."),
    hit_min_interval: float = typer.Option(0.06, "--hit-min-interval", help="Minimum interval between onsets (seconds)."),
    note_slices: bool = typer.Option(False, "--note-slices/--no-note-slices", help="Slice tonal stems into event WAVs (note/chord/phrase)."),
    note_stems: str = typer.Option("bass,guitar,piano,vocals,other", "--note-stems", help="Comma-separated stems to slice when --note-slices is enabled."),
    note_pre: float = typer.Option(0.01, "--note-pre", help="Seconds before onset to include in a slice."),
    note_post: float = typer.Option(0.60, "--note-post", help="Seconds after onset to include in a slice."),
    note_min_interval: float = typer.Option(0.08, "--note-min-interval", help="Minimum interval between onsets for tonal slicing (seconds)."),
    note_delta: float = typer.Option(0.15, "--note-delta", help="Onset detector sensitivity for tonal slicing (higher=less sensitive)."),
    note_max_events: int | None = typer.Option(None, "--note-max-events", help="Limit number of slices per stem (for testing)."),
):
    """Separate an audio file (or a time segment) into stems and write WAV outputs."""
    if input_file.suffix.lower() not in SUPPORTED_EXTS:
        raise typer.BadParameter(f"Unsupported format: {input_file.suffix}")

    out_dir.mkdir(parents=True, exist_ok=True)

    if stems_only:
        # Force-disable all slicing regardless of other flags
        drum_hits = False
        note_slices = False


    seg_id = uuid.uuid4().hex[:8]
    tmp_wav = out_dir / f"__segment__{seg_id}.wav"

    extract_segment_to_wav(input_file, tmp_wav, start=start, end=end)

    stems_dir = run_demucs(tmp_wav, out_dir=out_dir, model=model)

    created = []
    for wav in sorted(stems_dir.glob("*.wav")):
        stem = wav.stem.lower()
        key = "NA" if stem == "drums" else estimate_key_label_for_wav(wav)
        new_name = f"{input_file.stem}__{stem}__key-{key}.wav"
        new_path = stems_dir / new_name
        wav.rename(new_path)
        created.append((stem, key, new_path))

    if tmp_wav.exists():
        tmp_wav.unlink()

    print("\n[bold]== STEMS CREATED ==[/bold]")
    for stem, key, path in created:
        print(f" - {stem:>7} | key≈{key:<4} | {path}")
    print(f"\n[green]Stems written to:[/green] {stems_dir}\n")

    if stems_only:
        return

    if drum_hits:
        renamed_drums = next(stems_dir.glob(f"{input_file.stem}__drums__key-NA.wav"), None)
        if renamed_drums is None:
            print("[yellow]Note:[/yellow] No drum stem found. Skipping hit slicing.")
            return

        hits_dir = stems_dir / "drum_hits"
        hits_dir.mkdir(exist_ok=True)

        result = slice_and_classify_drum_hits(
            drums_wav=renamed_drums,
            out_dir=hits_dir,
            pre_s=hit_pre,
            post_s=hit_post,
            min_interval_s=hit_min_interval,
            prefix=input_file.stem,
        )

        print("[bold]== DRUM HITS ==[/bold]")
        print(f" Onsets detected: {result['onsets']}")
        print(f" Exported hits:   {result['exported']}")
        print(f"  - kick:  {result['counts'].get('kick', 0)}")
        print(f"  - snare: {result['counts'].get('snare', 0)}")
        print(f"  - hat:   {result['counts'].get('hat', 0)}")
        print(f"  - other: {result['counts'].get('other', 0)}")
        print(f"[green]Hits written to:[/green] {hits_dir}\n")

    # Tonal stem event slicing (note/chord/phrase events)
    if note_slices:
        wanted = {s.strip().lower() for s in note_stems.split(",") if s.strip()}
        print("[bold]== NOTE SLICES ==[/bold]")
        for stem, _key, stem_path in created:
            if stem not in wanted:
                continue
            out_events = stems_dir / f"{stem}_events"
            out_events.mkdir(exist_ok=True)
            res = slice_stem_into_events(
                stem_wav=stem_path,
                out_dir=out_events,
                prefix=input_file.stem,
                stem_label=stem,
                pre_s=note_pre,
                post_s=note_post,
                min_interval_s=note_min_interval,
                delta=note_delta,
                max_events=note_max_events,
            )
            renamed = 0
            for p in list(Path(out_events).glob(f"{input_file.stem}__{stem}__evt-*.wav")):
                pitch, _vr = estimate_pitch_note_for_wav(p)
                k = estimate_key_label_for_wav(p)
                p.rename(p.with_name(p.stem + f"__pitch-{pitch}__key-{k}.wav"))
                renamed += 1
            print(f" - {stem}: onsets={res['onsets']} slices={res['exported']} -> {out_events}")
        print("")

if __name__ == "__main__":
    app()
