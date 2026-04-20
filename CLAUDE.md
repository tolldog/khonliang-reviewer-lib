# khonliang-reviewer-lib Agent Notes

This repository is the shared importable SDK for review primitives. Keep it
small, reusable, and free of application-specific wiring or storage.

When working here:

- Put generic, content-agnostic review primitives here.
- Keep provider implementations (Ollama HTTP, Claude CLI subprocess, etc.) in
  `khonliang-reviewer`.
- Keep bus registration, GitHub posting, SQLite usage storage, and rule-table
  policy in `khonliang-reviewer`.
- Keep FR lifecycle, milestones, specs, and git/GitHub workflow in
  `khonliang-developer`.
- Do not add local config files, application databases, or transport code.
- Preserve backward-compatible aliases unless the consuming apps have already
  migrated.

## Kind-extensibility

The library has to stay open to non-code review kinds. `ReviewRequest.kind` is
a free-form string. When adding helpers, keep them content-agnostic unless
there is a clear cross-kind reason to specialize — specialize in the consuming
agent, not here.

## Validation

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall khonliang_reviewer
```

For docs-only changes, still check that examples reference exported names from
`khonliang_reviewer.__all__`.
