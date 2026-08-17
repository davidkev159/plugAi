# PlugAI — Agent-Toolkit Buildability Research

Composio AI Product Ops Intern take-home. Research, across 100 real-world apps, whether
each could be wrapped as an agent toolkit today: auth method, self-serve vs gated access,
API surface, existing MCP, and the buildability verdict — done with an agent, not by hand,
with real verification loops behind the accuracy numbers.

**Live case study:** https://davidkev159.github.io/plugAi/ (GitHub Pages, deployed from [`docs/`](docs/)) \
**Source repo:** https://github.com/davidkev159/plugAi \
**Deliverable page source:** [`site/index.html`](site/index.html) (source of truth — `docs/index.html` is a deploy copy)

## What's in this repo

```
data/apps.csv          the 100-app research set (num, category, app, hint)
agent/
  schema.py             the exact record every app must produce (Pydantic, validated)
  prompts.py             system/user prompts for the research agent
  pipeline.py             the research agent: Claude + Composio's COMPOSIO_SEARCH toolkit,
                           tool-use loop, checkpointed JSONL output
  compare.py               diffs two independent passes field-by-field -> agreement report
  main.py                   CLI entrypoint
output/                  pass1.jsonl, crosscheck.jsonl, agreement.json, human verification,
                          pass2.jsonl, final accuracy report (generated, not hand-written)
site/index.html          the single-page deliverable
```

## How the research actually happened (and how it's designed to run unattended)

There are two honest, distinct things here — don't conflate them:

**What actually produced the shipped dataset:** I ran this interactively inside Claude Code.
For each app, Claude called Composio's real `COMPOSIO_SEARCH` toolkit directly via
[`agent/run_tool.py`](agent/run_tool.py) — a thin CLI wrapper around
`composio.tools.execute(...)` — mostly `COMPOSIO_SEARCH_TAVILY_SEARCH` (domain-restricted,
returns real page content) with Google/DuckDuckGo search as fallback discovery. Claude read
the tool output, extracted the fields, and wrote each record straight into
`output/pass1.jsonl`, validated against `agent/schema.py` on every batch. This is deliberate:
`agent/pipeline.py` (below) also works, but it burns Anthropic API credit per tool-use turn
across ~100 apps, and running the search step through Claude Code itself (already available,
no extra spend) was the honest tradeoff for a take-home budget. Two early direct-fetch
failures (Zendesk 403, a guessed NotebookLM URL 404) were recovered by switching to
search-based lookup instead of retrying the same broken path — visible in `agent_notes` on
those two records.

**What `agent/pipeline.py` + `agent/main.py` are for:** a fully automated, unattended version
of the exact same approach — Claude driven through the real Anthropic API in a tool-use loop
against Composio's SDK, checkpointed JSONL output, resumable. Its `ResearchAgent.__init__`
was structurally verified against Composio's live API (traced a dummy key all the way to a
real 401 from Composio's auth endpoint) and its search execution was verified end-to-end
with a real query. It's what you'd point at this if you wanted to rerun or extend the
research without a human in the loop — see "Running it yourself" below.

**Verification — also a genuine independent method, not a second run of the same tool.**
A stratified sample (2 apps per category, 20 total, seeded random) was re-checked field by
field against the same primary evidence URLs, but using **WebFetch** — a direct page fetch —
instead of Composio's Tavily-search tool. Full results, including the one inconclusive check
(a WebFetch rendering limitation, disclosed rather than hidden) and the two precision fixes
it surfaced, are in [`output/verification_report.json`](output/verification_report.json) and
on the deliverable page's Verification section. `agent/compare.py` exists in this repo as a
generic two-pass diff utility (for the unattended `pipeline.py` workflow's automated
crosscheck step) but was not itself run to produce the shipped verification numbers — the
WebFetch hand-check is what actually backs the 95% confirmation rate.

Where a human was needed: judgment calls no tool call resolves cleanly — e.g. manually
un-conflating Waterfall.io from an unrelated "Diligent Equity Waterfall API" that a search
summary had blended together, deciding two apps (fanbasis, iPayX) were genuine dead ends
rather than retrying indefinitely, and flagging a community Otter.ai MCP server that asks
users to disable 2FA as a security concern worth calling out rather than listing neutrally.

## Running it yourself

This runs the **unattended `agent/pipeline.py` path** (see above) — a fresh, fully automated
research pass through the real Anthropic API, not a re-execution of the interactive Claude
Code session that produced the committed `output/pass1.jsonl`. Requires **Python 3.10+**, a
free [Composio](https://composio.dev) API key, and an
[Anthropic](https://console.anthropic.com/settings/keys) API key. No paid accounts for any
of the 100 researched apps are needed — a gate found behind a paid plan or partnership is
itself a valid, evidenced finding.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # fill in COMPOSIO_API_KEY and ANTHROPIC_API_KEY
```

```bash
# Pass 1 — full research run (checkpointed; safe to re-run/resume)
python -m agent.main research --out output/pass1.jsonl

# Independent cross-check pass
python -m agent.main research --crosscheck --out output/pass1_crosscheck.jsonl

# Diff the two passes -> agreement rate + list of disagreements to hand-verify
python -m agent.main compare output/pass1.jsonl output/pass1_crosscheck.jsonl --out output/agreement.json

# After hand-verifying a sample and patching the pipeline, re-run just the affected apps
python -m agent.main research --out output/pass2.jsonl --only 12,34,58
```

Each app costs one or more Claude tool-use turns against Composio's search toolkit — expect
a full 100-app pass to take a while and to consume real API credits on both sides.

## Honesty notes

See the "What the agent got wrong" section on the deliverable page for the specific apps
where the agent's first pass was wrong, and why — this README won't duplicate it, but the
short version is: ambiguous or thin docs, and vendor pages that conflate "supports OAuth"
with "OAuth is the primary/only method," are the two most common failure patterns.
