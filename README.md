# AI Property Video Generator

Turns property details and 4 to 8 images into a short (about 20 to 30 second) promotional MP4 with an opening title, a price scene, 0 to 5 feature scenes, and a closing enquiry prompt. Optional voice-over.

## Approach

The video script is produced by fixed templates that insert only values supplied in the input. The model does not write free text. Because nothing is generated, nothing can be invented. A fact checker then verifies the finished script against the input before any video is rendered.

Rule-based generation was chosen deliberately. The assignment permits it when justified. Here it removes the failure modes from the earlier attempt: an LLM adding amenities, rounding prices, or filling in missing features. No API key is needed, and the output is repeatable.

### How the earlier problems are handled

| Earlier problem | Handling in this version |
|---|---|
| Model added unsupported phrases ("close to schools") | Script text comes from templates. The fact checker rejects any word that is neither in the input nor a template word, and rejects evaluative words such as "near", "close", "luxury", or "great deal" unless the input contains them. |
| Price rounded or evaluated ("under ₹1 crore", "a great deal") | The price string is copied as typed. The fact checker requires every number in the script to appear exactly in the input, so "under ₹1 crore" would fail on both "under" and "1". |
| Missing key features led to invented features | Missing or empty `key_features` is recorded as missing, and the feature scenes are omitted. Nothing is filled in. |
| Scripts could exceed length limits | Captions are capped at 12 words and narration at 20 words. The fact checker enforces both. |
| Input problems caused crashes | All input problems are collected and reported together, with the video not generated. |

### Failure policy

- Missing required text fields, invalid price type, fewer than 4 or more than 8 images, missing image files, unsupported image types, features longer than 8 words, or more than 5 features: input is rejected with a list of every problem. No video is produced.
- Missing `key_features`: feature scenes are omitted, the CLI prints a note, and the video is shorter.
- Only 0 or 1 feature supplied: the video is produced with a warning.
- More scenes than images: images are reused in order.
- Fact-check failure (should not happen with the templates, and guards against future template edits): no video is produced.

## Setup

Requirements: Python 3.10 or newer, and ffmpeg.

```bash
# Install ffmpeg
#   Ubuntu/Debian: sudo apt install ffmpeg
#   macOS:         brew install ffmpeg
#   Windows:       winget install ffmpeg   (or download from ffmpeg.org and add to PATH)

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional fonts: the renderer uses DejaVu Sans Bold or Liberation Sans Bold if installed, otherwise Pillow's default font.

## Create sample images (synthetic, no real photos)

```bash
python scripts/make_sample_assets.py
```

## Run

Options: `--interactive` asks for details in the terminal, `--preview` opens the finished MP4 in your default player, `--voice` adds narration, `--check` prints the plan without rendering.

> **Warning:** `--voice` sends each narration line to Google's text-to-speech service over the internet. Do not use it with confidential listing details unless that is acceptable for your business. Without `--voice`, nothing leaves your machine.


```bash
# Validate the input and print the script only
python -m proptvid.cli --input sample/property.json --check

# Generate the silent video
python -m proptvid.cli --input sample/property.json

# Generate with voice-over (needs internet for gTTS)
python -m proptvid.cli --input sample/property.json --voice --output out/property_video_voice.mp4

# Listing with no key features (feature scenes omitted)
python -m proptvid.cli --input sample/property_no_features.json

# Invalid input (shows the error report, makes no video)
python -m proptvid.cli --input sample/invalid_property.json
```

Output is written to `out/property_video.mp4`, with a matching `out/property_video.script.json` that lists every scene's caption and narration for review.

## Input format

```json
{
  "name": "Park View 2-BHK Residences",          
  "location": "Sample Street, Sample City",
  "price": "₹85,00,000",
  "property_type": "2-BHK apartment",
  "key_features": ["Park View", "2 bedrooms"],   
  "cta": "Call Sample Realty at 000-0000000 to book a visit.",
  "images": ["images/img01.jpg", "images/img02.jpg", "images/img03.jpg", "images/img04.jpg"]
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Up to 12 words |
| `location` | yes | |
| `price` | yes | Text, exactly as it should appear |
| `property_type` | yes | |
| `cta` | yes | Closing enquiry line, up to 20 words, used verbatim |
| `images` | yes | 4 to 8 paths, relative to the JSON file or absolute. jpg, jpeg, png, or webp |
| `key_features` | no | Up to 5 items, each up to 8 words. Omit or leave empty to skip feature scenes |

## Output and scene timing

| Scene | Caption | Narration |
|---|---|---|
| Title | Property name | Introduces name, type, and location |
| Price | "Asking price: ..." | "The asking price is ..." |
| Feature (0 to 5) | Feature text | "Featuring ..." |
| Closing | "Enquire today" | CTA text |

Each scene lasts 4 seconds, with a 0.5 second crossfade. Total length is about 3.5 seconds per scene after overlaps. The video is 1280x720, 24 fps, H.264, yuv420p, so it plays in common players.

## Tests

```bash
pytest
```

The end-to-end render test runs only if ffmpeg is installed.

## Dependencies and external services

| Item | Use |
|---|---|
| Pillow | Frame rendering and text overlays |
| ffmpeg | MP4 encoding and audio mixing |
| gTTS (optional) | Voice-over via Google Text-to-Speech, needs internet. Used only with `--voice` |
| pytest | Tests |

No language model, AI API, or API key is used. The voice-over sends the narration text to Google's TTS service when `--voice` is used. Do not use real customer data with that option unless that is acceptable for your business.

## Limitations

- Templates produce plain, factual wording. Narration is not as varied or natural as a language model's output.
- Images are cropped to 16:9 and given a slow zoom. Portrait or unusual photos are cropped, not letterboxed.
- Background music is not included. The assignment lists it as optional.
- The interface is a CLI, not a graphical form.
- Scene timing is fixed at 4 seconds, so a video with 0 or 1 features is short.
- Text overlays show up to 3 lines per caption. Longer captions are cut off, though the fact checker already limits length to 12 words.

## Project layout

```
property-video-generator/
├── proptvid/
│   ├── cli.py          command-line entry point and orchestration
│   ├── models.py       input loading and validation
│   ├── script.py       template script, fact checker
│   ├── render.py       Pillow frames and ffmpeg encoding
│   └── narration.py    optional gTTS voice-over
├── scripts/make_sample_assets.py
├── sample/             sample inputs and synthetic images
├── tests/test_pipeline.py
├── requirements.txt
└── pytest.ini
```

## Image library (current default)

If the input has no `images` list, photos come from `assets/library/library.json`. Each entry records its file, tags, source (`owned`, `ai-generated`, or `placeholder`), licence, and, for AI images, the generator used. The loader rejects any entry missing a source or licence, so unlicensed images cannot enter a video.

Each scene gets one unique photo chosen by tag. Title uses an exterior, price a living room, the CTA a lobby or exterior, and each key feature a photo matching its words (for example "2 bedrooms" selects a `bedroom` tag). A feature with no matching photo falls back to a `general` photo, and if none is left the scene is dropped and reported.

The current library holds 10 **placeholder** illustrations made by `scripts/make_library_placeholders.py`. They are not photographs. Before a real submission, replace them with owned or AI-generated photos and update each entry's `source`, `licence`, and (for AI images) `generator`. The CLI prints a note whenever a placeholder appears in a video.

To use your own photos for one listing, pass an `images` list instead. Those photos are not checked for licence, so the submitter must confirm rights.
