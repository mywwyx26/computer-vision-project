from __future__ import annotations

import cv2
import numpy as np
import pytest

from spatial_tracking import (
    FlyTrackingConfig, estimate_background_from_frames,
    locate_fly_foreground, track_video_interval,
)


def test_estimate_background_uses_low_temporal_quantile() -> None:
    frames = []
    for center_x in (15, 30, 45, 60):
        frame = np.full((60, 80), 20, dtype=np.uint8)
        frame[20:35, center_x : center_x + 10] = 150
        frames.append(frame)

    background = estimate_background_from_frames(frames, quantile=0.0)

    assert background.shape == (60, 80)
    assert np.all(background == 20)


def test_locate_fly_foreground_finds_largest_fly_sized_blob() -> None:
    background = np.full((120, 160), 20, dtype=np.uint8)
    frame = background.copy()
    frame[40:80, 60:120] = 120
    frame[10:13, 10:13] = 200

    result = locate_fly_foreground(
        frame,
        background,
        config=FlyTrackingConfig(
            foreground_threshold=10,
            open_kernel_px=1,
            close_kernel_px=1,
            border_margin_px=(0, 0, 0, 0),
            min_component_area_fraction=0.01,
            max_component_area_fraction=0.5,
        ),
    )

    assert result["detected"] is True
    assert result["x_px"] == pytest.approx(89.5)
    assert result["y_px"] == pytest.approx(59.5)
    assert result["area_px"] == 2400
    assert result["body_length_px"] == 60


def test_locate_fly_foreground_reports_missing_detection() -> None:
    background = np.zeros((40, 50), dtype=np.uint8)
    result = locate_fly_foreground(
        background,
        background,
        config=FlyTrackingConfig(
            open_kernel_px=1,
            close_kernel_px=1,
            border_margin_px=(0, 0, 0, 0),
        ),
    )

    assert result["detected"] is False
    assert np.isnan(result["x_px"])


def test_video_interval_preserves_terminal_sample_and_missing_detection(tmp_path):
    video = tmp_path / 'sample.avi'
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*'MJPG'), 30., (160, 120))
    assert writer.isOpened()
    try:
        for number in range(45):
            frame = np.full((120, 160, 3), 20, dtype=np.uint8)
            if number != 15:
                frame[40:80, 50:110] = 140
            writer.write(frame)
    finally:
        writer.release()

    result = track_video_interval(
        video, np.full((120, 160), 20, dtype=np.uint8),
        start_frame=0, end_frame=45, sample_every_frames=15,
    )
    assert result.frame.tolist() == [0, 15, 30, 44]
    assert result.read_ok.all()
    assert result.detected.tolist() == [True, False, True, True]
    assert np.isnan(result.loc[result.frame.eq(15), 'x_px']).all()
    assert np.isfinite(result.loc[result.detected, ['x_px', 'y_px']]).all().all()
