# Conference Hall — a Claude Code orchestration template

A portable starter template that turns one Claude Code session into a
**manager** that talks to you in real time and delegates work to **background
subagents** — with a live web **control panel** (the *Conference Hall*) where
you watch every actor's stream and answer the decisions pinned to the top.

Clone it, run `./setup.sh`, start Claude Code, and open
<http://127.0.0.1:8787> beside your terminal.

```
┌─ your terminal ──────────────┐     ┌─ http://127.0.0.1:8787 ───────────────┐
│  you ⇄ manager (Claude)      │     │  [All] [manager•1] [research] [impl]   │
│  "build me X"                │     │  ┌──────────────────────────────────┐  │
│   → delegates in background  │     │  │ 📌 DECISION  Postgres or SQLite?  │  │
│   → answers come back        │     │  ├──────────────────────────────────┤  │
│                              │     │  │ SPAWN  research: map the API     │  │
└──────────────────────────────┘     │  │ RESULT  found 3 call sites …     │  │
                                      │  └──────────────────────────────────┘  │
                                      └────────────────────────────────────────┘
```

> _Screenshot placeholder — drop a real capture of the Conference Hall UI here._

## How it works (the mental model)

- **The manager routes; it never implements.** It converses with you, decomposes
  the task, and dispatches background subagents so your conversation never blocks.
- **Subagents are isolated and single-shot.** Each owns one workspace and one
  *channel*, reads only stable inputs (its task, its workspace, a named upstream
  `OUTPUT.md`), writes a canonical `OUTPUT.md`, and dies when done.
- **Subagents never talk to each other.** If one needs something another knows,
  it says so in its return summary and the **manager** re-spawns the right agent.
  One router, no agent-to-agent chatter.
- **Every actor writes only its own channel**, and the feed service serializes
  writes — so there's no shared-file clobbering. You see one browser tab per
  channel, plus an "All" tab.
- **Archiving keeps it bounded.** Resolved decisions and finished tasks get
  archived (hidden from the live view, kept on disk). The panel always reflects
  *current* state and never grows without end.

The control panel is the **Conference Hall**, a tiny local service that lives in
[`.claude/conference-hall/`](.claude/conference-hall/) — see its
[README](.claude/conference-hall/README.md) for the full internals (data model,
HTTP API, MCP tools).

## Quickstart

```bash
git clone <your-fork-url> my-project && cd my-project
./setup.sh                 # builds the venv, installs deps, marks scripts executable
claude                     # start Claude Code in the repo root
```

On its first turn the manager makes sure the Conference Hall is running and
gives you the URL. Open it:

```
http://127.0.0.1:8787/
```

Then just talk to the manager. Approve the one-time `conference-hall` MCP server
prompt when Claude Code asks. Answer pinned decisions in the terminal; watch
each subagent's tab populate live.

## Make it yours

- **Standing preferences** → edit [`.claude/MANAGER_NOTES.md`](.claude/MANAGER_NOTES.md).
  The manager reads it every session (e.g. default models, what to always surface
  as a decision).
- **The manager's behavior** → edit [`CLAUDE.md`](CLAUDE.md).
- **Add an agent** → copy [`.claude/agents/_TEMPLATE.md`](.claude/agents/_TEMPLATE.md)
  to `.claude/agents/<name>.md`. Set `name`, write a specific `description`
  (trigger + required inputs + return contract), scope `tools` tightly, pick
  `model`/`color`, add `isolation: worktree` for parallel code writers. The
  agent's Conference Hall channel = its `name`. Restart the session to load it.
  Ships with three real agents: **planner** (opus), **research** (haiku),
  **implementer** (sonnet, worktree-isolated).

## What's in the box

```
CLAUDE.md                       Manager role (loads every session)
.mcp.json                       Registers the conference-hall MCP server (MUST be at root)
setup.sh                        One-command bootstrap
.claude/
  settings.json                 Registers the SubagentStop hook
  MANAGER_NOTES.md              Standing preferences the manager reads each session
  .mcp.json.example             Absolute-path fallback template (see Troubleshooting)
  agents/                       _TEMPLATE.md + planner / research / implementer
  commands/                     Slash commands (e.g. /clean-hall — prune the panel)
  workspaces/                   Per-agent worklog.md + OUTPUT.md (created at runtime)
  hooks/subagent_stop.py        Posts "done" to an agent's channel on finish
  conference-hall/              The feed service + MCP server + web UI
```

## Requirements

- **Python 3.10+** (with the `venv` module — `python3-venv` on Debian/Ubuntu).
- **Claude Code** (CLI) with MCP support.
- **git**, **bash**, **curl**.
- A modern browser for the panel. Linux/macOS (uses `bash`/`curl`).

## Portability

`.mcp.json` is committed and **portable** — it points at a relative launcher
script (`./.claude/conference-hall/mcp_launch.sh`) that resolves its own
location, so the same file works in any clone with no path edits. (Claude Code
loads `.mcp.json` only from the project root, which is why it lives there.)

## Troubleshooting

| Symptom | Cause & fix |
|---------|-------------|
| MCP tools error **"connection refused"** | The feed service isn't running. The manager starts it automatically; or run `bash .claude/conference-hall/run.sh`. |
| `conference-hall` shows **"Pending approval"** | Normal for a project MCP server — approve it once inside `claude`. |
| MCP server **not found at all** | `.mcp.json` must be at the **project root** (not in `.claude/`). Don't move it. |
| Launcher path doesn't resolve on your setup | Run `./setup.sh --absolute-mcp` to write a per-machine absolute `.mcp.json` from `.claude/.mcp.json.example`. |
| **venv / PyJWT** install errors | Always use the venv `setup.sh` creates — system pip can error on PyJWT. Re-run `./setup.sh`. |
| **Port 8787 in use** | Stop the old one (`fuser -k 8787/tcp`) or set `FEED_PORT` (export it before `run.sh`; update the port in `.mcp.json`'s `FEED_URL`). |
| Panel says **"service unreachable"** | The feed service is down — start it as above; the page recovers on its own. |

## License

[MIT](LICENSE).
# claude-conference-hall
