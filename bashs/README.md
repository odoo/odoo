# Local CI Check - run ALL GitHub Actions checks before you push

Your GitHub Actions CI (`.github/workflows/ci.yml`) runs **five jobs** on
every push to `main` / `production`. Every time one fails remotely, you only
find out after the full pipeline has run on GitHub. `ci-check.ps1` runs the
**same checks locally** so a failing push is caught in minutes, on your
machine.

## The two commands

```powershell
# 1. Run ALL CI jobs locally (fast checks first, slow ones last)
.\bashs\ci-check.ps1

# 2. Optional: block pushes automatically until the check passes
.\bashs\install-pre-push.ps1
```

`ci-check.ps1` exits `0` when the same code would pass CI, and non-zero with
the failing lines when it would fail. `install-pre-push.ps1` installs a git
pre-push hook (`.githooks/pre-push`) so every `git push` runs the check
first - the push is blocked until it passes. Bypass once with
`git push --no-verify`.

## What ci-check.ps1 runs (mirrors every CI job)

**Fast phase (seconds):**

| CI job | Local check |
|---|---|
| `terraform` | `fmt -check -recursive`, `init -backend=false`, `validate` |
| `lint` | `ruff check` + `ruff format --check` on `custom_addons/invoice_agent` |
| `security` | `bandit --severity-level medium` on addon + invoice-ai |
| `security` | `trivy fs --severity CRITICAL,HIGH --ignore-unfixed` |
| `security` | DR runbook exists and is < 90 days old |
| `observability` | prometheus + alertmanager `checkconfig` via docker, grafana JSON validity |

If any fast check fails, the script stops immediately - you get feedback in
seconds instead of minutes.

**Slow phase (minutes, skipped with `-SkipSlow`):**

| CI job | Local check |
|---|---|
| `test` | The exact CI command under coverage: `coverage run --concurrency=thread --source=custom_addons/invoice_agent odoo-bin -d ci -i invoice_agent --addons-path=addons,custom_addons --test-enable --test-tags /invoice_agent --stop-after-init --log-level=test ...` |
| `test` | Log gate: greps for `FAIL\|ERROR\|CRITICAL`, filtering benign `(WARNING/x)` counters, same as CI |
| `test` | Coverage gate: >= 60% on invoice_agent (`-CoverageMin 70` to raise) |
| `security` | `docker build ./invoice-ai` + `trivy image --severity CRITICAL,HIGH` |

## Database parity

GitHub Actions always runs on a **fresh Postgres container**. Reusing a local
DB where invoice_agent is already installed makes Odoo skip the whole
`post_install` suite ("0 post-tests") so results silently stop matching CI.
By default the script **drops the `ci` DB before every run**. Use `-KeepDb`
for deliberate fast iteration - a zero-test guard then fails loudly if the
reused DB skipped the suite.

## Requirements

- Python 3.12 venv at `.\venv` (CI runner uses 3.12 too)
- PostgreSQL 16 reachable as `odoo/odoo@localhost:5432`
- Tools on PATH: `terraform`, `ruff`, `bandit`, `trivy`, `docker`
- CI deps:
  `.\venv\Scripts\python.exe -m pip install -r custom_addons/invoice_agent/requirements.txt coverage`

## Output

- Full Odoo test log: `odoo-test.log` (in `.gitignore`)
- Coverage report: `coverage.xml` (in `.gitignore`)
- Bandit reports: `bandit-addon.json`, `bandit-ai.json`

## Quick iteration during development

```powershell
.\bashs\ci-check.ps1 -SkipSlow      # seconds: terraform + lint + bandit + trivy fs
.\bashs\ci-check.ps1                # full run before pushing
```

Install the pre-push hook once and you never have to remember:

```powershell
.\bashs\install-pre-push.ps1
