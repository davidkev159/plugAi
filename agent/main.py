"""
CLI entrypoint for the research pipeline.

    python -m agent.main research --out output/pass1.jsonl
    python -m agent.main research --crosscheck --out output/pass1_crosscheck.jsonl
    python -m agent.main compare output/pass1.jsonl output/pass1_crosscheck.jsonl --out output/agreement.json
    python -m agent.main research --out output/pass2.jsonl --only 12,34,58   # targeted re-run after fixes
"""

from __future__ import annotations

import argparse

from agent.apps_loader import by_num, load_apps
from agent.compare import compare_passes


def cmd_research(args: argparse.Namespace) -> None:
    from agent.pipeline import ResearchAgent

    apps = load_apps()
    if args.only:
        nums = [int(x) for x in args.only.split(",")]
        apps = by_num(apps, nums)

    agent = ResearchAgent()
    agent.run_all(apps, out_path=args.out, crosscheck=args.crosscheck)


def cmd_compare(args: argparse.Namespace) -> None:
    summary = compare_passes(args.pass_a, args.pass_b, args.out)
    print(f"Compared {summary['n_compared']} apps.")
    print(f"Fully agree: {summary['n_fully_agree']} ({summary['agreement_rate']:.1%})")
    for field, rate in summary["field_agreement_rate"].items():
        print(f"  {field:<22} {rate:.1%}")
    print(f"Disagreements written to {args.out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PlugAI research agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_research = sub.add_parser("research", help="Run the research agent over apps.csv")
    p_research.add_argument("--out", required=True, help="Output .jsonl path")
    p_research.add_argument("--crosscheck", action="store_true", help="Use the stricter independent cross-check prompt")
    p_research.add_argument("--only", default=None, help="Comma-separated app numbers to (re-)run")
    p_research.set_defaults(func=cmd_research)

    p_compare = sub.add_parser("compare", help="Diff two research passes")
    p_compare.add_argument("pass_a")
    p_compare.add_argument("pass_b")
    p_compare.add_argument("--out", required=True)
    p_compare.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
