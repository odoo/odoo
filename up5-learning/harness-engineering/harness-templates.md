# Harness Engineering Templates

Source: https://walkinglabs.github.io/learn-harness-engineering/en/resources/templates/

## The four core files (start with these)

| File | Purpose | Status in this repo |
|---|---|---|
| `CLAUDE.md` | Agent operating manual — rules, conventions, definition of done | ✅ at repo root |
| `claude-progress.md` | Session-by-session state log | ✅ at repo root |
| `feature_list.json` | Machine-readable task tracker with acceptance criteria | ✅ at repo root |
| `init.sh` | One-command environment verification | — not needed (conda handles this) |

## Additional templates (add as the project grows)

| File | Purpose |
|---|---|
| `session-handoff.md` | Compact handoff between sessions: verified state, changes, next priorities |
| `clean-state-checklist.md` | Pre-session-end checklist: tests pass, progress logged, repo clean |
| `evaluator-rubric.md` | Scoring across correctness, verification, scope, reliability, handoff readiness |
| `quality-document.md` | Codebase health snapshot graded by domain and architectural layer |

## `feature_list.json` schema

```json
{
  "id": "unique-kebab-id",
  "area": "module_name",
  "title": "What the task accomplishes",
  "status": "todo | in-progress | blocked | done",
  "priority": "high | medium | low",
  "criteria": [
    "Specific, checkable acceptance condition 1",
    "Specific, checkable acceptance condition 2"
  ],
  "verification": "exact command to run",
  "evidence": "actual output or commit ref when done"
}
```

## `claude-progress.md` format

```markdown
## Current Verified State
- Branch: ...
- Last verified: YYYY-MM-DD
- Status: clean | in-progress | blocked

## Session Log

### Session N — YYYY-MM-DD
- Goal: ...
- Completed: ...
- Evidence: <paste test command + output>
- Next: ...
```
