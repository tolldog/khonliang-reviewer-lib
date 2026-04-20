"""Review contracts — content-agnostic data shapes for reviewer agents.

All fields are plain Python values so records round-trip through JSON without
custom encoders. Nested dataclass instances are reconstructed by the matching
``from_dict`` classmethods.

Kind-extensibility: ``ReviewRequest.kind`` is a free-form string. Adding a new
review kind (``"spec"``, ``"fr"``, ``"doc"``, ...) does not require any change
to this module.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Severity = Literal["nit", "comment", "concern"]
Disposition = Literal["posted", "dry_run", "errored"]


@dataclass(frozen=True)
class ArtifactRef:
    """Opaque pointer to a bus artifact.

    Lets callers pass large inputs (diffs, cached repo profiles, instructions)
    by reference instead of inline when the inline form would blow past a
    context budget.
    """

    artifact_id: str
    kind: str = ""
    title: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArtifactRef":
        return cls(**data)


@dataclass
class ReviewRequest:
    """Generic review request.

    ``content`` is whatever text the reviewer should evaluate — a unified diff,
    a spec body, a doc page — and ``kind`` identifies which review template the
    consuming agent should apply.
    """

    kind: str
    content: str
    instructions: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    refs: list[ArtifactRef] = field(default_factory=list)
    request_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewRequest":
        data = dict(data)
        refs = data.get("refs") or []
        data["refs"] = [
            ArtifactRef.from_dict(r) if isinstance(r, dict) else r for r in refs
        ]
        return cls(**data)


@dataclass
class ReviewFinding:
    """A single review observation.

    A summary-level note leaves ``path`` and ``line`` unset. An inline comment
    fills both. ``suggestion`` carries the body of a GitHub-style suggestion
    block when the reviewer proposes a concrete patch.
    """

    severity: Severity
    title: str
    body: str
    category: str = ""
    path: str | None = None
    line: int | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewFinding":
        return cls(**data)


@dataclass
class UsageEvent:
    """Per-review token accounting record.

    ``estimated_api_cost_usd`` is populated by the consuming agent using a
    ``ModelPricing`` entry from ``khonliang_reviewer.pricing``. For
    subscription-backed calls (Claude-via-CLI) this value is the hypothetical
    pay-per-token cost of the same work; for API-priced backends it is the
    actual spend.
    """

    timestamp: float
    backend: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    duration_ms: int = 0
    disposition: Disposition = "posted"
    request_id: str = ""
    repo: str = ""
    pr_number: int | None = None
    estimated_api_cost_usd: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UsageEvent":
        return cls(**data)


@dataclass
class ReviewResult:
    """Structured output of a single ``ReviewProvider.review`` call."""

    request_id: str
    summary: str
    findings: list[ReviewFinding] = field(default_factory=list)
    disposition: Disposition = "posted"
    error: str = ""
    usage: UsageEvent | None = None
    backend: str = ""
    model: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewResult":
        data = dict(data)
        findings = data.get("findings") or []
        data["findings"] = [
            ReviewFinding.from_dict(f) if isinstance(f, dict) else f
            for f in findings
        ]
        usage = data.get("usage")
        if isinstance(usage, dict):
            data["usage"] = UsageEvent.from_dict(usage)
        return cls(**data)


__all__ = [
    "ArtifactRef",
    "Disposition",
    "ReviewFinding",
    "ReviewRequest",
    "ReviewResult",
    "Severity",
    "UsageEvent",
]
