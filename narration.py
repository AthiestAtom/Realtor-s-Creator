"""Optional voice-over: each narration line is spoken at its scene's start time."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .render import RenderError, require_ffmpeg, scene_start_times


def add_narration(video_path, scenes, out_path) -> Path:
    try:
        from gtts import gTTS
    except ImportError as exc:
        raise RenderError("Voice-over needs gTTS (pip install gTTS), or run without --voice.") from exc

    ffmpeg = require_ffmpeg()
    starts = scene_start_times(len(scenes))
    with tempfile.TemporaryDirectory() as tmp:
        inputs, filters, labels = [], [], []
        for i, (scene, start) in enumerate(zip(scenes, starts)):
            clip = Path(tmp) / f"line{i:02d}.mp3"
            try:
                gTTS(text=scene.narration, lang="en").save(str(clip))
            except Exception as exc:
                raise RenderError(f"Voice-over generation failed (gTTS needs internet): {exc}") from exc
            idx = i + 1
            ms = int(round(start * 1000))
            inputs += ["-i", str(clip)]
            filters.append(f"[{idx}:a]adelay={ms}|{ms}[a{idx}]")
            labels.append(f"[a{idx}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0[aout]")
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(video_path), *inputs,
               "-filter_complex", ";".join(filters),
               "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-shortest",
               str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RenderError(f"ffmpeg audio step failed: {result.stderr[-500:]}")
    return Path(out_path)
