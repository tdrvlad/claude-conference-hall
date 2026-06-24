# Manager standing notes

Durable human preferences and context the manager reads at the start of every
session. Edit freely.

- (example) Prefer background delegation; keep the conversation responsive.
- (example) Surface security-sensitive choices as `decision` items; never auto-decide.
- (example) Default models: research=haiku, implementation=sonnet, planning=opus.
- (example) Conference Hall lives at .claude/conference-hall/ on port 8787.

## Confirmed human preferences (real)

- **Subagent dispatch: background (default).** Human prefers a responsive chat
  over the live inline console stream. They know background agents don't show
  the colored nested console output; they're fine relying on relayed summaries +
  each agent's `OUTPUT.md`/`worklog.md` + the Conference Hall. Only run an agent
  in the foreground if the human explicitly asks to watch it live.

## Demo project: "Plumber Dash" (a Mario-like game)

A worked example that exercises this template. Everything for it is marked
`DEMO_*` so it's easy to keep or delete.

- **Target spec:** `DEMO_GAME_BRIEF.md` (repo root). The game code lives in
  `demo-game/`. Tech: HTML5 Canvas + vanilla JS, **no build step**.
- **Demo agents** (in `.claude/agents/`, channels = their `name`):
  - `game-designer` (`DEMO_game-designer.md`) — fixes the constants, tile-map
    format, entity behaviors. Run FIRST. Writes only a design doc.
  - `engine-dev` (`DEMO_engine-dev.md`) — core loop/physics/collision/camera in
    `demo-game/`. Run SECOND, after the design doc.
  - `level-artist` (`DEMO_level-artist.md`) — sprites, the real level, HUD,
    win/lose screens. Run THIRD, after the engine is playable.
  - `playtester` (`DEMO_playtester.md`) — read-only QA vs the Definition of
    Done; reports bugs for you to route back to engine-dev / level-artist.
- **Recommended handoff order (mostly sequential):**
  planner → game-designer → engine-dev → level-artist → playtester → (route
  fixes) → playtester again. engine-dev and level-artist both write `demo-game/`,
  so run them in sequence (each reads the prior agent's finished OUTPUT.md +
  the now-stable `demo-game/` files) rather than in parallel.
- These demo agents are an example. Delete the `DEMO_*` files, `demo-game/`, and
  `DEMO_GAME_BRIEF.md` to get back to the clean template.
