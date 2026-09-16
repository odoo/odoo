# Module view — what exists, and who may depend on whom

> One of the views indexed by [`ARCHITECTURE.md`](ARCHITECTURE.md).
> This view answers *where does code live and what may it import*. For *what runs
> when*, see [`runtime.md`](runtime.md); for what is mechanically enforced,
> [`gates.md`](gates.md).

## Subsystem map

```
odoo/
├── orm/            The ORM, as an explicit 4-layer architecture (see below)
│   ├── primitives, parsing, validation, constants, _typing,
│   │   _protocols                                            (Layer 0)
│   ├── fields/, domain/                                       (Layer 1)
│   ├── models/  (BaseModel + 26 mixins, metaclass)            (Layer 2)
│   ├── runtime/ (Environment, Registry, Transaction, backend) (Layer 3)
│   ├── components/  pure-Python cache / compute / unit-of-work (cross-cutting)
│   ├── _recordset, model_test_env                               (seams)
│   └── decorators, registration, helpers                        (cross-cutting)
├── api/ · fields/ · models/   Thin public re-export shims over orm/ (stable imports)
├── db/             Decomposed sql_db.py + the resilience tier (flat modules)
│   ├── [foundation]   errors, dsn, utils,
│   │                  settings (PoolSettings: the frozen snapshot of the
│   │                  db_* options the pool is handed at boot)
│   ├── [connectivity] pool, cursor, ddl, schema, savepoint, schema_cache,
│   │                  bulk, lifecycle,
│   │                  endpoints (the endpoint-keyed pool/budget registry),
│   │                  replica (routes a cursor request to the replica or
│   │                  the primary through libs/breaker and the lag gate)
│   └── [resilience]   lag (replica apply-lag ceiling, db_replica_max_lag),
│                      budget (process-wide connection semaphore),
│                      leaks (who holds a checked-out connection),
│                      reaper (idle per-DSN pool reaping),
│                      probe (is this DSN reachable, permanently or not),
│                      metrics (SQL per cursor) · stats (what the pool did)
├── http/           Decomposed http.py (flat modules)
│   ├── [foundation]   constants, exceptions (the HTTP exception vocabulary),
│   │                  _protocols, settings (HttpSettings: the frozen snapshot
│   │                  of the options the serving tier reads)
│   ├── [serving]   application, dispatcher, routing, session, request_class,
│   │               _serve, _response, wrappers, stream, _csrf, controller,
│   │               core (the `request` proxy + its LocalStack), _dbfilter, _cors, _rpc,
│   │               _error_serialization, _session_lifecycle,
│   │               _retry (the RetryParticipant handed to service/transaction)
│   └── [features]  openapi (OpenAPI 3.1 from the routing map),
│                   _params (annotation-driven @route(typed=True) coercion),
│                   geoip
├── service/        Process lifecycle + the servers
│   ├── server, _base_server, _threaded (ThreadedServer + WebsocketServer),
│   │   _prefork, _reload (the master's other generation across a SIGHUP:
│   │   candidate, promotion, replacement), _census (the master's worker counts, a file its
│   │   children read for /web/metrics), _worker, _watcher (on libs/inotify), _transport (one
│   │   HTTP/1.1 exchange: head, body reader, WSGI environ, response framing,
│   │   the access log; what a prefork worker serves a connection with),
│   │   httpd (the threaded server: selector, pool, keep-alive), _cron, lifecycle,
│   │   _factory (picks and runs a server), _process_state (its two globals),
│   │   settings (ServerSettings: derived from the live config on each current() read; a change is logged when the lifecycle channel is on)
│   ├── db/         Database management, the /web/database/manager service
│   │               (seven modules in one-way order). Reads downward:
│   │               rpc -> {restore -> {lifecycle, listing, _dump_scanner},
│   │                       dump -> listing, lifecycle -> listing},
│   │               every one of them over _checks (the db-name, master
│   │               password and list_db guards)
│   └── transaction (the retrying() primitive), model, security, common,
│       _dispatch (arity policy + db-name exposure for the common/db RPC tables),
│       _env, _limits (time/memory/back-off budgets),
│       _sdnotify (READY/RELOADING/STOPPING/WATCHDOG to the service manager),
│       metrics (the Prometheus exposition web serves at /web/metrics)
├── modules/        The module graph (iterated by phase, dependency depth,
│   │               then name) and what loads it
│   └── module_graph, module, loading, migration, db, neutralize,
│       _protocols (what a loader needs of a cursor, narrower than one),
│       registry/ (a re-export shim — `Registry` itself is Layer 3, in
│                  `orm/runtime/registry.py`)
├── tools/          Odoo-COUPLED utilities (need ORM / config / runtime)
│   ├── assets/     Server-side asset pipeline (esbuild + ESM graph/bridges/
│   │               registry/lexer)
│   ├── pdf/        PDF reading/writing/merging + `PdfSigner` (CMS/PKCS#7)
│   └── babel_extractors/   Babel message extractors for Python and JavaScript
├── libs/           Odoo-AGNOSTIC utilities (no framework dependency)
├── _monkeypatches/ Explicit, import-hook-driven third-party patches
│                   (`PatchImportHook` on `sys.meta_path`; every
│                   non-underscore submodule exposes `patch_module()`)
├── cli/            Command-line entry points
└── addons/         The bundled base addons — `base` plus the `test_*` suites,
                    and only those. (`web` and the rest of the standard addons
                    live in the repo-root `addons/`, the second tree described
                    under *Public import surface*; this map is rooted at
                    `odoo/odoo/`.)
```

`service/` reads in one direction. `lifecycle` is what the server classes
import (preload, the re-exec, resident-registry sizing); `_process_state` holds
the `server` and `server_phoenix` globals they reach for; `_factory` picks a
class and runs it, so it sits above all three. Six `service` submodules read
live process state through `from . import _process_state`.

> **Notation.** A name ending in `/` is a directory and a bare name is a module.
> A name in `[brackets]` is a **logical grouping, not a directory** — `db/` and
> `http/` are flat packages, and the bracketed labels group their modules by
> role. Where the map enumerates a package's contents it does so exhaustively,
> per kind; an added module is written in by hand.
>
> **The bracketed tiers carry contracts of their own** —
> `db-resilience-below-connectivity` and `http-features-below-serving`, both in
> the table below. Filing a module in the right bracket is a decision, not a
> caption: `db/errors.py` and `dsn.py` import nothing else in `db/` and are
> used by both tiers; `utils.py` imports only its `[foundation]` sibling
> `settings` and, since its statement-text scanners moved to `ddl.py`
> (2026-09-13), is read by `[connectivity]` alone — it stays `[foundation]`
> for what it imports, not for who reads it;
> `http/_dbfilter.py`, `_cors.py`, `_rpc.py` and `_error_serialization.py` (one
> `helpers.py` until 2026-09-15) import `core` and are imported by
> `dispatcher`/`_serve`/`_session_lifecycle`, so they are `[serving]`, not
> `[features]`; `http/constants.py`, `exceptions.py` and `_protocols.py` import
> nothing else in `http/` at runtime and are read by both tiers, so they are
> `[foundation]`, and `http-features-below-serving` holds them below `[serving]`
> alongside `[features]`.
>
> `http/_protocols.py` names `Dispatcher`, `GeoIP`, `Session`, `FutureResponse`,
> `HTTPRequest` and `Response` from the tiers above it — legal, because every
> one is inside `if TYPE_CHECKING:` and never executes. An import count that
> does not honour the guard reports violations against a tier that has none.

### Ownership and legal direction

Each package owns one concern and may only depend downward.

| Package | Owns | Must not import | Contract |
|---------|------|-----------------|----------|
| `libs/` | Odoo-agnostic utilities | any `odoo.*` except `odoo.libs` | `libs-is-dependency-free` |
| `db/` | connections, cursors, DDL, pool resilience | any `odoo.*` except `odoo.libs`, `odoo.exceptions`, `odoo.release` — the ORM by `db-is-orm-agnostic`, and `odoo.tools` with everything else by `db-imports-only-libs`, so its settings arrive as a `PoolSettings` snapshot | `db-is-orm-agnostic`, `db-imports-only-libs` |
| `orm/` | models, fields, domains, Environment/Registry/Transaction, cache & compute | `odoo.service`, `odoo.http`, `odoo.cli` | `orm-below-the-serving-tier` |
| `tools/` | Odoo-coupled utilities | `odoo.orm.runtime` (Layers 0–1 stay allowed); `odoo.http` at module scope | `tools-does-not-reach-the-orm-runtime`, `tools-stays-below-the-serving-tier` |
| `modules/` | the module graph and what loads it | `odoo.addons.<module>` | `core-does-not-depend-on-addons` |
| `http/` | the WSGI application, routing, dispatch, sessions | `odoo.addons.<module>` | `core-does-not-depend-on-addons` |
| `service/` | process lifecycle, the servers, cron, RPC services | `odoo.addons.<module>` (2 exceptions) | `core-does-not-depend-on-addons` |
| `cli/` | command entry points | `odoo.addons.<module>` | `core-does-not-depend-on-addons` |
| `addons/` | the bundled base addons | `odoo.orm.*` | `facade-boundary` |

`_monkeypatches/` sits outside the direction rules by construction: it runs
before anything else (see **Process boot**) and patches third-party modules only.

### `tools/` has a third role: it is the façade for part of `libs/`

`tools/__init__.py` re-exports **22 of its 105 `__all__` symbols straight from
`odoo.libs`** — `SQL`, `float_round`, `float_compare`, `classproperty`, `lazy`,
`parse_version`, `SetDefinitions`, `pg_varchar`, `get_index_name` and 13 more.
Following each exported symbol one hop further — into the `tools` submodule
that supplies it — **59 of the 105 come from `odoo.libs`**, the other 46 from
`tools`' own modules (counted 2026-09-11).

Cost: at the point of use `from odoo.tools import float_round` and `from
odoo.tools import config` are indistinguishable, though one is a pure function
and the other reaches the whole runtime.

Resolve by *import*, not by `__module__`: `html_escape` and `single_email_re`
report `markupsafe` and `re` at run time, being a re-exported third-party alias
and a compiled pattern, so a live-attribute sweep answers 57.

| Caller | Import | Why |
|---|---|---|
| addon code | `odoo.tools`, either kind | the façade is the published surface |
| core code | the owning package — `odoo.libs.sql`, not `odoo.tools`, for `SQL` | a module's imports must state which layer it depends on |

### Public import surface

Addon code imports **`odoo.api`, `odoo.fields`, `odoo.models`** — never
`odoo.orm.*`. Each is an `__init__.py` re-export shim with an explicit
`__all__`, which is what lets the ORM's internal layout move without breaking
addon imports. `test_lint`'s `orm-import` rule (`E8508`,
`_checker_orm_import.py`) fails any runtime `odoo.orm.*` import in addon code
outside tests (`if TYPE_CHECKING:` exempt).

The serving tier has the same rule in a different shape. `odoo.http` and
`odoo.service` are packages whose public door is the package itself —
`odoo.http.ParamSpec`, `odoo.http.HttpExtension`, `odoo.service.get_env_str`,
`odoo.service.get_job_real_time_budget`, `odoo.service.metrics` — and whose
underscore-prefixed modules (`http/_params.py`, `service/_limits.py`,
`service/_env.py`) are theirs alone. Addon code does not import them; nothing
mechanical checks that.

| Tree | Module name | Note |
|---|---|---|
| `odoo/addons/` | `odoo.addons.*` | `base` plus the `test_*` suites |
| repo-root `addons/` | `addons.*` | mounted at `odoo.addons.*` by the addons-path loader at run time |

## The ORM layer model

The ORM is organised as strict layers; **runtime imports point downward only.**
Cross-layer references for *typing* are allowed when guarded by
`if TYPE_CHECKING:` (they never execute), which is how the layers share types
without forming import cycles.

```
Layer 3  runtime/      Environment, Registry, Transaction        ─┐ imports
Layer 2  models/       BaseModel, mixins, metaclass, table objs   │ downward
Layer 1  fields/ domain/   Field types, domain AST + optimizer    │ only
Layer 0  primitives parsing validation constants _typing _protocols ─┘

         components/   FieldCache · ComputeEngine · UnitOfWork · ModelGraph
                       Beside the stack, not under it: Layers 2 and 3 import
                       it, Layers 0 and 1 never do. Pure Python — no odoo
                       imports at runtime except odoo.libs. Collaborators
                       injected.
```

| Layer | May import | Notes |
|---|---|---|
| **0** `primitives` `parsing` `validation` `constants` `_typing` `_protocols` | no higher *ORM* layer | Forbidden set is `orm.fields`, `orm.domain`, `orm.models`, `orm.runtime`, `orm.components` **and** the façades `odoo.fields`/`odoo.models`/`odoo.api` — a re-export shim is the obvious way round a rule written only against `odoo.orm.*` |
| **1** `fields/` `domain/` | Layer 0 | Imports `components/` nowhere |
| **2** `models/` | Layers 0–1, `components/` | `mixins/recompute.py` → `components.recompute.RecomputeScheduler` |
| **3** `runtime/` | Layers 0–2, `components/` | Owns the instances: `Transaction` constructs `FieldCache`, `ComputeEngine`, `UnitOfWork`, `OrmCore`, interns every `Environment` and owns the flush policy |

The invariant at every layer is "nothing from the ORM above it", not "nothing
from `odoo`": all four import `odoo.tools`, `odoo.libs` and `odoo.exceptions`
freely.

**No ORM module imports `odoo_rust`.** The extension enters through one seam,
`odoo/libs/accel.py`, which resolves each accelerated name to the native
function or its pure-Python twin once at import; the ORM, `db/` and `web` reach
them from there, so whether a process runs on the extension is decided in one
place. `odoo/init.py` makes its absence fatal only under `ODOO_REQUIRE_NATIVE`
or `CI`; elsewhere it warns and runs on the fallbacks. The only other
importers are `odoo/init.py` and `odoo/libs/lint/scan.py`.

`orm/__init__.py`'s docstring states the same layer model member by member.

### `components/` — the two cache APIs

The cache/compute/unit-of-work engine. Pure Python apart from `odoo.libs`
(`model_graph.py` imports `Collector`), collaborators injected rather than
imported.

Two cache APIs, at different abstraction levels. **Both are sanctioned.**

| API | Key | Reached as | Owner |
|---|---|---|---|
| `OrmCore.get_value(field, record_id)` | raw id | `env.core` (`components/core.py`) | curated façade over the raw objects |
| `Cache.get_values(records, field)` | *recordset* | `env.cache` | resolves the field cache through the recordset's `env` |

`env.cache` is **not** a wrapper over `core`. It is what saves a caller from
knowing that a context-dependent field lives in the cache's *context* store,
`{cache_key: {id: value}}`, while every other field lives in its *flat* store,
`{id: value}`, or that a term-translated one is reached through a
`LangProxyDict`. A mechanical rewrite onto `core` would mishandle those
layouts and couple addon code to private field helpers.

**The two stores are addressed, never inferred.** `FieldCache` keeps the flat
values and the per-context sub-caches in separate mappings, so which shape a
field has is decided by the method a caller picks — `get_field_data` /
`get_context_data(field, key)`, `get_cached_ids` / `get_context_cached_ids`,
`has_any_cached` / `has_any_context_cached` — and `invalidate` sweeps both. No
method looks at a key to guess whether it is a record id or a context tuple; a
field that reaches the wrong store finds it empty. Layer 1 (`fields/`,
`domain/`) sees the cache **only** through those named `OrmCore` methods (31
`env.core` reaches on 2026-09-11).

The raw objects stay private to `Transaction` (`_cache_store`,
`_compute_engine`).

> **"Pure" is a direction claim, not an isolation claim.** The contract is about
> this package's imports. A component still cannot be imported alone:
> `import odoo.orm.components.model_graph` executes the parent package, and
> `orm/__init__.py`'s last line is `import odoo.init` — the bootstrap, which
> applies `_monkeypatches` and so loads `babel` (and `lxml` through it). Hence
> `components/tests/conftest.py` stubs the `odoo` / `odoo.orm` /
> `odoo.orm.components` namespace packages through
> `odoo/_testing_bootstrap.py::stub_odoo_packages` instead of importing them.
> Read "unit-testable" as "needs no ORM runtime objects", not "costs nothing to
> import".

## Dependency rules

Module-level imports only; `if TYPE_CHECKING:` bodies and function-local
imports are outside every rule (a deferred import is the sanctioned way to
break a cycle). Fifteen are tests in `tests/framework/test_layer_contracts.py`
(Tier 2), which fail on the offending line; the rest are held as the table says.

| Contract | Rule | Enforced by |
|----------|------|-------------|
| `libs-is-dependency-free` | `odoo/libs/**` must not import `odoo.*` (except `odoo.libs`) | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `db-is-orm-agnostic` | `odoo/db/**` must not import `odoo.orm/models/fields/api` | `tests/framework/test_layer_contracts.py` (Tier 2) (as `db-imports-only-libs`) |
| `db-imports-only-libs` | `odoo/db/**` imports `odoo.libs`, `odoo.exceptions`, `odoo.release` and the standard library, nothing else — not `odoo.tools`, whose option dict reaches the pool as the typed `PoolSettings` snapshot `odoo.tools.config` builds and hands in | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `tools-does-not-reach-the-orm-runtime` | `odoo/tools/**` must not import `odoo.orm.runtime` (Layers 0–1 stay allowed) | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `tools-stays-below-the-serving-tier` | `odoo/tools/**` must not import `odoo.http` **at module scope**; an import inside a function is the sanctioned form (`assets/esm_bridges.py`, `cache_version.py`, `urls.py` each take `request` that way), because the contract bounds what the layer costs to *load*, not what it may use | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `orm-helpers-and-registration-stay-below-runtime` | `orm/helpers.py` & `orm/registration.py` must not import `orm/runtime` | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `orm-components-are-pure-python` | `odoo/orm/components/**` must not import `odoo.*` (except `odoo.libs`) | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `orm-layer0-is-foundational` | Layer-0 (`primitives`, `parsing`, `validation`, `constants`, `_typing`, `_protocols`) imports no higher ORM layer | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `orm-layer1-below-models-and-runtime` | `orm/fields` & `orm/domain` must not import `orm/models`, `orm/runtime` or `odoo.db`; `fields/_field_ddl.py` → `odoo.db.schema` is the one exception, the only Layer-1 file that issues DDL | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `orm-models-below-runtime` | `orm/models` (Layer 2) must not import `orm/runtime` (Layer 3) | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `orm-seams-stay-below-models-and-runtime` | `orm/_recordset` & `orm/decorators` must not import `orm/models` or `orm/runtime` | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `facade-boundary` | addon code (`odoo/addons/**` **and** the repo-root `addons/**`) must not import `odoo.orm.*` (use `odoo.api`/`odoo.fields`/`odoo.models`), nor a private module of `odoo.service` or `odoo.http` (`odoo.http._params`, `odoo.service._limits` — use what the package exports) | `test_lint` `orm-import` (`E8508`) for the `odoo.orm.*` half; review for the private-module half |
| `core-does-not-depend-on-addons` | core packages must not import `odoo.addons.<module>` (bare `odoo.addons` for `__path__` discovery is fine — `tools/assets/esbuild.py` does) | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `db-resilience-below-connectivity` | `db/` `[resilience]` (lag, budget, leaks, reaper, probe, metrics, stats) must not import `[connectivity]` (pool, cursor, ddl, schema, savepoint, schema_cache, bulk, lifecycle, endpoints, replica) | `odoo/db/tests/test_source_pins.py::TestThePackageImportsOnlyWhatItMayDependOn` (Tier 2) |
| `http-features-below-serving` | `http/` `[features]` (openapi, `_params`, geoip) and `[foundation]` (constants, exceptions, `_protocols`, settings) must not import `[serving]` | `odoo/http/tests/test_layer_contract.py` (Tier 2), module-scope imports outside `TYPE_CHECKING` |
| `orm-below-the-serving-tier` | `odoo/orm/**` must not import `odoo.service`, `odoo.http` or `odoo.cli` — the serving tier runs on the ORM, never the reverse | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `transaction-primitive-is-transport-agnostic` | `odoo/service/transaction.py` must not import `odoo.http` — the transport injects a `RetryParticipant` instead, the shape by which `db/` receives its flushing savepoint | `tests/framework/test_layer_contracts.py` (Tier 2) |
| `root-modules-are-foundational` | `odoo/exceptions.py` & `odoo/release.py` must not import `odoo.*` except `odoo.libs`. **Not** `logutils.py`, which imports `db`/`tools` and is a consumer of the stack | `tests/framework/test_layer_contracts.py` (Tier 2) |

Three scope rules the table does not show:

| Rule | Detail |
|---|---|
| **Every contract is a DIRECT-edge rule, never transitive** | `orm-layer1-below-models-and-runtime` stops `odoo/orm/fields` importing `odoo.orm.runtime`; it says nothing about `odoo/orm/fields` → `odoo.tools.something` → `odoo.orm.runtime`. `tools/` is the Odoo-coupled utility layer, so transitively everything reaches everything through it. The narrower invariant holds at zero — `tools-does-not-reach-the-orm-runtime`. Add a targeted contract when a conduit matters |
| **Test files are outside the rules — but `odoo/tests/` is not test files** | any path with a `tests` component, plus `conftest.py` and `test_*.py`, is out of scope. The one carve-out is `odoo/tests/`, the shipped test *framework*: inside it only its own `test_*.py` and `conftest.py` are out, and `case.py`, `common.py`, `http.py` and the rest are in |
| **`odoo.tests` is exempt from `core-does-not-depend-on-addons`** | the framework's job is to drive application code. Its two addon reaches are both deferred and guarded — `tests/http.py` → `odoo.addons.bus` behind `if "bus.bus" not in self.env.registry: return`, and `tests/transaction_case.py` → `odoo.addons.bus.websocket` behind `try: … except ImportError` |

`core-does-not-depend-on-addons` is the mirror of `facade-boundary`: that one
stops addons reaching into ORM internals, this one stops the framework depending
on its own consumer. It holds at zero module-scope edges: the four
`odoo.service` → `odoo.addons.base.models.ir_cron` / `…ir_job` reaches it once
tolerated are function-local imports now (`_threaded.py`, `_worker.py`), the
sanctioned form. Reasoning in **Known boundary exceptions** in
[`gates.md`](gates.md).

## Coupling the import graph cannot see

Four coupling surfaces in this tree produce no import edge.

| Surface | Spelled as |
|---|---|
| mixin composition | `self.<sibling>` |
| Layer → runtime | `self.env.<m>`, `self.pool.<m>` |
| framework → addon models | `env["res.users"]` — a string |
| cycles inside one layer | every edge stays in-layer, so no direction rule sees it |

### The five mixin compositions

A root class over `__slots__ = ()` mixins collaborating through `self`.
`BaseModel` is the largest, composed from 26 `__slots__ = ()` mixins by
multiple inheritance — 18 public (`CreateMixin` … `AccessMixin`) plus 8 private
(`_PropertiesMixin`, `_QueryMixin`, `_ConstraintsMixin`, `_DisplayNameMixin`,
`_FieldComputeMixin`, `_HooksMixin`, `_MagicFieldsMixin`, `_ModelMetadataMixin`).

| Composition | Units | Root dominates its leaves? |
|---|---:|---|
| `BaseModel` (`orm/models/`) | 31 | no |
| `Field` (`orm/fields/`) | 5 | **yes** |
| `Registry` (`orm/runtime/`) | 7 | no |
| `Request` (`http/request_class.py`) | 5 | no |
| `Cursor` (`db/cursor.py`) | 3 | **yes** |

Units are **file-level** (2026-09-11): `BaseModel` counts 31 because
`read_group/` contributes five (`_empty`, `fill`, `format`, `mixin`, `sql`),
`base.py` is itself a unit, and the `_model_stubs` typing stub is not one; the
other four are root plus 6, 4, 3 and 2 mixins.

The last column is the shape claim, not a line count: a root larger than all its
leaves put together is a composition that has not actually been decomposed.
`BaseModel` is the target — its root is a fraction of its leaves — and two of
the other four still invert it. `Registry`'s root is lifecycle, model setup and
the cursor-opening entry points; replica routing lives in `db/replica.py` and
cross-process signalling in its own leaf (`_registry_signaling`).

`BaseModel`'s recordset identity — `env`, `_ids`, `_prefetch_ids`,
`_log_access` — is assigned by `IterationMixin.__init__` and read by every
unit; `Field`'s `description_attrs`, `Request`'s state on `RequestState`, and
`Cursor`'s `_cnx`, `_obj`, `_thread`, `_schema_cache`, `_before_statement` are
the same shape.

A mixin is a fragment of *one class*, so calling a sibling's method on another
recordset of the same model (`self.browse(…)`, `self.filtered(…)`,
`self.sudo()`) couples exactly as much as calling it on `self`. The other four
compositions hold no recordset of themselves.

#### The design rule for a new mixin

**A leaf that nothing in the composition depends on cannot close a cycle.** Put
new behaviour on one, and move the *declaration* with the methods — a unit owns
what its class body binds, and a leaf that reaches the root for its own state
has not left it. `_compute_field_value` lives on its own leaf
(`_FieldComputeMixin`) rather than on `RecomputeMixin` for that reason:
`traversal` already reaches `recompute` through `flush_model`, so its
`self.filtered("id")` would close a 2-cycle.

`base.py` is the target state that rule aims at: **in-degree 0, out-degree 0.**
It holds `__slots__`, `_register`, two setup hooks (`_is_valid_field_parameter`,
`_post_model_setup__`), `get_base_url`, and the three registration calls. Five
units depend on `_query` (`read`, `search`, `recompute`, `read_group/mixin`,
`read_group/sql`), which is where query construction lives.

For `Field` the units are the mixin composition only. Concrete field types are
*subclasses* and override base methods freely — that is the override surface, a
different graph.

### The layering is true of imports and false of the runtime graph

Layers 1 and 2 reach the runtime through `self.env` and `self.pool`, not through
imports. `orm-layer1-below-models-and-runtime` and `orm-models-below-runtime`
are clean and always will be, because that reach produces no import edge.

The two layers reach the `Registry` about as often — 31 member accesses each
on 2026-09-11 (every attribute on `<expr>.pool`, `pool`, `registry` or a local
bound from one) — and Layer 2 reaches more *distinct* members (18 against 10)
and has private reaches of its own (`_get_field_triggers`,
`_database_translated_fields`, `_database_company_dependent_fields`).

**Consequence:** a reader who takes the contracts as the whole picture predicts
the wrong blast radius for a change to `Environment` or `Registry`. Recorded as
[`risks.md`](risks.md) R1. A new ORM module must be given a layer in the map
above or an argued exemption.

**The `init_models` window.** `_post_init_queue`, `_foreign_keys`,
`_relation_reflections` and `_is_install` are fields of one `InitModelsPhase`
(`orm/runtime/_init_phase.py`) held as a single nullable `Registry._init_phase`
and read through the `init_phase` property, which raises a `RuntimeError`
naming the window when the phase is closed. Layer 1 calls
`pool.register_relation_table(...)`. The set of modules the loader has brought
up is public: `Registry.loaded_modules`. Pinned by
`odoo/orm/tests/test_init_models_phase.py`.

The phase snapshots the tables owned by concrete models before their schema is
initialized. `register_relation_table` admits only field-owned relation tables:
a Many2many reading a payload model's table must neither create a composite-key
replacement before that model initializes nor record it for relation-table
uninstall. Manual fields follow the same admission rule without acquiring module
reflection metadata. Ownership is recomputed for every initialization pass.

### The set of addon-owned models the framework may name is closed

The framework's largest real coupling to its consumer is spelled as a string
(`env["res.users"]`) and produces no import edge. `orm/_protocols.py` declares
what the framework *requires* of those models, narrowly: `ResUsersProtocol`
names the members the core cannot work without, not the hundreds `res.users`
has. `addons/base/tests/test_framework_contracts.py` checks each Protocol
against the live model, which is what catches `base` renaming a member under
the framework.

Seven subtrees reach no addon model at all — `orm/components`, `libs`, `db`,
the `api`/`fields`/`models` shims, `_monkeypatches` — each for an independent
reason, so a first reach there is a contradiction rather than a cost.

Inside the ORM the reach is narrower still. Everything the ORM asks of the
models-that-describe-models, of access, of external ids, of files, of settings
and of the locale goes through the six port objects named under **Seams**; the
`env["<base model>"]` sites left outside them are eight (`res.company` in
`helpers.py`, `res.groups` in `mixins/access.py`, `base` twice in
`fields/properties.py`, the import converter in `mixins/load.py`,
`res.currency.rate` in `read_group/sql.py`, the in-memory reflection's two in
`model_test_env.py`) and are frozen by
`odoo/orm/tests/test_architecture_pins.py`, which also freezes the five
statements the models, fields and domain layers still execute themselves (DDL
and schema in `mixins/schema.py` and `fields/_field_ddl.py`). Both maps may
shrink and must not grow; a regression names the file and where the site
belongs. `doc/architecture/factcheck.sh` derives both counts, the dispatch
inventory and the mixin composition from the pins and the classes and fails
when a page stops citing them.

### Direction rules are blind to cycles

Every edge of a cycle can sit inside one layer and cross no boundary. Python
hides this better than ESM does — a partially-initialised module is a live
object, so a cycle usually *works* until an entry point changes. **The ORM has
none.** The one import cycle in the core (2026-09-11):

```
odoo.cli     <-> odoo.cli.command
```

`from . import x` is an edge to `x`, not to the package: the ancestor package is
already on `sys.modules` when the importing module runs, so its `__init__`
finishing is never what the line waits on. `fields/base.py` holds six `from .
import _field_*` lines and `odoo.service`'s six `from . import _process_state`
readers form no cycle for that reason.

Function-local imports are not edges: a deferred import is the sanctioned way to
break a cycle. `odoo/tests/common.py` resolves the four `HttpCase` names through
a module-level `__getattr__` on first use, because `http.py` subclasses
`TransactionCase` and so must import `common` while executing.
`modules/db.py` imports `Manifest` from its owning module rather than through
the package that imports `db`.

## Seams that keep the layers decoupled

Every downward-only rule has a counterpart seam that lets the lower layer still
be *driven* by the upper one. **Adding a cross-layer dependency means adding a
seam, not an import.**

| Seam | Mechanism |
|---|---|
| `db/` ↔ ORM | `orm/runtime/savepoint.py` assigns `_OrmFlushingSavepoint` to `BaseCursor._flushing_savepoint_cls` at import, so `db/` never imports the ORM |
| `db/` ↔ `tools.config` | `tools/config.py` gives `db/settings.py`'s slot a source that builds a frozen `PoolSettings` from the option dict; every pool captures the snapshot it was built from, the free functions take one or ask the slot, and a test installs its own — so `db/` reads typed fields and never the dict, and never imports `odoo.tools` |
| `http/`, `service/` ↔ `tools.config` | the same slot shape (`odoo.libs.settings.SettingsSlot`), one per tier, and the same rule as `db/`: `ServerSettings` and `HttpSettings` name every option their package reads and `from_config` is the one place each key is spelled, but nothing is installed at boot — `current()` derives a snapshot from the live option dict per read (`http/` memoises it on `tools.config.generation`, the counter every option-layer write moves; a swapped `config.options` disables the memo), which is what keeps `config.patch(...)`, `config.options.new_child(...)` and the test sites that write a key after boot meaningful; a lifetime that genuinely freezes one captures it (`ThreadedWSGIServerReloadable` captures the snapshot its thread bound is computed from), and a test installs its own instead of patching the dict. The `/web/database/manager` service (`service/db/`) stays on the dict on purpose — `list_db` is flipped at run time by `odoo-bin db`, and the admin password is a credential it verifies and rewrites, not a setting |
| `components/` ↔ runtime | `FieldCache`/`ComputeEngine` take callbacks for SQL and recompute, so the engine never imports `Environment` |
| Layer 1 ↔ `BaseModel` | the model layer injects `BaseModel` into `orm/_recordset.py` via `set_base_model()`, so `fields/` and `domain/` recognise recordsets without importing Layer 2 |
| CRUD ↔ persistence | the model mixins dispatch row I/O through `env.backend`; a locked or conditional column write goes through `env.backend.columns` (`fetch_and_add`, `try_write`), a sequence through `env.backend.sequences` |
| ORM ↔ `addons/base` | six port objects on the registry, each the one file that names the base models it needs: `registry.metaschema` (ir.model, ir.model.fields, ir.model.constraint, ir.default, ir.model.data's load end), `registry.access_policy` (ir.model.access, ir.rule), `registry.xmlids` (ir.model.data), `registry.file_store` (ir.attachment), `registry.settings` (ir.config_parameter), `registry.locale` (res.lang, decimal.precision). The in-memory `ModelRegistry` carries the same six |
| framework ↔ addon models | string key (`env["res.users"]`), never an import; eight such sites remain in the ORM outside the ports and are pinned (below) |
| `ir.ui.view` ↔ view types | an addon that adds a view type registers an `ElementHandler` for its root tag (`addons/base/models/ir_ui_view_arch.py`) instead of inheriting the model; the pipeline stages stay on the model |

**`env.backend` is non-optional and has two implementors**: `PostgresBackend`
(`runtime/backend.py`, beside the `StorageBackend` protocol) owns the SQL —
every `INSERT`, `UPDATE`, `DELETE`, locking `SELECT`, m2m-table statement,
the reachability query behind `_has_cycle` and the counter increment behind
`_increment_fields_skiplock` is a method of the backend taking the model as its
argument; `runtime/_backend_memory.py`'s `InMemoryBackend` adapts the same
port to `DictBackend` (`components/storage.py`), the in-memory `read_group`,
foreign-key plan and table-constraint checks with it. The mixins call the port
and nothing else, so the production file carries no test-tier emulation, and
what stays on the model is query *compilation* — `_field_to_sql`,
`_order_to_sql`, `_traverse_related_sql` — which `Domain._to_sql` and
`read_group` call too.

PostgreSQL search compiles SQL and flushes its metadata at execution. The
in-memory adapter discovers domain, relation and ordering dependencies directly
from field metadata in `runtime/_search_flush.py`, without compiling SQL:
compilation can query PostgreSQL catalogs or invoke backend-specific callbacks.
Ordinary searches leave unrelated computes deferred and preserve dirty cache
values. Opaque custom Python predicates retain the conservative full flush;
SQL-only custom domains are unsupported by the in-memory adapter.
`tests/contract/test_search_flush.py` exercises the same recursive-compute
scenarios against PostgreSQL, while `odoo/orm/tests/test_search_flush_boundaries.py`
pins the database-free boundary.

Production CRUD sniffs the test backend neither via `transaction.storage` nor
via a null check.

**Capabilities: none declared, no branch that is lossy or blocking** (frozen at
odoo `f7e799ce3578`, 2026-09-13, re-read 2026-09-14 when the Reference field's
sibling prefetch moved onto `backend.columns` and `supports_column_scan` went
with it, and again 2026-09-15 when `_has_cycle`, `_increment_fields_skiplock`
and the transient vacuum's backlog probe moved onto the port and
`supports_recursive_queries` went with them; pinned by
`odoo/orm/tests/test_backend_dispatch_surface.py` and
`test_backend_protocol.py`):

| Measure | Value | What it counts |
|---|---:|---|
| declared capabilities | 0 | a backend answers every question of the protocol itself; a site that branched on what the backend could do was a site the backend now owns |
| dispatch sites | 30 across 20 files, 8 in Layer 1 | every `env.backend.<method>(` in the models, fields and domain |
| protocol methods without a caller | 0 | every `StorageBackend` method is dispatched from the ORM or from a base model spelling `env.backend.` |

What used to branch now calls the port: a many2many read is `read_m2m_groups`
(PostgreSQL joins the relation onto the comodel query, memory walks its rows in
the query's order); the parent store is `set_parent_paths`,
`records_with_parent_changed` and `move_parent_paths`, so a `_parent_store`
model keeps its paths in memory and `child_of` resolves through them; translation
echoes follow a write on both backends because the mirror logic reads the stored
dicts through `columns`; record rules apply in memory because the in-memory search
asks `registry.access_policy` for the domain, as PostgreSQL's search does.
`descendants` and `ancestors` are the two tree walks (a recursive CTE, a level
walk); `unlink_rows(model, ids)` deletes rows and runs the company-dependent
cleanup, and nothing else -- the xmlids and attachments a deletion drops are
collected by the mixin through `registry.xmlids` and `registry.file_store` before
the first batch.

The DB-free tier's safety marker is unchanged in what it protects: a registry
without `ir.rule` raises `InMemoryRecordRulesNotSupported` the moment an
access-checked search asks the policy for a domain; one handed an `ir.rule` class
gets real filtering.
