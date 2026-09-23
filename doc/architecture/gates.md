# The gates — what is mechanically enforced, and what that is worth

> Referenced by [`ARCHITECTURE.md`](ARCHITECTURE.md). The architecture is in
> [`module.md`](module.md) and [`runtime.md`](runtime.md); this file is the
> operator's manual for the machinery that keeps them true.

What is enforced is the standard tools on their pinned versions, the pytest
tiers, `test_lint`, and the DB-backed suites. The database-free gates run as
one command, `./gates.sh`, from the repo root, and `.github/workflows/gates.yml`
is the same command on a runner. Fifteen of the dependency rules in
[`module.md`](module.md#dependency-rules) are Tier-2 tests
(`tests/framework/test_layer_contracts.py`); the ORM half of the façade
boundary is `test_lint`'s; the rest are held by review.

## Running the checks

```bash
./gates.sh                                     # everything below the line, one exit code
./gates.sh --fast                              # lint and the two tiers
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
`gates.sh` keeps that bare environment under `~/.cache/odoo-gates/`. `mypy.ini`
holds `odoo.orm` to `disallow_untyped_defs` and `disallow_incomplete_defs`
outside its test trees (0 on 2026-09-22, from 384 that morning): a function
added to the ORM without a complete signature fails the core lane. `BaseModel`
declares `env: Environment` (the mixins keep `Any` for their own shortcuts), so
an addon's `self.env` is typed; `odoo-bin stubs -d <db>` writes
`odoo_registry_stubs.pyi` from a live registry and `mypy_registry_plugin.py`
(repo root, standalone so the checker never runs the framework bootstrap)
types every `env["<name>"]` from it. With generated registry types loaded, an
unknown literal model name is an error; dynamic strings retain the base type.
Finite unions of literal names retain the union of their model types and check
every alternative against the generated registry.
On generated recordsets, `mapped()` uses literal field paths to distinguish
scalar lists from related recordsets, including dotted paths and empty paths.
Unknown fields and scalar traversal are errors. Record-valued callbacks retain
their recordset type; dynamic paths and mixed scalar/record callbacks remain
`Any`. Field metadata changes recheck mapped callers in a running daemon.
A literal lookup with missing or empty registry types reports a setup error.
Regenerating the stub rechecks model lookups in the running mypy daemon.
Generated methods preserve staticmethod and classmethod binding, and model
class names avoid the stub's own imported and generated names. Optional
parameter defaults and coroutine methods retain their call semantics. Generated
stubs preserve readable properties and whether they have a setter, without
invoking their getters during generation. Property values remain `Any`. The CLI
stages the complete stub on the destination filesystem before replacing it,
so readers and failed writes preserve the preceding complete snapshot.
Measured on `sale/models` + `stock/models`
against the four-module set's stubs with `check_untyped_defs`: 3 222 readings
without the plugin, 2 854 with it -- 413 attribute complaints resolved, 56
additional diagnostics (a `Char` handed to `dict.get`, a recordset assigned
where an `OrderedSet` was declared, `with_company` given `Any | BaseModel`).
The `with_company` diagnostic was a declaration defect: a company record need
not have the receiver's model. Its input now accepts model records and the
environment's company protocol, while its result retains the receiver's type.
`doc/architecture/factcheck.sh` derives the figures these pages state (mixin
composition, base-model reaches, executed statements, dispatch sites) from the
classes and the pin tests, and fails when a page stops citing one.

The module machine docs are gated the same way, one `gates.sh` row per harness:
every `addons/*/machine_doc_v*/factcheck.sh`,
`odoo/addons/*/machine_doc_v*/factcheck.sh` and
`odoo/tests/machine_doc_v*/factcheck.sh` the tree holds is discovered and run,
so a new harness is gated the day it lands: a module that adds a model, a file
or a test without its machine doc fails `gates.sh` instead of leaving a red for
the next reader. Each gets the same interpreter as the other steps (`ODOO_VENV_PYTHON` and `VENV_PY`) and,
when the venv has an `<env>.conf` beside the checkout, `ODOO_CONF`, which
`web`'s `prepare_suite` counts need. Under `--ref` the worktree has no sibling
checkouts, so assertions about `enterprise`, `agromarin` or `design-themes`
report SKIP rather than pass; the repository's own figures are still checked.
Like the architecture figures they run in the full lane, not under `--fast`.
A harness whose check needs a named database (`web`'s bundle sizes,
`FACTCHECK_DB`) skips without one.

**`test_lint`** (`odoo/addons/test_lint/tests/`) holds the rules no general
linter knows — SQL-injection shapes, gettext discipline, N+1 query shapes,
manifest and XML conventions, record-field order, and `orm-import` (`E8508`):
addon code outside tests must reach the ORM through `odoo.api` / `odoo.fields`
/ `odoo.models`, never `odoo.orm.*`. Its floors live in
`odoo/addons/test_lint/tests/floors.json`, one integer per gate;
a gate with no entry is a hard zero. `assert_ratchet` is exact: a count above
the floor fails, and a count below it fails until the floor is lowered in the
same change.

Four real-dependency pytest suites are in no `testpaths` and run only when
named: `tests/contract` (`ODOO_CONTRACT_REQUIRE_DEPS=1`; PostgreSQL + psql +
pg_dump), `tests/process` (boots real `odoo-bin` processes), `tests/loading`
(installs `base` into a scratch database; pins the loader phase order, the
uninstall reload, migration ordering and migration-stage schema visibility)
and `tests/perf` (`./gates.sh --perf-counts` in CI, `--perf` for local timing;
installs `base` and the four-module set
`sale,purchase,stock,account` into two scratch databases and reads the ORM's
cost on them: statements per `res.partner` create, batch create, write loop,
batch write and `search_fetch`, per `sale.order` create and create+confirm, and
per order entry by a salesman through the form (`odoo.tests.Form`: the
onchanges for a customer and three lines, the save, the confirmation; its time
is the server's, `_bench.ServerClock`, not the form emulation's), as
**exact ratchets** for every measured operation, residual wall time — wall minus
driver, the fastest of the rounds, the median kept beside it — and the warm
`Registry loaded in` as **one-sided
floors** with a 25 % tolerance
(`ODOO_PERF_TOLERANCE`), plus the in-memory tier's cost per create and per
stored compute. The floors are `tests/perf/floors.json`, one machine's,
moved in the same change that moves the count; a reading below a time floor
passes and is the cue to lower it. **A time floor is judged only on a machine
running at the speed it was set on**: every check first times a fixed
interpreter-bound loop (`_bench.calibration_ms`), and above the file's
`calibration_ms` reference plus the tolerance the time floors print "not
judged" instead of failing; statement counts stay exact either way. The same
code read 51 and 127 ms an hour apart as this machine throttled, and dividing
by the calibration over-corrected (the loop slowed 3× where the ORM slowed
1.9×), which is why it gates rather than scales. Re-read the reference, on a
calm machine, whenever the floors are re-read. Attribute *where* time goes with a
signal-based sampler on the main thread, never cProfile shares or a sampling
thread: `agromarin-knowledge/research/2026-09-22-orm-best-in-class.md` §6).

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

Performance runs retain wall time, thread CPU time, driver time and residual wall
time separately in the perf-results.json artifact. CI enforces statement counts against a
PostgreSQL service; machine-specific time limits apply only with `--perf`. Missing
PostgreSQL fails the performance run instead of skipping it.

The counter measures driver submissions: one execute, executemany or COPY call
is one statement. SQL time includes pipeline synchronization waits. Batch creation
now counts COPY too; its baseline correction is recorded in qualities.md.
