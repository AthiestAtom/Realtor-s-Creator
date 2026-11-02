"""Input loading and validation. All problems are collected and reported together."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .library import DEFAULT_LIBRARY, LibraryError, LibraryItem, load_library

MIN_IMAGES = 4
MAX_IMAGES = 8
MAX_FEATURES = 5
MAX_FEATURE_WORDS = 8
MAX_NAME_WORDS = 12
MAX_CTA_WORDS = 20
MAX_FIELD_CHARS = 200
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
TEXT_FIELDS = ("name", "location", "price", "property_type", "cta")
FIXED_SCENES = ("title", "price", "cta")


class ValidationError(Exception):
    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


@dataclass
class Property:
    name: str
    location: str
    price: str
    property_type: str
    cta: str
    images: list                                      # user-supplied photos (may be empty)
    key_features: list = field(default_factory=list)
    image_map: dict = field(default_factory=dict)     # scene key -> image Path
    missing: list = field(default_factory=list)
    library: list = None                              # LibraryItem list when photos come from the library


def load_property(path) -> Property:
    path = Path(path)
    if not path.is_file():
        raise ValidationError([f"Input file not found: {path}"])
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError([f"Input file is not valid JSON: {exc.msg} (line {exc.lineno})."])
    return parse_property(raw, path.parent)


def _resolve(item: str, base_dir: Path) -> Path:
    path = Path(item)
    return (path if path.is_absolute() else base_dir / path).resolve()


def parse_property(raw, base_dir) -> Property:
    base_dir = Path(base_dir)
    problems = []
    if not isinstance(raw, dict):
        raise ValidationError(["Input must be a JSON object."])

    values = {}
    for key in TEXT_FIELDS:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"'{key}' is required and must be non-empty text.")
            continue
        value = " ".join(value.split())
        if len(value) > MAX_FIELD_CHARS:
            problems.append(f"'{key}' is longer than {MAX_FIELD_CHARS} characters.")
        values[key] = value
    if "name" in values and len(values["name"].split()) > MAX_NAME_WORDS:
        problems.append(f"'name' must be at most {MAX_NAME_WORDS} words.")
    if "cta" in values and len(values["cta"].split()) > MAX_CTA_WORDS:
        problems.append(f"'cta' must be at most {MAX_CTA_WORDS} words.")

    images, library = [], None
    raw_images = raw.get("images")
    if raw_images is None:
        try:
            library = load_library(raw.get("library") or DEFAULT_LIBRARY)
        except LibraryError as exc:
            problems.extend(exc.problems)
    elif not isinstance(raw_images, list) or not raw_images:
        problems.append(f"'images' is required: a list of {MIN_IMAGES} to {MAX_IMAGES} image paths.")
    else:
        if not MIN_IMAGES <= len(raw_images) <= MAX_IMAGES:
            problems.append(f"Provide {MIN_IMAGES} to {MAX_IMAGES} images; {len(raw_images)} given.")
        for item in raw_images:
            if not isinstance(item, str):
                problems.append(f"Image entry is not a file path: {item!r}")
                continue
            path = _resolve(item, base_dir)
            if not path.is_file():
                problems.append(f"Image not found: {item}")
            elif path.suffix.lower() not in IMAGE_EXTENSIONS:
                problems.append(f"Unsupported image type (use jpg, png or webp): {item}")
            elif path in images:
                problems.append(f"Image listed more than once: {item}. Each scene needs its own photo.")
            else:
                images.append(path)

    features, missing = [], []
    raw_features = raw.get("key_features")
    if raw_features is None or raw_features == []:
        missing.append("key_features")
    elif not isinstance(raw_features, list) or not all(isinstance(f, str) and f.strip() for f in raw_features):
        problems.append("'key_features' must be a list of non-empty text items.")
    else:
        features = [" ".join(f.split()).rstrip(". ") for f in raw_features]
        if len(set(features)) != len(features):
            problems.append("'key_features' contains a duplicate item.")
        if len(features) > MAX_FEATURES:
            problems.append(f"At most {MAX_FEATURES} key features are supported; {len(features)} given.")
        for feature in features:
            if len(feature.split()) > MAX_FEATURE_WORDS:
                problems.append(f"Feature too long (max {MAX_FEATURE_WORDS} words): '{feature}'.")

    image_map = {}
    raw_map = raw.get("image_map")
    if raw_map is not None and library is not None:
        problems.append("'image_map' needs an 'images' list. Library mode chooses photos by tag.")
    elif raw_map is not None:
        if not isinstance(raw_map, dict):
            problems.append("'image_map' must be an object mapping scene names to image paths.")
        else:
            allowed = set(FIXED_SCENES) | set(features)
            used = {}
            for key, item in raw_map.items():
                if key not in allowed:
                    problems.append(f"'image_map' key '{key}' is not a scene. Use title, price, cta, "
                                    "or an exact key_features item.")
                    continue
                if not isinstance(item, str):
                    problems.append(f"'image_map' entry '{key}' is not a file path.")
                    continue
                path = _resolve(item, base_dir)
                if path not in images:
                    problems.append(f"'image_map' entry '{key}' points to an image not listed in 'images': {item}")
                    continue
                if path in used:
                    problems.append(f"{item} is mapped to both '{used[path]}' and '{key}'. "
                                    "Each image can be used for one scene only.")
                    continue
                used[path] = key
                image_map[key] = path

    if problems:
        raise ValidationError(problems)

    return Property(
        name=values["name"], location=values["location"], price=values["price"],
        property_type=values["property_type"], cta=values["cta"], images=images,
        key_features=features, image_map=image_map, missing=missing, library=library,
    )
