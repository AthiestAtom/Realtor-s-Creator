"""Scene planning, template script, and fact checking.

Scene planning rules:
- Every scene gets its own photo, so no photo appears twice in one video.
- Title and CTA are always included. Price comes next, then key features in input order.
- If there are fewer photos than candidate scenes, features that do not fit are dropped
  and reported. Nothing is repeated to fill the gap.
- Photos mapped in image_map go to their named scene. Other scenes take the remaining photos in order.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .library import pick
from .models import Property

MAX_CAPTION_WORDS = 12
MAX_NARRATION_WORDS = 20
TEMPLATE_WORDS = {"introducing", "a", "in", "the", "asking", "price", "is",
                  "featuring", "enquire", "today"}
FORBIDDEN_WORDS = {
    "luxury", "luxurious", "spacious", "stunning", "beautiful", "dream", "amazing",
    "perfect", "great", "deal", "best", "cheap", "affordable", "bargain", "exclusive",
    "premium", "prime", "modern", "huge", "near", "nearby", "close", "metro",
    "schools", "under", "only", "just",
}
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass(frozen=True)
class Scene:
    kind: str          # title | price | feature | cta
    caption: str
    narration: str
    image: Path


def plan_scenes(prop: Property):
    """Return (scenes, notes)."""
    notes = []
    specs = {
        "title": ("title", prop.name,
                  f"Introducing {prop.name}, a {prop.property_type} in {prop.location}."),
        "price": ("price", f"Asking price: {prop.price}", f"The asking price is {prop.price}."),
        "cta": ("cta", "Enquire today", prop.cta),
    }
    for feature in prop.key_features:
        specs[feature] = ("feature", feature, f"Featuring {feature}.")

    capacity = len(prop.library) if prop.library is not None else len(prop.images)
    chosen = ["title", "cta"] + [k for k in prop.image_map if k not in ("title", "cta")]
    for key in ["price", *prop.key_features]:
        if key in chosen:
            continue
        if len(chosen) < capacity:
            chosen.append(key)
        elif key == "price":
            notes.append("Price scene dropped: not enough photos for one per scene.")
        else:
            notes.append(f"Feature '{key}' dropped: not enough photos for one per scene.")

    timeline = [k for k in ["title", "price", *prop.key_features] if k in chosen] + ["cta"]

    assigned, used = {}, set()
    if prop.library is not None:
        kept = []
        for key in timeline:
            item = pick(prop.library, used, key, specs[key][0])
            if item is None:
                notes.append(f"'{key}' dropped: no unused library photo matches.")
                continue
            used.add(item.path)
            assigned[key] = item.path
            kept.append(key)
        timeline = kept
    for key in timeline:
        if key in assigned:
            continue
        if key in prop.image_map:
            assigned[key] = prop.image_map[key]
            used.add(prop.image_map[key])
    free = [img for img in prop.images if img not in used]
    for key in timeline:
        if key not in assigned:
            assigned[key] = free.pop(0)
    if prop.library is None and free:
        notes.append(f"{len(free)} photo(s) not used: {', '.join(p.name for p in free)}.")

    scenes = [Scene(specs[k][0], specs[k][1], specs[k][2], assigned[k]) for k in timeline]
    return scenes, notes


def _words(text: str) -> list:
    return re.findall(r"[a-z]+", text.lower())


def source_corpus(prop: Property) -> str:
    return " ".join([prop.name, prop.location, prop.price, prop.property_type,
                     prop.cta, *prop.key_features])


def fact_check(prop: Property, scenes) -> list:
    """Return problems. An empty list means every line is supported by the input."""
    corpus = source_corpus(prop)
    source_words = set(_words(corpus))
    source_numbers = set(NUMBER.findall(corpus))
    issues = []
    for scene in scenes:
        for label, text, limit in (("caption", scene.caption, MAX_CAPTION_WORDS),
                                   ("narration", scene.narration, MAX_NARRATION_WORDS)):
            where = f"{scene.kind} {label}"
            count = len(text.split())
            if count > limit:
                issues.append(f"{where} has {count} words (limit {limit}).")
            for word in sorted(set(_words(text))):
                if word in FORBIDDEN_WORDS and word not in source_words:
                    issues.append(f"{where} uses evaluative word '{word}' that is not in the input.")
                elif word not in source_words and word not in TEMPLATE_WORDS:
                    issues.append(f"{where} uses unsupported word '{word}'.")
            for number in NUMBER.findall(text):
                if number not in source_numbers:
                    issues.append(f"{where} contains number '{number}' that is not in the input.")
    return issues
