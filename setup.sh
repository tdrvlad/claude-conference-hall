#!/usr/bin/env bash
# Conference Hall orchestration template — one-command bootstrap.
#
# Idempotent and safe to re-run: it will not clobber an existing venv or db.
#
#   ./setup.sh                 normal setup (keeps the portable relative .mcp.json)
#   ./setup.sh --absolute-mcp  ALSO generate an absolute-path .mcp.json from
#                              .mcp.json.example (fallback if the relative
#                              launcher does not resolve on your machine)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CH="$ROOT/.claude/conference-hall"
VENV="$CH/.venv"
ABSOLUTE_MCP=0
[ "${1:-}" = "--absolute-mcp" ] && ABSOLUTE_MCP=1

say() { printf '\033[36m▸\033[0m %s\n' "$*"; }
die() { printf '\033[31m✘ %s\033[0m\n' "$*" >&2; exit 1; }

# 1. Python 3.10+ ----------------------------------------------------------
command -v python3 >/dev/null 2>&1 || die "python3 not found. Install Python 3.10+."
PYV="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)' \
  || die "Python 3.10+ required, found $PYV."
say "Python $PYV OK."

# venv module present?
python3 -c 'import venv' 2>/dev/null \
  || die "python3 venv module missing. On Debian/Ubuntu: sudo apt install python3-venv"

# 2. venv + deps (use a venv — system pip errors on PyJWT) -------------------
if [ -x "$VENV/bin/python3" ]; then
  say "venv already exists — reusing $VENV"
else
  say "Creating venv at $VENV …"
  python3 -m venv "$VENV"
fi
say "Installing dependencies …"
"$VENV/bin/python3" -m pip install --upgrade pip --quiet
"$VENV/bin/pip" install -r "$CH/requirements.txt" --quiet
say "Dependencies installed."

# 3. Make scripts executable -----------------------------------------------
chmod +x "$ROOT/setup.sh" "$CH/run.sh" "$CH/mcp_launch.sh" \
         "$ROOT/.claude/hooks/subagent_stop.py" 2>/dev/null || true
say "Scripts marked executable."

# 4. Optional: absolute-path .mcp.json fallback ----------------------------
if [ "$ABSOLUTE_MCP" -eq 1 ]; then
  sed "s#__PROJECT_ROOT__#${ROOT}#g" "$ROOT/.claude/.mcp.json.example" \
    | grep -v '"_comment"' > "$ROOT/.mcp.json"
  say "Wrote absolute-path .mcp.json for ${ROOT}"
else
  say "Using portable relative .mcp.json (launcher self-locates)."
fi

# 5. Next steps ------------------------------------------------------------
cat <<EOF

$(printf '\033[32mSetup complete.\033[0m')

Next:
  1. Start the panel + Claude Code from the repo root:
         claude
     The manager auto-starts the Conference Hall on its first turn. Or start it
     yourself any time:
         bash .claude/conference-hall/run.sh
  2. Open the control panel in a browser:
         http://127.0.0.1:8787/
  3. Talk to the manager. It delegates to background subagents; watch each
     actor's tab populate live.

EOF
