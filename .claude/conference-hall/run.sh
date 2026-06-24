#!/usr/bin/env bash
# Start the Conference Hall feed service (server.py).
#
# - Self-locating: works regardless of the caller's working directory.
# - Idempotent: if the service is already answering on the port, it does NOT
#   start a second one.
# - Detached by default, so the manager can call it without blocking. Pass
#   --foreground to run it in the current terminal instead.
# - Honors FEED_PORT (default 8787) and FEED_DB (default conference_hall.db).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PORT="${FEED_PORT:-8787}"
URL="http://127.0.0.1:${PORT}"
PY="$DIR/.venv/bin/python3"
LOG="$DIR/conference_hall.log"
FOREGROUND=0
[ "${1:-}" = "--foreground" ] && FOREGROUND=1

if [ ! -x "$PY" ]; then
  echo "venv missing at $PY — run ./setup.sh from the repo root first." >&2
  exit 1
fi

# Already up? Don't double-start.
if curl -s -o /dev/null "${URL}/channels" 2>/dev/null; then
  echo "Conference Hall already running → ${URL}"
  exit 0
fi

if [ "$FOREGROUND" -eq 1 ]; then
  echo "Starting Conference Hall (foreground) → ${URL}"
  exec env FEED_PORT="$PORT" "$PY" server.py
fi

env FEED_PORT="$PORT" nohup "$PY" server.py > "$LOG" 2>&1 &
PID=$!
echo "Starting Conference Hall (pid ${PID}, log: ${LOG}) …"

for _ in $(seq 1 40); do
  if curl -s -o /dev/null "${URL}/channels" 2>/dev/null; then
    echo "Conference Hall is live → ${URL}"
    echo "Stop it with:  fuser -k ${PORT}/tcp"
    exit 0
  fi
  sleep 0.25
done

echo "Service did not come up in time — check ${LOG}." >&2
exit 1
