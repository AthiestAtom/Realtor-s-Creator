"""Generates eight synthetic property illustrations for the sample.

These are drawn with Pillow, not photographs, so there is no licence or
personal-data question. Existing files are never overwritten unless --force is given.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1600, 1000
OUT = Path(__file__).resolve().parents[1] / "sample" / "images"


def _font(size):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _gradient(d, top, bottom, height=H):
    for y in range(height):
        t = y / height
        d.line([(0, y), (W, y)], fill=tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))


def _window(d, x, y, w, h, lit=False):
    d.rectangle((x, y, x + w, y + h), fill=(255, 218, 150) if lit else (160, 196, 225), outline=(60, 60, 70), width=6)


def exterior(d):
    _gradient(d, (120, 170, 230), (220, 235, 250))
    d.rectangle((0, 820, W, H), fill=(110, 110, 115))
    d.rectangle((300, 160, 1300, 820), fill=(225, 220, 210))
    d.rectangle((300, 140, 1300, 160), fill=(90, 80, 70))
    for r in range(4):
        for c in range(5):
            _window(d, 360 + c * 180, 220 + r * 150, 120, 90)


def park_view(d):
    _gradient(d, (140, 200, 240), (230, 245, 255), 600)
    d.rectangle((0, 600, W, H), fill=(90, 170, 80))
    d.polygon([(700, H), (900, 600), (1000, 600), (1200, H)], fill=(220, 215, 200))
    for x, y, r in [(150, 520, 140), (420, 480, 120), (1250, 500, 150), (1500, 560, 110)]:
        d.rectangle((x - 12, y, x + 12, y + 200), fill=(100, 70, 40))
        d.ellipse((x - r, y - r, x + r, y + r * 0.6), fill=(40, 130, 60))


def living_room(d):
    _gradient(d, (235, 225, 210), (200, 185, 165), 760)
    d.rectangle((0, 760, W, H), fill=(150, 110, 80))
    _window(d, 1000, 140, 380, 380)
    d.rounded_rectangle((250, 440, 1050, 760), radius=40, fill=(90, 110, 140))
    d.rounded_rectangle((250, 360, 1050, 520), radius=50, fill=(80, 100, 130))
    d.ellipse((560, 820, 1040, 900), fill=(190, 150, 120))


def bedroom(d):
    _gradient(d, (225, 235, 240), (200, 215, 225), 760)
    d.rectangle((0, 760, W, H), fill=(170, 130, 95))
    _window(d, 150, 130, 360, 300)
    d.rounded_rectangle((600, 450, 1400, 800), radius=30, fill=(120, 90, 70))
    d.rounded_rectangle((620, 400, 1380, 520), radius=40, fill=(245, 245, 250))
    d.rounded_rectangle((640, 500, 1360, 560), radius=20, fill=(180, 200, 230))


def kitchen(d):
    _gradient(d, (240, 240, 235), (215, 215, 210), 560)
    for i in range(6):
        d.rectangle((120 + i * 240, 160, 340 + i * 240, 360), fill=(250, 250, 245), outline=(150, 150, 150), width=4)
    d.rectangle((0, 540, W, 580), fill=(170, 170, 175))
    d.rectangle((0, 580, W, H), fill=(200, 160, 120))
    for i in range(4):
        d.ellipse((220 + i * 330, 430, 340 + i * 330, 470), fill=(60, 60, 65))


def bathroom(d):
    _gradient(d, (210, 235, 240), (180, 215, 225), 1000)
    for y in range(0, H, 110):
        for x in range(0, W, 160):
            d.rectangle((x, y, x + 156, y + 106), outline=(150, 190, 200), width=2)
    d.rounded_rectangle((300, 560, 1300, 800), radius=60, fill=(250, 250, 250), outline=(180, 180, 180), width=5)
    d.rectangle((560, 150, 1040, 420), fill=(200, 230, 240), outline=(120, 120, 120), width=8)


def parking(d):
    _gradient(d, (150, 170, 190), (120, 120, 125), 560)
    d.rectangle((0, 560, W, H), fill=(95, 95, 100))
    for x in (120, 1380):
        d.rectangle((x, 200, x + 80, 700), fill=(180, 180, 185))
    for cx, color in ((420, (200, 60, 60)), (960, (60, 110, 200))):
        d.rounded_rectangle((cx - 230, 540, cx + 230, 700), radius=50, fill=color)
        d.rounded_rectangle((cx - 150, 450, cx + 150, 560), radius=40, fill=color)
        d.ellipse((cx - 170, 660, cx - 90, 740), fill=(30, 30, 30))
        d.ellipse((cx + 90, 660, cx + 170, 740), fill=(30, 30, 30))


def night_building(d):
    _gradient(d, (20, 30, 60), (70, 80, 110))
    d.rectangle((0, 820, W, H), fill=(40, 40, 50))
    d.rectangle((400, 160, 1200, 820), fill=(55, 60, 80))
    for r in range(5):
        for c in range(4):
            _window(d, 460 + c * 180, 220 + r * 120, 120, 80, lit=(r + c) % 3 != 0)


SCENES = [
    ("img01", exterior), ("img02", park_view), ("img03", living_room), ("img04", bedroom),
    ("img05", kitchen), ("img06", bathroom), ("img07", parking), ("img08", night_building),
]


def main(argv):
    force = "--force" in argv
    OUT.mkdir(parents=True, exist_ok=True)
    for name, painter in SCENES:
        target = OUT / f"{name}.jpg"
        if target.exists() and not force:
            print(f"Skipped existing {target} (use --force to overwrite)")
            continue
        img = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(img)
        painter(d)
        label = "SYNTHETIC SAMPLE"
        f = _font(36)
        box = d.textbbox((0, 0), label, font=f)
        tw, th = box[2] - box[0], box[3] - box[1]
        d.rectangle((W - tw - 60, H - th - 60, W - 20, H - 20), fill=(0, 0, 0))
        d.text((W - tw - 40, H - th - 46), label, font=f, fill=(255, 255, 255))
        img.save(target, quality=90)
        print(f"Wrote {target}")


if __name__ == "__main__":
    main(sys.argv[1:])
