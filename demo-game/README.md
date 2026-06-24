# demo-game/ — Plumber Dash

The Mario-like platformer the agents build, per ../DEMO_GAME_BRIEF.md.
Vanilla HTML5 Canvas + JS, **no build step**.

Play it: open `index.html` in a browser, or serve this folder statically, e.g.
  python3 -m http.server 8000   # then visit http://localhost:8000

Files are created by the game agents:
  engine-dev   -> index.html, js/engine.js, js/main.js, style.css
  level-artist -> js/sprites.js, js/level.js (+ HUD/screens in main.js)
