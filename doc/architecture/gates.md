# The gates — what is mechanically enforced, and what that is worth

> Referenced by [`ARCHITECTURE.md`](ARCHITECTURE.md). The architecture is in
> [`module.md`](module.md) and [`runtime.md`](runtime.md); this file is the
> operator's manual for the machinery that keeps them true.

What is enforced is the standard tools on their pinned versions, the pytest
tiers, `test_lint`, and the DB-backed suites. The database-free gates run as
one command, `./gates.sh`, from the repo root; the `.githooks/pre-push` hook
runs it on every commit about to leave the checkout (enable once per checkout
with `git config core.hooksPath .githooks`), and `.github/workflows/gates.yml`
is the same command on a runner. Fifteen of the dependency rules in
[`module.md`](module.md#dependency-rules) are Tier-2 tests
(`tests/framework/test_layer_contracts.py`); the ORM half of the façade
boundary is `test_lint`'s; the rest are held by review.

## Running the checks

```bash
./gates.sh                                     # everything below the line, one exit code
./gates.sh --fast                              # lint and the two tiers only
./gates.sh --ref <rev>                         # the same, on a worktree of <rev>
./gates.sh --rust --js                         # add the cargo and JS toolchains
```

`gates.sh` sequences the commands a developer types; it defines no gate of its
own, so there is nothing to reconcile with this page:

```bash
ruff check odoo/ --no-cache                    # core package, hard zero
ruff check tests/ --no-cache                   # hard zero
ruff format --check tests/
npx eslint .                                   # whole repo
npx tsc --project tsconfig.json --noEmit       # whole repo
npx prettier --list-different "**/*.scss"
pytest                                         # Tier 1, from the repo root
pytest odoo/orm/tests odoo/http/tests odoo/db/tests odoo/tools/tests \
    tests/service tests/framework              # Tier 2, separate process
python odoo-bin -d <db> -i test_lint --test-enable --stop-after-init
```

`mypy` is measured with mypy alone installed (`ignore_missing_imports`
resolves `lxml`, `psycopg`, `dateutil` to `Any`), never in the shared venv,
over `odoo.orm`, `odoo.db`, `odoo.libs`, `odoo.http`, `odoo.service`,
`odoo.modules`, and separately `odoo.tools`, `odoo.cli`, `odoo.tests`.
`gates.sh` keeps that bare environment under `~/.cache/odoo-gates/`.
`doc/architecture/factcheck.sh` derives the figures these pages state (mixin
composition, base-model reaches, executed statements, dispatch sites) from the
classes and the pin tests, and fails when a page stops citing one.

**`test_lint`** (`odoo/addons/test_lint/tests/`) holds the rules no general
linter knows — SQL-injection shapes, gettext discipline, N+1 query shapes,
manifest and XML conventions, record-field order, and `orm-import` (`E8508`):
addon code outside tests must reach the ORM through `odoo.api` / `odoo.fields`
/ `odoo.models`, never `odoo.orm.*`. Its floors live in
`odoo/addons/test_lint/tests/floors.json`, one integer per gate (13 entries);
a gate with no entry is a hard zero. `assert_ratchet` is exact: a count above
the floor fails, and a count below it fails until the floor is lowered in the
same change.

Three real-dependency pytest suites are in no `testpaths` and run only when
named: `tests/contract` (`ODOO_CONTRACT_REQUIRE_DEPS=1`; PostgreSQL + psql +
pg_dump), `tests/process` (boots real `odoo-bin` processes) and
`tests/loading` (installs `base` into a scratch database; pins the loader
phase order, the uninstall reload, migration ordering and migration-stage
schema visibility).

**DB-backed integration suites** — run against PostgreSQL 18, **each against
its own database**:

```bash
python odoo-bin --addons-path=odoo/addons,addons -d <db> -i <module> \
    --test-enable --test-tags /<module> --stop-after-init
```

The suites run this way: `base` (less the excluded `TestReportsRendering` and
`TestIrModelFieldsTranslation`), `test_http`, `test_orm`, `mrp`, `certificate`,
`stock`, `rpc`, `crm`, `data_recycle`, `mixin_report_sql` with
`test_mixin_report_sql`, `test_read_group`, `test_access_rights`,
`hr_work_entry` with `hr_work_entry_holidays`, `hr_holidays`, the three
`extract` branches, `test_base_order`, `approval` with `test_approval`,
`gateway_ml`, `project_hr`, `exchange`, `date_range`, `account_coa`,
`test_performance_compare`, `mail`, `test_mail`, `mail_group` and `mail_speech`.
`rpc`, `mail`, `test_mail`, `mail_group` and `mail_speech` run **with** the HTTP
server, because their `HttpCase` classes are the only end-to-end coverage of
what they test and none is a tour; the rest run `--no-http`.

`test_orm` — **1,239 test methods** under its `tests/` directory (2026-09-11)
— is the addon written to test the ORM. Above all
`test_domain_evaluator_parity.py`: the only check that a `Domain` means the
same to `search()` (SQL) and `filtered_domain()` (the in-memory predicate),
with a generative suite asserting the two evaluators agree *or both refuse*.
No DB-free tier can see a SQL/predicate divergence.
`TestBackendDifferential.test_divergence_ilike_unaccent` skips on
`registry.has_unaccent`, since a bare `template0` database lacks the
extension every developer database inherits from `db_template`.

`test_read_group` (123 test methods, the only coverage of the five
`read_group/` units) and `test_access_rights` (55, record rules and ACLs) are
counted by method, not by line. **A suite outside the set is a suite nobody
runs.**

### The architecture's own tests

Three Tier-2 files pin structure rather than behaviour and fail the day a move
is undone. `odoo/orm/tests/test_backend_protocol.py`: every `StorageBackend`
method has a caller and every capability flag a consumer; the in-memory backend
implements the whole protocol. `test_backend_dispatch_surface.py`: the inventory
of `env.backend` dispatch sites, its header count, and which of them the
in-memory backend answers differently. `test_architecture_pins.py`: the eight
`env["<base model>"]` sites outside the six port files and the five
statements the models, fields and domain layers execute themselves, as frozen
maps that may shrink and must not grow. None of them is a re-homed gate tree;
each is a test of one claim this document makes.

### The limits of "enforced"

**The integration suites are the only thing that runs addon tests in Python.**
Tier 1 and Tier 2 are DB-free; a change can satisfy both and still be wrong at
runtime. Read a green DB-free run as "the structure holds", never as "the
framework works".

**The JS suites run through `WebSuite` and `MobileWebSuite`** in
`addons/web/tests/test_js.py`, addon tests like any other — but an integration
run that is `--stop-after-init` and `--no-http` skips both classes at
`setUpClass`. They must run **under both presets**, desktop and mobile, because
the two presets select by tag and neither set is a superset of the other. Gate
each pass on its own passed-test **count** as well as on the exit code: a suite
contributing zero tests under a preset is not an error to the runner.

**Missing infrastructure fails a run.** `OdooTestResult`
(`odoo/tests/result.py`) treats a class whose `setUpClass` skips for want of a
server or a browser as an error, in mixed selections too; ordinary deliberate
skips keep their behaviour. `ODOO_REQUIRE_INFRA=0` is the explicit opt-out for
an incomplete local run and warns that coverage is missing; a post-install
phase that prepared tests and started none fails the run regardless.
`tests/framework/test_required_infrastructure.py` and
`tests/loading/test_post_install_exit_code.py` pin both.

**Suites interfere through the registry.** `test_http` depends on `mail`,
whose `res_partner_views.xml` inherits `base.view_res_partner_filter` anchored
on `<filter name="inactive">`, and base's
`test_hard_reset_from_file_still_works` overwrites that view with a minimal
`<search>`. The write re-validates the children, so `-i base` is green while
`-i base,test_http` raises `ValidationError`. One database per suite.

## Known boundary exceptions

**None that are debt.** Two, both `core-does-not-depend-on-addons`, both
scoped to `odoo.service`: `service/_threaded.py` and `service/_worker.py` call
`IrCron._process_jobs` / `IrJob._process_jobs`, `@staticmethod` entry points
that open their own cursor because they run *before* a registry exists for the
database, so there is no `env` to route through. Both imports are deferred to
call time (four call sites), and no override of either exists anywhere in
`odoo`/`enterprise`/`agromarin`.
