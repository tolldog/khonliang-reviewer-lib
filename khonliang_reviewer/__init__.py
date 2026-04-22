"""khonliang-reviewer-lib — shared review primitives.

Content-agnostic contracts and helpers for reviewer agents. Concrete provider
implementations (Ollama HTTP, Claude CLI subprocess, etc.) live in
`khonliang-reviewer`. Rule-table policy, GitHub posting, and SQLite usage
storage also live in the agent, not here.
"""

from khonliang_reviewer.contracts import (
    SEVERITY_ORDER,
    ArtifactRef,
    Disposition,
    ErrorCategory,
    ReviewFinding,
    ReviewRequest,
    ReviewResult,
    Severity,
    UsageEvent,
    severity_rank,
)
from khonliang_reviewer.pricing import ModelPricing, estimate_api_cost
from khonliang_reviewer.provider import ReviewProvider


__all__ = [
    "ArtifactRef",
    "Disposition",
    "ErrorCategory",
    "ModelPricing",
    "ReviewFinding",
    "ReviewProvider",
    "ReviewRequest",
    "ReviewResult",
    "SEVERITY_ORDER",
    "Severity",
    "UsageEvent",
    "estimate_api_cost",
    "severity_rank",
]
