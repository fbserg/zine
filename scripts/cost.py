"""Tally tokens and estimated API dollars per book into models/<name>/COST.json.

Sources: Claude editor subagent transcripts (~/.claude/projects/*zine*/*/subagents/*.jsonl)
and Codex rollout logs (~/.codex/sessions/**/rollout-*.jsonl, matched by worktree cwd).
Run after book.sh or finish.sh; site.py reads the JSON. Usage: python3 scripts/cost.py [name ...]
"""
import json, pathlib, sys

root = pathlib.Path(__file__).resolve().parent.parent
home = pathlib.Path.home()

# USD per million tokens: (input, output, cache write, cache read). Assumed list prices, not billed.
CLAUDE_PRICE = {
    'claude-haiku-4-5': (1, 5, 1.25, 0.1),
    'claude-sonnet-5': (3, 15, 3.75, 0.3),
    'claude-opus-5': (5, 25, 6.25, 0.5),
    'claude-fable-5-1': (15, 75, 18.75, 1.5),
}
CODEX_PRICE = (2, 8, 0, 0.5)   # input, output, unused, cached input
IMAGE_PRICE = 0.04             # per generated image, gpt-image class


def claude_editor(name):
    needle = f'models/{name}/SCRIPT.md'
    project_key = str(root).replace('/', '-')
    for path in home.glob(f'.claude/projects/{project_key}/*/subagents/agent-*.jsonl'):
        text = path.read_text()
        if needle not in text or 'editor and writer' not in text:
            continue
        usage = {}
        model = None
        for line in text.splitlines():
            row = json.loads(line)
            msg = row.get('message') or {}
            if row.get('type') != 'assistant' or 'usage' not in msg:
                continue
            model = msg.get('model') or model
            usage[msg['id']] = msg['usage']   # streamed chunks repeat one id; keep the last
        inp = sum(u.get('input_tokens', 0) for u in usage.values())
        out = sum(u.get('output_tokens', 0) for u in usage.values())
        cw = sum(u.get('cache_creation_input_tokens', 0) for u in usage.values())
        cr = sum(u.get('cache_read_input_tokens', 0) for u in usage.values())
        base = next((k for k in CLAUDE_PRICE if model and model.startswith(k)), None)
        if base is None:
            raise KeyError(f'no price for editor model {model!r} ({path.name})')
        pi, po, pcw, pcr = CLAUDE_PRICE[base]
        usd = (inp * pi + out * po + cw * pcw + cr * pcr) / 1e6
        return dict(model=model, input=inp, output=out, cache_write=cw, cache_read=cr, usd=round(usd, 3))
    return None


def codex_draw(name):
    sessions = []
    for path in home.glob('.codex/sessions/*/*/*/rollout-*.jsonl'):
        with path.open() as fh:
            first = json.loads(fh.readline())
        cwd = first.get('payload', {}).get('cwd', '')
        if not cwd.endswith(f'-{name}'):
            continue
        last = None
        images = 0
        for line in path.read_text().splitlines():
            if '"token_count"' in line:
                row = json.loads(line)
                if row.get('payload', {}).get('type') == 'token_count':
                    last = row['payload']['info']['total_token_usage']
            images += line.count('"type":"input_image"')
        if last:
            sessions.append((last, images))
    if not sessions:
        return None
    inp = sum(s['input_tokens'] for s, _ in sessions)
    cached = sum(s['cached_input_tokens'] for s, _ in sessions)
    out = sum(s['output_tokens'] + s['reasoning_output_tokens'] for s, _ in sessions)
    images = sum(i for _, i in sessions)
    pi, po, _, pc = CODEX_PRICE
    usd = ((inp - cached) * pi + cached * pc + out * po) / 1e6 + images * IMAGE_PRICE
    return dict(input=inp, cached=cached, output=out, images=images, usd=round(usd, 3))


names = sys.argv[1:] or [d.name for d in sorted(root.glob('models/*')) if (d / '8.jpg').exists()]
for name in names:
    editor = claude_editor(name)
    draw = codex_draw(name)
    total = round((editor or {}).get('usd', 0) + (draw or {}).get('usd', 0), 2)
    cost = dict(editor=editor, draw=draw, usd=total, partial=editor is None or draw is None)
    (root / 'models' / name / 'COST.json').write_text(json.dumps(cost, indent=1) + '\n')
    print(f'{name:10} editor={editor and editor["usd"]} draw={draw and draw["usd"]} images={draw and draw["images"]} total=${total}')
