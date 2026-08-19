# Contributing to Invoice Agent

Thank you for your interest in contributing to Invoice Agent. Here's how to get started.

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-fork>/odoo.git
cd odoo

# 2. Start the development stack
cp .env.example .env
docker compose up -d

# 3. Install addon dependencies (in the Odoo container)
docker compose exec odoo odoo -d odoo -i invoice_agent --stop-after-init
```

## Code Style

### Python

- **Formatter/Linter**: [ruff](https://docs.astral.sh/ruff/) with line-length=100
- **Type hints**: Required on all function signatures (`disallow_untyped_defs = true`)
- **Target**: Python 3.11+

```bash
cd invoice-ai
ruff check .        # lint
ruff format .       # format
mypy .              # type check
```

### Odoo Addons

- Follow the [OCA coding guidelines](https://github.com/odoo/odoo/wiki/Contributing)
- Use `@api.depends` for computed fields — never store without dependencies
- All new fields need XML security rules in `security/`

## Pull Requests

1. **Branch from `main`** — one feature per branch
2. **Write tests** — `pytest` for invoice-ai, Odoo tests for addons
3. **Run CI locally** before pushing:
   ```bash
   cd invoice-ai && ruff check . && mypy . && pytest
   ```
4. **PR description** must include: what changed, why, how to test, screenshot (if UI)
5. **No force-pushes** after review starts

## Testing

### invoice-ai (FastAPI service)

```bash
cd invoice-ai
pip install -e ".[dev]"
pytest                    # unit tests
locust --headless -u 5 -r 1 --run-time 1m  # load test (smoke)
```

### Odoo addons

```bash
docker compose exec odoo odoo -d odoo --test-tags /invoice_agent --stop-after-init
```

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(agent): add confidence-based kanban routing
fix(queue): prevent duplicate job on re-click
docs(readme): add architecture diagram
```

## Reporting Issues

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Logs (docker compose logs)
- Environment (OS, Docker version, Odoo version)

## Architecture Decisions

Major changes require an ADR (Architecture Decision Record) in `docs/`. See existing ADRs:
- ADR-003: Why a separate FastAPI service for LLM calls
- ADR-004: Why a transactional outbox for RabbitMQ
- ADR-005: Why pgvector + Voyage-3 for RAG
