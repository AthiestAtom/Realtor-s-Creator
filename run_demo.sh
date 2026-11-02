#!/usr/bin/env bash
# Full demo: set up a clean environment, run the tests, and generate the sample video.
set -e
cd "$(dirname "$0")"
echo "== 1. Checking ffmpeg =="; ffmpeg -version | head -1
echo "== 2. Creating virtual environment and installing requirements =="
python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
echo "== 3. Running tests =="
python -m pytest -q
echo "== 4. Validating the sample input =="
python -m proptvid.cli --input sample/property.json --check
echo "== 5. Generating the sample video =="
mkdir -p sample_output
python -m proptvid.cli --input sample/property.json --output sample_output/property_video.mp4
echo "== 6. Done. Video: sample_output/property_video.mp4 =="
