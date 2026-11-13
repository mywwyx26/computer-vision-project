"""Small standalone example for running the extracted tracker on one video."""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from spatial_tracking import sample_video_background, track_video_interval


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('--start-frame', type=int, default=0)
    parser.add_argument('--end-frame', type=int)
    parser.add_argument('--sample-every-frames', type=int, default=15)
    parser.add_argument('--output', type=Path, default=Path('trajectory.csv'))
    args = parser.parse_args()

    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f'could not open video: {args.video}')
    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
    finally:
        cap.release()

    end_frame = args.end_frame if args.end_frame is not None else frame_count
    background = sample_video_background(args.video)
    trajectory = track_video_interval(
        args.video, background,
        start_frame=args.start_frame, end_frame=end_frame,
        sample_every_frames=args.sample_every_frames,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    trajectory.to_csv(args.output, index=False)
    background_path = args.output.with_suffix('.background.png')
    if not cv2.imwrite(str(background_path), background):
        raise RuntimeError(f'could not save background: {background_path}')
    print(f'Wrote {len(trajectory)} sampled rows to {args.output}')
    print(f'Background: {background_path}; video fps: {fps:g}')


if __name__ == '__main__':
    main()
