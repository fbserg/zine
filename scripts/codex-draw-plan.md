# Goal
You are the illustrator and printer of an eight-page mini zine. Draw all eight pages with your image generation tool. Each page is ONE square image containing the picture and all of its words. Raster only. No SVG, no PIL drawing, no code-generated art.
If you have no image generation tool: STOP and say NO_IMAGE_TOOL.

# Read first
1. models/$VARIANT/DIRECTION.md: the direction.
2. art/STYLE.md: the print style. Put it verbatim at the start of every prompt, with "the second ink" replaced by the colour named on the script's first line.
3. models/$VARIANT/SCRIPT.md: the editor's script. Page N gives the exact words and the picture. The words are final; do not change, add, or drop any. The picture paragraph is a starting point. Take real risks with every page. The safe drawing is the wrong one. Keep the words and the story beats.
Precedence when anything disagrees: SCRIPT.md, then DIRECTION.md, then STYLE.md. Do not stop for conflicts; decide, keep drawing, note the decision in your final message.

# Per page N (1 through 8)
1. Build the prompt from the print style, the page's picture paragraph, and "The words on the page read exactly: ..." listing every word with its role, then "No other text anywhere."
2. Generate a square image. Save raw as models/$VARIANT/raw/N.png.
3. Look at it. Read every word back. Reject if any word is misspelled, missing, duplicated, or extra; if there is any colour beyond black, the second ink, and paper; or if the character looks different from earlier pages. Regenerate with a tightened prompt, up to three retries, then keep the best.
4. Keep the character consistent: once page 1 or 2 fixes their look, describe it in every later prompt.
5. Downscale: python3 -c "from PIL import Image; im=Image.open('models/$VARIANT/raw/N.png').convert('RGB'); im.thumbnail((1000,1000)); im.save('models/$VARIANT/N.jpg', quality=86, optimize=True)"

# Write only
models/$VARIANT/raw/*.png and models/$VARIANT/1.jpg through models/$VARIANT/8.jpg. Touch nothing else.

# Rules
Do NOT git add/commit/push/reset/checkout/stash or create branches. Edit and test only; leave changes unstaged. Committing is the orchestrator's job.
No new dependencies.

# Output
Per page: retries and why, the exact text read back, jpg size.
