# Spatial tracking walkthrough and code

Read **Spatial_tracking_overview.docx** for the illustrated walkthrough.

The `code` directory contains only raw-video position tracking and its tests.

- `spatial_tracking.py`: configuration and four original tracking functions.
- `run_tracking.py`: a small new command-line usage example.
- `requirements.txt`: NumPy, pandas, and OpenCV requirements.
- `test_spatial_tracking.py`: focused synthetic tests.

## Run

Use Python 3.12 or newer. From this directory:

```bash
uv run --with-requirements code/requirements.txt \
  python code/run_tracking.py "path/to/video.mp4" \
  --start-frame 0 --end-frame 900 \
  --sample-every-frames 15 --output trajectory.csv
```

Outputs are `trajectory.csv` and `trajectory.background.png`. Frame intervals
are half open: `[start_frame, end_frame)`. The final available frame is also
sampled when it falls off the regular sampling grid. The sample rate is
`fps / sample_every_frames`, approximately 2 Hz for 30 fps and a stride of 15.
Omit `--end-frame` to track to the end of the video. Background sampling always
uses frames across the full recording.

Check both `read_ok` and `detected` before treating a row as an observation.
Missing positions are NaN. Coordinates remain in full-resolution image pixels;
the tracker does not interpolate, smooth, or calibrate them into physical units.

The defaults assume one bright subject, a fixed darker scene, and a subject
large enough to pass the image-area filter. Inspect the background and overlays
before applying the tracker to different recording conditions. A positive
detection flag is not proof of a correct subject identification.

## Test

```bash
uv run --with-requirements code/requirements.txt --with pytest \
  python -m pytest -q code/test_spatial_tracking.py
```

## Source provenance

Extracted 2026-11-13 from `src/firefly_analysis/analysis/spatial.py` in
`firefly-analysis`, branch `analysis/within-fly-duration-definitions`,
HEAD `500708fea154cc0c8d81dc3df5a9f1c65eb4ae2e`.
The working tree contains other edits, but all five included definitions are
identical to HEAD and to branch `codex/spatial-residence-pilot`.

Only the module introduction and import list were adjusted for standalone use.
The configuration definition and original function bodies were copied unchanged.
No other project code or data is required by the extracted module.

| Definition | Original source lines |
| --- | --- |
| `FlyTrackingConfig` | 19-29 |
| `estimate_background_from_frames` | 150-190 |
| `sample_video_background` | 193-233 |
| `locate_fly_foreground` | 236-320 |
| `track_video_interval` | 323-392 |

The first three tests are unchanged original foreground/background tests with
imports redirected to the standalone module. The final test checks the sampled
video loop using a small generated video, including a missing detection and the
extra terminal sample. `run_tracking.py` is a newly written wrapper, not an
extracted original runner.

The walkthrough figures were computed from real recording frames with the
original default configuration. The table of missing observations is explicitly
illustrative. Video data and intermediate image assets are not in this package.
