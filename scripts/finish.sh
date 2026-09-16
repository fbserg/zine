#!/bin/bash
# finish.sh NAME RUN: land a drawn book whose book.sh died after launching its Codex lane.
# Same steps as book.sh step 4. Waits for the lane if it is still drawing.
set -e; cd "$(dirname "$0")/.."
NAME=${1:-}
[[ $NAME =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "invalid issue name: use lowercase letters, numbers, and single hyphens" >&2; exit 1; }
RUN=${2:-}
[[ $RUN =~ ^[0-9]+$ ]] || { echo "usage: finish.sh NAME RUN (numeric run ID)" >&2; exit 1; }
WT=/tmp/codex-wt-$RUN-$NAME; BRANCH=codex/book-$RUN-$NAME
PID=$(cat /tmp/codex-pid-$RUN-$NAME 2>/dev/null || true)
while [ -n "$PID" ] && kill -0 $PID 2>/dev/null; do sleep 30; done
n=$(ls $WT/models/$NAME/*.jpg 2>/dev/null | wc -l); [ "$n" = 8 ] || { echo "$NAME: expected 8 jpgs, got $n" >&2; exit 1; }
git -C $WT add models/$NAME/*.jpg; git -C $WT commit -qm "Draw zine ($NAME editor, Codex)"
git merge -q --no-ff $BRANCH -m "Merge $NAME zine"; git worktree remove --force $WT; git branch -D -q $BRANCH; rm -f /tmp/codex-pid-$RUN-$NAME
python3 scripts/cost.py $NAME >/dev/null; git add models/$NAME/COST.json; git commit -qm "Cost $NAME"
python3 - <<PY
import base64, pathlib
from PIL import Image
root = pathlib.Path('.').resolve(); name = '$NAME'
imgs = ''.join(f'<img src="data:image/jpeg;base64,{base64.b64encode((root/f"models/{name}/{n}.jpg").read_bytes()).decode()}" alt="Page {n}">' for n in range(1, 9))
(root/f'models/{name}/book.html').write_text(f'<title>Unprompted ({name})</title><style>body{{margin:0;background:#f4f2ec;padding-block:24px;padding-inline:16px}}main{{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:24px}}img{{display:block;width:100%;height:auto}}</style><main>{imgs}</main>')
ims = [Image.open(root/f'models/{name}/{n}.jpg').convert('RGB').resize((400,400)) for n in range(1,9)]
sheet = Image.new('RGB',(1600,800),'white')
for i, im in enumerate(ims): sheet.paste(im, ((i%4)*400, (i//4)*400))
sheet.save(f'/tmp/contact-{name}.jpg', quality=80)
PY
./scripts/deploy.sh >/dev/null 2>&1
echo "/tmp/contact-$NAME.jpg"; echo "$(pwd)/models/$NAME/book.html"; echo "https://zine.serg.lol/$NAME/"
