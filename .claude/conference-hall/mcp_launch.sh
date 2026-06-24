#!/usr/bin/env bash
# Portable launcher for the Conference Hall MCP server.
#
# It resolves its OWN location (via BASH_SOURCE), so the venv python and
# mcp_server.py are found by absolute path no matter where the repo was cloned
# or what the caller's working directory is. That is what makes .mcp.json
# portable: it only needs a project-root-relative path to THIS script.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/.venv/bin/python3"

if [ ! -x "$PY" ]; then
  echo "conference-hall: venv missing at $PY — run ./setup.sh first." >&2
  exit 1
fi

exec "$PY" "$DIR/mcp_server.py"
