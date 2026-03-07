# Repository Guidelines

## Project Structure & Module Organization
- `odoo/`: core framework code.
- `addons/`: upstream Odoo modules (treat as vendor code unless explicitly requested).
- `custom_addons/`: project-specific modules (`gov_*`, `knowledge/*`).
- `doc/` and `debian/`: documentation and packaging assets.
- `frontend/odoo-next-dummy/`: Next.js/Vitest frontend scaffold and integration docs.
- `scripts/`: local helper scripts (for example `start-with-lnav.ps1`).
- `docker-compose.yml`: local/production-like stack (Odoo + PostgreSQL + Ollama).

## Build, Test, and Development Commands
- Install Python deps:
```bash
pip install -r requirements.txt -r requirements-gov-general.txt
```
- Run Odoo locally:
```bash
./odoo-bin -c kodoo.conf -d kodoo --addons-path=addons,custom_addons
```
- Start Docker stack:
```bash
docker compose up -d
docker compose logs -f odoo
```
- Lint Python code:
```bash
ruff check .
```

## Coding Style & Naming Conventions
- Python target is 3.10 (`ruff.toml`); follow Odoo coding guidelines.
- Use 4-space indentation, `snake_case` for Python identifiers, and clear method names.
- Keep module folders in `snake_case` (example: `gov_account_move_template`).
- Prefer small, isolated changes; avoid refactoring vendor modules in `addons/` without need.

## Testing Guidelines
- Prefer module-scoped Odoo tests:
```bash
./odoo-bin -d test_kodoo --test-enable -i <module_name> --stop-after-init
```
- Put tests under each module’s `tests/` directory.
- Name test files with `test_*.py`; keep fixtures deterministic and database-safe.
- For frontend (when dependencies are present), use Vitest conventions under `src/tests`.

## Commit & Pull Request Guidelines
- Follow history style: `[FIX]`, `[IMP]`, etc., plus scope.
- Example: `[FIX] gov_compras: prevent null supplier crash`.
- One logical change per commit; include migration notes for data/model changes.
- PRs should use `.github/PULL_REQUEST_TEMPLATE.md` and fill: issue/feature addressed, current behavior, desired behavior, and CLA confirmation.

## Security & Configuration Tips
- Do not commit secrets, `.env`, or local config files.
- Keep production credentials out of source; inject via environment/secret manager.
- Review exposed ports and reverse proxy/SSL settings before production deploy.
