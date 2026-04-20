---
applyTo: "**"
---

# Review Instructions

Review this repository as a lightweight shared SDK for khonliang reviewer
agents.

Prioritize findings in this order:

1. Backward compatibility for public imports, dataclass constructors,
   serialized JSON shapes, and the `ReviewProvider` interface.
2. Behavioral bugs in the pricing math and usage-record aggregation.
3. Dependency discipline. This package should stay lightweight; avoid adding
   dependencies for behavior that can be handled with the standard library.
4. Test coverage for contract round-trips, pricing math, and provider
   interface conformance.
5. Documentation accuracy for public SDK usage and the kind-extensibility
   contract (`ReviewRequest.kind`).

Do not leave actionable correctness issues as vague future work. If a change
is needed for correctness or compatibility, call it out directly with the
affected file and line.

When reviewing contract or provider changes, check that:

- Dataclasses stay content-agnostic — no GitHub-specific or kind-specific
  fields creep into the generic contracts.
- Pricing math rounds consistently (use the same unit-of-account across input,
  output, cache-read, cache-creation).
- The `ReviewProvider` interface remains importable and implementable without
  taking a transport or storage dependency.
- Public exports listed in `khonliang_reviewer.__all__` continue to match the
  names documented in the README.
