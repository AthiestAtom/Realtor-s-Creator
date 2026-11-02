"""Animation library for slide-style video.

Three families, each with several named styles:
- camera moves (how the photo moves during a scene)
- caption entrances (how the text card arrives)
- transitions (how one scene hands over to the next)

Each scene gets a camera move and caption entrance by index, and the transition
after it. Neighbouring scenes never share a transition or an entrance.
"""
from __future__ import annotations

from PIL import Image

from .config import HEIGHT, WIDTH

BASE_SCALE = 1.12  # photos are prepared 12% larger than the frame so the camera has room

CAMERA_MOVES = ["zoom_in", "pan_left", "zoom_out", "pan_right"]
CAPTION_ENTRANCES = ["rise_fade", "slide_left", "drop_in", "scale_pop", "typewriter"]
TRANSITIONS = ["push_left", "push_up", "wipe_right", "zoom_dissolve", "fade"]


def clamp(x: float) -> float:
    return min(max(x, 0.0), 1.0)


def ease_in_out(x: float) -> float:
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x: float) -> float:
    x = clamp(x)
    return 1 - (1 - x) ** 3


def camera_window(name: str, p: float, base_w: int, base_h: int):
    """Crop box (left, top, right, bottom) inside the prepared base photo."""
    p = clamp(p)
    if name == "zoom_in":
        zoom, cx = 1.12 - 0.12 * p, 0.5
    elif name == "zoom_out":
        zoom, cx = 1.0 + 0.12 * p, 0.5
    elif name == "pan_left":
        zoom, cx = 1.06, 1.0 - p
    elif name == "pan_right":
        zoom, cx = 1.06, p
    else:
        raise ValueError(f"Unknown camera move: {name}")
    cw, ch = WIDTH * zoom, HEIGHT * zoom
    left = (base_w - cw) * cx
    top = (base_h - ch) * 0.5
    return (round(left), round(top), round(left + cw), round(top + ch))


def caption_pose(name: str, p: float):
    """Return (dx, dy, scale, opacity, text_reveal) for a caption at entrance progress p."""
    e = ease_out(p)
    if name == "rise_fade":
        return 0, int((1 - e) * 90), 1.0, e, 1.0
    if name == "slide_left":
        return int(-(1 - e) * 240), 0, 1.0, e, 1.0
    if name == "drop_in":
        return 0, -int((1 - e) * 140), 1.0, e, 1.0
    if name == "scale_pop":
        return 0, 0, 0.82 + 0.18 * e, clamp(p * 2.5), 1.0
    if name == "typewriter":
        return 0, 0, 1.0, clamp(p * 4), ease_in_out(p)
    raise ValueError(f"Unknown caption entrance: {name}")


def transition_frame(name: str, a: Image.Image, b: Image.Image, s: float) -> Image.Image:
    """Blend outgoing frame a into incoming frame b. s runs from 0 to 1."""
    s = ease_in_out(s)
    if name == "push_left":
        x = round(WIDTH * s)
        out = Image.new("RGB", (WIDTH, HEIGHT))
        out.paste(a, (-x, 0))
        out.paste(b, (WIDTH - x, 0))
        return out
    if name == "push_up":
        y = round(HEIGHT * s)
        out = Image.new("RGB", (WIDTH, HEIGHT))
        out.paste(a, (0, -y))
        out.paste(b, (0, HEIGHT - y))
        return out
    if name == "wipe_right":
        x = round(WIDTH * s)
        out = a.copy()
        if x > 0:
            out.paste(b.crop((0, 0, x, HEIGHT)), (0, 0))
        return out
    if name == "zoom_dissolve":
        z = 1 + 0.15 * s
        zw, zh = round(WIDTH * z), round(HEIGHT * z)
        big = a.resize((zw, zh), Image.BILINEAR)
        left, top = (zw - WIDTH) // 2, (zh - HEIGHT) // 2
        return Image.blend(big.crop((left, top, left + WIDTH, top + HEIGHT)), b, s)
    if name == "fade":
        return Image.blend(a, b, s)
    raise ValueError(f"Unknown transition: {name}")
