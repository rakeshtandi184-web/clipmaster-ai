
import os
import cv2
import numpy as np
import subprocess


def find_best_moments(video_path, clip_seconds=30, max_shorts=3):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise ValueError("Cannot open video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = total_frames / fps if fps > 0 else 0

    if duration <= 0:
        cap.release()
        raise ValueError("Invalid video")

    clip_seconds = min(clip_seconds, duration)
    scores = []
    previous = None
    second = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
        ok, frame = cap.read()

        if not ok:
            break

        small = cv2.resize(frame, (160, 90))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        score = 0
        if previous is not None:
            score = float(
                np.mean(cv2.absdiff(gray, previous))
            )

        scores.append((second, score))
        previous = gray
        second += 1

    cap.release()

    if not scores:
        raise ValueError("No video frames found")

    candidates = []

    for start in range(max(1, int(duration - clip_seconds) + 1)):
        end = start + int(clip_seconds)
        window = [
            score for sec, score in scores
            if start <= sec < end
        ]
        if window:
            candidates.append((float(np.mean(window)), start))

    candidates.sort(reverse=True)

    selected = []
    for score, start in candidates:
        if all(
            abs(start - old) >= clip_seconds
            for old in selected
        ):
            selected.append(start)

        if len(selected) >= max_shorts:
            break

    return sorted(selected)


def create_short(video_path, output_path, start, duration=30):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    command = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    subprocess.run(command, check=True)

    return output_path


def create_shorts(video_path, output_dir="outputs",
                  clip_seconds=30, max_shorts=3):

    moments = find_best_moments(
        video_path, clip_seconds, max_shorts
    )

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for index, start in enumerate(moments, 1):
        output_path = os.path.join(
            output_dir, f"short_{index}.mp4"
        )

        create_short(
            video_path, output_path,
            start, clip_seconds
        )

        results.append(output_path)

    return results
                    
