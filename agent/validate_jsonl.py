"""Validate an output JSONL file against AppResearchRecord. Prints errors, exits nonzero if any."""

from __future__ import annotations

import json
import sys

from pydantic import ValidationError

from agent.schema import AppResearchRecord


def main(path: str) -> None:
    n_ok = 0
    n_err = 0
    seen_nums = set()
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            try:
                rec = AppResearchRecord.model_validate(raw)
                if rec.num in seen_nums:
                    print(f"line {i}: DUPLICATE num {rec.num}")
                    n_err += 1
                    continue
                seen_nums.add(rec.num)
                n_ok += 1
            except ValidationError as e:
                print(f"line {i} (app={raw.get('app')}): INVALID")
                print(e)
                n_err += 1
    print(f"\n{n_ok} valid, {n_err} invalid. Covered app nums: {sorted(seen_nums)}")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main(sys.argv[1])
