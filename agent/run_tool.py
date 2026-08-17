"""
Thin CLI wrapper so a tool-calling agent (in this case: Claude Code itself,
during the take-home) can invoke a single Composio COMPOSIO_SEARCH tool
without spinning up an LLM loop.

Usage:
    python -m agent.run_tool <TOOL_SLUG> '<json args>'

Example:
    python -m agent.run_tool COMPOSIO_SEARCH_TAVILY_SEARCH \
        '{"query": "Zendesk API authentication", "include_domains": ["developer.zendesk.com"], "include_raw_content": true, "max_results": 3}'

This exists because a full Anthropic-API-driven agent loop (agent/pipeline.py) costs real
money per tool-use turn across ~100 apps. Composio's COMPOSIO_SEARCH toolkit itself is
free-tier / NO_AUTH beyond a Composio account, so this lets the *reasoning* happen for free
(a human, or an already-running coding agent) while the *tool execution* still genuinely goes
through Composio's SDK — same tools, same evidence, no LLM-API spend required to produce the
dataset. agent/pipeline.py remains the fully-automated, unattended version for anyone who
does want to spend the API credit to run it hands-off.
"""

from __future__ import annotations

import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m agent.run_tool <TOOL_SLUG> '<json args>'", file=sys.stderr)
        sys.exit(1)

    slug, args_json = sys.argv[1], sys.argv[2]
    args = json.loads(args_json)

    from composio import Composio

    composio = Composio()
    user_id = "plugai-research"
    # Priming the tool cache via .get() before .execute() — without this the SDK's
    # execute() raises a bare KeyError on the slug (verified empirically).
    composio.tools.get(user_id=user_id, tools=[slug])
    result = composio.tools.execute(slug, user_id=user_id, arguments=args)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
