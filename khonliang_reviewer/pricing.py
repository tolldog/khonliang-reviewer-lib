"""Pricing math for usage accounting.

For every review, the estimated API-equivalent cost in USD is computed from a
per-model pricing entry. Subscription-backed calls (Claude-via-CLI) carry the
hypothetical pay-per-token cost so subscription spend can be compared against
equivalent API spend. API-priced backends carry the actual spend.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


_TOKENS_PER_MTOKEN = 1_000_000.0


@dataclass(frozen=True)
class ModelPricing:
    """Per-model `$/Mtoken` rates for a single backend+model pair.

    Rates are independent: cached input tokens use ``cache_read_per_mtoken_usd``
    and are not also billed at ``input_per_mtoken_usd``. Pricing sources
    typically publish cache-read and cache-creation rates separately from the
    base input rate; this record preserves that split.
    """

    backend: str
    model: str
    input_per_mtoken_usd: float = 0.0
    output_per_mtoken_usd: float = 0.0
    cache_read_per_mtoken_usd: float = 0.0
    cache_creation_per_mtoken_usd: float = 0.0
    currency: str = "USD"
    source_url: str = ""
    as_of: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelPricing":
        return cls(**data)


def estimate_api_cost(
    pricing: ModelPricing,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    """Return the USD cost implied by ``pricing`` for the given token counts."""
    return (
        input_tokens * pricing.input_per_mtoken_usd
        + output_tokens * pricing.output_per_mtoken_usd
        + cache_read_tokens * pricing.cache_read_per_mtoken_usd
        + cache_creation_tokens * pricing.cache_creation_per_mtoken_usd
    ) / _TOKENS_PER_MTOKEN


__all__ = ["ModelPricing", "estimate_api_cost"]
