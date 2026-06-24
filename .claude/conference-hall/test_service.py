#!/usr/bin/env python3
"""Smoke tests for the Conference Hall feed service.

Run the service first (bash run.sh), then:  python3 test_service.py
Uses only the standard library. Exits non-zero on the first failure.
Tests run against a `__test__*` channel set so they don't disturb real data.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("FEED_URL", "http://127.0.0.1:8787").rstrip("/")
PASS, FAIL = 0, 0


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  \033[32m✓\033[0m {name}")
    else:
        FAIL += 1
        print(f"  \033[31m✗ {name}\033[0m")


def main():
    chan = "__test__"
    # clean slate
    call("POST", f"/channels/{chan}/clear")

    # 1. POST returns an id; item appears in GET
    st, r = call("POST", "/items", {"channel": chan, "html": "<p>hi</p>", "type": "note"})
    check("POST /items returns 200 + id", st == 200 and r and r["id"].startswith("it_"))
    note_id = r["id"]
    st, items = call("GET", f"/items?channel={chan}")
    check("posted item appears in GET /items", any(i["id"] == note_id for i in items))

    # 2. decision auto-pins and sorts first
    st, d = call("POST", "/items", {"channel": chan, "html": "<b>choose</b>", "type": "decision"})
    check("decision comes back pinned", d and d["pinned"] is True)
    st, items = call("GET", f"/items?channel={chan}")
    check("pinned decision sorts first", items and items[0]["type"] == "decision")

    # 3. <table> HTML round-trips intact
    tbl = "<table><tr><th>a</th></tr><tr><td>1</td></tr></table>"
    st, t = call("POST", "/items", {"channel": chan, "html": tbl, "type": "result"})
    st, items = call("GET", f"/items?channel={chan}")
    got = next((i for i in items if i["id"] == t["id"]), None)
    check("<table> HTML round-trips byte-for-byte", got and got["html"] == tbl)

    # 4. /channels reports counts + decisions
    st, chans = call("GET", "/channels")
    row = next((c for c in chans if c["channel"] == chan), None)
    check("/channels has the test channel with n=3", row and row["n"] == 3)
    check("/channels decisions count = 1", row and row["decisions"] == 1)

    # 5. archive removes from live but include_archived shows it
    call("POST", f"/items/{d['id']}/archive")
    st, live = call("GET", f"/items?channel={chan}")
    check("archived item gone from live feed", all(i["id"] != d["id"] for i in live))
    st, allitems = call("GET", f"/items?channel={chan}&include_archived=true")
    check("archived item still in include_archived", any(i["id"] == d["id"] for i in allitems))

    # 6. DELETE removes permanently
    call("DELETE", f"/items/{note_id}")
    st, live = call("GET", f"/items?channel={chan}&include_archived=true")
    check("deleted item is gone permanently", all(i["id"] != note_id for i in live))

    # 7. clear_channel archives all live items
    call("POST", f"/channels/{chan}/clear")
    st, live = call("GET", f"/items?channel={chan}")
    check("clear_channel empties the live feed", live == [])

    # 8. error cases
    st, _ = call("PATCH", f"/items/{t['id']}", {})
    check("empty PATCH -> 400", st == 400)
    st, _ = call("PATCH", "/items/it_nope", {"html": "x"})
    check("PATCH missing id -> 404", st == 404)

    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
