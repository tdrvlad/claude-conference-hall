"""Conference Hall — feed service.

A tiny SQLite-backed HTTP service that stores feed `items`, partitioned by
`channel` (one channel per actor: "manager", or a subagent's name). The server
serializes all writes, so many actors can post concurrently without clobbering
a shared file.

Run:  python server.py     (or ./run.sh)
Env:  FEED_PORT (default 8787), FEED_DB (default conference_hall.db)
"""

import os
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = os.environ.get("FEED_DB", str(Path(__file__).parent / "conference_hall.db"))
STATIC_DIR = Path(__file__).parent / "static"

# Types that auto-pin to the top of their channel unless `pinned` is given.
AUTO_PIN_TYPES = {"decision", "todo"}


def init_db() -> None:
    with db() as cx:
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id       TEXT PRIMARY KEY,
                channel  TEXT NOT NULL,
                type     TEXT NOT NULL,
                html     TEXT NOT NULL,
                pinned   INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0,
                created  REAL NOT NULL
            )
            """
        )
        cx.execute(
            "CREATE INDEX IF NOT EXISTS idx_items_channel "
            "ON items (channel, archived, created)"
        )


@contextmanager
def db():
    """A short-lived connection per request — safe across FastAPI's threadpool."""
    cx = sqlite3.connect(DB_PATH)
    cx.row_factory = sqlite3.Row
    try:
        yield cx
        cx.commit()
    finally:
        cx.close()


def row_to_item(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "channel": row["channel"],
        "type": row["type"],
        "html": row["html"],
        "pinned": bool(row["pinned"]),
        "archived": bool(row["archived"]),
        "created": row["created"],
    }


# ---- request bodies -------------------------------------------------------

class NewItem(BaseModel):
    channel: str
    html: str
    type: str = "note"
    pinned: Optional[bool] = None  # None => auto-decide from type


class PatchItem(BaseModel):
    html: Optional[str] = None
    type: Optional[str] = None
    pinned: Optional[bool] = None


# ---- app ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Conference Hall feed", lifespan=lifespan)


@app.post("/items")
def create_item(body: NewItem) -> dict:
    if body.pinned is None:
        pinned = body.type in AUTO_PIN_TYPES
    else:
        pinned = body.pinned
    item_id = "it_" + uuid.uuid4().hex[:12]
    created = time.time()
    with db() as cx:
        cx.execute(
            "INSERT INTO items (id, channel, type, html, pinned, archived, created) "
            "VALUES (?, ?, ?, ?, ?, 0, ?)",
            (item_id, body.channel, body.type, body.html, int(pinned), created),
        )
    return {"id": item_id, "channel": body.channel, "type": body.type, "pinned": pinned}


@app.get("/items")
def list_items(channel: Optional[str] = None, include_archived: bool = False) -> list:
    clauses = []
    params: list = []
    if not include_archived:
        clauses.append("archived = 0")
    if channel is not None:
        clauses.append("channel = ?")
        params.append(channel)
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with db() as cx:
        rows = cx.execute(
            f"SELECT * FROM items {where} ORDER BY pinned DESC, created DESC",
            params,
        ).fetchall()
    return [row_to_item(r) for r in rows]


@app.get("/channels")
def list_channels() -> list:
    with db() as cx:
        rows = cx.execute(
            """
            SELECT channel,
                   COUNT(*) AS n,
                   SUM(CASE WHEN type = 'decision' THEN 1 ELSE 0 END) AS decisions
            FROM items
            WHERE archived = 0
            GROUP BY channel
            ORDER BY channel
            """
        ).fetchall()
    return [
        {"channel": r["channel"], "n": r["n"], "decisions": r["decisions"] or 0}
        for r in rows
    ]


@app.patch("/items/{item_id}")
def patch_item(item_id: str, body: PatchItem) -> dict:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="empty patch")
    sets = ", ".join(f"{k} = ?" for k in fields)
    values = [int(v) if k == "pinned" else v for k, v in fields.items()]
    with db() as cx:
        cur = cx.execute(
            f"UPDATE items SET {sets} WHERE id = ?", [*values, item_id]
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="no such item")
        row = cx.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return row_to_item(row)


@app.delete("/items/{item_id}")
def delete_item(item_id: str) -> dict:
    with db() as cx:
        cur = cx.execute("DELETE FROM items WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="no such item")
    return {"deleted": item_id}


@app.post("/items/{item_id}/archive")
def archive_item(item_id: str) -> dict:
    with db() as cx:
        cur = cx.execute(
            "UPDATE items SET archived = 1 WHERE id = ?", (item_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="no such item")
    return {"archived": item_id}


@app.post("/channels/{channel}/clear")
def clear_channel(channel: str) -> dict:
    with db() as cx:
        cur = cx.execute(
            "UPDATE items SET archived = 1 WHERE channel = ? AND archived = 0",
            (channel,),
        )
    return {"channel": channel, "archived": cur.rowcount}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("FEED_PORT", "8787"))
    uvicorn.run(app, host="127.0.0.1", port=port)
