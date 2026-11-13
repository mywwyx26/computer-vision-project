"""Raw-video subject localization and sampled position tracking.

Extracted tracking definitions from firefly-analysis analysis/spatial.py.
Function and configuration bodies are unchanged. See README.md for provenance.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

@dataclass(frozen=True)
class FlyTrackingConfig:
    """Settings for foreground-based fly localization."""

    background_quantile: float = 0.05
    foreground_threshold: int = 12
    open_kernel_px: int = 5
    close_kernel_px: int = 11
    border_margin_px: tuple[int, int, int, int] = (15, 30, 30, 30)
    min_component_area_fraction: float = 0.005
    max_component_area_fraction: float = 0.30


def estimate_background_from_frames(
    frames: Sequence[np.ndarray],
    *,
    quantile: float = 0.05,
) -> np.ndarray:
    """Return a low-quantile grayscale background from sampled video frames.

    The fly is brighter than the dark arena floor in these recordings.  A low
    temporal quantile therefore estimates the fly-free intensity at each pixel
    while preserving static chamber structure for subsequent subtraction.
    """

    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be in [0, 1]")
    if not frames:
        raise ValueError("frames must contain at least one image")

    grayscale: list[np.ndarray] = []
    expected_shape: tuple[int, int] | None = None
    for frame in frames:
        arr = np.asarray(frame)
        if arr.ndim == 3:
            if arr.shape[2] < 3:
                raise ValueError("color frames must have at least three channels")
            # OpenCV video frames are BGR.  Integer weights avoid importing cv2
            # in this pure array helper and are sufficiently accurate here.
            arr = np.rint(
                0.114 * arr[..., 0]
                + 0.587 * arr[..., 1]
                + 0.299 * arr[..., 2]
            )
        if arr.ndim != 2:
            raise ValueError("each frame must be a grayscale or BGR image")
        if expected_shape is None:
            expected_shape = arr.shape
        elif arr.shape != expected_shape:
            raise ValueError("all sampled frames must have the same shape")
        grayscale.append(arr.astype(np.float32, copy=False))

    background = np.quantile(np.stack(grayscale), quantile, axis=0)
    return np.clip(np.rint(background), 0, 255).astype(np.uint8)


def sample_video_background(
    video_path: str | Path,
    *,
    sample_count: int = 48,
    quantile: float = 0.05,
) -> np.ndarray:
    """Estimate a recording background from uniformly spaced raw-video frames."""

    import cv2

    if sample_count < 2:
        raise ValueError("sample_count must be at least 2")
    source = Path(video_path)
    if not source.exists():
        raise FileNotFoundError(source)

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f"could not open video: {source}")
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if frame_count < 1:
        cap.release()
        raise RuntimeError(f"video has no readable frames: {source}")

    frames: list[np.ndarray] = []
    try:
        for frame_number in np.linspace(
            0,
            frame_count - 1,
            min(sample_count, frame_count),
            dtype=int,
        ):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_number))
            ok, frame = cap.read()
            if ok:
                frames.append(frame)
    finally:
        cap.release()
    if len(frames) < 2:
        raise RuntimeError(f"could not sample enough frames from {source}")
    return estimate_background_from_frames(frames, quantile=quantile)


def locate_fly_foreground(
    frame: np.ndarray,
    background: np.ndarray,
    *,
    config: FlyTrackingConfig | None = None,
) -> dict[str, float | int | bool]:
    """Locate the largest fly-sized positive foreground component in one frame."""

    import cv2

    settings = config or FlyTrackingConfig()
    image = np.asarray(frame)
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif image.ndim == 2:
        gray = image
    else:
        raise ValueError("frame must be a grayscale or BGR image")
    bg = np.asarray(background)
    if gray.shape != bg.shape:
        raise ValueError("frame and background must have the same image shape")
    if settings.foreground_threshold < 0:
        raise ValueError("foreground_threshold must be non-negative")
    if settings.open_kernel_px < 1 or settings.close_kernel_px < 1:
        raise ValueError("morphology kernel sizes must be positive")

    difference = cv2.subtract(gray.astype(np.uint8), bg.astype(np.uint8))
    mask = (difference >= settings.foreground_threshold).astype(np.uint8) * 255
    top, bottom, left, right = settings.border_margin_px
    if min(top, bottom, left, right) < 0:
        raise ValueError("border margins must be non-negative")
    if top:
        mask[:top] = 0
    if bottom:
        mask[-bottom:] = 0
    if left:
        mask[:, :left] = 0
    if right:
        mask[:, -right:] = 0

    open_kernel = np.ones(
        (settings.open_kernel_px, settings.open_kernel_px), dtype=np.uint8
    )
    close_kernel = np.ones(
        (settings.close_kernel_px, settings.close_kernel_px), dtype=np.uint8
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_kernel)
    n_labels, _, stats, centroids = cv2.connectedComponentsWithStats(mask)

    image_area = float(gray.shape[0] * gray.shape[1])
    min_area = settings.min_component_area_fraction * image_area
    max_area = settings.max_component_area_fraction * image_area
    candidates = [
        index
        for index in range(1, n_labels)
        if min_area <= float(stats[index, cv2.CC_STAT_AREA]) <= max_area
    ]
    if not candidates:
        return {
            "detected": False,
            "x_px": np.nan,
            "y_px": np.nan,
            "area_px": np.nan,
            "bbox_x_px": np.nan,
            "bbox_y_px": np.nan,
            "bbox_width_px": np.nan,
            "bbox_height_px": np.nan,
            "body_length_px": np.nan,
        }

    component = max(candidates, key=lambda index: stats[index, cv2.CC_STAT_AREA])
    x, y, width, height, area = stats[component]
    centroid_x, centroid_y = centroids[component]
    return {
        "detected": True,
        "x_px": float(centroid_x),
        "y_px": float(centroid_y),
        "area_px": int(area),
        "bbox_x_px": int(x),
        "bbox_y_px": int(y),
        "bbox_width_px": int(width),
        "bbox_height_px": int(height),
        "body_length_px": float(max(width, height)),
    }


def track_video_interval(
    video_path: str | Path,
    background: np.ndarray,
    *,
    start_frame: int,
    end_frame: int,
    sample_every_frames: int = 15,
    config: FlyTrackingConfig | None = None,
) -> pd.DataFrame:
    """Track fly position on sampled frames in a half-open video interval."""

    import cv2

    if start_frame < 0 or end_frame <= start_frame:
        raise ValueError("expected 0 <= start_frame < end_frame")
    if sample_every_frames < 1:
        raise ValueError("sample_every_frames must be positive")

    source = Path(video_path)
    if not source.exists():
        raise FileNotFoundError(source)
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise RuntimeError(f"could not open video: {source}")
    video_end = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    stop = min(end_frame, video_end)
    sample_frames = list(range(start_frame, stop, sample_every_frames))
    if sample_frames and sample_frames[-1] != stop - 1:
        sample_frames.append(stop - 1)

    rows: list[dict[str, float | int | bool]] = []
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_frame))
        next_decoded_frame = int(start_frame)
        for frame_number in sample_frames:
            while next_decoded_frame < frame_number:
                if not cap.grab():
                    break
                next_decoded_frame += 1
            ok, frame = cap.read()
            next_decoded_frame += 1
            if not ok:
                row = locate_fly_foreground(
                    np.zeros_like(background),
                    background,
                    config=config,
                )
                row["read_ok"] = False
            else:
                row = locate_fly_foreground(frame, background, config=config)
                row["read_ok"] = True
            row["frame"] = int(frame_number)
            rows.append(row)
    finally:
        cap.release()

    columns = [
        "frame",
        "read_ok",
        "detected",
        "x_px",
        "y_px",
        "area_px",
        "bbox_x_px",
        "bbox_y_px",
        "bbox_width_px",
        "bbox_height_px",
        "body_length_px",
    ]
    return pd.DataFrame(rows, columns=columns)
