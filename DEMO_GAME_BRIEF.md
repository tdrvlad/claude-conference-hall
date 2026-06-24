# DEMO_GAME_BRIEF — "Plumber Dash", a simple Mario-like platformer

The concrete target the game-building agents work toward. Keep it small and
finishable. The manager hands the relevant slices of this brief to each agent.

## Tech (decided — don't re-litigate)

- **HTML5 Canvas + vanilla JavaScript. No build step, no framework, no npm.**
  The game must run by opening `demo-game/index.html` in a browser (or serving the
  `demo-game/` folder statically).
- All code lives in **`demo-game/`**:
  ```
  demo-game/
    index.html        canvas + script tags
    js/engine.js      loop, input, physics, collision, camera
    js/sprites.js     programmatic sprite drawing (no image files)
    js/level.js       tile map data + entities (coins, enemies, goal)
    js/main.js        wires it together, HUD, win/lose/restart
    style.css         minimal page styling
  ```
- **No external art assets.** Sprites are drawn programmatically on the canvas
  (colored shapes / simple pixel blocks). This keeps it self-contained.

## The game

A single side-scrolling level. The player is a little plumber.

**Controls**
- Left / Right: `←`/`→` or `A`/`D` — run.
- Jump: `Space` or `↑` — variable height (hold = higher, to a cap).
- `R` — restart after win/lose.

**Player physics**
- Gravity pulls down each frame; jumping sets an upward velocity.
- Runs with acceleration + friction (not instant max speed).
- AABB collision against solid tiles: lands on top, blocked by sides, bonks head.

**World**
- Tile-based level (tile size 32px). Tiles: empty, ground/brick (solid).
- A camera that scrolls horizontally to follow the player.
- Level is wider than the screen.

**Entities**
- **Coins** — collect on touch, `+1` score, play a tiny flash. (≥ 8 in the level.)
- **Goombas** — one enemy type, walks back and forth on platforms. Stomp from
  above to defeat it (`+score`, small bounce); touch it from the side and you
  lose a life and respawn at the last safe spot (or level start).
- **Goal flag** — touching it at the end wins the level.

**Rules / HUD**
- 3 lives. Falling into a pit (below the level) costs a life.
- HUD shows score and lives, top-left.
- Win screen on reaching the flag; game-over screen at 0 lives. `R` restarts.

## Tunable constants (the designer owns the exact numbers)

`GRAVITY`, `MOVE_ACCEL`, `MAX_RUN_SPEED`, `FRICTION`, `JUMP_VELOCITY`,
`JUMP_CUTOFF`, `TILE`, `CANVAS_W`, `CANVAS_H`, `GOOMBA_SPEED`. The game-designer
fixes these in the design doc so the engine and level agents share one source
of truth.

## Definition of done

Open `demo-game/index.html` → you can run, jump, collect coins, stomp a goomba, die
to one, fall in a pit, lose lives, reach the flag to win, and press `R` to
restart. Runs at a steady frame rate with no console errors.

## Stretch (only if the core is solid)

Sound effects (WebAudio beeps), a second enemy, moving platforms, a title
screen. Do **not** start these until the Definition of Done is met.
