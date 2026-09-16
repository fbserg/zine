#!/bin/bash
# book.sh NAME [-e MODEL] "seed line" ["seed line" ...]
# One command, one book: direction, headless editor, Codex draw lane, land, deploy.
# MODEL (-e) overrides the editor model: opus (default), sonnet, haiku, fable.
set -e
# Whole body in a function: bash parses it before running, so editing this file mid-run cannot break a running book.
main() {
cd "$(dirname "$0")/.."

NAME=${1:-}
[[ $NAME =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "invalid issue name: use lowercase letters, numbers, and single hyphens" >&2; exit 1; }
shift

MODEL=""
if [ "$1" = "-e" ]; then MODEL=$2; shift 2; fi

RUN=$$
WT=/tmp/codex-wt-$RUN-$NAME
BRANCH=codex/book-$RUN-$NAME

# stdout is for the orchestrator, which judges art only: contact sheet, book.html,
# site URL, nothing else. Everything else (cost, tokens, retries, deploy) goes to
# the per-book log. fd 3/4 keep a path to the real terminal for the final lines
# and for hard failures.
mkdir -p models/$NAME
LOG=models/$NAME/book.log
exec 3>&1 4>&2 >"$LOG" 2>&1

# 1. Direction: models/NAME/DIRECTION.md = direction/RULES.md with the seed lines inserted.
# A DIRECTION.md already in place (hand-written) is kept when no seed lines are given.
[ $# = 0 ] && [ -f models/$NAME/DIRECTION.md ] || { sed '/^Everything else is yours/,$d' direction/RULES.md; printf '%s\n' "$@"; sed -n '/^Everything else is yours/,$p' direction/RULES.md; } > models/$NAME/DIRECTION.md

# A per-book STYLE.md overrides art/STYLE.md for both editor and illustrator.
STYLE=art/STYLE.md; [ -f models/$NAME/STYLE.md ] && STYLE=models/$NAME/STYLE.md

# 2. Editor: headless opus-worker (or -e MODEL) writes models/NAME/SCRIPT.md.
# A SCRIPT.md already in place is kept (editor ran elsewhere).
if [ ! -f models/$NAME/SCRIPT.md ]; then
WRITE_PLAN=$(sed "s|\$VARIANT|$NAME|g; s|art/STYLE.md|$STYLE|g" scripts/codex-write-plan.md)
MODEL_FLAG=()
[ -n "$MODEL" ] && MODEL_FLAG=(--model "$MODEL")
claude --agent opus-worker --effort high "${MODEL_FLAG[@]}" --permission-mode bypassPermissions -p "$WRITE_PLAN"
fi
# Some editors (Haiku) reply with the script instead of writing it; the reply is the log.
[ -f models/$NAME/SCRIPT.md ] || { [ "$(head -c4 $LOG)" = "Ink:" ] && cp $LOG models/$NAME/SCRIPT.md; }
[ -f models/$NAME/SCRIPT.md ] || { echo "editor did not write models/$NAME/SCRIPT.md, see $LOG" >&4; exit 1; }

git add models/$NAME/DIRECTION.md models/$NAME/SCRIPT.md
[ -f models/$NAME/STYLE.md ] && git add models/$NAME/STYLE.md
if ! git diff --cached --quiet; then git commit -qm "Script $NAME: $*"; fi

# 3. Illustrator: one Codex lane in its own worktree, draws all eight pages.
DRAW_PLAN=$(sed "s|\$VARIANT|$NAME|g; s|art/STYLE.md|$STYLE|g" scripts/codex-draw-plan.md)
git worktree add -q -b $BRANCH $WT HEAD
mkdir -p $WT/models/$NAME/raw
nohup setsid codex exec --dangerously-bypass-approvals-and-sandbox -C $WT -o /tmp/codex-out-$RUN-$NAME.md "Implement this plan exactly. Make reasonable choices, don't ask. PLAN:
$DRAW_PLAN" </dev/null > /tmp/codex-run-$RUN-$NAME.log 2>&1 &
sleep 3
pgrep -f "codex exec .*codex-wt-$RUN-$NAME" | head -1 > /tmp/codex-pid-$RUN-$NAME
PID=$(cat /tmp/codex-pid-$RUN-$NAME)
echo "$NAME draw lane pid $PID, worktree $WT"
( sleep 3600; kill -0 $PID 2>/dev/null && kill -TERM $PID ) >/dev/null 2>&1 &

while kill -0 $PID 2>/dev/null; do sleep 30; done

# 4. Land: commit the lane, merge, cost, render, deploy. One lander at a time: parallel runs collided on .git/index.lock.
exec 9>.git/book.lock; flock 9
n=$(ls $WT/models/$NAME/*.jpg 2>/dev/null | wc -l)
echo "$NAME jpgs=$n"
[ "$n" = 8 ] || { echo "expected 8 jpgs, got $n; see /tmp/codex-out-$RUN-$NAME.md and $LOG" >&4; exit 1; }

git -C $WT add models/$NAME/*.jpg
git -C $WT commit -qm "Draw zine ($NAME editor, Codex)"
git merge -q --no-ff $BRANCH -m "Merge $NAME zine"
git worktree remove --force $WT
git branch -D -q $BRANCH
rm -f /tmp/codex-pid-$RUN-$NAME

python3 scripts/cost.py $NAME
git add models/$NAME/COST.json
git commit -qm "Cost $NAME"

python3 -c "
import base64, pathlib
root = pathlib.Path('.').resolve()
name = '$NAME'
imgs = ''.join(f'<img src=\"data:image/jpeg;base64,{base64.b64encode((root/f\"models/{name}/{n}.jpg\").read_bytes()).decode()}\" alt=\"Page {n}\">' for n in range(1, 9))
(root / f'models/{name}/book.html').write_text(f'''<title>Unprompted ({name})</title>
<style>
:root{{--bg:#f4f2ec}}
@media (prefers-color-scheme: dark){{:root:not([data-theme=\"light\"]){{--bg:#1c1b19}}}}
:root[data-theme=\"dark\"]{{--bg:#1c1b19}}
body{{margin:0;background:var(--bg);padding-block:24px;padding-inline:16px}}
main{{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:24px}}
img{{display:block;width:100%;max-width:100%;height:auto}}
</style>
<main>{imgs}</main>
''')
from PIL import Image
ims = [Image.open(root/f'models/{name}/{n}.jpg').convert('RGB').resize((400,400)) for n in range(1,9)]
sheet = Image.new('RGB',(1600,800),'white')
for i, im in enumerate(ims): sheet.paste(im, ((i%4)*400, (i//4)*400))
sheet.save(f'/tmp/contact-{name}.jpg', quality=80)
"

./scripts/deploy.sh

echo "/tmp/contact-$NAME.jpg" >&3
echo "$(pwd)/models/$NAME/book.html" >&3
echo "https://zine.serg.lol/$NAME/" >&3
}
main "$@"
