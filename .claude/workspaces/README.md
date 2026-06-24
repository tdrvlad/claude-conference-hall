# Agent workspaces

One folder per subagent, created by the agent on first run. Each folder is
owned by exactly ONE agent — that agent is the sole writer.

  <agent>/
    worklog.md    running notes; the agent reads this first for continuity
    OUTPUT.md     canonical distilled result; the ONLY file other agents and
                  the manager may READ for handoffs

Handoff rule: agents read finished OUTPUT.md files only — never another agent's
live worklog. The manager routes all cross-agent needs.

Live activity is logged to the Conference Hall (one channel per agent), not
here. These files are the durable per-agent record.
