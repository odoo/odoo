# Clean State Checklist

Run at the end of every session before the final commit.
All five dimensions must be ✅. Missing one = incomplete session — stash and defer.

---

## Dimension 1 — Build passes

- [ ] `./verify.sh <module>` exits 0 for every module touched this session

## Dimension 2 — Tests pass (including pre-existing)

- [ ] Test output shows `0 failed, 0 error(s)`
- [ ] No pre-existing test was broken by changes this session
- [ ] If any test was skipped or marked `@unittest.skip`, a reason is recorded

## Dimension 3 — Progress recorded

- [ ] `claude-progress.md` → Current Verified State reflects actual state right now
- [ ] `claude-progress.md` → Next Steps is specific and actionable for the next session
- [ ] `feature_list.json` → `state` updated for every task touched
- [ ] Any non-obvious decision recorded in `DECISIONS.md` with WHY

## Dimension 4 — No temporary artifacts

- [ ] No `print()` debug statements in committed Python files
- [ ] No `_logger.debug(...)` left in for temporary investigation (use `_logger.info` sparingly if permanent)
- [ ] No commented-out code blocks (`# old code here`)
- [ ] No `TODO` / `FIXME` / `HACK` markers unless the item is tracked in `feature_list.json`
- [ ] No scratch files, temp fixtures, or `test_manual_*.py` files in the repo

## Dimension 5 — Startup path functional

- [ ] `conda run -n odoo19 python odoo-bin --version` succeeds
- [ ] `psql -U odoo -c "SELECT 1;" -d odoo_dev` succeeds
- [ ] `./verify.sh account` exits 0 (baseline — confirms environment is not broken)

---

## Session integrity rule

A session either fully commits with clean state **or** rolls back uncommitted work:

```bash
git stash   # preserve incomplete work
```

"I'll clean up next session" = never cleaning up. Entropy compounds with each deferred session.

---

## Quick reference — common violations

| Violation | Fix |
|---|---|
| `print()` left in model | Remove or replace with `_logger.info(...)` |
| Commented-out code | Delete it — git history preserves old versions |
| `TODO` without a task | Either add to `feature_list.json` or delete the comment |
| `./verify.sh account` broken | Do not commit until it passes — investigate first |
| `claude-progress.md` stale | Update before committing — next session depends on it |
