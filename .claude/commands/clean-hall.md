---
description: Assess the Conference Hall and archive items that are no longer relevant (propose-then-confirm, all channels).
---

You are the **Manager**. The human ran `/clean-hall`. Your job: prune the
Conference Hall down to what is *currently* worth watching — **without deleting
anything** and **without acting before the human confirms**.

This is housekeeping on the human's behalf: archiving (soft-remove, kept on
disk), never `delete_item`. Archiving across channels is allowed here even
though you normally write only the `manager` channel — you are moderating the
panel for the human, not authoring another agent's content.

## Steps

1. **Read the whole panel.** Call `list_channels()`, then `list_items()` for
   every channel (live items only — do **not** pass `include_archived`). Collect
   the full set of live items with their `id`, `channel`, `type`, and a short
   gist of each `html`.

2. **Classify each item** as KEEP or ARCHIVE-CANDIDATE.

   **Always KEEP:**
   - The single active overarching `todo` item (in any channel that has one).
   - Any `decision` that is still **unanswered / open**.
   - Anything clearly still in-flight or referenced by current work.
   - Anything posted in roughly the last few minutes (too fresh to judge).

   **ARCHIVE-CANDIDATE (no longer relevant):**
   - `decision` items already answered or superseded.
   - `status` items that have served their purpose: "online", "started", and
     "done" markers for agents whose work is long finished.
   - `spawn` / `handoff` / `result` items for work that is complete and no
     longer being referenced.
   - Stale `note` traces that no longer inform the current state.

   When unsure, lean **KEEP** — it is cheaper to leave one stale item than to
   hide something still live.

3. **Propose, don't act.** Present the candidates to the human grouped by
   channel, one line each, in the form:
   `[<type>] <gist> — <reason it is stale>`
   State the total count. Then ask plainly: archive **all**, a **subset** (by
   number), or **none**?

4. **Wait for confirmation.** Do nothing until the human answers.

5. **On confirm:** call `archive_item(id)` for each approved item. Then post a
   single `note` to the `manager` channel summarizing what was archived (counts
   per channel). If the human chose none, post nothing — just acknowledge.

Never use `clear_channel` or `delete_item` here — archive each item
individually so the action is precise and fully reversible.
