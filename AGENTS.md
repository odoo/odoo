# Repository Guidelines

## Project Structure & Module Organization
- `odoo/`: core framework code.
- `addons/`: upstream Odoo modules (treat as vendor code unless explicitly requested).
- `custom_addons/`: project-specific modules, including the public-sector suite under `public_sector/gov_*` and `knowledge/*`.
- `doc/` and `debian/`: documentation and packaging assets.
- `frontend/odoo-next-dummy/`: Next.js/Vitest frontend scaffold and integration docs.
- `scripts/`: local helper scripts (for example `start-with-lnav.ps1`).
- `docker-compose.yml`: stable Docker stack for the production-like runtime (Odoo + PostgreSQL + Ollama).

## Build, Test, and Development Commands
- Install local native deps for development/tests:
```bash
python -m pip install -r requirements.txt -r requirements-gov-runtime.txt
```
- Install optional AI deps locally only when an AI feature/test explicitly needs them:
```bash
python -m pip install -r requirements-gov-ai.txt
```
- Run Odoo natively with database manager over the Docker PostgreSQL service:
```bash
make dev
```
- Run Odoo natively with database manager over fully local PostgreSQL:
```bash
make dev-safe
```
- Run Odoo natively against fully local PostgreSQL:
```bash
make dev-host-up
```
- Start/update the stable Docker stack:
```bash
docker compose up -d
make refresh-safe
```
- Lint Python code:
```bash
ruff check .
```

## Coding Style & Naming Conventions
- Local development uses the repo's `.venv`/`pyenv` Python 3.12; `ruff.toml` still targets `py310` for compatibility checks. Follow Odoo coding guidelines.
- Use 4-space indentation, `snake_case` for Python identifiers, and clear method names.
- Keep module folders in `snake_case` (example: `gov_account_move_template`).
- Prefer small, isolated changes; avoid refactoring vendor modules in `addons/` without need.

## Testing Guidelines
- Run module tests, AI tests, and exploratory validation on the native/local Python instance (`.venv`), not inside the stable Docker Odoo container.
- Prefer `make dev` when you need fast database switching through the Odoo database manager while reusing the Docker PostgreSQL data/service.
- Prefer `make dev-safe` when you need the same database-manager workflow but want isolation from the Docker database and stable stack.
- Use `make dev-host-up` only when you intentionally want a fully local PostgreSQL workflow separated from the Docker data.
- Treat Docker as the stable/public-like runtime; refresh that environment with `make refresh-safe` after validating changes locally.
- Prefer module-scoped Odoo tests:
```bash
./odoo-bin -c deploy/odoo/kodoo.dev-host.local.conf -d ktest --test-enable -i <module_name> --stop-after-init
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
