"""Load the 100-app research set from data/apps.csv."""

from __future__ import annotations

import csv
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "apps.csv"


def load_apps(path: Path = DATA_PATH) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            {"num": int(row["num"]), "category": row["category"], "app": row["app"], "hint": row["hint"]}
            for row in reader
        ]


def by_num(apps: list[dict], nums: list[int]) -> list[dict]:
    wanted = set(nums)
    return [a for a in apps if a["num"] in wanted]
