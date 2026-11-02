"""Creates placeholder library images and assets/library/library.json.

These are plain illustrations, not photographs. Replace each file with an owned
or AI-generated photo, and update its licence entry in library.json.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "assets" / "library"
ROOT.mkdir(parents=True, exist_ok=True)

ENTRIES = [
    ("ext-01", "exterior", ["exterior", "general", "park view"], "exterior"),
    ("ext-02", "lobby", ["lobby", "general"], "lobby"),
    ("liv-01", "living room", ["living", "general"], "living"),
    ("bed-01", "bedroom", ["bedroom", "general"], "bedroom"),
    ("bath-01", "bathroom", ["bathroom", "general"], "bathroom"),
    ("kit-01", "kitchen", ["kitchen", "general"], "kitchen"),
    ("park-01", "garden view", ["park view", "garden", "general"], "garden"),
    ("parking-01", "parking", ["parking", "general"], "parking"),
    ("bal-01", "balcony", ["balcony", "general"], "balcony"),
    ("gym-01", "gym", ["gym", "general"], "gym"),
]


def _font(size):
    for name in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _sky(d, top=(150, 190, 230), bottom=(220, 235, 245), floor=None):
    for y in range(540):
        t = y / 540
        d.line([(0, y), (960, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    if floor:
        d.rectangle((0, 400, 960, 540), fill=floor)


def _room(d, wall=(235, 228, 215), floor=(200, 170, 130)):
    d.rectangle((0, 0, 960, 540), fill=wall)
    d.polygon([(0, 400), (960, 400), (960, 540), (0, 540)], fill=floor)


def _tree(d, x, y, r=70):
    d.rectangle((x - 8, y, x + 8, y + 120), fill=(110, 80, 50))
    d.ellipse((x - r, y - 2 * r, x + r, y + 10), fill=(60, 130, 70))


def draw_scene(kind, d):
    if kind == "exterior":
        _sky(d, floor=(90, 130, 90))
        d.rectangle((250, 120, 710, 420), fill=(235, 235, 240), outline=(90, 90, 90), width=4)
        for r in range(4):
            for c in range(5):
                d.rectangle((285 + c * 80, 160 + r * 62, 335 + c * 80, 200 + r * 62), fill=(120, 170, 210))
    elif kind == "lobby":
        _room(d, wall=(225, 225, 230), floor=(170, 170, 175))
        d.rectangle((380, 120, 580, 400), fill=(90, 90, 100))
        d.rectangle((400, 140, 560, 380), fill=(60, 60, 70))
        d.ellipse((450, 40, 510, 100), fill=(255, 230, 160))
    elif kind == "living":
        _room(d)
        d.rectangle((180, 300, 780, 420), fill=(90, 120, 150))
        d.rectangle((160, 260, 800, 320), fill=(80, 110, 140))
        d.rectangle((120, 150, 300, 260), fill=(160, 190, 210))
        d.rectangle((160, 420, 800, 430), fill=(70, 60, 50))
    elif kind == "bedroom":
        _room(d, wall=(230, 220, 235), floor=(190, 160, 120))
        d.rectangle((200, 300, 760, 400), fill=(140, 100, 70))
        d.rectangle((220, 250, 420, 320), fill=(250, 250, 250))
        d.rectangle((200, 230, 760, 300), fill=(200, 210, 230))
        d.rectangle((760, 150, 900, 380), fill=(120, 90, 60))
    elif kind == "kitchen":
        _room(d, wall=(245, 240, 230), floor=(150, 120, 90))
        d.rectangle((80, 330, 880, 420), fill=(200, 200, 200))
        d.rectangle((80, 300, 880, 330), fill=(70, 70, 70))
        for x in (120, 300, 480, 660):
            d.rectangle((x, 130, x + 120, 260), fill=(150, 190, 220))
    elif kind == "bathroom":
        _room(d, wall=(220, 240, 240), floor=(180, 200, 200))
        d.ellipse((150, 330, 430, 430), fill=(250, 250, 250), outline=(160, 160, 160), width=4)
        d.rectangle((600, 120, 640, 330), fill=(160, 160, 160))
        d.ellipse((580, 100, 680, 140), fill=(200, 200, 200))
    elif kind == "parking":
        _sky(d, floor=(110, 110, 115))
        d.rectangle((0, 380, 960, 540), fill=(110, 110, 115))
        for x in (120, 520):
            d.rounded_rectangle((x, 300, x + 320, 400), radius=30, fill=(200, 60, 60))
            d.rounded_rectangle((x + 60, 250, x + 240, 310), radius=25, fill=(180, 50, 50))
            d.ellipse((x + 40, 380, x + 100, 440), fill=(30, 30, 30))
            d.ellipse((x + 230, 380, x + 290, 440), fill=(30, 30, 30))
    elif kind == "garden":
        _sky(d, floor=(80, 150, 80))
        d.polygon([(0, 420), (960, 360), (960, 540), (0, 540)], fill=(90, 160, 90))
        _tree(d, 200, 360)
        _tree(d, 500, 330, r=90)
        _tree(d, 800, 370)
        d.ellipse((380, 430, 620, 490), fill=(120, 190, 240))
    elif kind == "balcony":
        _sky(d, top=(120, 170, 220), floor=None)
        d.rectangle((0, 330, 960, 540), fill=(200, 200, 200))
        for x in range(0, 960, 60):
            d.line([(x, 260), (x, 340)], fill=(60, 60, 60), width=6)
        d.line([(0, 260), (960, 260)], fill=(60, 60, 60), width=8)
        d.ellipse((120, 90, 240, 170), fill=(255, 240, 180))
        _tree(d, 760, 300, r=60)
    elif kind == "gym":
        _room(d, wall=(210, 215, 220), floor=(120, 120, 125))
        d.rectangle((120, 300, 340, 340), fill=(60, 60, 60))
        d.rectangle((140, 250, 150, 300), fill=(40, 40, 40))
        d.rectangle((400, 330, 720, 360), fill=(50, 50, 50))
        d.ellipse((410, 300, 470, 360), fill=(30, 30, 30))
        d.ellipse((650, 300, 710, 360), fill=(30, 30, 30))
    else:
        _sky(d, floor=(120, 150, 120))


def draw_placeholder(path: Path, label: str, kind: str):
    img = Image.new("RGB", (960, 540))
    d = ImageDraw.Draw(img)
    draw_scene(kind, d)
    d.rectangle((0, 490, 960, 540), fill=(30, 30, 30))
    d.text((20, 20), label.upper(), font=_font(40), fill=(20, 20, 20))
    d.text((20, 500), "PLACEHOLDER illustration - replace with an owned or AI-generated photo", font=_font(22), fill=(255, 255, 255))
    img.save(path, quality=90)


items = []
for item_id, label, tags, kind in ENTRIES:
    filename = f"{item_id}.jpg"
    draw_placeholder(ROOT / filename, label, kind)
    items.append({
        "id": item_id,
        "file": filename,
        "tags": tags,
        "source": "placeholder",
        "licence": "Generated by project script. Not a real property photo.",
        "status": "placeholder",
    })

(ROOT / "library.json").write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
print(f"Wrote {len(items)} placeholder images and library.json to {ROOT}")
