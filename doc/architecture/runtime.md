# Runtime view — what runs, when, and in how many processes

> One of the views indexed by [`ARCHITECTURE.md`](ARCHITECTURE.md).
> This view answers *what happens at run time*. For *where code lives and what it
> may import*, see [`module.md`](module.md).

The module view is a claim about source. This one is a claim about processes,
threads, cursors and order — none of which an import graph can express. Where a
claim here is proved by a running test, the test is named.

## Lifecycles

Four runtime paths a reader has to hold to debug the core. Each is a sketch;
where a canonical unflattened version exists it is named.

### Process boot

```
odoo-bin
└─ odoo.cli.main()                     cli/command.py — bootstrap parse, pick command
   └─ <Command>.run(args)              cli/server.py for the default `server` command
      └─ service._factory.start()
         ├─ load_server_wide_modules()
         ├─ choose WebsocketServer | PreforkServer | ThreadedServer
         └─ server.run(preload, stop)
            └─ service.lifecycle.preload_registries(dbnames)
               └─ Registry.new(db, update_module=…)      one registry per database
```

Before any of that, importing `odoo.orm`, `odoo.modules` or `odoo.cli.command`
executes **`odoo/init.py`**, the framework bootstrap, in this order:

| # | Step | Fails how |
|---|---|---|
| 1 | enforce `MIN_PY_VERSION` | `SystemExit` naming the required version |
| 2 | import the `odoo_rust` native extension | a hard, explained `ImportError` when `ODOO_REQUIRE_NATIVE` or `CI` is set; otherwise a `RuntimeWarning` and the process runs on the pure-Python twins behind `odoo/libs/accel.py` (slower, not wrong) |
| 3 | `assert_fresh`: compare `odoo_rust.__source_crc__` against the crate on disk; `assert_optimised`: require the `release` profile (`odoo/libs/native.py`) | refuses to start when the built extension is **stale**, naming the rebuild command, or is a debug build. Skipped when the crate directory is absent (an installed wheel) or `ODOO_SKIP_RUST_FRESHNESS_CHECK` / `ODOO_ALLOW_DEBUG_RUST` is set. The sibling `odoo_lint` extension is checked the same way, but at *its* import site in `odoo/libs/lint/scan.py` — it is not a runtime dependency and a server that never runs a lint gate never loads it |
| 4 | retune the GC threshold set | — |
| 5 | `_monkeypatches.patch_init()` | anything that must be patched before third-party modules load has to run from here |

Step 3 is a separate failure from step 2: a stale extension imports cleanly and
then segfaults on a cyclic `fast_clone` and mis-orders timezone-aware columns,
neither of which names its cause.

The other runtime floor is enforced later and by a different subsystem:
`db/pool.py::_check_min_server_version` compares the server against
`MIN_PG_VERSION` at connect time and raises `PoolError`. Both constants live in
`odoo/release.py` and are named here rather than restated.

| Config | Server | Concurrency |
|---|---|---|
| `workers = 0` (default) | `ThreadedServer` | Python threads, one process, debugger-friendly |
| `workers > 0` | `PreforkServer` | forked OS processes, no shared memory |
| `odoo.evented` | `WebsocketServer` | Python threads on the websocket port, one process; no gevent anywhere in the fork |

All three end in the same `preload_registries` → `Registry.new` path. The choice
is not a deployment knob: a large part of the ORM's runtime design exists
*because* `workers > 0` is supported.

### Concurrency, and why the process model is architectural

With one process, a registry is an ordinary Python object and invalidating it is
an attribute write. With `workers > 0` there are N processes that share no
memory, each holding its own `Registry` per database, and **a model change made
in worker A is invisible to worker B**. There is no shared-memory channel. So
the framework coordinates through the database.

`orm/runtime/_registry_signaling.py` implements it as a sequence protocol over
ordinary tables (`orm_signaling_registry`, plus one per cache key in
`CACHES_BY_KEY`), each holding nothing but a `SERIAL` id and a timestamp:

| Operation | Mechanism | Why this way |
|---|---|---|
| **Publishing** | `Registry.signal_changes()` `INSERT`s a row and reads back **the id the database generated** (`RETURNING id`) | not `local + 1`: concurrent inserts are the normal case, so two workers signalling together take ids N+1 and N+2 while both would record `+= 1` locally, and the loser would see `db > local` and pay a full `Registry.new()` — the most expensive operation in the system — to learn about a change it made itself |
| **Observing** | `Registry.check_signaling()` reads each table's serial (`pg_sequence_last_value`) against what this process last saw — `get_sequences` does it in one prebuilt `SELECT` of eleven sequence reads (2026-09-13: 0.21 ms median on a live request, from 0.40 ms with `max(id)` subselects, which planned per call) | a **registry** sequence ahead means the model classes are stale: adopt an already-published newer registry if one exists, else drain the pool and call `Registry.new()`. A **cache** sequence ahead clears only the LRUs behind that key, which is why eviction costs far less than a rebuild and why the two use separate tables |
| **Tolerating lag** | a sequence *below* the local one is logged and ignored as stale | signaling may be read through a read-only cursor that lands on a replica, and a replica behind the primary must not thrash every worker's registry |

Three consequences for code anywhere in the core:

- **A registry is per `(process, database)`, never global.** Anything attached to
  one is invisible to the other workers until something signals.
- **A process-lifetime cache must be registered in `CACHES_BY_KEY`**, or it
  serves stale values in every worker but the one that changed the data — and no
  test with `workers = 0` can reproduce it.
- **`Registry.new()` can run more than once per process**, and not only at boot:
  a signaling check triggers it, and so does `_UninstallRequiresReload` from
  inside `load_modules`. Code that assumes one registry build per process start
  is wrong.

The cron runner is the same argument in a second place. `service/_threaded.py`
and `service/_worker.py` reach `IrCron._process_jobs` / `IrJob._process_jobs`
directly — the two tolerated `core-does-not-depend-on-addons` exceptions —
because a cron thread runs *before* a registry exists for that database and has
no `env` to route through.

### Registry build

`Registry.new()` is the most expensive operation in the system and the only way
a database's model classes come into existence. It refuses to run against a
system or template database, allocates the registry, probes the database's
capabilities (`_probe_capabilities`: `unaccent`, `pg_trgm`, and the
per-code-point text transforms `_get_text_transforms` caches per process and
database), sets up cross-process signalling, then hands off to
`modules.loading.load_modules()`, whose phases are methods on `_ModuleLoader`:

```
Registry.new(db)
├─ setup_signaling()                      cross-process registry/cache sequences
└─ load_modules(registry, …)
   ├─ bootstrap()                         `base` present? graph seeded?
   ├─ run_pre_upgrade_scripts()           update only
   ├─ capture_database_field_metadata()   update only, before the schema moves
   ├─ open_environment_and_load_base()    first Environment; `base` data loaded
   ├─ load_languages()
   ├─ apply_module_requests()             update only: to-install / to-upgrade
   ├─ converge_module_graph()             load modules until the graph is stable
   ├─ finalize_registry_setup()             _setup_models__ / init_models
   ├─ run_end_migrations()                update only
   ├─ finalize_constraints()              deferred constraints, then NOT NULL
   ├─ uninstall_removed_modules()         update only; may force one full reload
   ├─ warn_invalid_custom_views()         update only
   └─ register_model_hooks() · check_null_constraints()
```

Fourteen of the 23 `loader.*` calls, in call order; the sketch selects, it does
not enumerate. Every one of the 23 is *called* on a plain load too — the
"update only" phases return at their first line when `update_module` is false.
The full sequence is `loading.py`'s; `tests/loading/test_load_modules_phases.py`
pins it against a real load, and
[`scenarios.md`](scenarios.md#scenario-a--installing-a-module) selects thirteen
for a different purpose.

Two consequences before touching this path:

- **The graph is iterated by phase, then dependency depth, then name** — never by
  filesystem order. A module's data loads only after every dependency's.
- **`uninstall_removed_modules()` can raise `_UninstallRequiresReload`**, which
  makes `load_modules` call `Registry.new()` again from inside itself
  (`tests/loading/test_load_modules_uninstall.py`).

After `load_modules` returns, `Registry._new_finalize` marks the registry
ready, calls `_get_field_triggers()`, and `signal_changes()` so other workers
reload.

The trigger graph is keyed on `Field` identity, and a table-inheritance tree
gives every model its own `Field` for one stored column, so a dependency on a
root column is registered against every sibling's copy
(`_depended_fields_in_tree`). The trigger-tree walk closes a cycle on the
**fact** a field stands for (`_trigger_fact_of`: the root table and column
name for a tree field, the field itself elsewhere), not on the `Field`. A
self-dependency shared by `n` siblings is then one level of `n` targets, as it
is on a single model; keyed on `Field` it was `n!` paths, which is what put an
install at 58 GB with nine `resource.asset` subtypes.

### Request lifecycle (HTTP)

```
WSGI  →  Application.__call__  →  Request (_post_init: session + db)
      →  _serve_static | _serve_nodb | _serve_db
            _serve_db: _acquire_registry_cursor → check_signaling → Environment → ir.http._match
                match  → service.transaction.retrying(_serve_ir_http):
                             ir.http._authenticate → ir.http._pre_dispatch
                             → Dispatcher.pre_dispatch → Dispatcher.dispatch
                             (→ ir.http._dispatch → endpoint)
                             → ir.http._post_dispatch
                no match → retrying(_serve_ir_http_fallback):
                             ir.http._serve_fallback → ir.http._post_dispatch
            → cr.close() → response
```

Three details the sketch flattens, all claims about **order**:

- **`retrying()` lives in `odoo/service/transaction.py`**, not on a model. It
  re-runs the callable on PostgreSQL serialization/deadlock errors, rewinding
  uploaded files between attempts. The attempt includes flush and commit:
  a concurrency rejection at commit is retried too. Replay requires successful
  rollback, transaction reset and registry reset. The cursor's `commit_count`
  must remain unchanged since entry; once work is durable, a post-commit hook
  failure propagates without replay or local registry rollback. Connection
  errors with an unknown commit outcome are not retryable. Pinned by
  `tests/service/test_transaction_recovery.py` and
  `tests/contract/test_transaction_recovery.py`.
- **Session publication follows a successful commit.**
  `Dispatcher.post_dispatch` → `Request._save_session()` stages persistence.
  The request's postcommit hook writes the session and publishes its cookie;
  rollback restores the attempt's original session. The successful return from
  `retrying()` also invokes the idempotent publication hook for cursor adapters
  that suppress callbacks. `_serve_db` closes the cursor in its `finally`.
- **RO → RW promotion.** A route declared `readonly` first runs on a read-only
  cursor. If its handler writes, `psycopg.errors.ReadOnlySqlTransaction` is
  caught, a read/write cursor is acquired and **the handler runs a second time**
  — so non-transactional side effects (emails, outbound calls) must not precede
  the first write.

The runtime proof of the order is
`odoo/addons/test_http/tests/test_lifecycle_order.py`, which patches
`Request._save_session` and *both* cursor classes and reads the sequence off the
serving thread: `[commit, save_session]` normally and on the promoted path.
(Both cursor classes, because under `HttpCase` the request's `env.cr` is a
`TestCursor`, which subclasses `BaseCursor` rather than `Cursor`; instrumenting
`Cursor.commit` alone observes nothing.)

`Dispatcher` has three subclasses (`HttpDispatcher`, `JsonRPCDispatcher`,
`Json2Dispatcher`) selected by `routing["type"]`.

The canonical, unflattened call graph — every stage and what each is responsible
for — is **`odoo/http/README.md`**, which also carries `http/`'s module map.

### Transaction, cache and flush

One `Transaction` per cursor (`cr.transaction`), created lazily by the first
`Environment` built on that cursor. It owns the registry reference and the
per-transaction machinery:

```
Cursor ──── transaction ────┬─ registry          the model classes
                            ├─ _cache_store      FieldCache   (field values, dirty ids)
                            ├─ _compute_engine   ComputeEngine (pending recomputes)
                            ├─ core              OrmCore  ← the curated facade, env.core
                            ├─ unit_of_work      UnitOfWork (the fixpoint loops)
                            ├─ backend           PostgresBackend · InMemoryBackend = DB-free
                            ├─ envs              interned Environments
                            └─ default_env       the Environment a cursor-driven flush runs through
```

`Environment(cr, uid, context, su)` is **interned** per `(cr, uid, su, context)`:
constructing one with the same key returns the existing object. Environments are
cheap and identity-comparable, and any per-request state must live on the
transaction or the request, never on an `Environment` you happen to hold.
`Transaction.environment()` is the one place that interns: `Environment.__new__`
validates its arguments and delegates, so the key (`_EnvironmentSet.key`,
`runtime/transaction.py`) and the fast path that short-circuits on the last
environment handed out (`_EnvironmentSet.matches`) sit beside each other, and
`Transaction` is per-cursor by construction, so nothing re-checks the cursor
after a lookup. `uid == SUPERUSER_ID` forces `su=True` before the key is built.

`default_env` is the environment a cursor-driven flush runs through and the user
`_check_sudo_commands` downgrades to. The code that opens a transaction sets it —
`execute_cr`, `request.update_env()`, the module loader, the cron and job
runners, the CLI and the test harnesses — and the transaction adopts the first
environment built for a real user only when no opener did. That adoption is a
`Transaction` policy, not a constructor side effect: building an `Environment`
never touches it, and `_OrmFlushingSavepoint` has nothing to snapshot.

**Writes do not reach SQL where you write them.** `create()`/`write()` update the
field cache, mark ids dirty, and schedule dependent computes; the database sees
no write until a flush. A flush is a *fixpoint loop*, because recomputing one
field can dirty another:

```
env.flush_all()  ≡  transaction.flush(env)
└─ Transaction._flush_as(env)   binds the callbacks, reads `tolerant_recompute`, raises, profiles
   └─ UnitOfWork.flush_until_converged(recompute_fn, flush_fn)  ≤ MAX_FIXPOINT_ITERATIONS (1000)
      ├─ recompute_fn(field)  → model._recompute_field(field)
      └─ flush_fn(models)     → model.flush_model()   inside one cr.pipeline()
                                 ├─ _recompute_fields(stored computed fields)
                                 └─ _flush()  pops the dirty ids → UPDATE

cr.flush()
└─ transaction.flush()          through default_env — SUPERUSER, with a warning, when there is none —
   │                            then the N+1 and ORM profiler reports
   └─ cr.precommit.run()        interleaved, up to BaseCursor._MAX_FLUSH_PASSES (10)
```

The policy lives on `Transaction`: `flush(env)` flushes through the environment
it is handed and is what `env.flush_all()` delegates to (~2,500 addon call
sites across this repository's two addon trees, 2026-09-11); `flush()` with no
argument is the cursor's form, which picks the environment and reports the
profilers. `BaseCursor.flush()` is not a delegate — it owns the precommit hooks
and interleaves them with the transaction flush until both settle — so its pass
limit stays on the cursor.

Non-convergence is an error, not a warning: the loop raises unless the context
carries `tolerant_recompute`, and `UnitOfWork` carries a stall detector so a loop
that stops making progress fails in seconds instead of grinding to the cap.
`flush_model()` / `flush_recordset()` are the scoped versions and both
short-circuit when nothing is pending or dirty.

The loop still issues *reads*: prefetch `SELECT`s land where the field is first
touched ([`qualities.md`](qualities.md#scenario-1--write-throughput)).

**When the cache reaches the database, and when it must not.** The states a
stored value passes through are *cached* (the slot holds it), *dirty* (a
`write`/`create` set it and `Field.mark_dirty` listed the record in the unit of
work; the row does not hold it yet), *pending* (`PENDING` in the slot: a stored
compute owes it) and *absent* (nothing cached; the next read fetches). What
moves a value between them:

| Event | Flushes | Then |
|---|---|---|
| `env.flush_all()`, `flush_model()`, `flush_recordset()` | everything, the model's fields, the records' fields | recompute pending stored computes to a fixpoint, `UPDATE`/`INSERT` the dirty ones through the backend |
| `env.execute_query(sql)` — every `_search`, `read_group`, fetch and port statement | exactly the fields the statement reads (`SQL.to_flush`), across a table-inheritance tree | so a read never sees a column older than its own cache |
| `invalidate_model()` / `invalidate_recordset()` with `flush=True` (the default) | the fields being dropped | then drops them; with `flush=False` it refuses a field that is dirty (`_check_no_pending_write`) rather than lose the write |
| `unlink()` | everything | before the `DELETE`, so no dirty write targets a gone row |
| a parent-store write | the parent field | before the path recomputation reads it |
| `cr.flush()` at a savepoint or commit boundary | everything, then the precommit hooks, interleaved to a fixpoint | |
| `cr.execute(...)` — raw SQL | **nothing** | flush by hand first (`coding_guidelines.rst` §6.5) |

Two rules follow, and every cache-maintenance path in `fields/` obeys them:

1. **No fetch inside a write.** Between a write's first cache mutation and its
   `modified()`, nothing may read a value that is not cached: the miss would
   flush the half-written transaction and run computes on partial values. This
   is why `Many2one._update_inverses` sorts an appended one2many in memory and
   caches it unsorted when the keys are not there, why a stored many2many write
   does the same, and why another scope's slot is *evicted* (its next read
   fetches, later) rather than refreshed.
2. **A cache write is a claim about the row after the flush.** A slot holds
   what the database will read back — for an x2many, what the scope's search
   returns (the invariant above); for a column, the converted value. A path
   that cannot make that claim leaves the slot absent instead.

**A new record's cache mirrors what it was given, and nothing more.** `new()`
(`models/mixins/env.py::_update_cache`) caches every value, then tells each
relational value's inverse fields about the record — a new line given a new
move lands in the move's one2manys whose domain it satisfies, as a write would
place it. The reverse is deliberately absent: lines given to one one2many are
*not* echoed into a sibling one2many over the same many2one
(`Many2one._update_inverse` is a bare cache set), although the write path
(`_update_inverses`) does exactly that on saved records. The onchange protocol
(`addons/web/models/record_snapshot.py`, `odoo/tests/form.py`, the JS static
list) depends on it: the client owns each x2many list independently and
matches an echoed CREATE only against that list's own ids, so a line reported
under a second list would get a fresh virtual id there and come back
duplicated on the next round-trip. `odoo/orm/tests/test_new_record_sibling_one2many.py`
pins both halves.

**An x2many cache slot belongs to the access scope that filled it.** The field
cache keys a context-dependent field's slot by the values `Field.depends_context`
names (`lang`, `active_test`, `company`, `uid`); every x2many adds `access`
(`Environment._access_scope`: `True` under sudo, else the uid with the allowed
company ids sorted), because `One2many.read` / `Many2many.read` cache what the
*reading* environment's search returned — with the record rules applied — and one
shared slot let a sudo read hand a user every company's rules, and a user read
starve sudo of the rows the rules had hidden.

*The invariant.* For a stored x2many `F`, a record `r` with a real id and a scope
`S`: **if `S`'s slot holds a value for `(F, r)`, that value is the set of ids
`S`'s own search for `r`'s relation returns at that point of the transaction —
in the comodel's order as of the slot's last fill or append when the order keys
were in memory then, else in the order written — and a slot holding nothing
says nothing; the next read searches.** A later write to a member's order key
(a rename under `complete_name`) does not re-sort the slots that hold it, as
upstream does not either. One
exception is stated rather than paid for: the writer's own slot lists what the
writer itself wrote in this transaction even when its read rule would hide it (a
create or write rule may admit what the read rule hides; checking would cost the
comodel's access check on every write, and upstream reads the same way).
`odoo/orm/tests/test_x2many_scope_invariant_dbfree.py` walks forty random
sequences of reads and writes by two users in three company scopes and the
superuser — over a plain one2many, one with a callable domain, one declared
`bypass_search_access` and a many2many, with rule fields of both kinds written
along the way — and checks the invariant after every step (300 further seeds
at 80 steps read clean on 2026-09-16); `base/tests/test_x2many_cache_scope.py::
TestX2manyScopeInvariant` is the same walk on PostgreSQL with `res.partner`,
its tags and a name rule. A cache rule that breaks the invariant fails there
before it fails a query pin.

*What maintains it*, each pinned by a named test in `odoo/orm/tests/`: a read by
`S` fills `S`'s slot, and the superuser's too when nothing narrows `S`'s read
(`_reads_as_superuser`: a static field domain, no `_search` override on the
comodel, model access, no read rule); a full value written by `S` sets `S`'s
slot, sets the superuser's when the same holds and evicts every other scope's
entry (a value still holding pending lines is mirrored instead — a pending
mutation is one for everyone); at create the given value is the truth for every
scope; an inverse-side addition (a many2one write, a create, a many2many link)
appends to the superuser's slot and the writer's and evicts every other user's
entry; an inverse-side removal applies to every scope; a write to a field a
scope's read rule tests, or one a comodel's `_search` override declares in
`_search_visibility_fields` (`_evict_user_scopes_reading_through`, from
`WriteMixin.write`), empties that scope's slots of every x2many whose comodel
was written — the verdict may have changed, and the next read searches. None
of it fetches mid-write (`Many2one._update_inverses` documents why there must
be none). Three shapes are structural, not special cases: a *pending* record
(`NewId`) has no search to decide anything, so `_ScopedSlot` routes it to one
slot shared by every scope (and `RecordCache` peeks there too); a *computed*
x2many is what its compute produced (under sudo for `compute_sudo`), so its slot
is scope-less; and a model that *delegates its fetch to sudo* after its own
access check (`mail.message.fetch`) fills the superuser slot, so a read that
finds no value after such a fetch is served from there once
(`_value_after_delegated_fetch`). The events `field.x2many.scope_sync`,
`scope_evict`, `scope_evict_rule_field_written`, `scope_mirror_pending`,
`scope_handover`, `read_mirrored_to_superuser` and `delegated_fetch_served` on
the `orm.fields.relational._base` channels show each decision; the plan that
weighed the alternative (one slot holding the truth, visibility applied on the
way out) is `agromarin-knowledge/plans/2026-09-14-x2many-cache-access-scope.md`.

**A many2many write reaches only the links its writer can read.** `Many2many.write_real`
builds the old relation from the writer's own slot, and `_apply_relation_delta` deletes only
pairs that were in it. So a restricted user's `Command.clear()` or `Command.set()` leaves in
place the links their record rules hide, and a sudo write reaches every link. The rule is the
mirror of `_check_new_relation_access`, which refuses a link to a record the writer cannot read:
a user can neither add nor remove what they cannot see. It is also what keeps a multi-company
field such as a product's taxes whole when one company's user saves it.

Before the scopes split, the result depended on what the shared slot happened to hold. The
removal reached the hidden links only if a sudo or admin read had just filled the slot. Upstream's
`test_many2many` read that accident as "clear removes all records".

`TestRules.test_a_user_clear_keeps_the_links_the_user_cannot_read_whatever_is_cached` and
`test_a_user_set_replaces_only_the_links_the_user_can_read` pin the rule, and both go red on the
shared-slot behaviour.

**A per-transaction memo is `TransactionMemo`** (`odoo/tools/cache.py`): a
container in `cr.cache` that `BaseModel.create`, `write` and `unlink` discard
for the models it names (`invalidated_by`, a list of models or a mapping model →
fields for write). Addons memoize configuration lookups with it — routes' rule
kinds, rule candidates per selection domain, orderpoints by scope, the default
warehouse, boms by product, invoice-template reports, currency rate history,
analytic plans, approval escalation targets, the last sequence of a journal —
and never hand-roll the three overrides that pop a key. A savepoint rollback
clears `cr.cache` as before; a memo whose truth is changed by a path that
bypasses `write()` (a direct column write, `_locked_increment`) discards itself
there.

Row I/O at the bottom goes through `env.backend`, the persistence port described
under **Seams** in [`module.md`](module.md#seams-that-keep-the-layers-decoupled)
— which is what lets the whole ORM run against `InMemoryBackend` with no
database. **`backend` is non-optional and has two implementors**, which is why
the sketch above names one rather than leaving it unset. Beside it the registry
carries the six port objects through which the ORM talks to `addons/base`
(`registry.metaschema`, `access_policy`, `xmlids`, `file_store`, `settings`,
`locale`); the in-memory `ModelRegistry` carries the same six, so a mixin that
needs a meta-schema answer or an access domain asks the same object on either
tier.
