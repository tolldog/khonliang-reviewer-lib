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

#: Low-to-high severity ordering. Exposed as a tuple (rather than an
#: :class:`enum.IntEnum`) because the contract is the :data:`Severity`
#: ``Literal`` — callers already branch on string values. The tuple is
#: the single source of truth for "is X more severe than Y?" questions;
#: use :func:`severity_rank` to compare without hard-coding indices.
SEVERITY_ORDER: tuple[Severity, ...] = ("nit", "comment", "concern")

#: Precomputed rank lookup for :data:`SEVERITY_ORDER`. O(1) lookup that
#: type-checks cleanly (``dict[str, int]`` accepts any ``str`` key without
#: the ``Literal``/``str`` variance friction ``tuple.index`` has).
_SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(SEVERITY_ORDER)}


def severity_rank(severity: str) -> int:
    """Return the 0-based rank of ``severity`` within :data:`SEVERITY_ORDER`.

    Higher rank = more severe. Unknown values raise :class:`ValueError`
    rather than silently collapsing to a default — severity labels cross
    trust boundaries (provider output, skill args) and a typo shouldn't
    be treated as ``"nit"`` just because that's the lowest rank.
    """
    try:
        return _SEVERITY_RANK[severity]
    except KeyError as exc:
        raise ValueError(
            f"unknown severity {severity!r}; expected one of {list(SEVERITY_ORDER)}"
        ) from exc


Disposition = Literal["posted", "dry_run", "errored"]

#: Structured classification for errored reviews, so callers can branch on
#: error type without parsing the free-form ``error`` string. Empty string is
#: the default for successful / non-errored results. The enum is open in
#: practice — providers may add new categories over time — but staying within
#: the defined set keeps downstream observers (bus dashboards, gap reports,
#: ops alerts) stable.
ErrorCategory = Literal[
    "",
    "auth_not_provisioned",
    "binary_not_found",
    "subprocess_timeout",
    "nonzero_exit",
    "malformed_envelope",
    "backend_error",
    "unknown",
]


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
    error_category: str = ""
    #: Number of findings the consuming agent dropped from the
    #: ``ReviewResult`` before returning to the caller (severity_floor
    #: post-filter, content-gate rejections, etc.). Defaults to 0 so
    #: agents that don't filter keep the same on-wire shape. Measured
    #: over time this lets operators see how much noise different models
    #: generate under a given floor without re-running reviews.
    findings_filtered_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain ``dict``.

        Omits ``findings_filtered_count`` from the serialized dict when 0
        to preserve the pre-existing wire shape; decoder defaults to 0
        when the key is absent.
        """
        data = asdict(self)
        if data.get("findings_filtered_count", 0) == 0:
            data.pop("findings_filtered_count", None)
        return data

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
    error_category: str = ""
    usage: UsageEvent | None = None
    backend: str = ""
    model: str = ""
    created_at: float = field(default_factory=time.time)
    #: Findings the distill pipeline removed (severity floor, dedup,
    #: max_findings cap) — the audit trail that lets audit / benchmark
    #: corpora recover the full raw output. Empty by default (and always
    #: empty on the raw provider path / the ``audit_corpus`` audience,
    #: which skips distillation). Populated by the consuming pipeline, not
    #: by providers.
    dropped_findings: list[ReviewFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain ``dict``.

        Manually serializes the nested ``usage`` field via
        :meth:`UsageEvent.to_dict` rather than letting :func:`asdict`
        recurse into it — ``asdict`` bypasses custom ``to_dict`` methods
        on nested dataclasses, which would re-emit ``findings_filtered_count``
        even when 0 and break the omit-when-zero wire-shape guarantee
        that ``UsageEvent.to_dict`` establishes. ``ReviewResult`` is the
        typical on-wire path (``UsageEvent`` rarely ships standalone), so
        the nested case is the one that has to hold the contract.
        """
        data = asdict(self)
        if self.usage is not None:
            data["usage"] = self.usage.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewResult":
        data = dict(data)
        findings = data.get("findings") or []
        data["findings"] = [
            ReviewFinding.from_dict(f) if isinstance(f, dict) else f
            for f in findings
        ]
        dropped = data.get("dropped_findings") or []
        data["dropped_findings"] = [
            ReviewFinding.from_dict(f) if isinstance(f, dict) else f
            for f in dropped
        ]
        usage = data.get("usage")
        if isinstance(usage, dict):
            data["usage"] = UsageEvent.from_dict(usage)
        return cls(**data)


__all__ = [
    "ArtifactRef",
    "Disposition",
    "ErrorCategory",
    "ReviewFinding",
    "ReviewRequest",
    "ReviewResult",
    "SEVERITY_ORDER",
    "Severity",
    "UsageEvent",
    "severity_rank",
]
