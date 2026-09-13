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
each migration an addon author writes. A review rule, not a gate.

## R3 — The DB-free tiers cannot see behaviour

**What.** Tier 1 and Tier 2 read import graphs, call graphs and in-memory
models; neither executes the framework against PostgreSQL. A change can satisfy
both and still be wrong at runtime.

**Evidence.** As of odoo `f7e799ce3578` (2026-09-13) no dispatch site branches on a
capability instead of calling the port, and record rules, the parent store and
translation echoes run on `InMemoryBackend` as they do on PostgreSQL; what
`odoo/orm/tests/test_backend_dispatch_surface.py` still marks `LOSSY` is fetch
bookkeeping (`bin_size`, to-flush), jsonb translation merges and
company-dependent columns on update, and the `ir.default` cleanup on unlink.
The gap that remains is not in the port but in the harness: a module's test
class cannot yet be hosted on the in-memory tier, because building a registry
from `base`'s real models and their data files stops at the shared id space of
`ir.actions` -- so the eligibility figures ([`ARCHITECTURE.md`](ARCHITECTURE.md#forces))
say which tests *could* run without a database, not which do.

**Cost.** A green DB-free run reads as "the framework works" when it means "the
structure holds". Nearly every integration suite is run `--no-http` (R4), so
what "runs addon tests" executes is the database half of each suite and not its
browser half.

**What would close it.** Broadening the integration suites — more suites, and a
server under the ones already there — is the only lever; DB-free gates cannot
reach this class of defect by construction.

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
