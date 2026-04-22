"""Round-trip + serialization tests for the review contracts."""

from __future__ import annotations

import json

import pytest

from khonliang_reviewer import (
    SEVERITY_ORDER,
    ArtifactRef,
    ErrorCategory,
    ReviewFinding,
    ReviewRequest,
    ReviewResult,
    UsageEvent,
    severity_rank,
)


def test_artifact_ref_round_trip():
    ref = ArtifactRef(artifact_id="art_123", kind="diff", title="PR #42 diff")
    assert ArtifactRef.from_dict(ref.to_dict()) == ref


def test_review_request_round_trip_with_refs():
    request = ReviewRequest(
        kind="pr_diff",
        content="diff --git a/file b/file\n@@ -1 +1 @@\n-old\n+new\n",
        instructions="Review for correctness and tests.",
        context={"repo": "tolldog/example", "pr_number": 42},
        metadata={"run_id": "r-123"},
        refs=[ArtifactRef(artifact_id="art_profile", kind="profile")],
        request_id="req-1",
    )
    restored = ReviewRequest.from_dict(request.to_dict())
    assert restored == request
    assert isinstance(restored.refs[0], ArtifactRef)


def test_review_request_json_round_trip():
    request = ReviewRequest(kind="spec", content="# Spec body", request_id="req-2")
    blob = json.dumps(request.to_dict())
    restored = ReviewRequest.from_dict(json.loads(blob))
    assert restored == request


def test_review_finding_round_trip():
    finding = ReviewFinding(
        severity="concern",
        title="Missing test for edge case",
        body="The empty-input path isn't covered.",
        category="testing",
        path="pkg/mod.py",
        line=42,
        suggestion="def test_empty_input():\n    ...",
    )
    assert ReviewFinding.from_dict(finding.to_dict()) == finding


def test_review_finding_summary_level_has_no_anchor():
    finding = ReviewFinding(severity="comment", title="Overall", body="Looks fine.")
    restored = ReviewFinding.from_dict(finding.to_dict())
    assert restored.path is None
    assert restored.line is None
    assert restored.suggestion is None


def test_usage_event_round_trip():
    event = UsageEvent(
        timestamp=1776660000.0,
        backend="ollama",
        model="qwen3.5",
        input_tokens=1234,
        output_tokens=567,
        cache_read_tokens=800,
        cache_creation_tokens=100,
        duration_ms=4321,
        disposition="posted",
        request_id="req-3",
        repo="tolldog/example",
        pr_number=42,
        estimated_api_cost_usd=0.01234,
    )
    assert UsageEvent.from_dict(event.to_dict()) == event


def test_review_result_round_trip_with_nested_usage_and_findings():
    usage = UsageEvent(
        timestamp=1776660000.0,
        backend="claude_cli",
        model="claude-opus-4-7",
        input_tokens=100,
        output_tokens=50,
    )
    result = ReviewResult(
        request_id="req-4",
        summary="LGTM with one nit.",
        findings=[
            ReviewFinding(
                severity="nit",
                title="Variable name",
                body="`paths` mis-names a str return.",
                path="README.md",
                line=66,
            ),
        ],
        disposition="posted",
        usage=usage,
        backend="claude_cli",
        model="claude-opus-4-7",
        created_at=1776660001.0,
    )
    restored = ReviewResult.from_dict(result.to_dict())
    assert restored == result
    assert isinstance(restored.findings[0], ReviewFinding)
    assert isinstance(restored.usage, UsageEvent)


def test_review_result_without_usage():
    result = ReviewResult(request_id="req-5", summary="dry run", disposition="dry_run")
    restored = ReviewResult.from_dict(result.to_dict())
    assert restored.usage is None
    assert restored.disposition == "dry_run"


def test_review_result_errored_carries_error_string():
    result = ReviewResult(
        request_id="req-6",
        summary="",
        disposition="errored",
        error="backend timed out after 60s",
    )
    restored = ReviewResult.from_dict(result.to_dict())
    assert restored.disposition == "errored"
    assert restored.error == "backend timed out after 60s"


def test_review_result_errored_carries_error_category():
    result = ReviewResult(
        request_id="req-7",
        summary="",
        disposition="errored",
        error="claude binary not on PATH",
        error_category="binary_not_found",
    )
    restored = ReviewResult.from_dict(result.to_dict())
    assert restored.error_category == "binary_not_found"


def test_review_result_error_category_defaults_empty():
    result = ReviewResult(request_id="req-8", summary="all good")
    restored = ReviewResult.from_dict(result.to_dict())
    assert restored.error_category == ""


def test_usage_event_round_trips_error_category():
    event = UsageEvent(
        timestamp=1776660000.0,
        backend="claude_cli",
        model="claude-opus-4-7",
        disposition="errored",
        error="subscription token expired",
        error_category="auth_not_provisioned",
    )
    restored = UsageEvent.from_dict(event.to_dict())
    assert restored.error_category == "auth_not_provisioned"
    assert restored.error == "subscription token expired"


def test_error_category_literal_includes_expected_values():
    """The exported ``ErrorCategory`` alias documents the intended category set.

    Providers should prefer these canonical values so downstream observers
    (dashboards, gap reports) stay aligned across backends.
    """
    import typing

    categories = set(typing.get_args(ErrorCategory))
    assert categories >= {
        "",
        "auth_not_provisioned",
        "binary_not_found",
        "subprocess_timeout",
        "nonzero_exit",
        "malformed_envelope",
        "backend_error",
        "unknown",
    }


def test_review_request_kind_is_free_form():
    """Library must not constrain the set of review kinds."""
    for kind in ("pr_diff", "spec", "fr", "doc", "pr_description", "custom_kind_xyz"):
        request = ReviewRequest(kind=kind, content="body")
        assert ReviewRequest.from_dict(request.to_dict()).kind == kind


# ---------------------------------------------------------------------------
# Severity ordering helpers
# ---------------------------------------------------------------------------


def test_severity_order_is_low_to_high():
    """Contract: ``SEVERITY_ORDER`` runs from least to most severe.

    Any future helper (filters, threshold comparators) relies on this
    axis direction — ``severity_rank("concern") > severity_rank("nit")``.
    Flipping the tuple would silently reverse every filter; the test
    locks the direction.
    """
    assert SEVERITY_ORDER == ("nit", "comment", "concern")


def test_severity_rank_orders_strictly_increasing():
    assert severity_rank("nit") < severity_rank("comment") < severity_rank("concern")


def test_severity_rank_rejects_unknown_value():
    with pytest.raises(ValueError, match="unknown severity"):
        severity_rank("CRITICAL")


def test_severity_rank_rejects_empty_string():
    """Empty string is not a valid severity — don't let it collapse to rank 0."""
    with pytest.raises(ValueError):
        severity_rank("")


# ---------------------------------------------------------------------------
# UsageEvent.findings_filtered_count
# ---------------------------------------------------------------------------


def test_usage_event_findings_filtered_count_defaults_zero():
    """Agents that don't filter keep the same on-wire shape as before.

    ``to_dict()`` omits ``findings_filtered_count`` entirely when 0, so
    strict JSON-schema consumers that predate the field don't observe a
    new key. The in-memory field still defaults to 0 on the dataclass.
    """
    event = UsageEvent(timestamp=1.0, backend="ollama", model="qwen3.5")
    assert event.findings_filtered_count == 0
    assert "findings_filtered_count" not in event.to_dict()


def test_usage_event_to_dict_emits_field_when_nonzero():
    """Non-zero values must be emitted so operators can observe filtering."""
    event = UsageEvent(
        timestamp=1.0,
        backend="ollama",
        model="qwen3.5",
        findings_filtered_count=3,
    )
    data = event.to_dict()
    assert data["findings_filtered_count"] == 3


def test_usage_event_from_dict_defaults_to_zero_when_key_absent():
    """Decoder must tolerate dicts that predate the field (key absent -> 0).

    Pairs with the omit-when-zero encoder to keep the round-trip
    shape-preserving for unfiltered events.
    """
    data = {"timestamp": 1.0, "backend": "ollama", "model": "qwen3.5"}
    restored = UsageEvent.from_dict(data)
    assert restored.findings_filtered_count == 0


def test_usage_event_round_trips_findings_filtered_count():
    event = UsageEvent(
        timestamp=1.0,
        backend="ollama",
        model="qwen3.5",
        findings_filtered_count=7,
    )
    restored = UsageEvent.from_dict(event.to_dict())
    assert restored.findings_filtered_count == 7


def test_usage_event_round_trips_zero_value_via_omit():
    """Zero round-trips through the omit-when-zero path back to 0."""
    event = UsageEvent(timestamp=1.0, backend="ollama", model="qwen3.5")
    restored = UsageEvent.from_dict(event.to_dict())
    assert restored.findings_filtered_count == 0


def test_review_result_to_dict_omits_nested_findings_filtered_count_when_zero():
    """Nested ``usage`` dict inside ``ReviewResult.to_dict()`` must also omit the
    key when zero.

    ``ReviewResult.to_dict()`` is the typical on-wire shape — ``UsageEvent``
    rarely ships standalone. A naive ``asdict(self)`` would bypass
    ``UsageEvent.to_dict()`` and re-emit the zero value, silently breaking the
    wire-shape guarantee round 1 established. This test locks the nested path.
    """
    result = ReviewResult(
        request_id="req-nested-zero",
        summary="all clean",
        usage=UsageEvent(timestamp=1.0, backend="ollama", model="qwen3.5"),
    )
    data = result.to_dict()
    assert "findings_filtered_count" not in data["usage"]


def test_review_result_to_dict_emits_nested_findings_filtered_count_when_nonzero():
    """Non-zero nested value must survive ``ReviewResult.to_dict()``.

    Pairs with the omit-when-zero test: operators must still observe filtering
    activity on the on-wire shape.
    """
    result = ReviewResult(
        request_id="req-nested-nonzero",
        summary="filtered some",
        usage=UsageEvent(
            timestamp=1.0,
            backend="ollama",
            model="qwen3.5",
            findings_filtered_count=4,
        ),
    )
    data = result.to_dict()
    assert data["usage"]["findings_filtered_count"] == 4


def test_review_result_round_trips_nested_findings_filtered_count():
    """End-to-end: ``ReviewResult`` -> dict -> JSON -> dict -> ``ReviewResult``
    preserves a non-zero nested counter.

    The omit-when-zero path is covered by the other nested tests; this one
    covers the non-trivial value through the full decode pipeline so the
    backward-compat guarantee + new-field semantics are both locked in.
    """
    original = ReviewResult(
        request_id="req-nested-rt",
        summary="round-trip with filter",
        usage=UsageEvent(
            timestamp=1.0,
            backend="ollama",
            model="qwen3.5",
            findings_filtered_count=2,
        ),
    )
    restored = ReviewResult.from_dict(json.loads(json.dumps(original.to_dict())))
    assert restored.usage is not None
    assert restored.usage.findings_filtered_count == 2
