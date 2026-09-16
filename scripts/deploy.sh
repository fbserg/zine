#!/bin/bash
# Render site/ and deploy it as a Cloudflare Worker with static assets at zine.serg.lol.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -f wrangler.local.toml ]] || { echo "Copy wrangler.toml to wrangler.local.toml and configure your Worker and KV first." >&2; exit 1; }
python3 scripts/site.py
npx --yes wrangler@4 deploy --config wrangler.local.toml
