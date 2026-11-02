"""Command-line entry point.

  python -m proptvid.cli --input sample/property.json
  python -m proptvid.cli --input sample/property.json --voice
  python -m proptvid.cli --input sample/property.json --check
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .models import ValidationError, load_property
from .narration import add_narration
from .render import RenderError, render_video, total_duration
from .script import fact_check, plan_scenes


def _ask(prompt: str, required: bool = True) -> str:
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("  This field is required.")


def interactive_input(path: Path) -> Path:
    """Ask for property details in the terminal and write them to a JSON file."""
    print("Enter property details (press Enter after each line).")
    data = {
        "name": _ask("Property name: "),
        "location": _ask("Location: "),
        "price": _ask("Price exactly as it should appear (e.g. ₹85,00,000): "),
        "property_type": _ask("Property type (e.g. 2-BHK apartment): "),
        "cta": _ask("Closing enquiry line: "),
    }
    features = _ask("Key features, separated by commas (blank to skip): ", required=False)
    if features:
        data["key_features"] = [f.strip() for f in features.split(",") if f.strip()]
    photos = _ask("Photo paths, separated by commas (blank to use the image library): ", required=False)
    if photos:
        data["images"] = [p.strip() for p in photos.split(",") if p.strip()]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved your details to {path}")
    return path


def _open_preview(path: Path) -> None:
    opener = shutil.which("xdg-open") or shutil.which("open")
    if opener:
        subprocess.Popen([opener, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        print(f"No viewer found. Open this file in any video player: {path}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Turn property details and photos into a short promo MP4.")
    parser.add_argument("--input", help="Path to the property JSON file")
    parser.add_argument("--interactive", action="store_true", help="Enter details in the terminal instead")
    parser.add_argument("--preview", action="store_true", help="Open the finished MP4 in the default player")
    parser.add_argument("--output", default="out/property_video.mp4", help="Output MP4 path")
    parser.add_argument("--voice", action="store_true", help="Add gTTS voice-over (needs internet)")
    parser.add_argument("--check", action="store_true", help="Validate and print the plan only")
    args = parser.parse_args(argv)
    if args.interactive:
        args.input = str(interactive_input(Path("property_input.json")))
    if not args.input:
        parser.error("either --input or --interactive is required")

    try:
        prop = load_property(args.input)
    except ValidationError as exc:
        print("Input problems found. No video was made:", file=sys.stderr)
        for problem in exc.problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    for field_name in prop.missing:
        print(f"Note: '{field_name}' was not supplied, so its scenes were omitted.")

    scenes, notes = plan_scenes(prop)
    for note in notes:
        print(f"Note: {note}")

    if prop.library is not None:
        used = {s.image for s in scenes}
        ids = [item.id for item in prop.library if item.path in used]
        print(f"Photos from image library: {', '.join(ids)}")
        if any(item.source == "placeholder" and item.path in used for item in prop.library):
            print("Note: some photos are placeholders. Replace them in assets/library before publishing.")

    issues = fact_check(prop, scenes)
    if issues:
        print("Script failed the fact check. No video was made:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 2

    duration = total_duration(len(scenes))
    print(f"Plan ({len(scenes)} scenes, about {duration:.0f}s):")
    for n, scene in enumerate(scenes, start=1):
        print(f"  {n}. [{scene.kind}] photo={scene.image.name}")
        print(f"       caption:   {scene.caption}")
        print(f"       narration: {scene.narration}")

    if args.check:
        return 0

    out = Path(args.output)
    silent = out.with_name(out.stem + ".silent.mp4")
    try:
        render_video(scenes, silent)
        if args.voice:
            add_narration(silent, scenes, out)
            silent.unlink(missing_ok=True)
        else:
            silent.replace(out)
    except RenderError as exc:
        print(f"Video could not be made: {exc}", file=sys.stderr)
        return 3

    out.with_suffix(".script.json").write_text(json.dumps({
        "property": {k: str(v) if k == "image_map" else v
                     for k, v in vars(prop).items() if k != "images"},
        "scenes": [{"kind": s.kind, "caption": s.caption, "narration": s.narration,
                    "photo": s.image.name} for s in scenes],
        "notes": notes,
    }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Saved {out} ({duration:.1f}s)")
    if args.preview:
        _open_preview(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
