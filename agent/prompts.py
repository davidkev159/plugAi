"""System/user prompt templates for the research agent."""

SCHEMA_INSTRUCTIONS = """
You are researching one third-party app/API for Composio, a company that turns apps into
tool calls AI agents can use. Your job: determine, with evidence, whether this app could be
wrapped as an agent toolkit today.

For the app given, use your search tools to find PRIMARY sources (the vendor's own developer
docs, API reference, or pricing/auth pages) — not blog posts or third-party summaries. Prefer
official docs domains. You have four tools:
  - COMPOSIO_SEARCH_SEARCH / COMPOSIO_SEARCH_DUCK_DUCK_GO_SEARCH: general web search, good
    for discovery (e.g. finding the right docs URL, or "<app> MCP server").
  - COMPOSIO_SEARCH_TAVILY_SEARCH: pass include_raw_content=true and include_domains set to
    the vendor's own docs domain (from the hint URL) to pull the actual full text of a
    specific docs page — this is your primary way to "read" a page, not just see a snippet.
  - COMPOSIO_SEARCH_EXA_ANSWER: ask a direct question and get a synthesized answer with
    citations; use as a cross-check on an ambiguous finding, not as your only source.

Determine:
1. category (use the category given) and a one-line description of what the app does.
2. auth_methods: which of OAuth2 / API key / Basic / Token (static/bearer) / HMAC-signed
   request / No auth / Other are used for API access. List all that documented.
3. access_tier: can a developer self-serve credentials for free, on a free trial, does it
   require a paid plan, admin/org approval, or a partnership / contact-sales gate to get API
   access at all.
4. api_surface: REST, GraphQL, REST + GraphQL, SDK-only (no raw HTTP docs), or no public API
   found. Give a rough sense of breadth (e.g. "broad, 200+ endpoints" vs "narrow, ~5 endpoints")
   if you can tell.
5. existing_mcp: true/false — does this vendor already ship or document an official MCP server
   (search for "<app> MCP server").
6. buildability_verdict: "Buildable today" / "Buildable with a workaround" / "Blocked:
   access/credential gate" / "Blocked: no usable API surface" / "Blocked: unclear / needs
   human research". If not "Buildable today", give the single biggest blocker in one sentence.
7. evidence_urls: the actual URLs you used to answer the above (2-5 links, real ones you
   fetched, not guessed).
8. confidence: your own 0.0-1.0 confidence in this record as a whole.
9. agent_notes: anything ambiguous, contradictory across sources, paywalled/behind a login you
   could not verify, or that a human should double check.

If you cannot find something after a reasonable search, say so explicitly (use "Unknown" /
false / empty list) rather than guessing. Do not fabricate URLs.

When you are done researching, respond with ONLY a single fenced ```json code block containing
one JSON object with exactly these keys: num, category, app, one_liner, auth_methods,
auth_notes, access_tier, access_notes, api_surface, api_breadth_notes, existing_mcp,
existing_mcp_notes, buildability_verdict, main_blocker, evidence_urls, confidence, agent_notes.
No text before or after the code block.
"""

CROSSCHECK_ADDENDUM = """
IMPORTANT — this is an independent cross-check pass, not the first look at this app.
Do not assume any prior answer is correct. Go to the vendor's own docs domain directly
(the hint URL you're given, or search "site:<vendor-domain>") and re-derive every field
from primary sources only. Be conservative: if the official docs are ambiguous or you can't
reach a page, mark the field Unknown rather than inferring from memory or secondary sources.
"""


def build_user_prompt(app: dict, crosscheck: bool = False) -> str:
    header = (
        f"App #{app['num']}: {app['app']}\n"
        f"Category: {app['category']}\n"
        f"Hint / likely docs domain: {app['hint']}\n\n"
    )
    body = SCHEMA_INSTRUCTIONS
    if crosscheck:
        body += CROSSCHECK_ADDENDUM
    return header + body
