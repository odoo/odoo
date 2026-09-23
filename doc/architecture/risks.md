# Risks — where the implementation and the design disagree

> Referenced by [`ARCHITECTURE.md`](ARCHITECTURE.md). The views describe the
> architecture as it is meant to work. This page records where it
> **demonstrably does not**, or where the guarantee is thinner than the word
> suggests.

Each entry names what is wrong, the evidence, what it would cost, and what would
close it. **No entry here is speculative.** Anything needing a "might" is not a
risk, it is a question — those live at the bottom of the view that owns the
subject, under *what this view does not cover*.

| # | Risk | Severity |
|---|---|---|
| R1 | The layering is true of imports and false of the runtime graph | Medium |
| R2 | Migration stage (`pre`/`post`) is unenforced and unrecoverable | High |
| R3 | The DB-free tiers cannot see behaviour | High |
| R4 | Headless test runs skip the tours they select | High |
| R5 | `web` publishes no API | Medium |

---

## R1 — The layering is true of imports and false of the runtime graph

**What.** The direction contracts are clean and always will be, because Layers 1
and 2 reach the runtime through `self.env` / `self.pool`, which produces no
import edge. The two layers reach the `Registry` about as often (31 member
accesses each, 2026-09-11) and Layer 2 names more distinct members (18 against
10), three of them private.

**Evidence.** [`module.md`](module.md#the-layering-is-true-of-imports-and-false-of-the-runtime-graph).

**Cost.** A reader who takes the layer diagram as the whole picture predicts the
wrong blast radius for a change to `Environment` or `Registry`. A comprehension
risk, not a correctness one — which is why it is Medium.

**What would close it.** Nothing, strictly — the seam is the design. It is
recorded so the diagram is never read alone.

## R2 — Migration stage is unenforced and unrecoverable

**What.** `pre` is the only migration stage that can observe the old schema;
once the module graph converges, the columns have changed. A migration that
needs the previous representation and is filed as `post-` has nothing to read.

**Evidence.** `modules/migration.py::migrate_module`; threaded in
[`scenarios.md`](scenarios.md#scenario-b--upgrading-a-database-that-holds-data).
The stage semantics themselves are pinned by
`tests/loading/test_migration_schema_visibility.py` (`pre` sees no new column,
`post` sees it), and a script whose prefix matches no stage is reported by
`_warn_unstaged_scripts`.

**Cost.** Silent data loss on upgrade of a populated database. No test of the
framework can distinguish a `post-` script that wanted the new schema from one
that needed the old.

**What would close it.** Nothing mechanical: the remaining half is a property of
each migration an addon author writes. A review rule, not a gate. What shortens
the loop is `odoo-bin schema_diff -d <db> -u <module>` (2026-09-22): the upgrade
runs in a transaction the command rolls back, and its DDL, migrations and
catalog churn are printed -- an idle `-u sale` on the four-module set reads 14
idempotent statements in 12 s, a `-i mail` on `base` 994, and a migration that
would stop the run stops the preview with the same error. The production-copy
rehearsal still owns the whole answer; this is the minute before the twenty.

## R3 — The DB-free tiers cannot see behaviour

**What.** Tier 1 and Tier 2 read import graphs, call graphs and in-memory
models; neither executes the framework against PostgreSQL. A change can satisfy
both and still be wrong at runtime.

**Evidence.** As of odoo `f7e799ce3578` (2026-09-13) no dispatch site branches on a
capability instead of calling the port, and record rules, the parent store and
translation echoes run on `InMemoryBackend` as they do on PostgreSQL. Re-read
2026-09-14: the one site `odoo/orm/tests/test_backend_dispatch_surface.py` still
marks `LOSSY` is `_read_group`, for `sum_currency`, an order by an array
aggregate and an order term outside the groupby; fetch bookkeeping, the jsonb
merges, the company-dependent guards on unlink and `load()` (with the real
`ir.fields.converter` handed to an isolated registry) run on both tiers, and
`model_test_env` ends every test with `Cache.check` against its rows as
`TransactionCase` does against PostgreSQL. Re-read 2026-09-15: the `_has_cycle`
walk, the counter increment and the transient vacuum's backlog probe are port
methods (no capability flag is declared any more), grouping sets and the
empty-having probe run through `read_grouping_sets_rows` / `read_group_rows`, and
the in-memory unlink lets a referrer the batch deletes refuse nothing, as the SQL
scan after DELETE does -- one "same verdict" note in the inventory was false until
then. Access rights and record rules stay outside the tier by design and raise
loud markers.
Re-read 2026-09-22: `base` itself is hosted. `module_model_classes("base")`
builds a 151-model registry from its real definition classes, the dict storage
reads a root table through its children as PostgreSQL's `INHERITS` does (the
shared id space of `ir.actions` that stopped it before), `_create_fixtures`
mirrors `base_data.sql`'s superuser row so base's own `res_users_data.xml`
loads over it, and `load_module_data(env, "base")` runs 66 of the 67 data
files through the loader's own converter -- the one left, `ir_module_module.xml`,
names categories `Module.update_list()` creates from manifests, which is the
loader's job and not a file's. `orm/tests/test_host_base_dbfree.py` (about 30 s,
most of it the currency and country files) pins the result: 162 ACL rows, 37
rules, an internal user reading 3 partners and refused an `ir.access` row, a
portal user reading its own, an act_window read through
`ir.actions.actions`. **A module's own test classes run on it** (2026-09-22): `InMemoryCase`
(`odoo/tests/in_memory_case.py`) is a `TransactionCase` that overrides one
method, `_open_class_transaction` -- the whole of what binds a case to a
database, extracted for it -- so the per-test savepoint, the cache clears and
the callback restore are inherited, and **a hosted class's own `setUpClass`
builds its fixtures in the environment the case actually uses**. That
ordering is what made hosting general: while the in-memory environment was
installed *after* the hosted `setUpClass` ran, every class fixture landed in
the database and the tests then ran against an environment that did not have
it. `base/tests/test_in_memory_host.py` now hosts thirteen classes from six
of base's own test modules -- config parameters, groups (including the
cache-invalidation and privilege-sorting suites), currencies, languages and
the three `Form` suites -- bodies untouched, only the base class differing:
**72 tests, 0 failed, of which 4 are skipped by name as database-bound**
(three read through hand-written SQL, one opens a second cursor to race an
INSERT). The `Form` classes say `hosts_modules = ("base", "web")`, `web`
being where `onchange()` lives. `/base` reads 4043 tests with them against
3980 without.
One environment is built per module set and shared by every class naming it,
each class taking a savepoint over it: the thirteen classes cost 1 m 43 s in
total against some 30 s *each* when every class built its own.
Three defects were found by hosting these classes, and two are the tier's
fidelity rather than the harness's:
- **A search over a relation answered differently here than on PostgreSQL.**
  To SQL a many2many is a table and a join reads the link row without
  consulting the comodel's `active`; the in-memory search evaluates the
  domain with `filtered_domain`, whose relational read applied `active_test`.
  `res.company` searched on `user_ids` therefore missed the inactive
  superuser, which is every `env.companies` of a test. The evaluation runs
  with `active_test=False` now -- the model's own active condition is already
  in the domain the optimizer hands the backend.
- **The tier reflected a model once, under the module that defines it.** The
  loader reflects it once per module that defines *or extends* it, so
  `web.model_res_company` exists on a database and web's report bindings name
  it. The seeding mirrors `_reflect_models`/`_reflect_field_params` now.
- A query budget cannot be graded where there are no statements:
  `assertQueryCount` and `assertQueriesConstant` run the body and leave the
  count to the database-backed run of the same test.
What that leaves: the eligibility figures
([`ARCHITECTURE.md`](ARCHITECTURE.md#forces)) still say which tests *could*
run without a database, and moving a suite is a base-class change per class.

**Cost.** A green DB-free run reads as "the framework works" when it means "the
structure holds". Nearly every integration suite is run `--no-http` (R4), so
what "runs addon tests" executes is the database half of each suite and not its
browser half.

**What would close it.** Broadening the integration suites — more suites, and a
server under the ones already there — is the only lever; DB-free gates cannot
reach this class of defect by construction.

*Differential coverage, re-read 2026-09-16.* Where the same claim is asserted
on both backends, a divergence of the emulation fails somewhere: the x2many
scope invariant runs the same random walk in memory
(`orm/tests/test_x2many_scope_invariant_dbfree.py`) and on PostgreSQL
(`base/tests/test_x2many_cache_scope.py::TestX2manyScopeInvariant`); row
operations (`has_cycle`, the skip-locked increment, the restrict guard) and
grouping sets are pinned on both, and `_InMemoryReadGroup` — 520 lines of
grouping, granularity and aggregate emulation on 2026-09-21 — is drawn against PostgreSQL by
`test_read_group/tests/test_backend_matrix.py::TestReadGroupBackendWalk`:
random rows, then random `_read_group` calls (groupbys, granularities,
aggregates, orders, havings, limits, offsets) run through both tiers and
compared row for row, twelve seeds each for scalars, for temporal
granularities and for grouping sets. Its first run found the array-aggregate
order the inventory had marked unsupported; the grouping-sets draw found that
a many2one order term sorts the sets that lack it by `ANY_VALUE()` of the
joined name, which PostgreSQL picks per group and the in-memory tier drops —
no caller orders a set by a column it does not group by, so the draw keeps
the many2one out of sets that lack it rather than pin either reading. What it
does not draw: many2many and property groupbys and `sum_currency`, which keep
their hand-written cases.

## R4 — Headless test runs skip the tours they select

**What.** Every `HttpCase` — a tour, and any test that drives a browser or an
HTTP client against the server — needs a running HTTP server, and `--no-http`
starts none. A HOOT run does not reach a tour either: it mounts components
against a mock server. Between the two, a tour runs nowhere unless someone runs
the suite with a server. Of the suites in [`gates.md`](gates.md), only `rpc`,
`mail`, `test_mail`, `mail_group` and `speech` run served.

**Evidence.** `OdooTestResult` treats a class whose `setUpClass` skips for
missing infrastructure as an error by default (`ODOO_REQUIRE_INFRA`), and a
post-install phase that prepared tests and started none fails the run, so a
headless run no longer reports the skipped half as a pass — it reports it as
missing, and the tours still do not run.

**Cost.** A tour regression lands and stays until somebody runs the suite by
hand with a server. Every `--no-http` flag is a decision that the tour classes
of that suite are deferred.

**What would close it.** Chrome on the machine and the flag dropped suite by
suite, each drop paired with a passed-test count floor set to the served
figure. The entry closes when no suite is run headless.

## R5 — `web` publishes no API

**What.** Everything under `addons/web/static/src` is reachable as
`@web/<path>`. Every specifier a sibling repository (`enterprise`,
`agromarin`, `design-themes`) imports is a rename `web` cannot perform
unilaterally, and nothing records which specifiers are reached from where.

**Evidence.** `grep -rhoE "@web/[a-z_/]+" enterprise agromarin design-themes
--include=*.js | sort -u` is the surface; no file in the tree holds it.

**Cost.** A rename inside `web` breaks a sibling checkout with no signal in
`web`'s own suites; the break surfaces in whichever workspace next loads the
sibling.

**What would close it.** A face rule — consumers enter a directory at its
`index.js` or a published module, never at a file beneath — and a recorded
surface that can only shrink.

---

## Adding an entry

Give it a number, the evidence that makes it checkable, the cost if it bites,
and what would close it. An entry with no closing condition is a complaint.
