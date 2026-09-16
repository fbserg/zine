#!/bin/bash
# queue.sh NAME [-e MODEL] "seed line" ...  : append a book request to models/QUEUE.
# scripts/drain.sh starts queued books whenever fewer than MAX_LANES Codex lanes run.
set -e
[[ ${1:-} =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "invalid issue name: use lowercase letters, numbers, and single hyphens" >&2; exit 1; }
cd "$(dirname "$0")/.."
printf '%s\n' "$(printf '%q ' "$@")" >> models/QUEUE; echo "queued: $1 ($(wc -l < models/QUEUE) in queue)"
