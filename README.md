# audio-sep (Windows CLI)

Extract stems/slicings to wav-files from an audio-file, includes possibility for drum hit slicing/classification and keyboard/piano stem/slicing.
The stems are analysed for possible key, where key is added to filename.

## Versions:
0.1.0 - First version from ChatGPT.\
0.2.0 - Vibe coding to fix errors with conversion.\
0.3.0 - Vibe coding to fix errors with two working-dirs for isolating stems.\
0.4.0 - Vibe coding to add:\
        Text output from the script that outlines the different stems/sounds that are isolated.\
	      Drum-stem onset detection + hit slicing + classification (kick/snare/hat).\
	      Keyboard as a stem: requires instrument separation / instrument recognition beyond the standard 4-stem Demucs output.\
0.5.0 - Added stem-notes also for bass,guitar,piano,vocals,other.\
0.6.0 - Fixed warning with spectrum.py, and default options.

## Install (dev)

### Python
Install Python 3.11

### Install FFmpeg
Install in PowerShell: `winget install -e --id Gyan.FFmpeg`

However, as the above does not contain thew dll:s needed for build, we needed to:
- Download full build from: https://www.gyan.dev/ffmpeg/builds: ffmpeg-7.1.1-full_build-shared.7z
  - Extract iso that exe and dll:s are under `C:\Code\tools\ffmpeg\bin`
- Run: `sysdm.cpl`, and add path to dll:s: 
  - Advanced tab → Environment Variables
    - Under User variables (or System):
	  - Select Path → Edit
        - New → add (before row for Gyans.FFmpeg): C:\Code\tools\ffmpeg\bin
- Check with the following PowerShell that .dll:s are shown:
    ```
    $ff = Split-Path (Get-Command ffmpeg).Source
    dir $ff | findstr /i ".dll"
    ```

### Setup PowerShell
Run the following PowerShell-command: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted`

### Setup the environment
In PowerShell run:
```
python -m venv .venv
.\.venv\Scripts\activate
pip install -U pip setuptools wheel
pip install torchcodec
```

### Build
In PowerShell run:
```
pip install -e .
```

## Usage
Usage: `audio-sep [COMMAND] [OPTIONS] [INPUT_FILE]`
Command:
```
separate										   Separate stems (default, optional)
```

Options:
```
--out               -o                    PATH     Out-directory, created if not exists [default: out].
--start                                   FLOAT    Start time in seconds [default: 0.0].
--end                                     FLOAT    End time in seconds (optional).
--model                                   TEXT     Demucs model name, default: htdemucs. Try htdemucs_6s for piano/guitar).
--stems-only                                       Only write stems (skip drum-hit-, and note-slicing).
--drum-hits         --no-drum-hits                 Slice drum stem into hits and classify. [default: no-drum-hits].
--hit-pre                                 FLOAT    Seconds before onset to include in a hit. [default: 0.03].
--hit-post                                FLOAT    Seconds after onset to include in a hit. [default: 0.25].
--hit-min-interval                        FLOAT    Minimum interval between onsets (seconds). [default: 0.06].
--note-slices       --no-note-slices               Slice tonal stems into event WAVs (note/chord/phrase) [default: no-note-slices].
--note-stems                              TEXT     Comma-separated stems to slice when --note-slices is enabled [default: bass,guitar,piano,vocals,other].
--note-pre                                FLOAT    Seconds before onset to include in a slice. [default: 0.01].
--note-post                               FLOAT    Seconds after onset to include in a slice. [default: 0.6].
--note-min-interval                       FLOAT    Minimum interval between onsets for tonal slicing (seconds) [default: 0.08].
--note-delta                              FLOAT    Onset detector sensitivity for tonal slicing (higher=less sensitive) [default: 0.15].
--note-max-events                         INTEGER  Limit number of slices per stem (for testing).
--version           -V                             Show version and exit
--help                                             Show this message and exit.   
```

### Default action (separate) - 'separate' command is optional:
audio-sep "song.mp3" --start 3 --end 13 -o out

### Explicit command still works:
audio-sep separate "song.mp3" --start 3 --end 13 -o out

### Keyboard/piano stem (experimental):
audio-sep "song.mp3" --model htdemucs_6s -o out

## To create executable (note that FFmpeg is not included in install):
-----------------------------------------------------------------------------
In PowerShell run:
```
pip install pyinstaller
pyinstaller --onefile --name audio-sep --console src/audio_sep/cli.py
```

## Notes
- Requires FFmpeg available on PATH.
- Demucs models are downloaded on first run.
