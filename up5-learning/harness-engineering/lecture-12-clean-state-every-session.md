# Lecture 12 — Why Every Session Must Leave a Clean State

Source: https://walkinglabs.github.io/learn-harness-engineering/en/lectures/lecture-12-why-every-session-must-leave-a-clean-state/

## Core insight

Without systematic cleanup discipline, technical debt accumulates exponentially.
Subsequent sessions spend disproportionate time diagnosing problems rather than making progress.

> "'Clean up later' functionally means never cleaning up."
> "Entropy growth is the default. Only active management counteracts it." (Lehman's laws)

## The 12-week evidence

| Metric | Without cleanup | With cleanup |
|---|---|---|
| Build success rate (week 12) | 68% | 97% |
| Test pass rate (week 12) | 61% | 95% |
| Startup time (week 12) | 60+ min | 9 min |

Cost of cleanup: ~5 minutes per session. Return: 29-34 pp quality improvement, 85% faster startup.

## Five non-negotiable clean state dimensions

| # | Dimension | What it means |
|---|---|---|
| 1 | **Build passes** | `./verify.sh` exits 0 for all touched modules |
| 2 | **Tests pass** | `0 failed, 0 error(s)` including pre-existing tests |
| 3 | **Progress recorded** | `claude-progress.md` + `feature_list.json` + `DECISIONS.md` current |
| 4 | **No temporary artifacts** | No debug prints, commented code, untracked TODOs, scratch files |
| 5 | **Startup path functional** | `python odoo-bin --version` + `psql` still succeed |

All five are required. Missing one = incomplete session. **Stash, don't commit partial state.**

## Session integrity model

Like a database transaction:
- **Commit**: all five dimensions ✅ → push
- **Rollback**: any dimension fails → `git stash` incomplete work, document blocker, exit clean

## Quality document

Active health tracker scoring each module across five dimensions (V/U/T/A/C) with A-F grades.
- Updated when a module reaches `state: passing`
- Any module at D or F blocks new feature work
- Enables catching structural drift before it compounds

## Dual-mode cleanup

| Mode | Frequency | What |
|---|---|---|
| Immediate | Every session end | Artifact hygiene, checklist, commit |
| Periodic | Monthly | Full system scan for structural drift; disable one harness component and benchmark |

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| "I'll clean up next session" | Entropy compounds — deferred cleanup never happens |
| Cleanup as emergency response | Should be routine, not firefighting |
| Build-only validation | Code compiles ≠ tests pass ≠ progress documented ≠ clean |
| Static harness | Components that were necessary become overhead — periodically prune |

## How this maps to `odoo-up5`

| Concept | Implementation |
|---|---|
| Five dimensions | `up5-docs/standards/clean-state-checklist.md` — physical exit checklist |
| Dimension 4 (artifact hygiene) | Hard Constraint #14 in `CLAUDE.md` |
| Quality document | `up5-docs/standards/quality-document.md` — V/U/T/A/C grades per `up5_*` module |
| Session integrity | `git stash` for incomplete work; never commit partial state |
| Periodic cleanup | Monthly: review quality-document.md; prune any harness rule that adds no value |
| Session End reference | CLAUDE.md Session End links to checklist; step 6 confirms Dimension 4 |
