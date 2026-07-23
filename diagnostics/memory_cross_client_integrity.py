"""Cross-client memory integrity diagnostics for Hermes Doctor.

Detects multi-agent memory drift without requiring a shared backend:
- hot MEMORY.md still carrying superseded content markers
- memory cards missing protocol fields (clients / status / supersedes / cognitive_type)
- active facts that claim to supersede each other inconsistently
- capacity pressure on MEMORY.md and card directories

Pure read-only diagnosis. Never mutates the profile.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PROTOCOL_FIELDS = ("clients", "status", "supersedes", "cognitive_type")
ACTIVE_STATUSES = frozenset({"active", "current", "hot", "ok", ""})
SUPERSEDED_STATUSES = frozenset({"superseded", "archived", "retired", "stale"})
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


@dataclass
class MemoryFinding:
    code: str
    severity: str
    path: str
    detail: str
    prescription_hint: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class MemoryCard:
    path: str
    fields: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def status(self) -> str:
        return str(self.fields.get("status", "") or "").strip().lower()

    @property
    def clients(self) -> list[str]:
        raw = self.fields.get("clients") or []
        if isinstance(raw, str):
            return [c.strip() for c in raw.split(",") if c.strip()]
        if isinstance(raw, list):
            return [str(c).strip() for c in raw if str(c).strip()]
        return []

    @property
    def supersedes(self) -> list[str]:
        raw = self.fields.get("supersedes") or []
        if isinstance(raw, str):
            return [c.strip() for c in raw.split(",") if c.strip()]
        if isinstance(raw, list):
            return [str(c).strip() for c in raw if str(c).strip()]
        return []

    @property
    def memory_id(self) -> str:
        mid = self.fields.get("id") or self.fields.get("memory_id") or Path(self.path).stem
        return str(mid).strip()


def _parse_scalar(value: str) -> Any:
    text = value.strip()
    if not text:
        return ""
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip().strip("'\"") for p in inner.split(",")]
        return [p for p in parts if p]
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    return text


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    body = text[match.end() :]
    fields: dict[str, Any] = {}
    current_list_key: str | None = None
    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        # list continuation under key
        if current_list_key and re.match(r"^\s+-\s+", line):
            item = re.sub(r"^\s+-\s+", "", line).strip().strip("'\"")
            bucket = fields.setdefault(current_list_key, [])
            if not isinstance(bucket, list):
                bucket = [bucket]
                fields[current_list_key] = bucket
            bucket.append(item)
            continue
        if ":" not in line:
            current_list_key = None
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "" or value == "|" or value == ">":
            fields[key] = []
            current_list_key = key
        else:
            fields[key] = _parse_scalar(value)
            current_list_key = None
    return fields, body


def load_memory_card(path: Path) -> MemoryCard:
    text = path.read_text(encoding="utf-8", errors="ignore")
    fields, body = parse_frontmatter(text)
    return MemoryCard(path=str(path), fields=fields, body=body)


def iter_card_files(cards_dir: Path) -> Iterable[Path]:
    if not cards_dir.is_dir():
        return []
    return sorted(p for p in cards_dir.rglob("*.md") if p.is_file())


def _capacity_findings(memory_md: Path, cards_dir: Path, memory_limit: int) -> list[MemoryFinding]:
    findings: list[MemoryFinding] = []
    if memory_md.is_file():
        size = memory_md.stat().st_size
        if size > memory_limit:
            findings.append(
                MemoryFinding(
                    code="memory_md_over_capacity",
                    severity="high",
                    path=str(memory_md),
                    detail=f"MEMORY.md is {size} bytes (limit {memory_limit})",
                    prescription_hint="RX-MEM-001",
                )
            )
        elif size > int(memory_limit * 0.8):
            findings.append(
                MemoryFinding(
                    code="memory_md_near_capacity",
                    severity="medium",
                    path=str(memory_md),
                    detail=f"MEMORY.md is {size} bytes (80% of limit {memory_limit})",
                    prescription_hint="RX-MEM-001",
                )
            )
        text = memory_md.read_text(encoding="utf-8", errors="ignore").lower()
        if "superseded" in text or "已替代" in text or "已过期" in text:
            findings.append(
                MemoryFinding(
                    code="superseded_still_hot",
                    severity="high",
                    path=str(memory_md),
                    detail="Hot MEMORY.md still contains superseded/expired markers",
                    prescription_hint="RX-MEM-003",
                )
            )
    if cards_dir.is_dir():
        count = sum(1 for _ in cards_dir.rglob("*.md"))
        if count > 200:
            findings.append(
                MemoryFinding(
                    code="card_directory_bloat",
                    severity="medium",
                    path=str(cards_dir),
                    detail=f"cards directory has {count} markdown files",
                    prescription_hint="RX-MEM-001",
                )
            )
    return findings


def _protocol_findings(cards: Sequence[MemoryCard]) -> list[MemoryFinding]:
    findings: list[MemoryFinding] = []
    by_id: dict[str, MemoryCard] = {}
    for card in cards:
        by_id[card.memory_id] = card
        missing = [f for f in PROTOCOL_FIELDS if f not in card.fields]
        if missing:
            findings.append(
                MemoryFinding(
                    code="missing_protocol_fields",
                    severity="medium",
                    path=card.path,
                    detail=f"missing fields: {', '.join(missing)}",
                    prescription_hint="RX-MEM-004",
                )
            )
        if not card.clients and "clients" in card.fields:
            findings.append(
                MemoryFinding(
                    code="empty_clients",
                    severity="low",
                    path=card.path,
                    detail="clients field present but empty — multi-agent ownership unknown",
                    prescription_hint="RX-MEM-004",
                )
            )
        status = card.status
        if status and status not in ACTIVE_STATUSES | SUPERSEDED_STATUSES:
            findings.append(
                MemoryFinding(
                    code="unknown_status",
                    severity="low",
                    path=card.path,
                    detail=f"unrecognized status={status!r}",
                    prescription_hint="RX-MEM-004",
                )
            )
        if status in SUPERSEDED_STATUSES and not card.supersedes and not card.fields.get("superseded_by"):
            # superseded without lineage is fine; hot-loading superseded is the problem handled elsewhere
            pass

    # supersedes chain integrity
    for card in cards:
        for target in card.supersedes:
            target_id = Path(str(target)).stem
            other = by_id.get(target_id) or by_id.get(str(target))
            if other is None:
                findings.append(
                    MemoryFinding(
                        code="dangling_supersedes",
                        severity="medium",
                        path=card.path,
                        detail=f"supersedes unknown id/path: {target}",
                        prescription_hint="RX-MEM-003",
                    )
                )
                continue
            if other.status in ACTIVE_STATUSES and card.status in ACTIVE_STATUSES:
                findings.append(
                    MemoryFinding(
                        code="active_supersedes_active",
                        severity="high",
                        path=card.path,
                        detail=f"active card supersedes another active card {other.memory_id}",
                        prescription_hint="RX-MEM-003",
                    )
                )
            if other.status in ACTIVE_STATUSES and card.status in SUPERSEDED_STATUSES:
                findings.append(
                    MemoryFinding(
                        code="supersession_inverted",
                        severity="high",
                        path=card.path,
                        detail=f"superseded card claims to supersede still-active {other.memory_id}",
                        prescription_hint="RX-MEM-003",
                    )
                )
    return findings


def _client_coverage_findings(cards: Sequence[MemoryCard], expected_clients: Sequence[str] | None) -> list[MemoryFinding]:
    if not expected_clients:
        return []
    findings: list[MemoryFinding] = []
    seen: set[str] = set()
    for card in cards:
        if card.status in SUPERSEDED_STATUSES:
            continue
        for c in card.clients:
            seen.add(c.lower())
    missing = [c for c in expected_clients if c.lower() not in seen]
    if missing and cards:
        findings.append(
            MemoryFinding(
                code="client_coverage_gap",
                severity="medium",
                path="cards/",
                detail=f"no active card references clients: {', '.join(missing)}",
                prescription_hint="RX-MEM-005",
            )
        )
    return findings


def diagnose_memory_integrity(
    profile_root: str | Path,
    *,
    memory_limit: int = 2200,
    expected_clients: Sequence[str] | None = None,
    cards_subdir: str = "memories/cards",
) -> dict[str, Any]:
    """Run read-only integrity checks against a Hermes profile root."""
    root = Path(profile_root)
    memory_md = root / "MEMORY.md"
    cards_dir = root / cards_subdir
    if not cards_dir.is_dir():
        # common alternate layouts
        for alt in ("memory/cards", "cards", "memories"):
            candidate = root / alt
            if candidate.is_dir():
                cards_dir = candidate
                break

    cards = [load_memory_card(p) for p in iter_card_files(cards_dir)]
    findings = []
    findings.extend(_capacity_findings(memory_md, cards_dir, memory_limit))
    findings.extend(_protocol_findings(cards))
    findings.extend(_client_coverage_findings(cards, expected_clients))

    high = sum(1 for f in findings if f.severity == "high")
    medium = sum(1 for f in findings if f.severity == "medium")
    return {
        "ok": high == 0,
        "profile_root": str(root),
        "memory_md": str(memory_md) if memory_md.exists() else None,
        "cards_dir": str(cards_dir) if cards_dir.exists() else None,
        "card_count": len(cards),
        "finding_counts": {"high": high, "medium": medium, "low": len(findings) - high - medium, "total": len(findings)},
        "findings": [f.to_dict() for f in findings],
        "protocol_fields": list(PROTOCOL_FIELDS),
    }


def summarize_findings(payload: Mapping[str, Any]) -> str:
    counts = payload.get("finding_counts") or {}
    lines = [
        f"memory integrity ok={payload.get('ok')} cards={payload.get('card_count')} "
        f"high={counts.get('high', 0)} medium={counts.get('medium', 0)} low={counts.get('low', 0)}"
    ]
    for item in payload.get("findings") or []:
        lines.append(f"- [{item.get('severity')}] {item.get('code')}: {item.get('detail')} ({item.get('path')})")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(description="Diagnose cross-client memory integrity")
    parser.add_argument("profile_root", nargs="?", default=str(Path.home() / ".hermes"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=2200)
    parser.add_argument("--clients", default="", help="comma-separated expected clients")
    args = parser.parse_args()
    clients = [c.strip() for c in args.clients.split(",") if c.strip()] or None
    result = diagnose_memory_integrity(args.profile_root, memory_limit=args.limit, expected_clients=clients)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(summarize_findings(result))
    sys.exit(0 if result["ok"] else 1)
