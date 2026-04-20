# khonliang-reviewer-lib

Reusable review primitives for the khonliang reviewer agents.

This library contains the shared contracts and helpers used by review-focused
agents (starting with `khonliang-reviewer`) and by any other agent that wants
to produce structured review output — code, specs, FRs, docs, or external
content — without taking a dependency on a specific provider or storage
backend.

## What Belongs Here

- `ReviewRequest`, `ReviewFinding`, `ReviewResult` — generic review contracts,
  content-agnostic.
- `ReviewProvider` — abstract interface every backend (Ollama, Claude-via-CLI,
  future GPT/Gemini) implements.
- `UsageEvent` + `ModelPricing` — token-accounting records and per-model
  pricing entries.
- `ErrorCategory` — canonical error classifications so callers can branch
  on error type without parsing free-form `error` strings. Used on both
  `ReviewResult.error_category` and `UsageEvent.error_category`.
- `estimate_api_cost` — pricing math so subscription-backed calls can be
  compared against pay-per-token API spend.
- `ArtifactRef` — opaque pointer to bus artifacts so large inputs (diffs,
  profiles, instructions) can be passed by reference instead of inline.

## What Does Not Belong Here

- Concrete provider implementations (Ollama HTTP client, Claude CLI subprocess,
  etc.). Those live in `khonliang-reviewer`.
- Bus registration, skill wiring, or agent lifecycle. Those live in
  `khonliang-reviewer` and use `khonliang-bus-lib`.
- GitHub review posting, SQLite usage storage, repo-profile fetch. Those live
  in `khonliang-reviewer`.
- Rule-table policy for picking `(backend, model)` from `(kind, profile, size)`.
  Policy primitives may end up here later once patterns stabilize; initial
  implementation keeps policy in the reviewer app.

## Kind-Extensibility

`ReviewRequest.kind` carries a free-form string (`"pr_diff"` initially). New
kinds — `"spec"`, `"fr"`, `"pr_description"`, `"doc"` — slot in without any
change to this library. Kind-specific prompt templates and rule-table rows
live in the agent that handles them.

## Typical Consumer

```python
from khonliang_reviewer import (
    ReviewProvider,
    ReviewRequest,
    ReviewResult,
    ReviewFinding,
    UsageEvent,
    ModelPricing,
    estimate_api_cost,
)


class OllamaProvider(ReviewProvider):
    name = "ollama"

    async def review(self, request: ReviewRequest) -> ReviewResult:
        # ...call the Ollama endpoint, build findings, compute usage
        ...
```

## Validation

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall khonliang_reviewer
```
