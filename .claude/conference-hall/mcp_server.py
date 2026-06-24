"""Conference Hall — MCP server.

A thin MCP wrapper over the Conference Hall feed service. It exposes the feed
as first-class tools so the manager and subagents can post to their channels
without shelling out to curl.

IMPORTANT: this is a *proxy*. The feed service (server.py) must already be
running, or every tool will fail with a connection error. Start the service
first (./run.sh or `python server.py`); Claude Code launches this MCP server.

Env: FEED_URL (default http://127.0.0.1:8787)
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

FEED_URL = os.environ.get("FEED_URL", "http://127.0.0.1:8787")

mcp = FastMCP("conference-hall")
client = httpx.Client(base_url=FEED_URL, timeout=10.0)


def _raise_for_feed(resp: httpx.Response) -> None:
    """Surface the feed's error detail to the caller instead of a bare status."""
    if resp.is_error:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise RuntimeError(f"feed returned {resp.status_code}: {detail}")


def _send(method: str, path: str, **kw) -> httpx.Response:
    """Make a request to the feed, turning connection failures into a clear hint."""
    try:
        resp = client.request(method, path, **kw)
    except httpx.RequestError as e:
        raise RuntimeError(
            f"Cannot reach the Conference Hall feed at {FEED_URL} ({e}). "
            "The feed service is probably not running — start it with "
            "`bash .claude/conference-hall/run.sh`, then retry."
        ) from None
    _raise_for_feed(resp)
    return resp


@mcp.tool()
def post_item(channel: str, html: str, type: str = "note", pinned: bool | None = None) -> dict:
    """Post one item to a channel in the Conference Hall feed (the human's live dashboard).

    Use this to surface your work to the human and the manager: decisions you
    need a human to make, results you produced, a TODO you're tracking, status
    updates, handoffs, spawns.

    channel: YOUR OWN actor name. The manager uses "manager"; a subagent uses
        its own agent name. Only ever write to your own channel — never another
        actor's. This is how the feed avoids clobbering.
    html: the item body as arbitrary HTML. Rich content is encouraged and
        renders raw in the UI: <p>, <ul>, <table>, <pre>/<code> for code,
        <svg> for diagrams, Mermaid-as-<pre>, <a> links. Keep it self-contained.
    type: one of "note" (default), "decision", "result", "spawn", "handoff",
        "todo", "status". The UI colour-codes the badge by type.
        - "decision" and "todo" AUTO-PIN to the top of the channel (the human
          sees pending decisions front-and-centre) unless you pass pinned.
        - "decision" = something a human must choose; archive it once resolved.
        - "status" = started / progress / done; "result" = finished output.
    pinned: leave as None to use the auto-pin rule above. Pass True/False to
        force or prevent pinning regardless of type.

    Returns {id, channel, type, pinned}. Keep the id if you'll later update,
    archive, or delete this item (e.g. a TODO block you refresh as you go).
    """
    body: dict = {"channel": channel, "html": html, "type": type}
    if pinned is not None:
        body["pinned"] = pinned
    return _send("POST", "/items", json=body).json()


@mcp.tool()
def list_items(channel: str | None = None, include_archived: bool = False) -> list:
    """Read the current state of the feed. Read before deciding or acting.

    The manager should call this on its own channel (channel="manager") at the
    start of a turn to recover continuity: what decisions are still open, what
    the running TODO says. A subagent rarely needs this.

    channel: omit to read every channel, or pass a channel name to scope it.
    include_archived: False (default) returns only live items; True also returns
        resolved/archived ones.

    Items come back ordered pinned-first, then newest-first. Each item is
    {id, channel, type, html, pinned, archived, created}.
    """
    params: dict = {"include_archived": include_archived}
    if channel is not None:
        params["channel"] = channel
    return _send("GET", "/items", params=params).json()


@mcp.tool()
def list_channels() -> list:
    """List the active channels with their live item counts.

    Returns [{channel, n, decisions}] where n is the live item count and
    decisions is the number of open (live) decisions in that channel. Useful to
    see at a glance which actors have unresolved decisions.
    """
    return _send("GET", "/channels").json()


@mcp.tool()
def update_item(id: str, html: str | None = None, type: str | None = None, pinned: bool | None = None) -> dict:
    """Update an existing item in place. Pass only the fields you want to change.

    The classic use: the manager keeps a single "todo" item and refreshes its
    html as work progresses (update_item(id, html=...)), instead of posting a
    new TODO each time. Also used to unpin a resolved decision (pinned=False).

    At least one of html/type/pinned must be provided. Returns the full updated
    item. Errors if the id does not exist.
    """
    body: dict = {}
    if html is not None:
        body["html"] = html
    if type is not None:
        body["type"] = type
    if pinned is not None:
        body["pinned"] = pinned
    return _send("PATCH", f"/items/{id}", json=body).json()


@mcp.tool()
def archive_item(id: str) -> dict:
    """Archive an item: soft-remove it from the live feed (kept on disk).

    This is the bounding mechanism — Conference Hall is a current-state
    dashboard, not an append-forever log. Use it when a decision is resolved,
    a TODO is finished, or a status no longer matters. Prefer this over delete
    so the history is retained.
    """
    return _send("POST", f"/items/{id}/archive").json()


@mcp.tool()
def delete_item(id: str) -> dict:
    """Hard-delete an item permanently (no history kept).

    Use only to remove a mistake. To resolve something normally, archive_item
    is almost always the right tool instead.
    """
    return _send("DELETE", f"/items/{id}").json()


@mcp.tool()
def clear_channel(channel: str) -> dict:
    """Archive ALL live items in a channel at once — a soft reset of that tab.

    Useful to start a channel clean without losing history. Returns the count
    archived.
    """
    return _send("POST", f"/channels/{channel}/clear").json()


if __name__ == "__main__":
    mcp.run()
