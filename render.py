"""Frame rendering (Pillow) and MP4 encoding (ffmpeg)."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import CAPTION_SECONDS, FPS, HEIGHT, SCENE_SECONDS, TRANSITION_SECONDS, WIDTH
from .motion import (BASE_SCALE, CAMERA_MOVES, CAPTION_ENTRANCES, TRANSITIONS,
                     camera_window, caption_pose, clamp, transition_frame)
from .script import Scene

PER_SCENE = round(SCENE_SECONDS * FPS)
TRANS_FRAMES = round(TRANSITION_SECONDS * FPS)
ACCENT = (232, 110, 40, 255)
KICKERS = {"title": "NEW LISTING", "price": "PRICING", "feature": "KEY FEATURE", "cta": "GET IN TOUCH"}
FONT_FILES = [
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


class RenderError(Exception):
    pass


def require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RenderError("ffmpeg was not found on PATH. Install it (see README) and try again.")
    return path


def total_duration(scene_count: int) -> float:
    return scene_count * SCENE_SECONDS - max(scene_count - 1, 0) * TRANSITION_SECONDS


def scene_start_times(scene_count: int) -> list:
    step = (PER_SCENE - TRANS_FRAMES) / FPS
    return [i * step for i in range(scene_count)]


def _font(size: int):
    for name in FONT_FILES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _cover(img: Image.Image, width: int, height: int) -> Image.Image:
    img = img.convert("RGB")
    scale = max(width / img.width, height / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - width) // 2, (img.height - height) // 2
    return img.crop((left, top, left + width, top + height))


def _wrap(text: str, font, max_width: int) -> list:
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _partial(lines: list, reveal: float) -> list:
    if reveal >= 1:
        return lines
    budget = int(sum(len(line) for line in lines) * reveal)
    out = []
    for line in lines:
        if budget <= 0:
            break
        out.append(line[:budget])
        budget -= len(line)
    return out


class _SceneRenderer:
    def __init__(self, scene: Scene, index: int):
        self.scene = scene
        self.camera = CAMERA_MOVES[index % len(CAMERA_MOVES)]
        self.entrance = CAPTION_ENTRANCES[index % len(CAPTION_ENTRANCES)]
        self.transition = TRANSITIONS[index % len(TRANSITIONS)]
        self.base = _cover(Image.open(scene.image), round(WIDTH * BASE_SCALE), round(HEIGHT * BASE_SCALE))
        self.size = 68 if scene.kind == "title" else 46
        self.font = _font(self.size)
        self.kicker_font = _font(28)
        self.kicker = KICKERS[scene.kind]
        self.lines = _wrap(scene.caption, self.font, WIDTH - 180)[:3]
        self.line_h = int(self.size * 1.25)
        band_h = 40 + 34 + self.line_h * len(self.lines) + 30
        self.band_top = HEIGHT - band_h - 48

    def frame(self, t: float) -> Image.Image:
        p = clamp(t / SCENE_SECONDS)
        box = camera_window(self.camera, p, *self.base.size)
        img = self.base.crop(box).resize((WIDTH, HEIGHT), Image.BILINEAR).convert("RGBA")
        layer = self._caption_layer(t)
        if layer is not None:
            img.alpha_composite(layer)
        return img.convert("RGB")

    def _caption_layer(self, t: float):
        p = clamp(t / CAPTION_SECONDS)
        dx, dy, scale, opacity, reveal = caption_pose(self.entrance, p)
        if opacity <= 0.001:
            return None
        card = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        top = self.band_top
        draw.rounded_rectangle((48, top, WIDTH - 48, HEIGHT - 48), radius=20, fill=(12, 12, 16, 185))
        draw.text((88, top + 24), self.kicker, font=self.kicker_font, fill=ACCENT)
        draw.rectangle((88, top + 70, WIDTH - 88, top + 74), fill=ACCENT)
        y = top + 92
        for line in _partial(self.lines, reveal):
            draw.text((88, y), line, font=self.font, fill=(255, 255, 255, 255))
            y += self.line_h
        if scale != 1.0:
            w, h = round(WIDTH * scale), round(HEIGHT * scale)
            card = card.resize((w, h), Image.BILINEAR)
            x, y0 = (WIDTH - w) // 2 + dx, (HEIGHT - h) // 2 + dy
        else:
            x, y0 = dx, dy
        canvas = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        canvas.paste(card, (x, y0), card)
        canvas.putalpha(canvas.getchannel("A").point(lambda a: int(a * opacity)))
        return canvas


def _iter_frames(scenes):
    renderers = [_SceneRenderer(scene, i) for i, scene in enumerate(scenes)]
    last = len(renderers) - 1
    for i, renderer in enumerate(renderers):
        start = 0 if i == 0 else TRANS_FRAMES
        end = PER_SCENE if i == last else PER_SCENE - TRANS_FRAMES
        for f in range(start, end):
            yield renderer.frame(f / FPS)
        if i < last:
            following = renderers[i + 1]
            for k in range(TRANS_FRAMES):
                a = renderer.frame((PER_SCENE - TRANS_FRAMES + k) / FPS)
                b = following.frame(k / FPS)
                yield transition_frame(renderer.transition, a, b, (k + 1) / (TRANS_FRAMES + 1))


def render_video(scenes, out_path) -> Path:
    """Render a silent H.264 MP4 from a list of Scene objects."""
    ffmpeg = require_ffmpeg()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in _iter_frames(scenes):
            proc.stdin.write(frame.tobytes())
    except BrokenPipeError:
        pass
    finally:
        proc.stdin.close()
    err = proc.stderr.read()
    if proc.wait() != 0:
        raise RenderError(f"ffmpeg failed: {err.decode(errors='replace')[-500:]}")
    return out_path
