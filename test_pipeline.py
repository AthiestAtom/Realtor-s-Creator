import shutil
from pathlib import Path

import pytest
from PIL import Image

from proptvid.models import ValidationError, parse_property
from proptvid.render import render_video
from proptvid.script import Scene, fact_check, plan_scenes


def _images(tmp: Path, count: int = 8):
    names = []
    for i in range(count):
        path = tmp / f"img{i}.jpg"
        Image.new("RGB", (800, 600), (i * 30, 100, 150)).save(path)
        names.append(path.name)
    return names


def _raw(tmp: Path, count: int = 8, **overrides):
    raw = {
        "name": "Park View 2-BHK Residences",
        "location": "Sample Street, Sample City",
        "price": "₹85,00,000",
        "property_type": "2-BHK apartment",
        "cta": "Call Sample Realty at 000-0000000 to book a visit.",
        "images": _images(tmp, count),
        "key_features": ["Park View", "2 bedrooms", "Covered parking"],
    }
    raw.update(overrides)
    return raw


def test_full_plan_uses_each_photo_once(tmp_path):
    prop = parse_property(_raw(tmp_path), tmp_path)
    scenes, notes = plan_scenes(prop)
    assert [s.kind for s in scenes] == ["title", "price", "feature", "feature", "feature", "cta"]
    photos = [s.image for s in scenes]
    assert len(set(photos)) == len(photos)
    assert all("not used" in n for n in notes)
    assert fact_check(prop, scenes) == []


def test_not_enough_photos_drops_features_with_note(tmp_path):
    prop = parse_property(_raw(tmp_path, count=4), tmp_path)
    scenes, notes = plan_scenes(prop)
    assert len(scenes) == 4
    assert len({s.image for s in scenes}) == 4
    assert [s.kind for s in scenes] == ["title", "price", "feature", "cta"]
    assert any("'2 bedrooms' dropped" in n for n in notes)
    assert any("'Covered parking' dropped" in n for n in notes)


def test_image_map_is_honoured(tmp_path):
    raw = _raw(tmp_path, count=5, key_features=["Park View"])
    raw["image_map"] = {"cta": raw["images"][4], "title": raw["images"][0]}
    prop = parse_property(raw, tmp_path)
    scenes, _ = plan_scenes(prop)
    assert scenes[0].image == prop.images[0]
    assert scenes[-1].image == prop.images[4]


def test_image_map_reusing_a_photo_is_rejected(tmp_path):
    raw = _raw(tmp_path)
    raw["image_map"] = {"title": raw["images"][0], "cta": raw["images"][0]}
    with pytest.raises(ValidationError) as err:
        parse_property(raw, tmp_path)
    assert any("mapped to both" in p for p in err.value.problems)


def test_image_map_unknown_scene_rejected(tmp_path):
    raw = _raw(tmp_path)
    raw["image_map"] = {"garden": raw["images"][0]}
    with pytest.raises(ValidationError) as err:
        parse_property(raw, tmp_path)
    assert any("not a scene" in p for p in err.value.problems)


def test_same_photo_listed_twice_rejected(tmp_path):
    raw = _raw(tmp_path)
    raw["images"][1] = raw["images"][0]
    with pytest.raises(ValidationError) as err:
        parse_property(raw, tmp_path)
    assert any("listed more than once" in p for p in err.value.problems)


def test_missing_images_are_reported(tmp_path):
    raw = _raw(tmp_path, images=["nope1.jpg", "nope2.jpg", "nope3.jpg", "nope4.jpg"])
    with pytest.raises(ValidationError) as err:
        parse_property(raw, tmp_path)
    assert sum("Image not found" in p for p in err.value.problems) == 4


def test_too_few_images_rejected(tmp_path):
    raw = _raw(tmp_path)
    raw["images"] = raw["images"][:2]
    with pytest.raises(ValidationError) as err:
        parse_property(raw, tmp_path)
    assert any("Provide 4 to 8 images" in p for p in err.value.problems)


def test_all_problems_reported_together(tmp_path):
    raw = _raw(tmp_path, location="", price=8500000)
    with pytest.raises(ValidationError) as err:
        parse_property(raw, tmp_path)
    assert any("'location'" in p for p in err.value.problems)
    assert any("'price'" in p for p in err.value.problems)


def test_missing_features_omit_feature_scenes(tmp_path):
    raw = _raw(tmp_path)
    del raw["key_features"]
    prop = parse_property(raw, tmp_path)
    assert prop.missing == ["key_features"]
    scenes, _ = plan_scenes(prop)
    assert all(s.kind != "feature" for s in scenes)
    assert fact_check(prop, scenes) == []


def test_fact_check_catches_invented_feature(tmp_path):
    prop = parse_property(_raw(tmp_path), tmp_path)
    scene = Scene("feature", "Close to schools", "Featuring close to schools.", prop.images[0])
    issues = fact_check(prop, [scene])
    assert any("schools" in i for i in issues)
    assert any("close" in i for i in issues)


def test_fact_check_catches_rounded_price(tmp_path):
    prop = parse_property(_raw(tmp_path), tmp_path)
    scene = Scene("price", "Asking price", "The asking price is under ₹1 crore.", prop.images[0])
    issues = fact_check(prop, [scene])
    assert any("'under'" in i for i in issues)
    assert any("'1'" in i for i in issues)


def test_fact_check_catches_evaluative_claim(tmp_path):
    prop = parse_property(_raw(tmp_path), tmp_path)
    scene = Scene("price", "Asking price", "A great deal at ₹85,00,000.", prop.images[0])
    assert any("'great'" in i for i in fact_check(prop, [scene]))


def test_fact_check_enforces_caption_length(tmp_path):
    prop = parse_property(_raw(tmp_path), tmp_path)
    scene = Scene("feature", " ".join(["Park"] * 13), "Featuring Park View.", prop.images[0])
    assert any("13 words" in i for i in fact_check(prop, [scene]))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_end_to_end_render(tmp_path):
    prop = parse_property(_raw(tmp_path), tmp_path)
    scenes, _ = plan_scenes(prop)
    out = render_video(scenes, tmp_path / "video.mp4")
    assert out.exists() and out.stat().st_size > 10_000


# ---- image library mode ----
import json as _json
from proptvid.library import load_library, LibraryError


def _lib_raw(**overrides):
    raw = {
        "name": "Park View 2-BHK Residences",
        "location": "Sample Street, Sample City",
        "price": "₹85,00,000",
        "property_type": "2-BHK apartment",
        "cta": "Call Sample Realty at 000-0000000 to book a visit.",
        "key_features": ["Park View", "2 bedrooms", "Covered parking"],
    }
    raw.update(overrides)
    return raw


def test_library_mode_gives_each_scene_a_unique_tagged_photo(tmp_path):
    prop = parse_property(_lib_raw(), tmp_path)
    assert prop.library is not None and len(prop.library) >= 8
    scenes, _ = plan_scenes(prop)
    photos = [s.image for s in scenes]
    assert len(set(photos)) == len(photos)
    by_key = {s.caption: s.image.name for s in scenes}
    assert by_key["2 bedrooms"] == "bed-01.jpg"
    assert by_key["Covered parking"] == "parking-01.jpg"
    assert by_key["Park View"] == "park-01.jpg"


def test_library_entry_without_licence_is_rejected(tmp_path):
    (tmp_path / "x.jpg").write_bytes(b"")
    index = tmp_path / "library.json"
    index.write_text(_json.dumps({"items": [{"id": "a", "file": "x.jpg", "source": "owned",
                                             "licence": "", "tags": ["exterior"]}]}))
    with pytest.raises(LibraryError) as err:
        load_library(index)
    assert any("licence" in p for p in err.value.problems)


def test_ai_generated_library_entry_needs_generator(tmp_path):
    (tmp_path / "x.jpg").write_bytes(b"")
    index = tmp_path / "library.json"
    index.write_text(_json.dumps({"items": [{"id": "a", "file": "x.jpg", "source": "ai-generated",
                                             "licence": "tool terms", "tags": ["exterior"]}]}))
    with pytest.raises(LibraryError) as err:
        load_library(index)
    assert any("generator" in p for p in err.value.problems)


def test_library_mode_rejects_image_map(tmp_path):
    raw = _lib_raw()
    raw["image_map"] = {"title": "x.jpg"}
    with pytest.raises(ValidationError) as err:
        parse_property(raw, tmp_path)
    assert any("image_map" in p for p in err.value.problems)
