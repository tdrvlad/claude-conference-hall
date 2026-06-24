# CLAUDE-SETUP-BIBLE

The architecture, principles, and design rules for our manager/subagent
orchestration setup. This is the reference we use when creating agents for any
project. Read it once to understand *why* the pieces are shaped the way they
are; consult the checklists when authoring a new agent.

---

## 1. The mental model

One Claude Code session is the **Manager**. It talks to the human in real time,
decides what needs doing, and **delegates everything** to **subagents**. It
never implements work itself. A small local service — the **Conference Hall** —
is the shared activity log and the human's live control panel: every actor
writes to its own channel, and the human watches it in a browser beside the
terminal.

Three actors, three roles:

- **Human** — gives direction in the terminal, answers decisions, watches the
  Conference Hall.
- **Manager** — converses, routes, delegates to background subagents, logs to
  its channel, maintains the overarching TODO and the decision queue.
- **Subagents** — isolated workers. Each runs in its own context, does one
  scoped job, writes a result, and dies.

The whole design exists to satisfy four constraints at once:

1. **The human can always talk to the Manager** (work happens in the
   background, never blocking the conversation).
2. **State persists across sessions and across simultaneous agents** without
   files clobbering each other.
3. **State stays bounded** — it never grows without limit.
4. **The human has full, rich visibility** into what every agent is doing.

Everything below is downstream of those four constraints.

---

## 2. Why the pieces are shaped this way (the reasoning)

Understanding the rationale prevents you from "simplifying" the design into its
failure modes later.

### 2.1 Why the Manager only delegates

A long single session accumulates everything — file reads, tool output, dead
ends — until attention degrades and quality drops. Delegating heavy work to
subagents keeps the Manager's context lean and its judgment sharp. The Manager
holds the conversation and the plan; the subagents hold the mess.

### 2.2 Why subagents run in the background

A **foreground** subagent blocks the conversation until it finishes. A
**background** subagent runs concurrently while the human keeps talking. Since
constraint #1 is "the human can always talk to the Manager," background is the
default. Foreground is reserved for the rare case where a fast result is needed
before the Manager can even reply.

> **The background caveat.** Background subagents run with permissions already
> granted in the session and **auto-deny** anything that would otherwise prompt
> — they silently skip that one tool call and continue. So every agent's tools
> must be pre-scoped to exactly what it needs; if a background agent comes back
> thin, a permission prompt was probably skipped. Re-run in foreground to see
> the prompt, or widen the tool grant.

### 2.3 Why subagents never talk to each other

A subagent's lifecycle is: spawn → read context once → work → return → **die**.
There is no "later" in which it notices a message. Real-time peer messaging
would require both agents alive and polling at the same time — which subagents
are not. So peer messaging is impossible *by construction* with subagents.

The consequence: **the Manager is the only router.** When a subagent needs
something another agent knows, it states that need in its return summary; the
Manager reads it and spawns the other agent. This isn't a limitation to work
around — it's what keeps all routing decisions in one inspectable place (the
Conference Hall). (If you ever truly need agents talking mid-run, that is what
Claude Code's experimental **Agent Teams** is for — but reach for it only when
manager-relayed handoffs are demonstrably the bottleneck.)

### 2.4 Why "one writer per channel / workspace"

Multiple actors writing the same file is last-write-wins with no locking — a
clobbering race. We eliminate the race instead of managing it: **every file and
every channel has exactly one writer.** The Manager owns the `manager` channel;
each subagent owns its own channel and its own workspace folder. Nobody edits
anyone else's. The Conference Hall service serializes concurrent writes to
*different* channels safely because they never touch the same rows.

### 2.5 Why handoffs read OUTPUT.md, never live files

A subagent reads another agent's work only through that agent's **finished
`OUTPUT.md`** — never its live worklog or scratchpad. A finished OUTPUT.md is a
*stable* artifact: the writer is already dead, so there's no read-during-write
race. Reading a live file risks reading half-written state. Stable inputs only.

### 2.6 Why the Conference Hall is a service, not a file

We considered a hand-edited HTML file. It works for a single writer but fights
every other constraint: concurrent agents clobber it, rich content (tables,
diagrams) is awkward to splice, and "clear this item" means fragile string
surgery. A tiny CRUD service makes all of these first-class operations
(`append`, `read`, `archive`, `delete`) and serializes concurrent writes. The
complexity didn't vanish — it moved from "Claude carefully editing files" to "a
dumb service," which is where it belongs.

### 2.7 Why archiving keeps state bounded

The Conference Hall is a **current-state dashboard**, not an append-forever
log. Resolved decisions and stale items are **archived** — soft-removed from
the live feed, kept on disk. So the live view reflects *now* and stays small,
while history survives if you ever want it (`include_archived=true`). No
rotation logic, no unbounded growth. Archiving *is* the bounding mechanism.

---

## 3. The components

### 3.1 The Manager (`CLAUDE.md` at repo root)

Loads every session. Its responsibilities:

- **Session start:** ensure the Conference Hall service is running (health-check;
  start it if down), then tell the human the URL.
- **Each turn:** read its own channel for continuity (open decisions, current
  TODO, recent activity), then decide: answer directly or delegate.
- **Delegate** heavy/long work as background subagents with a precise task
  prompt (goal + exact inputs + reminder to fill OUTPUT.md and surface needs).
- **Route** cross-agent needs: read a subagent's returned need, spawn the agent
  that can satisfy it, feed the answer onward. Log every step.
- **Maintain** in its channel: one overarching `todo` item (updated in place),
  `decision` items for human choices (pinned; archived once answered), and
  `spawn`/`handoff`/`result` items tracing the flow.

### 3.2 Subagents (`.claude/agents/*.md`)

Each is a single markdown file: YAML frontmatter (config) + body (system
prompt). It runs in an isolated context with its own tools and permissions, and
returns only its result to the Manager. See §4 for how to design one.

### 3.3 Workspaces (`.claude/workspaces/<agent>/`)

One folder per subagent, sole-writer. Created by the agent on first run.

- `worklog.md` — running notes; the agent reads this first for continuity
  across its own past runs (this is what makes an otherwise-stateless subagent
  effectively stateful: the folder is its memory).
- `OUTPUT.md` — the canonical, distilled result; the **only** file other agents
  and the Manager read for handoffs.

### 3.4 The Conference Hall (`.claude/conference-hall/`)

A local feed service (SQLite + HTTP) plus an MCP server wrapping its
operations. Item shape:

```
{ id, channel, type, html, pinned, archived, created }
```

- **channel** — who wrote it: `manager` or an agent name. One writer each.
- **type** — `decision` | `todo` | `spawn` | `handoff` | `result` | `status` |
  `note`. `decision` and `todo` auto-pin to the top of their channel.
- **html** — arbitrary rich content: tables, `<pre>` (code, Mermaid), `<svg>`,
  links. Rendered raw (trusted local content).
- **pinned / archived** — pinned floats to top; archived leaves the live feed.

The UI is tabbed: one tab per channel + an "All" tab, decisions pinned, live
counts per tab. Actors talk to it via the `conference-hall` MCP tools
(`post_item`, `list_items`, `list_channels`, `update_item`, `archive_item`,
`delete_item`, `clear_channel`).

### 3.5 The SubagentStop hook (`.claude/hooks/subagent_stop.py`)

Fires when any subagent finishes; posts a `status` "done" item to that agent's
channel so the UI shows live/done without polling. Fail-silent — never blocks
an agent if the service is down.

---

## 4. How to design an agent

This is the part you'll use most. An agent is defined by its frontmatter
(config) and its body (system prompt). Get three things right and the agent is
predictable: the **description** constrains the Manager *into* the agent; the
**output format** constrains the agent into *stopping*; the **tools** constrain
what it can break.

### 4.1 Frontmatter fields

| Field | Purpose | Rule of thumb |
|---|---|---|
| `name` | Identity + how the Manager invokes it | Lowercase, hyphenated, **unique across the whole `.claude/` tree** (folders don't namespace). |
| `description` | When to delegate + shapes the Manager's task prompt | The highest-leverage field. See §4.2. |
| `tools` | Capabilities | Least privilege. Omitting = inherits ALL parent tools (avoid). See §4.3. |
| `model` | Cost/capability routing | `haiku` cheap research, `sonnet` implementation, `opus` hard reasoning. Omit to inherit. |
| `color` | Visual tag in the `/agents` panel | Set by role family. One of: red, blue, green, yellow, purple, orange, pink, cyan. |
| `skills` | Preloaded expertise | Full skill content injected at startup. Use for knowledge the agent *always* needs; let occasional knowledge be discovered. |
| `isolation: worktree` | Per-invocation git worktree | Add for code writers that may run in parallel, so they never collide on files. Skip for read-only agents. |
| `background: true` | Always run concurrently | Usually leave unset; let the Manager decide per task. |

### 4.2 Writing the `description` (the lever)

The description does two jobs: it tells the Manager *when* to delegate, and it
**shapes the task prompt the Manager writes**. Pack in three things:

1. **Trigger** — when to use this agent ("Use after a spec exists…", "Use to
   investigate how X works…").
2. **Input contract** — what the Manager MUST provide. This is the lever:
   phrases like *"Must be told the exact files to review"* or *"Must be given
   the spec and the path to the upstream research OUTPUT.md"* force the Manager
   to write a specific prompt instead of a vague one.
3. **Return contract** — what it produces and where ("Returns a citable
   findings report at its workspace OUTPUT.md").

> Bad: `Reviews code.`
> Good: `Read-only code review of a specified diff. Must be told exactly which
> files or commit range to review. Returns issues grouped by severity in
> OUTPUT.md; never modifies files.`

### 4.3 Scoping `tools` (least privilege)

Match tools to the job — both to prevent accidents and to make each agent's
role legible:

- **Research / read-only** → `Read, Glob, Grep`. Physically cannot mutate.
- **Reviewer** (needs to see diffs) → add `Bash` for `git diff`, but **not**
  `Edit`/`Write`.
- **Code writer** → `Read, Glob, Grep, Edit, Write, Bash` + `isolation: worktree`.

### 4.4 The body (system prompt) — four required moves

1. **Role + mortality.** One line on who it is, plus: *it runs in its own
   context and dies when it finishes — read everything you need at the start,
   emit everything by the end.* This single framing prevents the "I'll do it
   later" failure.
2. **Conference Hall channel.** State its channel = its `name`. It posts a
   `status` item on start and a `result` item on finish; skip silently if the
   service is unreachable. It writes only its own channel.
3. **Workspace + hard rules** (copy verbatim into every agent):
   - Read only stable inputs — own workspace, assigned task, and any upstream
     `OUTPUT.md` the Manager names. Never read another agent's live files.
   - Write only its own workspace and its own channel. Never write `manager`.
   - Never contact other agents. Surface cross-agent needs in the return
     summary: *"To proceed I need X, which the &lt;other&gt; agent should determine."*
4. **Output format** — the natural stopping point. Numbered sections the agent
   fills; completing them all *is* the signal to stop. Keep these four as the
   spine and add domain sections as needed:
   1. **Summary** — what it did, bottom line.
   2. **Result** — the deliverable or path to `OUTPUT.md`.
   3. **Cross-agent needs** — phrased as above, or "none".
   4. **Obstacles encountered** — setup issues, workarounds, flags, dependency
      problems, or "none". (Surfacing these stops the Manager from
      rediscovering the same problems.)

### 4.5 Agent template (copy this)

```yaml
---
name: <lowercase-hyphenated-unique>
description: >
  <Trigger>. Must be told <explicit input contract>. Returns <what + where>.
  <Constraint, e.g. never modifies files>.
tools: <smallest set: Read, Glob, Grep [+ Bash] [+ Edit, Write]>
model: <haiku | sonnet | opus>     # optional
color: <role-family color>          # optional
# skills: [<skill-name>]            # optional, preloaded expertise
# isolation: worktree               # for parallel code writers
---

You are the **<role>** agent. You run in your own context and die when you
finish — read everything you need at the start; emit everything by the end.

## Conference Hall — your channel is **`<name>`**
Post a `status` item when you start and a `result` item (summary + OUTPUT.md
path) when you finish, via the `conference-hall` MCP tools. Skip if unreachable.
Write only your own channel.

## Workspace (sole writer)
`.claude/workspaces/<name>/` — worklog.md (read first), OUTPUT.md (canonical
result others read).

## Rules
- Read only stable inputs: your task, your workspace, and any upstream
  OUTPUT.md the manager names. Never read another agent's live files.
- Write only your workspace and your channel. Never write the manager channel.
- Don't contact other agents. Surface needs in the return summary:
  "To proceed I need X, which the <other> agent should determine."

## Output format (fill every section, then stop)
1. Summary — …
2. Result — … (or path to OUTPUT.md)
3. Cross-agent needs — … or "none"
4. Obstacles encountered — … or "none"
<add domain-specific sections here>
```

---

## 5. Designing a roster for a project

When you start a new project, don't invent agents at random. Derive them from
the work:

1. **Start with the pipeline.** Most software work decomposes into: plan →
   research → implement → review → test. Map each stage to an agent. The three
   starters (`planner`, `research`, `implementer`) cover the front of that
   pipeline; add `reviewer` and `tester` as needed.
2. **One clear job per agent.** Single responsibility. If an agent's description
   needs "and" to cover two unrelated jobs, split it.
3. **Scope tools to the job**, not to convenience. Read-only by default; grant
   write only where the job is to change things.
4. **Pick the model by difficulty**, not by habit — cheap models for search and
   mechanical work, expensive for judgment.
5. **Make handoffs explicit.** The planner's output *is* the Manager's routing
   script: a numbered plan naming which agent does each step and what each
   needs. That closes the loop — planner produces the chain, Manager executes
   it, every step lands in the Conference Hall.
6. **Parallelize only independent work.** Default to sequential. Use parallel
   background agents (each worktree-isolated) only when tasks genuinely don't
   depend on each other. Parallel-by-default is the most common cost pathology.

### Common roster (starting point, extend per project)

| Agent | Job | Tools | Model | Worktree |
|---|---|---|---|---|
| `planner` | Goal → numbered handoff plan | Read, Glob, Grep | opus | no |
| `research` | Read-only investigation → findings | Read, Glob, Grep | haiku | no |
| `implementer` | Write code to a spec | Read, Glob, Grep, Edit, Write, Bash | sonnet | yes |
| `reviewer` | Read-only review → severity-ranked issues | Read, Glob, Grep, Bash | sonnet | no |
| `tester` | Write/run tests → pass-fail report | Read, Glob, Grep, Edit, Write, Bash | sonnet | yes |

---

## 6. Invariants (never violate these)

These are the rules that keep the system coherent. If a change would break one,
the change is wrong.

1. **The Manager never implements work** — it converses and routes.
2. **Default to background subagents** — the human conversation never blocks.
3. **The Manager is the only router** — subagents never talk to each other.
4. **One writer per channel and per workspace** — no shared-file writes.
5. **Handoffs read finished `OUTPUT.md` only** — never another agent's live files.
6. **Cross-agent needs go in the return summary**, in the exact relay phrasing.
7. **Pre-scope every agent's tools** — background agents auto-deny prompts.
8. **The Conference Hall reflects current state** — resolve by archiving, so it
   stays bounded; it is a dashboard, not an append-forever log.
9. **Every agent has: a specific description, a scoped tool set, a defined
   output format** — these three make it predictable.

---

## 7. Quick reference

**Item types** (Conference Hall): `decision` (human must choose, pinned) ·
`todo` (overarching task list, pinned) · `spawn` (subagent dispatched) ·
`handoff` (routing between agents) · `result` (agent finished) · `status`
(start/done/milestone) · `note` (everything else).

**Channels**: `manager` (the main session) + one per agent (= agent name).

**MCP tools**: `post_item` · `list_items` · `list_channels` · `update_item` ·
`archive_item` · `delete_item` · `clear_channel`.

**Agent file locations**: project `.claude/agents/` (this repo) or user
`~/.claude/agents/` (all your projects). Project wins name conflicts. Agents
edited on disk load at **session start** — restart to pick them up.

**The three levers per agent**: `description` constrains the Manager into the
agent · `output format` constrains the agent into stopping · `tools` constrain
what it can break.