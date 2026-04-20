"""ReviewProvider — abstract interface every backend implements."""

from __future__ import annotations

from abc import ABC, abstractmethod

from khonliang_reviewer.contracts import ReviewRequest, ReviewResult


class ReviewProvider(ABC):
    """A single review backend.

    Providers are transport- and storage-agnostic: they take a
    :class:`ReviewRequest`, call their model, and return a
    :class:`ReviewResult` that includes a populated :class:`UsageEvent`.
    Concrete implementations (Ollama HTTP client, Claude CLI subprocess,
    future GPT/Gemini adapters) live in ``khonliang-reviewer``.
    """

    #: Short stable identifier used in usage records and pricing lookups
    #: (e.g. ``"ollama"``, ``"claude_cli"``).
    name: str = ""

    @abstractmethod
    async def review(self, request: ReviewRequest) -> ReviewResult:
        """Run a review, return the structured result."""
        raise NotImplementedError


__all__ = ["ReviewProvider"]
