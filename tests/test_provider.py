"""Tests for the ReviewProvider abstract interface."""

from __future__ import annotations

import time

import pytest

from khonliang_reviewer import (
    ReviewProvider,
    ReviewRequest,
    ReviewResult,
    UsageEvent,
)


def test_review_provider_is_abstract():
    """ReviewProvider cannot be instantiated without a review() implementation."""
    with pytest.raises(TypeError):
        ReviewProvider()  # type: ignore[abstract]


class _StubProvider(ReviewProvider):
    """Minimal concrete implementation used to exercise the interface."""

    name = "stub"

    async def review(self, request: ReviewRequest) -> ReviewResult:
        return ReviewResult(
            request_id=request.request_id,
            summary=f"stub review of kind={request.kind}",
            disposition="dry_run",
            backend=self.name,
            model="stub-model",
            usage=UsageEvent(
                timestamp=time.time(),
                backend=self.name,
                model="stub-model",
                input_tokens=len(request.content),
            ),
        )


async def test_stub_provider_returns_review_result():
    provider = _StubProvider()
    request = ReviewRequest(kind="pr_diff", content="hello", request_id="req-1")

    result = await provider.review(request)

    assert isinstance(result, ReviewResult)
    assert result.request_id == "req-1"
    assert result.backend == "stub"
    assert result.disposition == "dry_run"
    assert result.usage is not None
    assert result.usage.backend == "stub"
    assert result.usage.input_tokens == len("hello")


async def test_stub_provider_preserves_kind():
    """The provider contract should carry the caller's kind into the response."""
    provider = _StubProvider()
    for kind in ("pr_diff", "spec", "fr"):
        result = await provider.review(
            ReviewRequest(kind=kind, content="body", request_id=f"req-{kind}")
        )
        assert kind in result.summary
