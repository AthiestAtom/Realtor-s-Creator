"""Realty Assistant image library: tagged, provenance-checked property photos.

Every entry must state where its image came from and under what licence.
Entries without that information are rejected, so unlicensed images cannot
enter a video by accident.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LIBRARY = Path(__file__).resolve().parents[1] / "assets" / "library" / "library.json"
ALLOWED_SOURCES = {"owned", "ai-generated", "placeholder"}
REQUIRED_KEYS = ("id", "file", "source", "licence", "tags")

# Words in a key feature that select a library tag.
FEATURE_KEYWORDS = {
    "park view": "park view", "garden": "garden", "bedroom": "bedroom",
    "bathroom": "bathroom", "parking": "parking", "kitchen": "kitchen",
    "balcony": "balcony", "gym": "gym", "lift": "lobby", "lobby": "lobby",
    "pool": "pool", "living": "living",
}
# Fixed scenes prefer these tags.
FIXED_TAGS = {"title": ["exterior"], "price": ["living", "exterior"], "cta": ["lobby", "exterior"]}


class LibraryError(Exception):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


@dataclass(frozen=True)
class LibraryItem:
    id: str
    path: Path
    source: str
    licence: str
    tags: tuple
    status: str


def load_library(path=DEFAULT_LIBRARY) -> list:
    path = Path(path)
    if not path.is_file():
        raise LibraryError([f"Image library index not found: {path}"])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LibraryError([f"Image library index is not valid JSON: {exc.msg} (line {exc.lineno})."])
    entries = data.get("items") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise LibraryError(["Image library index must contain an 'items' list."])

    problems, items, seen = [], [], set()
    for n, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            problems.append(f"Library entry {n} is not an object.")
            continue
        label = entry.get("id", f"entry {n}")
        missing = [k for k in REQUIRED_KEYS if not entry.get(k)]
        if missing:
            problems.append(f"Library item '{label}' is missing: {', '.join(missing)}.")
            continue
        if entry["id"] in seen:
            problems.append(f"Library item id '{label}' is used more than once.")
        seen.add(entry["id"])
        if entry["source"] not in ALLOWED_SOURCES:
            problems.append(f"Library item '{label}' has unknown source '{entry['source']}'.")
        if entry["source"] == "ai-generated" and not entry.get("generator"):
            problems.append(f"Library item '{label}' is AI-generated but has no 'generator' (tool/model).")
        if not isinstance(entry["tags"], list) or not all(isinstance(t, str) for t in entry["tags"]):
            problems.append(f"Library item '{label}' has invalid 'tags'.")
            continue
        image = (path.parent / entry["file"]).resolve()
        if not image.is_file():
            problems.append(f"Library item '{label}' file not found: {entry['file']}")
            continue
        items.append(LibraryItem(entry["id"], image, entry["source"], entry["licence"],
                                 tuple(entry["tags"]), entry.get("status", "approved")))
    if problems:
        raise LibraryError(problems)
    return sorted(items, key=lambda item: item.id)


def preferred_tags(key: str, kind: str) -> list:
    if kind == "feature":
        tags = [tag for word, tag in FEATURE_KEYWORDS.items() if word in key.lower()]
    else:
        tags = list(FIXED_TAGS[key])
    return tags + ["general"]


def pick(items, used: set, key: str, kind: str):
    """Best unused item for a scene: first preferred tag that has a free photo, in id order."""
    for tag in preferred_tags(key, kind):
        for item in items:
            if item.path not in used and tag in item.tags:
                return item
    return None
