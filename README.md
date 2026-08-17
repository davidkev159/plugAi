# PlugAI — Agent-Toolkit Buildability Research

Composio AI Product Ops Intern take-home. Research, across 100 real-world apps, whether
each could be wrapped as an agent toolkit today: auth method, self-serve vs gated access,
API surface, existing MCP, and the buildability verdict — done with an agent, not by hand,
with real verification loops behind the accuracy numbers.

**Live case study:** <!-- TODO: deployed HTML URL --> \
**Deliverable page source:** [`site/index.html`](site/index.html)

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

## How the research agent works

1. **Pass 1 (research)** — for each app, Claude is given the app + category + a hint URL and
   a tool-use loop restricted to Composio's `COMPOSIO_SEARCH` toolkit (`COMPOSIO_SEARCH_WEB`,
   `COMPOSIO_SEARCH_FETCH_URL_CONTENT`, `COMPOSIO_SEARCH_DUCK_DUCK_GO` — no extra API key
   needed beyond Composio's own). It searches, fetches real docs pages, and returns one JSON
   object matching `agent/schema.py`. Records are validated with Pydantic; invalid/failed
   apps are logged, not silently dropped.
2. **Automated cross-check** — a second, independent pass re-derives every app from primary
   sources only, told explicitly not to trust a prior answer. `agent/compare.py` diffs pass 1
   against the cross-check field-by-field; disagreements are exactly the apps that get
   prioritized for human verification — agreement between two independent runs is a cheap,
   automatable trust signal, not a substitute for a real check.
3. **Human verification** — a stratified sample across all 10 categories (plus every
   disagreement from step 2) is hand-checked against the actual vendor docs. Logged as
   `VerificationEntry` records: agent-said vs verified-truth vs correct/incorrect.
4. **Fix + pass 2** — errors found in step 3 are traced to a root cause (bad prompt wording,
   confusing "OAuth requested" with "OAuth2 live", missing MCP search term, etc.), the
   pipeline is patched, and the affected apps are re-run. The same sample is re-verified to
   show the accuracy delta.

Where a human was needed: judgment calls the agent can't safely make on its own — e.g.
docs written for a stale API version, auth that's technically documented but effectively
dead, or "OAuth requested"-style roadmap language that reads like a shipped feature. These
are called out explicitly on the deliverable page, not hidden.

## Running it yourself

Requires **Python 3.10+**, a free [Composio](https://composio.dev) API key, and an
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
