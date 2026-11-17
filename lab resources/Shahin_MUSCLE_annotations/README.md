# Leg-muscle calcium recordings: human annotations

These are hand labels for 44 calcium-imaging recordings of *Drosophila* leg muscles (R22H05>GCaMP7s, 2022).
Use them to check how well your algorithm detects:

- when the fly is **moving** or quiet, and
- when, during quiet periods, the leg muscles stop pulsing (**suppressed**).

One trained person, Jack Kettering, labeled every recording by eye. He watched each recording as 4-second windows.

## Where the data is

The data is on the lab NAS, share `Lab_Files3`:

```
Lab_Files3/mfk/projects/2025_neural_physiological_correlates_of_sleep/
```

On a Mac with the share mounted, this is `/Volumes/Lab_Files3/mfk/projects/2025_neural_physiological_correlates_of_sleep/`.

In `sessions.csv`, the `stack_path` column gives each recording's image stack relative to that folder. For example:

```
Shahin_MUSCLE/20220711_Fly1_R22H05_UASG7s_7D_m61/20220711_Fly1_R22H05_UASG7s_7D_m61_muscle/_1_MMStack_Default.ome.tif
```

About each stack:

- **Format.** It is a Micro-Manager OME-TIFF of 256 x 344 pixels, uint16, about 3 GB.
- **Frame rate.** One frame every 0.225 s (about 4.44 Hz).
- **Length.** Most recordings have 18000 frames (about 67.6 min). One has 13500 frames and one has 9000.
- **Timestamps.** The per-frame timestamps are in the `metadata_path` file, under `ElapsedTime-ms`.
- **Which file to use.** Use only the file named in `stack_path`. Some folders also contain `Substack (...).tif`, `*_lowintensity_concat.tif` or `.avi` files. These are derived copies with different frame numbering.
- **Behaviour videos.** The `.mp4` behaviour videos in the folders are **not** reliably synchronised with the calcium stacks; their clock offset can be wrong by minutes. The labels come from the calcium movie alone, so you don't need the videos.

## Files

### `annotations.csv`

There is one row per labeled interval, 738 rows in total.

| column | meaning |
|---|---|
| `session_id` | the recording; this is the folder name under `Shahin_MUSCLE/` |
| `label` | `moving`, `active` or `suppressed` (see below) |
| `start_frame` | first frame of the interval: 0-based and **inclusive** |
| `end_frame` | last frame of the interval: 0-based and **inclusive** |
| `n_frames` | `end_frame - start_frame + 1` |
| `start_sec`, `end_sec` | time of those two frames on the calcium clock, for reference |

Frame `i` is the `i`-th image in the OME-TIFF, counting from 0. In Python:

```python
import tifffile
series = tifffile.TiffFile(path).series[0]            # shape (n_frames, 256, 344)
clip = series.asarray(key=slice(start_frame, end_frame + 1))
```

In Fiji or ImageJ, which counts from 1, the same interval is slices `start_frame+1` to `end_frame+1`.

### `sessions.csv`

There is one row per recording. It has these columns:

- the stack and metadata paths;
- `fly_id` and `muscle`;
- `n_frames`, `frame_interval_sec` and `duration_sec`;
- `last_labeled_frame`, `labels_from`, `quick_pass` and `reviewer_note` (see *Caveats*).

## Labels

Within each recording, the intervals follow on from each other with no gaps or overlaps, from frame 0 to `last_labeled_frame`.

| label | meaning | frames | hours |
|---|---|---|---|
| `moving` | the fly walks, turns, grooms or shifts its body | 248,497 | 15.6 |
| `active` | the fly is quiet, and the leg muscles are bright and pulsing | 479,223 | 30.0 |
| `suppressed` | the fly is quiet, and the leg muscles go dark and stop pulsing | 50,714 | 3.2 |

- **Quiet** means `active` and `suppressed` together.
- **Suppression episodes** are the 155 `suppressed` intervals. They occur in 26 of the 44 recordings. The median episode lasts about 61 s, and the shortest lasts 8 s.
- **Proboscis extension and small posture adjustments** were counted as quiet, not as moving.

## Caveats

Read these before you score anything.

1. **Boundary precision.** Jack labeled 4-s windows of 18 frames, and the boundaries snap to those windows. A boundary can therefore be off by up to about 18 frames from where an onset truly is. Score with a tolerance of at least ±18 frames, or use interval overlap (IoU), rather than demanding exact frame matches.
2. **Very short intervals.** Eight intervals are shorter than 10 frames. Most are small slivers of `active` between a suppression episode and the start of movement. They come from how the label rounds were combined, not from a real state lasting under 2 s, so it is fine to ignore them.
3. **Unlabeled final frames.** In 30 recordings, the last 2–5 frames are unlabeled, so `last_labeled_frame` is less than `n_frames - 1`. Exclude those frames from scoring.
4. **`quick_pass = True` (21 recordings).** Jack saved these labels faster than the windows could be played back at normal speed, and 16 of the 21 he left unchanged from an earlier review round. Their moving/quiet labels had already been reviewed one bout at a time, and their suppression labels had been reviewed one episode at a time. Even so, treat "no suppression here" in these recordings as less carefully checked than in the others.
5. **`labels_from`.** The labels for 20220720_Fly2_R22H05_UASG7s_5-6D_m83 come from Jack's two earlier rounds: quiet bouts first, then suppression episodes. His file from the full-labeling round could not be read. The other 43 recordings come from the full-labeling round.
6. **Recordings from the same fly.** Several recordings come from the same fly: 44 recordings from 31 flies, marked by `fly_id`. If you train anything, split by `fly_id` and not by recording. Otherwise the test set leaks into the training set.
7. **One annotator.** All labels come from one person. On a blind re-check of 5 recordings, Jack's suppression labels agreed with his own earlier labels at an IoU of 0.76–0.90 in 4 recordings and 0.57 in the fifth. Expect a good algorithm to match him at about that level, not perfectly.

## Suggested scoring

- **Moving vs quiet.** Compare per frame: precision, recall and F1, ignoring a ±18-frame band around each labeled boundary.
- **Suppression.**
  - Episode-level: count a detected episode as a match when it overlaps a labeled one with IoU ≥ 0.3, then report precision, recall and F1.
  - Time-level: report the IoU of all `suppressed` frames per recording.
  - Look only within quiet frames, because suppression is defined only when the fly is quiet.

For reference, our own detector scored episode F1 ≈ 0.70 and time IoU ≈ 0.57. That score was measured against Jack's earlier suppression round, not this final export.

---

This export was generated by `scripts/export_annotations.py` in the muscleCalciumAnalysis repository, from the approved `labels_reviewed.csv` files.
