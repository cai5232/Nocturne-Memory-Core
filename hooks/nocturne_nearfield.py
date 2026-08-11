#!/usr/bin/env python3
"""UserPromptSubmit hook: inject Nearfield once per session.

Claude Code-compatible JSON hook output. Other hosts can import build_block().
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

NEARFIELD_PATH = Path(os.environ.get("NOCTURNE_NEARFIELD_PATH", "./nearfield/Nearfield.md")).expanduser()
STICKY_PATH = Path(os.environ.get("NOCTURNE_NEARFIELD_STICKY", "~/.nocturne/nearfield_sessions.json")).expanduser()
MAX_CHARS = int(os.environ.get("NOCTURNE_NEARFIELD_MAX_CHARS", "1800"))
STICKY_MAX_AGE = float(os.environ.get("NOCTURNE_NEARFIELD_STICKY_AGE", str(36 * 3600)))


def session_key(payload: dict) -> str:
    for key in ("sessionId", "session_id", "session", "cwd"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())[:180]
    return "default"


def load_sticky() -> dict:
    try:
        value = json.loads(STICKY_PATH.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_block(payload: dict, force: bool = False) -> str:
    try:
        text = NEARFIELD_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not text:
        return ""
    key = session_key(payload)
    sticky = load_sticky()
    now = time.time()
    row = sticky.get(key)
    if not force and isinstance(row, dict) and now - float(row.get("ts") or 0) <= STICKY_MAX_AGE:
        return ""
    if not force:
        sticky = {k: v for k, v in sticky.items() if isinstance(v, dict) and now - float(v.get("ts") or 0) <= STICKY_MAX_AGE}
        sticky[key] = {"ts": now, "path": str(NEARFIELD_PATH)}
        STICKY_PATH.parent.mkdir(parents=True, exist_ok=True)
        temp = STICKY_PATH.with_suffix(f".{os.getpid()}.tmp")
        temp.write_text(json.dumps(sticky, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, STICKY_PATH)
    if len(text) > MAX_CHARS:
        text = text[: MAX_CHARS - 1].rstrip() + "…"
    return "Nearfield\n" + text


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        payload = {}
    event = payload.get("hook_event_name") or payload.get("hookEventName") or "UserPromptSubmit"
    if event != "UserPromptSubmit":
        return 0
    block = build_block(payload)
    if block:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": block}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
