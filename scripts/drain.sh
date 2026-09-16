#!/bin/bash
# drain.sh: every 30s, if Codex lanes < MAX_LANES and models/QUEUE has a line, pop it and run book.sh with it.
# Runs until the queue is empty. Logs to models/drain.log. Book output lines go to models/NAME/book.out.
cd "$(dirname "$0")/.."; MAX=${MAX_LANES:-999}
while true; do
  [ -s models/QUEUE ] || { echo "$(date +%H:%M) queue empty, drain done" >> models/drain.log; exit 0; }
  lanes=$(pgrep -fc 'codex exec --dangerously')
  if [ "$lanes" -lt "$MAX" ]; then
    line=$(head -1 models/QUEUE); sed -i '1d' models/QUEUE
    eval "set -- $line"; name=$1
    echo "$(date +%H:%M) start $name (lanes=$lanes)" >> models/drain.log
    mkdir -p models/$name
    ( scripts/book.sh "$@" > models/$name/book.out 2>&1; echo "$(date +%H:%M) done $name exit=$?" >> models/drain.log ) &
    sleep 5   # let the editor finish and the lane appear before counting again
  else
    sleep 30
  fi
done
