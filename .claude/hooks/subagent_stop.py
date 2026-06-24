#!/usr/bin/env python3
"""SubagentStop hook — post a 'done' status to the finishing agent's channel.

Two ways to learn which channel to post to, tried in order:

1. The hook payload's `subagent_name` / `name` field, if present. (Some setups
   and the test harness pass this directly.)
2. Otherwise, scan the subagent's transcript (`transcript_path`) for the last
   channel it posted to via the conference-hall `post_item` tool, and reuse it.
   This is robust because the real SubagentStop payload usually does NOT carry
   the agent's name — but the agent's own posts reveal its channel.

Fail-silent by contract: any error, or no determinable channel, -> exit 0 with
no output. The authoritative 'done' signal is still the agent's own `result`
post (see _TEMPLATE.md); this hook is a convenience.

Standard library only, so it runs under the system `python3` (no venv needed).
"""
import json
import os
import sys
import urllib.request

FEED_URL = os.environ.get("FEED_URL", "http://127.0.0.1:8787").rstrip("/")


def channel_from_payload(payload: dict):
    name = payload.get("subagent_name") or payload.get("name")
    if name and name != "unknown":
        return name
    return None


def channel_from_transcript(path: str):
    """Last channel this agent posted to via conference-hall post_item."""
    if not path or not os.path.isfile(path):
        return None
    channel = None
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            if "post_item" not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            msg = rec.get("message", rec)
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_use"
                    and "post_item" in str(block.get("name", ""))
                ):
                    ch = (block.get("input") or {}).get("channel")
                    if ch:
                        channel = ch  # keep the latest
    return channel


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    channel = channel_from_payload(payload) or channel_from_transcript(
        payload.get("transcript_path", "")
    )
    if not channel:
        return  # nothing we can attribute this to — stay silent

    body = json.dumps(
        {
            "channel": channel,
            "type": "status",
            "html": "<i>finished</i> (auto-logged by SubagentStop hook)",
        }
    ).encode()
    req = urllib.request.Request(
        f"{FEED_URL}/items",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=3).read()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail-silent, always exit 0
