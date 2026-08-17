"""
Automated cross-check comparison.

Diffs two independent research passes (e.g. pass1.jsonl vs a crosscheck pass that was
told to re-derive everything from primary sources only) field by field. Apps where the
two passes disagree are exactly the ones worth spending human verification time on —
agreement between two independent agent runs is a cheap, automatable proxy for
trustworthiness, not a substitute for the real hand-check.
"""

from __future__ import annotations

import json
from pathlib import Path

COMPARE_FIELDS = [
    "auth_methods",
    "access_tier",
    "api_surface",
    "existing_mcp",
    "buildability_verdict",
]


def _load(path: str) -> dict[int, dict]:
    records = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if "error" in rec:
            continue
        records[rec["num"]] = rec
    return records


def compare_passes(pass_a_path: str, pass_b_path: str, out_path: str) -> dict:
    a = _load(pass_a_path)
    b = _load(pass_b_path)
    shared = sorted(set(a) & set(b))

    rows = []
    agree_count = 0
    field_agree = {field: 0 for field in COMPARE_FIELDS}

    for num in shared:
        ra, rb = a[num], b[num]
        row = {"num": num, "app": ra["app"], "fields": {}}
        row_agrees = True
        for field in COMPARE_FIELDS:
            va, vb = ra.get(field), rb.get(field)
            match = va == vb
            if match:
                field_agree[field] += 1
            else:
                row_agrees = False
            row["fields"][field] = {"pass_a": va, "pass_b": vb, "match": match}
        row["fully_agrees"] = row_agrees
        if row_agrees:
            agree_count += 1
        rows.append(row)

    summary = {
        "n_compared": len(shared),
        "n_fully_agree": agree_count,
        "agreement_rate": round(agree_count / len(shared), 3) if shared else None,
        "field_agreement_rate": {
            field: round(field_agree[field] / len(shared), 3) if shared else None for field in COMPARE_FIELDS
        },
        "disagreements": [r for r in rows if not r["fully_agrees"]],
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
