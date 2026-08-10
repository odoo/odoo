# Local CI Check - run GitHub Actions checks before you push

Your GitHub Actions CI (`.github/workflows/ci.yml`) runs on every push to
`main` / `production`. Every time it fails remotely, you only find out after
the full pipeline has run on GitHub. These scripts run the **exact same
checks locally** so a failing push is caught in minutes, on your machine.

## The two commands

```powershell
# 1. Run the full CI 'test' job locally (this is the one that gatekeeps pushes)
.\bashs\ci-check.ps1

# 2. Optional: block pushes automatically until the check passes
.\bashs\install-pre-push.ps1
```

`ci-check.ps1` exits `0` when the same code would pass CI, and non-zero with
the failing lines when it would fail. `install-pre-push.ps1` installs a git
pre-push hook (`.githooks/pre-push`) so every `git push` runs the check
first - the push is blocked until it passes. Bypass once with
`git push --no-verify`.

## What ci-check.ps1 runs (identical to CI)

1. **Preflight** - venv exists, every pip dep CI installs is importable,
   Postgres answers as `odoo/odoo@localhost:5432`.
2. **Database** - **the `ci` DB is DROPPED before every run by default.**
   GitHub Actions always runs on a fresh Postgres container; reusing a DB
   where invoice_agent is already installed makes Odoo skip the whole
   `post_install` suite ("0 post-tests") so the local results silently stop
   matching CI. Drop the DB and you get the same 64-module install + full
   suite that CI runs. For deliberate fast iteration use `-KeepDb` - the
   script then fails loudly if the reused DB skipped the suite.
3. **Tests** - the CI command verbatim under coverage:
   `coverage run --concurrency=thread --source=custom_addons/invoice_agent odoo-bin -d ci -i invoice_agent --addons-path=addons,custom_addons --test-enable --test-tags /invoice_agent --stop-after-init --log-level=test --db_host=localhost --db_port=5432 --db_user=odoo --db_password=odoo`
4. **Log gate** - greps the log for `FAIL|ERROR|CRITICAL`, filtering benign
   `(WARNING/x)` counters, same as CI's `grep` pipeline.
5. **Coverage gate** - requires >= 60% coverage on `custom_addons/invoice_agent`
   (CI's `COVERAGE_MIN`). Raise it with `-CoverageMin 70`.

## Requirements (already set up on this machine)

- Python 3.12 venv at `.\venv` (CI runner uses 3.12 too)
- PostgreSQL 16 reachable as `odoo/odoo@localhost:5432` with `CREATEDB`
  (CI auto-creates the `ci` database; the script does the same)
- CI deps:
  `.\venv\Scripts\python.exe -m pip install -r custom_addons/invoice_agent/requirements.txt coverage`

## Output

- Full Odoo test log: `odoo-test.log` (in `.gitignore`)
- Coverage report: `coverage.xml` (in `.gitignore`)

## Verified parity with GitHub Actions (2026-08-08)

A fresh-DB local run ended with `55 post-tests`, ~13 failures - the same
shape as the GitHub run. The fixed OCR pipeline issues (invalid `numbercall`
cron field, `skipTest` TypeError, cron commit-forbidden cursor, the corrupt
PDF guard) are gone from both.

## Known remaining failures (same on local and GitHub CI)

- `test_controllers.py` group of 12: the routes are registered in code but
  the `HttpCase` HTTP process does not expose them yet; all 12 fail
  identically locally and on GitHub.
- The tesseract binary is not present on the GitHub runner either, so the
  end-to-end OCR test is skipped there too (now with the fixed `SkipTest`).
- If a run fails and leaves the `ci` DB mid-state, just re-run - the DB is
  dropped automatically on each run.
