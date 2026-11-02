# Demo: 60-second walkthrough

1. Install (see README), then run:
   ```bash
   python -m proptvid.cli --input sample/property.json --preview
   ```
2. The terminal prints the plan: 8 scenes, each with its own tagged photo and its caption and narration. Notes appear if a feature was dropped or a placeholder photo is used.
3. The MP4 opens in your player. Scenes show a slow camera move, a caption that animates in, and a transition to the next scene.
4. Try a bad input to see validation:
   ```bash
   python -m proptvid.cli --input sample/invalid_property.json
   ```
   Every problem is listed together and no video is made.
5. Enter your own listing without editing JSON:
   ```bash
   python -m proptvid.cli --interactive --preview
   ```

Sample output is in `sample_output/`: the MP4 and the script JSON with every caption and narration line.
