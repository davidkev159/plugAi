"""
The research agent.

For each app: spins up a Claude tool-use loop scoped to Composio's COMPOSIO_SEARCH
toolkit (web search + fetch-URL-content, no extra API key needed beyond Composio's own),
lets the model search/fetch real docs, then parses its final JSON block into an
AppResearchRecord. Validated records are appended to an output JSONL file (checkpointed,
so a crashed/interrupted run can resume without re-paying for already-done apps).

Usage (see agent/main.py for the CLI):
    from agent.pipeline import ResearchAgent
    agent = ResearchAgent()
    agent.run_all(apps, out_path="output/pass1.jsonl")
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.prompts import build_user_prompt
from agent.schema import AppResearchRecord

load_dotenv()

MODEL = os.environ.get("RESEARCH_MODEL", "claude-sonnet-5")
MAX_TOOL_TURNS = 8  # hard cap so one app can't loop forever / burn budget


def _extract_json_block(text: str) -> dict:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        # fall back: maybe the model returned raw JSON with no fence
        match = re.search(r"(\{.*\})", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(1))


class ResearchAgent:
    def __init__(self, user_id: str = "plugai-research"):
        # Imported lazily so the rest of the repo (schema, csv loader, HTML build)
        # works even before composio/anthropic + API keys are set up.
        from composio import Composio
        from composio_anthropic import AnthropicProvider
        import anthropic

        composio_key = os.environ.get("COMPOSIO_API_KEY")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if not composio_key or not anthropic_key:
            raise RuntimeError(
                "Missing COMPOSIO_API_KEY and/or ANTHROPIC_API_KEY. "
                "Copy .env.example to .env and fill both in."
            )

        self.composio = Composio(provider=AnthropicProvider())
        self.client = anthropic.Anthropic()
        self.user_id = user_id
        # composio.tools.get(...) is the real (rc) SDK surface — earlier docs describe a
        # composio.create()/session.tools() wrapper that isn't in the installed 1.0 rc;
        # verified against the actual installed package via introspection, not assumed.
        #
        # The COMPOSIO_SEARCH toolkit also doesn't ship the FETCH_URL_CONTENT tool the docs
        # site described (verified live: 13 real tools, no such slug among them). Scoped
        # instead to the 4 tools actually useful for docs research — Google/DuckDuckGo search
        # for discovery, Tavily search (which supports include_raw_content +
        # include_domains, i.e. a domain-restricted "fetch full page text") for reading a
        # specific docs page, and Exa's cited-answer tool as a cross-check.
        self.tools = self.composio.tools.get(
            user_id=user_id,
            tools=[
                "COMPOSIO_SEARCH_SEARCH",
                "COMPOSIO_SEARCH_TAVILY_SEARCH",
                "COMPOSIO_SEARCH_DUCK_DUCK_GO_SEARCH",
                "COMPOSIO_SEARCH_EXA_ANSWER",
            ],
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
    def _call_model(self, messages: list[dict]):
        return self.client.messages.create(
            model=MODEL,
            max_tokens=4096,
            tools=self.tools,
            messages=messages,
        )

    def research_one(self, app: dict, crosscheck: bool = False) -> AppResearchRecord:
        prompt = build_user_prompt(app, crosscheck=crosscheck)
        messages = [{"role": "user", "content": prompt}]

        response = self._call_model(messages)
        turns = 0
        while response.stop_reason == "tool_use" and turns < MAX_TOOL_TURNS:
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            results = self.composio.provider.handle_tool_calls(user_id=self.user_id, response=response)
            messages.append({"role": "assistant", "content": response.content})
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": blk.id, "content": json.dumps(res)}
                        for blk, res in zip(tool_use_blocks, results)
                    ],
                }
            )
            response = self._call_model(messages)
            turns += 1

        text = "".join(b.text for b in response.content if b.type == "text")
        raw = _extract_json_block(text)
        # num/category/app come from our own data, not the model's memory
        raw["num"] = app["num"]
        raw["category"] = app["category"]
        raw["app"] = app["app"]
        return AppResearchRecord.model_validate(raw)

    def run_all(self, apps: list[dict], out_path: str, crosscheck: bool = False) -> None:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        done_nums: set[int] = set()
        if out.exists():
            for line in out.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    done_nums.add(json.loads(line)["num"])

        with open(out, "a", encoding="utf-8") as f:
            for app in apps:
                if app["num"] in done_nums:
                    continue
                t0 = time.time()
                try:
                    record = self.research_one(app, crosscheck=crosscheck)
                    f.write(record.model_dump_json() + "\n")
                    f.flush()
                    print(f"[{app['num']:>3}] {app['app']:<30} ok  ({time.time() - t0:.1f}s)")
                except (ValidationError, ValueError, Exception) as e:  # noqa: BLE001
                    error_record = {
                        "num": app["num"],
                        "category": app["category"],
                        "app": app["app"],
                        "error": str(e),
                    }
                    f.write(json.dumps(error_record) + "\n")
                    f.flush()
                    print(f"[{app['num']:>3}] {app['app']:<30} FAILED: {e}")
