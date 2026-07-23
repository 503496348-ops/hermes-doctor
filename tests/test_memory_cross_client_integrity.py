from pathlib import Path

from diagnostics.memory_cross_client_integrity import (
    diagnose_memory_integrity,
    load_memory_card,
    parse_frontmatter,
    summarize_findings,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_parse_frontmatter_list_fields():
    fields, body = parse_frontmatter(
        "---\nstatus: active\nclients:\n  - hermes\n  - codex\nsupersedes: [old-1]\ncognitive_type: preference\n---\nbody here\n"
    )
    assert fields["status"] == "active"
    assert fields["clients"] == ["hermes", "codex"]
    assert fields["supersedes"] == ["old-1"]
    assert "body here" in body


def test_detects_superseded_still_hot_and_active_chain(tmp_path: Path):
    profile = tmp_path / "profile"
    _write(profile / "MEMORY.md", "User prefers X\n# superseded\nold fact still hot\n")
    cards = profile / "memories" / "cards"
    _write(
        cards / "mem-new.md",
        "---\nid: mem-new\nstatus: active\nclients: [hermes]\nsupersedes: [mem-old]\ncognitive_type: fact\n---\nnew\n",
    )
    _write(
        cards / "mem-old.md",
        "---\nid: mem-old\nstatus: active\nclients: [hermes]\nsupersedes: []\ncognitive_type: fact\n---\nold\n",
    )

    payload = diagnose_memory_integrity(profile, memory_limit=50)
    codes = {f["code"] for f in payload["findings"]}
    assert "superseded_still_hot" in codes
    assert "active_supersedes_active" in codes
    assert payload["ok"] is False
    assert "memory integrity ok=False" in summarize_findings(payload)


def test_missing_protocol_fields_and_client_gap(tmp_path: Path):
    profile = tmp_path / "profile"
    _write(profile / "MEMORY.md", "short\n")
    cards = profile / "memories" / "cards"
    _write(cards / "bare.md", "---\ntitle: bare\n---\nno protocol\n")
    _write(
        cards / "owned.md",
        "---\nid: owned\nstatus: active\nclients: [hermes]\nsupersedes: []\ncognitive_type: operational\n---\nok\n",
    )

    payload = diagnose_memory_integrity(profile, expected_clients=["hermes", "codex", "claude"])
    codes = {f["code"] for f in payload["findings"]}
    assert "missing_protocol_fields" in codes
    assert "client_coverage_gap" in codes
    card = load_memory_card(cards / "owned.md")
    assert card.clients == ["hermes"]


def test_healthy_profile_is_ok(tmp_path: Path):
    profile = tmp_path / "profile"
    _write(profile / "MEMORY.md", "compact hot layer\n")
    cards = profile / "memories" / "cards"
    _write(
        cards / "a.md",
        "---\nid: a\nstatus: active\nclients: [hermes, codex]\nsupersedes: []\ncognitive_type: preference\n---\nA\n",
    )
    _write(
        cards / "b.md",
        "---\nid: b\nstatus: superseded\nclients: [hermes]\nsupersedes: []\nsuperseded_by: a\ncognitive_type: preference\n---\nold\n",
    )
    payload = diagnose_memory_integrity(profile, expected_clients=["hermes", "codex"])
    assert payload["ok"] is True
    assert payload["finding_counts"]["high"] == 0
