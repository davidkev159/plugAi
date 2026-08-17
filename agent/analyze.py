"""
Pattern analysis over the full pass1 dataset.

Produces output/analysis.json: the aggregated findings the HTML deliverable's
headline/patterns section is built from. Deliberately kept separate from the
raw per-app records so the "insight over raw table" step is a distinct,
inspectable artifact.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


def load(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    apps = load("output/pass1.jsonl")
    apps.sort(key=lambda a: a["num"])
    n = len(apps)

    # --- Auth method distribution ---
    auth_counter = Counter()
    for a in apps:
        for m in a["auth_methods"]:
            auth_counter[m] += 1

    # --- Access tier distribution overall and by category ---
    tier_counter = Counter(a["access_tier"] for a in apps)
    cat_tier = defaultdict(lambda: Counter())
    categories = []
    for a in apps:
        if a["category"] not in categories:
            categories.append(a["category"])
        cat_tier[a["category"]][a["access_tier"]] += 1

    SELF_SERVE = {"Self-serve, free", "Self-serve, free trial"}
    GATED = {"Requires paid plan", "Requires admin/org approval", "Partnership / contact-sales gated"}

    cat_summary = []
    for cat in categories:
        counts = cat_tier[cat]
        total = sum(counts.values())
        self_serve = sum(v for k, v in counts.items() if k in SELF_SERVE)
        gated = sum(v for k, v in counts.items() if k in GATED)
        unknown = total - self_serve - gated
        cat_summary.append(
            {
                "category": cat,
                "total": total,
                "self_serve": self_serve,
                "gated": gated,
                "unknown_or_unclear": unknown,
                "self_serve_pct": round(100 * self_serve / total, 1),
            }
        )

    # --- Buildability verdict distribution ---
    verdict_counter = Counter(a["buildability_verdict"] for a in apps)

    # --- MCP adoption ---
    mcp_apps = [a["app"] for a in apps if a["existing_mcp"]]

    # --- API surface distribution ---
    surface_counter = Counter(a["api_surface"] for a in apps)

    # --- Main blockers (non-null), roughly bucketed by keyword ---
    blockers = [a["main_blocker"] for a in apps if a.get("main_blocker")]

    def bucket_blocker(text: str) -> str:
        t = text.lower()
        if "review" in t or "approval" in t or "vet" in t:
            return "App/developer review process"
        if "paid" in t or "plan" in t or "subscription" in t or "$" in t:
            return "Requires paid plan/subscription"
        if "contact" in t or "sales" in t or "partner" in t or "book a call" in t:
            return "Partnership / sales contact required"
        if "admin" in t or "role" in t or "permission" in t:
            return "Internal admin/role restriction"
        if "cli" in t or "not a hosted api" in t or "local" in t:
            return "Not a hosted API (CLI/local tool)"
        if "unclear" in t or "could not" in t or "no primary" in t or "no first-party" in t:
            return "Research gap (no primary docs found)"
        return "Other"

    blocker_buckets = Counter(bucket_blocker(b) for b in blockers)

    # --- Easy wins: buildable today AND self-serve free (the truest "zero friction" set) ---
    easy_wins = sorted(
        [a["app"] for a in apps if a["buildability_verdict"] == "Buildable today" and a["access_tier"] == "Self-serve, free"]
    )

    # --- Needs outreach: contact-sales/partnership gated, or fully blocked ---
    needs_outreach = sorted(
        [
            {"app": a["app"], "category": a["category"], "reason": a["main_blocker"] or a["access_tier"]}
            for a in apps
            if a["access_tier"] == "Partnership / contact-sales gated" or a["buildability_verdict"] == "Blocked: access/credential gate"
        ],
        key=lambda x: x["app"],
    )

    # --- Research gaps (agent got defeated / had to flag unclear) ---
    research_gaps = [
        {"app": a["app"], "num": a["num"], "issue": a["main_blocker"]}
        for a in apps
        if a["buildability_verdict"] == "Blocked: unclear / needs human research"
    ]

    # --- Average confidence, and lowest-confidence apps (candidates for further review) ---
    avg_confidence = round(sum(a["confidence"] for a in apps) / n, 3)
    lowest_confidence = sorted(apps, key=lambda a: a["confidence"])[:8]
    lowest_confidence_list = [{"app": a["app"], "num": a["num"], "confidence": a["confidence"]} for a in lowest_confidence]

    analysis = {
        "n_apps": n,
        "auth_method_distribution": dict(auth_counter.most_common()),
        "access_tier_distribution": dict(tier_counter.most_common()),
        "self_serve_vs_gated_overall": {
            "self_serve": sum(v for k, v in tier_counter.items() if k in SELF_SERVE),
            "gated": sum(v for k, v in tier_counter.items() if k in GATED),
            "unknown_or_unclear": sum(v for k, v in tier_counter.items() if k not in SELF_SERVE and k not in GATED),
        },
        "category_breakdown": cat_summary,
        "buildability_verdict_distribution": dict(verdict_counter.most_common()),
        "api_surface_distribution": dict(surface_counter.most_common()),
        "mcp_adoption": {"count": len(mcp_apps), "pct": round(100 * len(mcp_apps) / n, 1), "apps": sorted(mcp_apps)},
        "main_blocker_buckets": dict(blocker_buckets.most_common()),
        "easy_wins": easy_wins,
        "needs_outreach": needs_outreach,
        "research_gaps": research_gaps,
        "avg_confidence": avg_confidence,
        "lowest_confidence_apps": lowest_confidence_list,
    }

    Path("output/analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
