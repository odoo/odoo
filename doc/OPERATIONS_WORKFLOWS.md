# Operations Workflows

This document defines the intended operational split between the named hosts in the Kodoo environment.

## Host Roles

`dex-00`
- Main development workstation.
- Runs native Odoo development flows, local validation, experiments, upgrades, and release candidate preparation.
- Typical commands: `make dev`, `make dev-safe`, `make dev-host-up`, module tests, local smoke checks.

`dex-01`
- Secure bastion/middleware host.
- Used to access `srv-01` over SSH, carry operator credentials, and execute production-oriented workflows.
- Should not be used for day-to-day development.

`srv-01`
- Stable 24/7 runtime.
- Runs only the stable Docker stack and related operational tasks: deploy, refresh, logs, smoke, backup, restore, rollback, replica monitoring.
- Must not run native host development targets such as `make dev` or `make dev-safe`.

## PostgreSQL Redundancy

- Production now supports an asynchronous physical standby named `kodoo-db-replica`.
- This protects the full PostgreSQL cluster, not only the default Odoo database, so tenant databases created later are replicated automatically as well.
- The replica is a hot standby for recovery and read-only inspection; applications should keep writing to `kodoo-db`.
- Use `make db-replica-status` and `make db-replica-lag` on `srv-01` to verify streaming health.
- Keep a logical backup policy as well; streaming replication reduces RPO but does not replace versioned backups against operator error or bad writes.

## Workflow Rules

### Patch

1. Implement and validate the patch on `dex-00`.
2. Test against the closest safe copy of production data or a deterministic staging database.
3. Freeze the exact revision to deploy.
4. From `dex-01`, connect to `srv-01`, take or verify a rollback point, deploy, and run `make refresh-safe`.
5. Confirm `make smoke` and log health on `srv-01`.

### Stable Release

1. Build the release candidate on `dex-00`.
2. Run targeted tests, migration checks, and operator validation on `dex-00`.
3. Document migration notes and rollback command before production deploy.
4. From `dex-01`, orchestrate the deploy on `srv-01`.
5. On `srv-01`, update the stable Docker runtime, refresh services, and verify public health.

### Experimental Features

1. Experimental work stays on `dex-00`.
2. Prefer isolated local PostgreSQL via `make dev-safe`.
3. Keep experiment branches and databases separate from release candidates.
4. Promote to patch/release workflow only after validation and explicit decision.

### Hotfix

1. Reproduce and fix on `dex-00` with the smallest viable change.
2. Validate quickly but explicitly before touching production.
3. Use `dex-01` to access `srv-01` and prepare rollback first.
4. Apply on `srv-01`, then immediately run `make refresh-safe` and `make smoke`.
5. Roll back first if health checks fail.

### Rollback

1. Keep the previous known-good revision and latest backup identified before every deploy.
2. Restore the previous app revision first.
3. Restore data only when the incident requires it.
4. Re-run smoke checks and public health checks on `srv-01`.
5. Investigate the failed candidate later on `dex-00`, never directly on the live stack.

## Makefile Policy

The Makefile enforces a lightweight host policy:

- `HOST_ROLE=dex00`: production-oriented targets are blocked.
- `HOST_ROLE=dex01`: development-oriented host-run targets are blocked.
- `HOST_ROLE=srv01`: development-oriented host-run targets are blocked.
- `HOST_ROLE=unknown`: no hard block, but the policy text still guides usage.

Host role is auto-detected from hostname when possible:

- `dex-00` -> `dex00`
- `dex-01` -> `dex01`
- `srv-01` -> `srv01`

You can override detection explicitly when needed:

```bash
make host-role-status HOST_ROLE=dex00
```

Operational targets also print invocation context so the operator can see where the command is being executed from:

- current host and detected role
- current user
- current working directory
- local vs SSH invocation
- SSH peer information when available
- interactive TTY detection
