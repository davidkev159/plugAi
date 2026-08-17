"""
Data schema for a single app's research record.

This is the contract the research agent must fill in for every app in
data/apps.csv. Keeping it as a strict Pydantic model means:
  - the LLM's structured output is validated, not just hoped-for JSON
  - the verification pass can diff field-by-field against hand checks
  - the HTML deliverable can render straight from output/*.json
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AuthMethod(str, Enum):
    OAUTH2 = "OAuth2"
    API_KEY = "API key"
    BASIC = "Basic"
    TOKEN = "Token (static/bearer)"
    HMAC_SIGNED = "HMAC-signed request"
    NONE = "No auth / public"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class AccessTier(str, Enum):
    SELF_SERVE_FREE = "Self-serve, free"
    SELF_SERVE_TRIAL = "Self-serve, free trial"
    PAID_PLAN_REQUIRED = "Requires paid plan"
    ADMIN_APPROVAL = "Requires admin/org approval"
    PARTNERSHIP_GATED = "Partnership / contact-sales gated"
    UNKNOWN = "Unknown"


class ApiSurface(str, Enum):
    REST = "REST"
    GRAPHQL = "GraphQL"
    REST_AND_GRAPHQL = "REST + GraphQL"
    SDK_ONLY = "SDK only, no raw HTTP docs"
    NO_PUBLIC_API = "No public API found"
    UNKNOWN = "Unknown"


class BuildabilityVerdict(str, Enum):
    BUILDABLE_TODAY = "Buildable today"
    BUILDABLE_WITH_WORKAROUND = "Buildable with a workaround"
    BLOCKED_ACCESS = "Blocked: access/credential gate"
    BLOCKED_API = "Blocked: no usable API surface"
    BLOCKED_UNCLEAR = "Blocked: unclear / needs human research"


class AppResearchRecord(BaseModel):
    num: int
    category: str
    app: str
    one_liner: str = Field(description="What the app does, in one line.")

    auth_methods: list[AuthMethod] = Field(default_factory=list)
    auth_notes: Optional[str] = None

    access_tier: AccessTier
    access_notes: Optional[str] = None

    api_surface: ApiSurface
    api_breadth_notes: Optional[str] = Field(
        default=None,
        description="Rough sense of surface size, e.g. 'broad: 200+ endpoints' or 'narrow: ~5 endpoints'.",
    )
    existing_mcp: bool = False
    existing_mcp_notes: Optional[str] = None

    buildability_verdict: BuildabilityVerdict
    main_blocker: Optional[str] = Field(
        default=None, description="One sentence: the single biggest blocker, if not buildable today."
    )

    evidence_urls: list[str] = Field(default_factory=list)

    confidence: float = Field(ge=0.0, le=1.0, description="Agent's self-reported confidence 0-1.")
    agent_notes: Optional[str] = Field(
        default=None, description="Anything the agent flagged as uncertain, contradictory, or needing a human."
    )


class VerificationEntry(BaseModel):
    """One hand-verification result comparing an agent field to ground truth."""

    num: int
    app: str
    field: str
    agent_said: str
    verified_truth: str
    correct: bool
    verifier_note: Optional[str] = None
    evidence_url: Optional[str] = None
