"""Tests for pricing math + ModelPricing serialization."""

from __future__ import annotations

import math

from khonliang_reviewer import ModelPricing, estimate_api_cost


def test_model_pricing_round_trip():
    pricing = ModelPricing(
        backend="claude_cli",
        model="claude-opus-4-7",
        input_per_mtoken_usd=15.0,
        output_per_mtoken_usd=75.0,
        cache_read_per_mtoken_usd=1.5,
        cache_creation_per_mtoken_usd=18.75,
        source_url="https://anthropic.com/pricing",
        as_of="2026-04-19",
    )
    assert ModelPricing.from_dict(pricing.to_dict()) == pricing


def test_estimate_api_cost_basic():
    pricing = ModelPricing(
        backend="ollama",
        model="qwen3.5",
        input_per_mtoken_usd=2.0,
        output_per_mtoken_usd=8.0,
    )
    # 1M input tokens * $2/Mtoken = $2
    assert estimate_api_cost(pricing, input_tokens=1_000_000) == 2.0
    # 500k output tokens * $8/Mtoken = $4
    assert estimate_api_cost(pricing, output_tokens=500_000) == 4.0


def test_estimate_api_cost_all_token_classes():
    pricing = ModelPricing(
        backend="claude_cli",
        model="claude-opus-4-7",
        input_per_mtoken_usd=15.0,
        output_per_mtoken_usd=75.0,
        cache_read_per_mtoken_usd=1.5,
        cache_creation_per_mtoken_usd=18.75,
    )
    cost = estimate_api_cost(
        pricing,
        input_tokens=10_000,
        output_tokens=2_000,
        cache_read_tokens=50_000,
        cache_creation_tokens=5_000,
    )
    # hand-computed: (10000*15 + 2000*75 + 50000*1.5 + 5000*18.75) / 1_000_000
    # = (150_000 + 150_000 + 75_000 + 93_750) / 1_000_000
    # = 468_750 / 1_000_000
    # = 0.46875
    assert math.isclose(cost, 0.46875, rel_tol=1e-9)


def test_estimate_api_cost_zero_tokens_is_zero():
    pricing = ModelPricing(backend="x", model="y", input_per_mtoken_usd=100.0)
    assert estimate_api_cost(pricing) == 0.0


def test_estimate_api_cost_zero_pricing_is_zero():
    pricing = ModelPricing(backend="local", model="qwen3.5")  # all rates default to 0
    cost = estimate_api_cost(
        pricing,
        input_tokens=999_999,
        output_tokens=999_999,
        cache_read_tokens=999_999,
        cache_creation_tokens=999_999,
    )
    assert cost == 0.0


def test_estimate_api_cost_cache_read_vs_input_are_separate():
    """Cached input tokens should use the cache-read rate, not input rate."""
    pricing = ModelPricing(
        backend="claude_cli",
        model="claude-opus-4-7",
        input_per_mtoken_usd=15.0,
        cache_read_per_mtoken_usd=1.5,
    )
    full_rate = estimate_api_cost(pricing, input_tokens=100_000)
    cached_rate = estimate_api_cost(pricing, cache_read_tokens=100_000)
    assert full_rate == 1.5  # 100k * $15/Mtoken
    assert cached_rate == 0.15  # 100k * $1.5/Mtoken
    assert full_rate == cached_rate * 10  # 10x cheaper on cache hit
