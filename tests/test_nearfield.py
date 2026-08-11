import json
from datetime import date

import nearfield


def test_sample_day_reads_generic_jsonl(monkeypatch, tmp_path):
    ledger = tmp_path / "chat.jsonl"
    ledger.write_text(
        "\n".join([
            json.dumps({"ts": "2026-08-10T01:00:00+00:00", "role": "user", "text": "hello"}),
            json.dumps({"ts": "2026-08-10T02:00:00+00:00", "role": "assistant", "content": "world"}),
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(nearfield, "LEDGER", ledger)
    monkeypatch.setattr(nearfield, "TZ", nearfield.ZoneInfo("UTC"))
    sample = nearfield.sample_day(date(2026, 8, 10))
    assert "hello" in sample
    assert "world" in sample


def test_assemble_attenuates_older_days(monkeypatch, tmp_path):
    root = tmp_path / "nearfield"
    days = root / "days"
    days.mkdir(parents=True)
    for index, day in enumerate(("2026-08-10", "2026-08-09", "2026-08-08")):
        (days / f"{day}.md").write_text(f"# {day}\n\n" + (chr(65 + index) * 800), encoding="utf-8")
    monkeypatch.setattr(nearfield, "ROOT", root)
    output = nearfield.assemble()
    text = output.read_text(encoding="utf-8")
    sections = text.split("## ")[1:]
    assert len(sections) == 3
    assert len(sections[0]) > len(sections[1]) > len(sections[2])
