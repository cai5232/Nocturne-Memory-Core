from pathlib import Path

import server


def test_nearfield_dashboard_is_wired():
    html = Path(server.__file__).with_name("dashboard.html").read_text(encoding="utf-8")
    assert 'data-tab="nearfield"' in html
    assert 'id="nearfield-view"' in html
    assert "loadNearfieldList" in html
    assert "assembleNearfieldRolling" in html
    assert "not full lived memory" not in html
    assert "proof of lived experience" not in html


def test_nearfield_storage_and_rolling(monkeypatch, tmp_path):
    monkeypatch.setenv("NOCTURNE_NEARFIELD_DIR", str(tmp_path / "nearfield"))

    first = server._nearfield_write_day("2026-08-10", "# 2026-08-10\n\nFirst day.")
    second = server._nearfield_write_day("2026-08-11", "# 2026-08-11\n\nSecond day.")

    assert first["date"] == "2026-08-10"
    assert second["date"] == "2026-08-11"
    assert [row["date"] for row in server._nearfield_list_days()] == ["2026-08-11", "2026-08-10"]
    assert "Second day." in server._nearfield_read_day("2026-08-11")

    rolling = server._nearfield_assemble()
    assert rolling.startswith("# Nearfield\n")
    assert "## Today · 2026-08-11" in rolling
    assert "## Yesterday · 2026-08-10" in rolling
    assert "Second day." in rolling
    assert "First day." in rolling


def test_public_hook_has_only_nearfield_heading():
    hook = Path(server.__file__).with_name("hooks") / "nocturne_nearfield.py"
    text = hook.read_text(encoding="utf-8")
    assert 'return "Nearfield\\n" + text' in text
    assert "not full lived memory" not in text
    assert "verify against history" not in text
