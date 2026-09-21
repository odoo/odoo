# Scenario view — end-to-end threads through the other views

> One of the views indexed by [`ARCHITECTURE.md`](ARCHITECTURE.md).
> Each other view is a projection: modules, runtime, data, deployment. A
> scenario is a **thread that crosses all of them**, which is the only way to see
> an interaction no single view contains.

`runtime.md` already threads two: [process
boot](runtime.md#process-boot) and the [request
lifecycle](runtime.md#request-lifecycle-http). This page carries the two that
cross the most views and are least visible from any one of them — installing a
module, and upgrading a database that already holds data.

## Scenario A — installing a module

Entry point is `modules/loading.py::load_modules`, whose phases are named methods
on `_ModuleLoader` and run in this order:

| # | Phase | Crosses into |
|---|---|---|
| 1 | `bootstrap()` — create the base schema if the database is empty | data (DDL) |
| 2 | `run_pre_upgrade_scripts()` — *only* when upgrading existing modules | data |
| 3 | `capture_database_field_metadata()` — snapshot `ir_model_fields` **before** anything changes it | data |
| 4 | `open_environment_and_load_base()` — `base` must exist before any graph work | runtime |
| 5 | `load_languages()` | data |
| 6 | `apply_module_requests()` — "updating modules list": reconcile `ir_module_module` against `addons_path` | data + module |
| 7 | `converge_module_graph()` — resolve dependencies and load each module's Python, data and views | module + data |
| 8 | `untranslate_dropped_fields()` | data |
| 9 | `finalize_registry_setup()` | runtime |
| 10 | `run_end_migrations()` | data |
| 11 | `restore_relations_dropped_by_migrations()` — re-`init()` any view-backed table a migration took down with it | data (DDL) |
| 12 | `finalize_constraints()` — SQL constraints last, once all columns exist | data |
| 13 | `uninstall_removed_modules()` | data + module |
| 14 | `reinit_models_to_check()` | runtime |

Fourteen of `load_modules`' 24 calls, in call order. The numbering is this
table's, not the loader's; the order is pinned against a real load by
`tests/loading/test_load_modules_phases.py`. The ten left out split two ways:

| Left out | Why |
|---|---|
| `log_modules_that_never_loaded`, `log_pending_module_states`, `log_assertion_report`, `mark_database_partially_updated`, `collect_models_with_manual_fields` | reporting and bookkeeping — they cross no view |
| `register_model_hooks`, `check_null_constraints`, `warn_invalid_custom_views`, `run_post_update_model_checks`, `run_deferred_at_install_tests` | real work, selected out of *this* thread rather than out of the loader. Three of the five appear in [`runtime.md`](runtime.md#registry-build)'s sketch; the fifth runs the `at_install` suites the loader held back until their installed dependents had loaded |

Three things this ordering encodes that no other view states:

**Metadata is captured before it is mutated (3 before 7).** The comparison that
produces DDL is between the *previous* `ir_model_fields` and the field set the
loaded Python declares. Capture it after the graph converges and there is
nothing left to compare against — the schema diff is computed from a snapshot,
not from live state.

**Constraints are finalised last (12).** A constraint can reference a column a
later module in the same run adds, so applying them per module would fail on
orderings that are otherwise legal. Same argument as the flush fixpoint, applied
to DDL.

**Uninstalling can force a second full registry build.** Phase 13 may raise
`_UninstallRequiresReload`, caught and answered with a fresh `Registry.new(…)` —
logged as *"Reloading registry once more after uninstalling modules"*
(`tests/loading/test_load_modules_uninstall.py`). Uninstall is therefore the one
operation that can pay the cold registry cost **twice** in a single command; at
the cold figures in
[`qualities.md`](qualities.md#scenario-2--registry-build-and-boot), the
difference between a minute and two.

Under `workers > 0` the whole thread runs in one worker, and every other worker
learns about it only through the signalling tables — see
[`data.md`](data.md#2-the-signalling-tables--cross-process-coordination).

## Scenario B — upgrading a database that holds data

Installing into an empty database and upgrading a populated one are the *same
code path* with different consequences, and the difference is entirely in the
migration hooks. `modules/migration.py::migrate_module` runs at three stages:

| Stage | Marker | Runs | Use |
|---|---|---|---|
| `pre` | `[>version]` | **before** the module's models are loaded and its DDL applied | reshape data the new schema could not read |
| `post` | `[version>]` | after the module's data is loaded | backfill using the new schema |
| `end` | `[$version]` | after **every** module in the run has finished | cross-module reconciliation |

Scripts are discovered by filename prefix (`pre-`, `post-`, `end-`) under a
version directory, so a migration is selected by *the version being crossed*,
not by the module's current state. `_get_migration_files` selects on
`name.startswith(f"{stage}-")`, case-sensitively; a script under a version
directory that matches no stage is reported by `_warn_unstaged_scripts` as a
warning, not an error, because an addon may keep a helper module beside its
scripts. (415 scripts under `migrations/` and 8 under `upgrades/` across this
repository's two addon trees, 0 unstaged, 2026-09-11.)

The architectural consequence: **`pre` is the only stage that can see the old
shape.** Once the graph converges the columns have already changed, so a
migration needing the previous representation and written as `post` has nothing
to read. `tests/loading/test_migration_schema_visibility.py` upgrades a probe
module across a real schema change and asks each stage, through
`information_schema`, what the table looked like: the `pre` script sees no new
column, the `post` script sees it. Whether a script *wanting* the old shape was
filed at the right stage is a property of each migration an author writes and
is caught by nothing — [`risks.md`](risks.md) R2.

Two asymmetries against Scenario A:

- **Cost is not comparable.** Scenario A's cold figures install into an *empty*
  database. An upgrade additionally rewrites existing rows, and nothing in this
  document set measures that — listed as a gap in
  [`qualities.md`](qualities.md#what-this-page-does-not-measure).
- **Failure is not symmetric.** A failed install leaves a database nobody was
  using; a failed upgrade leaves one somebody was. The filestore is not
  transactional with PostgreSQL either
  ([`data.md`](data.md#the-dual-storage-seam)), so a rolled-back upgrade can
  still have written attachment bytes.

## What this view does not thread

- **Backup and restore**, which crosses PostgreSQL and the filestore and is the
  most common way a deployment is broken by a torn pair.
- **Rolling restart under `workers > 0`**, where old and new workers hold
  different registries simultaneously.
- **A cron job's lifecycle**, from `ir_cron` row to `WorkerCron` execution.
