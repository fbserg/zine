# Make an UNPROMPTED issue

Start with one situation. Write eight pages. Draw them as a sequence. Read the result without an explanation.

[Clover](https://zine.serg.lol/clover/) is the worked example. Its [script](models/clover/SCRIPT.md) and [direction](models/clover/DIRECTION.md) show the full input, while the numbered JPEGs show the output.

## 1. Choose a seed

Clover starts with: **“a girl looking in the grass for four-leaf clovers.”**

The seed supplies a situation. The editor supplies the plot, exact words, composition, and ending. Keep the seed short enough to leave those choices open.

The [seed list](direction/SEEDS.md) contains other experiments. An optional place or style line can shift the result. Use invented situations and omit private details.

## 2. Create the issue folder

Choose a new name. Do not overwrite Clover.

```sh
mkdir -p models/my-clover
cp direction/RULES.md models/my-clover/DIRECTION.md
```

Insert your seed before `Everything else is yours.` in the new direction file.

The default rules specify eight square pages, one recurring character, black plus one accent ink, and sixty words maximum. The cover counts toward that budget. Read [art/STYLE.md](art/STYLE.md) for the print texture, shapes, and lettering.

If you want a different visual system, add `models/my-clover/STYLE.md` and give that file to both editor and illustrator. Update the direction to agree with it.

## 3. Write the script

Use [scripts/codex-write-plan.md](scripts/codex-write-plan.md) as the editor prompt. Replace `$VARIANT` with `my-clover`. The filename is historical: the prompt can go to any editor with access to the files.

Give the editor only the new direction and chosen style. Ask for a fresh story, then save the result as `models/my-clover/SCRIPT.md`.

The script begins with `Ink: <colour>`. Each `## Page N` section contains:

| Field | Meaning |
| --- | --- |
| `Words:` | Every word to print, with headline or small-text roles. Use `none` for a silent page. |
| `Picture:` | One paragraph with the frame, character pose, objects, ink placement, and composition |

Clover uses green. Its word sequence is:

| Page | Printed words | Story beat |
| --- | --- | --- |
| 1 | UNPROMPTED | A girl searches a small patch of grass |
| 2 | None | The search expands |
| 3 | three. | The first find disappoints |
| 4 | three. three. three. three. three. | The pattern repeats |
| 5 | None | Night approaches and a raccoon watches |
| 6 | fine. | She gives up |
| 7 | None | Four leaves stick to her shoe |
| 8 | four. | The raccoon gets the prize |

Check the script before you draw. Count the words. Confirm eight pages. Read the story without the picture descriptions, then check that the pictures carry the silent beats.

## 4. Draw all eight pages

Use [scripts/codex-draw-plan.md](scripts/codex-draw-plan.md). Replace `$VARIANT` with the new folder name. If the issue has its own style, replace the shared style path too.

Keep one illustrator context for the whole book. Once the character has a look, preserve its hair, clothes, proportions, and expression across later pages.

For each page, the prompt combines:

1. The style, with the chosen accent ink named explicitly.
2. That page's picture paragraph.
3. The exact printed words and their roles.
4. A request for no additional text.

Each page is one raster image with the words already inside it. The gallery does not add lettering. Save raw output under `models/my-clover/raw/`, which Git ignores.

Inspect every generated page at readable size:

- Match every word to the script, including punctuation and repeated words.
- Check for missing, duplicate, or extra text.
- Check the character against earlier pages.
- Check the palette and page shape.
- Check the visual fact that carries the joke. Clover needs three leaves early and four leaves at the end.

The illustrator prompt allows up to three retries per page, then retains the best result. That limit can still leave defects. Review the final sequence before publication.

## 5. Export and preview

Save eight square RGB JPEGs named `1.jpg` through `8.jpg`. The original prompt exports at most 1000 pixels per side, JPEG quality 86, with optimization enabled.

For example, convert one raw page with Pillow:

```sh
python3 - <<'PY'
from PIL import Image
with Image.open('models/my-clover/raw/1.png') as source:
    image = source.convert('RGB')
    image.thumbnail((1000, 1000))
    image.save('models/my-clover/1.jpg', quality=86, optimize=True)
PY
```

Repeat for all eight pages. Then use the [README preview commands](README.md#preview-the-gallery-locally).

Read the book from cover to ending. Inspect it at phone width as well as full size. The result should make sense without the script beside it.

Commit the direction, script, final JPEGs, and any custom style. A cost file is optional. Do not commit raw outputs or execution logs.

## Optional automated production

The shell scripts preserve the original local workflow. The manual path above needs fewer assumptions.

| Requirement | Why it exists |
| --- | --- |
| Bash, Git, `flock`, `setsid`, `pgrep`, GNU `sed` | Local process, worktree, and queue control |
| Python with Pillow | Gallery, standalone HTML, and contact sheet |
| A configured `claude` CLI with an `opus-worker` agent | Headless script editor |
| A configured `codex` CLI with image generation access | One illustration process for all pages |
| Node.js, npm, Cloudflare authentication, `wrangler.local.toml` | Automatic deployment at the end |
| A clean main checkout | Commits and merges happen in the caller's checkout |

These tools and accounts are not installed or configured by the repository. The editor agent name is a local prerequisite. Replace it in `scripts/book.sh` if your setup uses a different agent.

**`book.sh` invokes both agent CLIs with permission checks bypassed. It creates commits, starts a worktree, merges artwork, and deploys.** Run it only with trusted local inputs in an environment you control. It is not a service for visitor-submitted prompts.

Example, after all prerequisites are ready:

```sh
scripts/book.sh my-clover "A girl searches the grass for four-leaf clovers."
```

An optional `-e MODEL` argument selects the editor model. Use a model available in your environment.

The stages are:

1. Create the direction from the shared rules and supplied seeds.
2. Write the script unless that file already exists.
3. Commit the text inputs and start the illustrator in a separate Git worktree.
4. Wait for the process, check for eight JPEGs, commit and merge them.
5. Estimate cost from local logs and create a standalone HTML book and contact sheet.
6. Build and deploy the gallery.

An existing direction is preserved when no seed arguments are supplied. An existing script skips the editor. This is useful for manual scripts, but means reruns can reuse stale work. Prefer a fresh issue name for a fresh attempt.

Logs go to `models/<name>/book.log`. The final output prints the contact sheet path, standalone book path, and gallery URL. The printed gallery URL is set to the original gallery in `book.sh` and `finish.sh`; change it for your deployment.

## Interrupted runs and batches

Inspect the issue log and the illustrator's output before recovery. Run `scripts/finish.sh NAME RUN` only when you intend to merge the artwork and deploy it. `RUN` is the identifier in `/tmp/codex-pid-RUN-NAME`. The worktree and branch must still exist.

The recovery script waits for a live illustrator process, checks for eight JPEGs, then commits, merges, estimates cost, and deploys. Run recovery alone. It does not take the landing lock used by `book.sh`.

`queue.sh` stores local shell-quoted requests in an ignored queue. `drain.sh` executes those requests. Never put untrusted text directly into the queue file. Set `MAX_LANES` explicitly before a batch; the current default is 999. Start with one lane. Shared-checkout commits and recovery are not fully isolated across concurrent jobs.

The automated path does not validate artwork quality or prove that every command succeeded merely because eight files exist. Check the gallery after deployment. Preserve failed logs locally until you understand the failure.

## Print output

The repository produces eight separate square page images and a web reader. It has no fold marks, bleed setup, page imposition, or print-ready PDF export. Arrange the pages for your chosen paper and fold before physical production.
