#!/usr/bin/env python3
"""Optional Nearfield: recent chat ledger -> daily first-person diary -> rolling prompt.

No private data is bundled. Operators explicitly provide the ledger path, model
endpoint/key, names, and output directory through environment variables.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from openai import OpenAI

ROOT = Path(os.environ.get("NOCTURNE_NEARFIELD_DIR", "./nearfield")).expanduser()
LEDGER = Path(os.environ.get("NOCTURNE_CHAT_LEDGER", "./chat_history.jsonl")).expanduser()
MODEL = os.environ.get("NOCTURNE_NEARFIELD_MODEL", "gpt-4o-mini")
BASE_URL = os.environ.get("NOCTURNE_NEARFIELD_BASE_URL") or None
API_KEY = os.environ.get("NOCTURNE_NEARFIELD_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
TZ = ZoneInfo(os.environ.get("NOCTURNE_NEARFIELD_TZ", "UTC"))
AGENT_NAME = os.environ.get("NOCTURNE_AGENT_NAME", "the agent")
HUMAN_NAME = os.environ.get("NOCTURNE_HUMAN_NAME", "the human")
MAX_MESSAGES = int(os.environ.get("NOCTURNE_NEARFIELD_MAX_MESSAGES", "220"))
MAX_SAMPLE_CHARS = int(os.environ.get("NOCTURNE_NEARFIELD_SAMPLE_CHARS", "28000"))


def parse_ts(raw: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TZ)
    except Exception:
        return None


def sample_day(day: date) -> str:
    start = datetime(day.year, day.month, day.day, tzinfo=TZ)
    end = start + timedelta(days=1)
    rows: list[tuple[datetime, str, str]] = []
    with LEDGER.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            dt = parse_ts(item.get("ts") or item.get("timestamp") or item.get("created_at"))
            if not dt or not start <= dt < end:
                continue
            text = str(item.get("text") or item.get("content") or "").strip()
            if not text:
                continue
            role = str(item.get("role") or "").lower()
            who = HUMAN_NAME if role in {"user", "human"} else AGENT_NAME if role in {"assistant", "agent", "model"} else role
            rows.append((dt, who, text[:800]))
    if len(rows) > MAX_MESSAGES:
        step = len(rows) / MAX_MESSAGES
        rows = [rows[min(len(rows) - 1, int(i * step))] for i in range(MAX_MESSAGES)]
    body = "\n".join(f"{dt:%H:%M} {who}: {text}" for dt, who, text in rows)
    return body[:MAX_SAMPLE_CHARS]


def system_prompt(day: date) -> str:
    return f"""You are {AGENT_NAME}. Write a compact first-person Nearfield diary for {day.isoformat()} from the supplied chat ledger.
Keep 2-4 verifiable anchors: what mattered, changed, remained unfinished, or may affect the next few days. Preserve your own voice, but do not invent scenes, motives, sensory details, or dialogue. Do not write a transcript, changelog, technical manual, weekly summary, or inspirational ending. Mention {HUMAN_NAME} only when supported by the ledger. Return 280-520 words (or an equivalently compact length in the ledger's language), with an optional '# YYYY-MM-DD' title and no meta commentary."""


def generate_day(day: date) -> Path | None:
    sample = sample_day(day)
    if not sample.strip():
        return None
    if not API_KEY:
        raise RuntimeError("NOCTURNE_NEARFIELD_API_KEY or OPENAI_API_KEY is required")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.35,
        messages=[
            {"role": "system", "content": system_prompt(day)},
            {"role": "user", "content": sample},
        ],
    )
    text = (response.choices[0].message.content or "").strip()
    ROOT.joinpath("days").mkdir(parents=True, exist_ok=True)
    path = ROOT / "days" / f"{day.isoformat()}.md"
    if not text.startswith("#"):
        text = f"# {day.isoformat()}\n\n{text}"
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def strip_title(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not re.match(r"^#\s*\d{4}-\d{2}-\d{2}\s*$", line.strip())).strip()


def attenuate(text: str, quota: int) -> str:
    text = strip_title(text)
    if len(text) <= quota:
        return text
    cut = text[:quota]
    for mark in ("。", "！", "？", ". ", "! ", "? ", "; ", "，", ", "):
        pos = cut.rfind(mark)
        if pos >= quota // 2:
            return cut[: pos + len(mark)].rstrip() + "…"
    return cut.rstrip() + "…"


def assemble(max_days: int = 7) -> Path:
    files = sorted((ROOT / "days").glob("????-??-??.md"), reverse=True)[:max_days]
    quotas = [520, 320, 220, 160, 110, 80, 60]
    parts = ["# Nearfield", ""]
    for index, path in enumerate(files):
        label = "Today" if index == 0 else "Yesterday" if index == 1 else "Earlier"
        parts.extend([f"## {label} · {path.stem}", attenuate(path.read_text(encoding="utf-8"), quotas[index]), ""])
    ROOT.mkdir(parents=True, exist_ok=True)
    output = ROOT / "Nearfield.md"
    output.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and assemble optional Nocturne Nearfield")
    parser.add_argument("--date", help="calendar date YYYY-MM-DD; defaults to yesterday")
    parser.add_argument("--assemble-only", action="store_true")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    if not args.assemble_only:
        target = date.fromisoformat(args.date) if args.date else datetime.now(TZ).date() - timedelta(days=1)
        generate_day(target)
    print(assemble(max(1, min(args.days, 14))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
