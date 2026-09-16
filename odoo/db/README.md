# `odoo.db` — PostgreSQL connectivity layer

Fork-specific replacement for upstream's monolithic `sql_db.py`: psycopg 3
(server-side binding, pipeline mode) fronted by per-database
`psycopg_pool.ConnectionPool`s. Read this before editing; the detailed
invariants live in this file, not in module docstrings — none of the `.py`
files here carry one, so this README is the only map.

## Module map

| Module | Contents | Pure? |
|---|---|---|
| `__init__.py` | Public API only: `db_connect`, `close_db`/`close_all`, `drain_db`/`drain_all`, `get_pool_health`, `get_replica_health`, `cancel_queries_of`, the process `registry`, and `sql_counter` via module `__getattr__` | no |
| `endpoints.py` | `EndpointRegistry`: the lazy registry of `ConnectionPool`s keyed `(endpoint, readonly)` and of `ConnectionBudget`s keyed by endpoint, plus the endpoint resolution (`get_endpoint_key`, `get_maxconn_at_endpoint`) both sides of the budget comparison share. Was module state in `__init__.py` | no |
| `cursor.py` | `BaseCursor` (hooks, flush convergence, savepoint seam), `Cursor` (the `cr` object: execute/executemany, DDL handling, the lost-connection replay, close/commit/rollback guards) and `Connection`, the `(pool, dbname, dsn)` record whose `cursor()` builds one — it lives beside the class it instantiates, so `pool.py` never imports `cursor.py` | no |
| `pool.py` | `ConnectionPool` (per-DSN psycopg_pool registry, borrow/give_back, idle-pool reaper, stale-credential eviction, direct maintenance-DB path, `get_health()`) | no |
| `probe.py` | `ReachabilityProbe`: is this DSN connectable, and permanently or not — the pre-flight probe, its leader/follower dedup, the `postgres`-side existence check and the per-key proof. Was inlined in `pool.py` | no |
| `budget.py` | `ConnectionBudget`: the shared `db_maxconn` cap, its permit `Condition` and its saturation counter | yes |
| `stats.py` | `PoolStats`: borrow-wait histogram, pool churn and probe-outcome counters behind `ConnectionPool.get_health()` | yes |
| `reaper.py` | `IdlePoolReaper`: which quiet per-DSN pools to close and how often to look (the decision; the pool keeps the locking and teardown); `trim_idle_to_ceiling` / `close_idle_connections`: the backend ceiling across a `ConnectionPool`'s per-DSN pools, enforced on every return | yes |
| `leaks.py` | `CheckoutTracker`: which connections are out, since when, from which thread and borrow site | yes |
| `lag.py` | `ReplicaLagGate` + `LAG_SQL`: sampled apply-lag ceiling that demotes stale reads to the primary | yes |
| `replica.py` | `ReplicaRouter`: the primary `Connection`, the optional readonly one, the `CircuitBreaker` (`odoo/libs/breaker.py` — Odoo-agnostic, so `libs/`) and the `ReplicaLagGate` composed into one decision — which connection serves a cursor request, and the mode (`ro` / `ro->rw` / `rw`) it decided; `WritePins`, the read-your-writes table; `REPLICA_RETRY_TIME`, the breaker's cooldown ceiling; `is_readonly_cursor_enabled`; `get_replica_health`, every live router's state for the metrics surface. Was the body of `Registry.cursor` | no |
| `pipeline.py` | `_PipelineMixin`: `cr.pipeline()` — arming on the second statement, the sync-on-demand behind `rowcount`/`description`, the wait accounting, the deferred-error seam at block exit. Its own module because it is the one concern of the cursor with eight attributes of its own; the methods resolve through `Cursor`'s MRO at no per-call cost | no |
| `bulk.py` | `_BulkAccessMixin`: `copy_from` (COPY, optional binary + pre-generated ids), `execute_values` | no |
| `savepoint.py` | `Savepoint` / `_FlushingSavepoint` (ORM state restore is injected by `odoo.orm.runtime.savepoint`) | yes |
| `ddl.py` | Statement-text scanning: `iter_sql_code_ranges`/`get_value_marker_positions` (the `%s` markers outside literals and comments, shared with `bulk`), DDL keyword detection, client-side param inlining (`$N` is rejected in DDL positions) | yes |
| `schema.py` | Schema DDL operations executed against a `cr`: create/alter tables, columns, constraints, foreign keys, indexes, views; `TableKind`, `SQL_ORDER_BY_TYPE` (relocated from the former `tools/sql.py`: PostgreSQL-generic but cursor-coupled, so `db/` rather than `libs/`); and the catalog capability probes `FunctionStatus` / `get_unaccent_status` / `has_trigram`, relocated from `modules/db.py` — reaching them through the module system dragged `odoo.orm.runtime` in behind them. `get_tables_existing` asks for `_EXISTING_RELKINDS`, derived from `TableKind` so the two cannot disagree — a partitioned table (`'p'`) reported as absent makes `_auto_init` issue `CREATE TABLE` over it and the registry fails to load with `DuplicateTable` | no |
| `dsn.py` | DSN expansion/normalization (pool keys, password fingerprint, `_get_key_dbname` — the one reader of a key's database), connect-error classification | yes |
| `errors.py` | `CURSOR_LOGGER_NAME`, retry taxonomy (`PG_RETRY_*`), user-fault taxonomy (`PG_USER_FAULT_*`), the stale-plan marker (`PG_STALE_PLAN_EXCEPTIONS`, `mark_stale_cached_plan`, `is_stale_cached_plan`), `has_reached_server`, `_log_sql_error`'s four log tiers | yes |
| `lifecycle.py` | What happens to a connection at its three moments: psycopg_pool's `configure` and `check` callbacks, and the session reset `give_back` runs on the returning thread (`register_adapters` and its numeric-to-float loader, the transaction flags set once per connection, prepare tuning, the reset and the liveness probe as libpq simple queries, the grace-windowed health check sized by `PoolSettings.healthcheck_grace`) | yes |
| `schema_cache.py` | `TransactionSchemaCache`: per-cursor, transaction-lifetime catalog facts for `copy_from` (id sequences, column types) | yes |
| `metrics.py` | `_MetricsMixin` (query counters, thread metrics, DEBUG per-table stats), `classify_query` (the statement -> (kind, table) classifier those stats key on), `sql_counter` | yes |
| `utils.py` | `get_connection_info_for_database`, `is_maintenance_db`, `update_planner_stats` | yes |
| `settings.py` | `PoolSettings`: the frozen snapshot of every `db_*` option the package reads, `from_config` to build one, and the slot (`current`, `installed`, `override`) through which `odoo.tools.config` supplies it — the one door the option dict has into this package. Every policy the package applies reads the slot, including the router's `replica_max_lag` and `replica_write_pin`: `Registry.init` passes neither, so a `pool_settings.override(...)` reaches a registry built inside it | yes |

“Pure” = importable and testable without a database or the framework. No
module here imports `odoo.tools`: the `db-imports-only-libs` contract holds the
package to `odoo.libs`, `odoo.exceptions`, `odoo.release` and the standard
library — re-armed in `tests/test_source_pins.py::TestThePackageImportsOnlyWhatItMayDependOn`
after it went with `tooling/` (2026-09-11); a `TYPE_CHECKING` import is the
one exception, and the scanner has a control showing it tells the two apart.

> **Nothing enforces the rest of this table.** Add the row in the same commit
> as the module; a stale row is found by reading.

## Load-bearing invariants (cross-module)

- **`db_maxconn` bounds this process's backends against a server, idle
  ones included.** The budget bounds what is checked out; each per-DSN pool
  separately retains up to `maxconn` *idle* connections for
  `db_conn_max_idle`, so without more a host serving many databases held
  `maxconn × n_databases` backends at rest — measured: four databases under
  `db_maxconn = 2` held four, with never more than one checked out. Every
  return now trims (`reaper.trim_idle_to_ceiling`, when the `ConnectionPool`
  has more than one per-DSN pool; 442 ns for four pools under the ceiling)
  the oldest idle connections of the least recently borrowed pools until
  the pools hold no more than `maxconn` in total, never below a pool's
  `min_size`, through psycopg_pool's own bookkeeping
  (`tests/contract/test_psycopg_pool_internals.py` pins the four attributes
  against the installed release). Measured: the same four databases hold
  two backends after the sequence and two after 2 s of two threads cycling
  across all four. A working set wider than `maxconn` thrashes —
  1 475 trims in those 2 s, each a reconnect — and
  `odoo_pool_connections_trimmed_total` is the counter that says so: raise
  `db_maxconn`, the ceiling is doing its job. The read/write and read-only
  `ConnectionPool`s trim independently, so two pools on one server can
  hold `2 × maxconn` at rest; the budget they share still bounds
  checkouts. Everything below is about how the *budget* is keyed and is
  orthogonal to this.

- **One budget per PostgreSQL server**: `db_maxconn` is the cap for a *server*,
  because that is what an operator sizes `max_connections` against, so
  `__init__.py` keys its `ConnectionBudget`s on the resolved `(host, port)` of
  `get_connection_info_for_database`. This has been wrong in both directions. A budget per
  *pool* let one worker hold `2 * db_maxconn` — 128 against a stock 100. One
  budget for *both* pools fixed that but bounded the sum of two independent
  servers once `db_replica_host` was set: the replica added no concurrency, and
  (verified against a live pair, `db_maxconn = 4`) four replica checkouts made
  the primary refuse. Endpoint-keying keeps both properties — same server, one
  budget; different servers, one each — and `db_maxconn_replica` sizes the
  replica's independently when it is genuinely distinct.

  The discriminator must be the *resolved endpoint*, never "is `db_replica_host`
  set": `test_enable` and `dev_mode=replica` deliberately point the read-only
  pool at the primary, and a replica host equal to the primary's is a legitimate
  way to exercise readonly routes. Treating those as two servers reinstates the
  `2 * db_maxconn` overshoot exactly. Both traps are pinned in
  `tests/test_endpoints.py`, and the key's derivation in
  `tests/test_invariants.py`.

  **Both sides of that comparison must default a missing value the same way,
  and for a while they did not** — which reinstated the overshoot through the
  one door left open. `_endpoint_of` read the port from `db_port`, which always
  has a value; the URI side read only what the URI literally spelled. So
  `postgresql:///db` resolved to `(None, None)`, never equalled `(None, 5432)`,
  and was filed as a second server with a second budget. Every ordinary URI
  omits `?port=`, and `--log-db` is the only `allow_uri=True` caller in the
  tree — `logutils.PostgreSQLHandler.emit` calls `db_connect` on every log
  record. Measured at `db_maxconn = 2`: two cursors exhausted the budget, a
  third was correctly refused, a URI cursor to the *same* server opened anyway,
  and the process held three backends against one server. One
  `get_endpoint_key` now resolves both sides, and it defaults a URI's missing host and port from
  **the config, not the environment**: `db_host`/`db_port` are registered with
  `env_name="PGHOST"`/`"PGPORT"`, so the config has already folded the
  environment in, and asking `os.environ` again is both a second source of
  truth and the worse one — it misses a `db_host` set in the *conf file*, which
  puts a bare `postgresql:///db` back on its own budget. (It is also slow:
  `os.environ` decodes on every access, and one `os.environ.get("PGHOST")`
  measures 357 ns on a function that runs per `db_connect`.) The defaulting is
  the URI path's alone — the ordinary path has nothing to default, because
  `get_connection_info_for_database` omits what has no value and that is the same "unset"
  the configured endpoint resolves to. An explicit socket directory is still
  not resolved against the compiled-in default; those two file apart, which
  errs toward an extra budget for one server rather than one budget spanning
  two.

  **There is one registry, not two, and it is an object.** `_Pool`/`_Pool_readonly` plus `_budgets`
  on one side and `_uri_pools` plus `_uri_budgets` on the other were the same
  concept keyed differently, and the duplication was charged five times: two
  pool factories, two budget lookups, and six fan-out functions each repeating
  the same three-way walk. The configured endpoint is not a special case, it is
  a key. That also closed a race the fan-out carried — `_get_uri_pool` inserted
  under `_pool_lock` while `is_pooled`, `get_pool_health`, `close_db`, `close_all`,
  `drain_db` and `drain_all` iterated the dict bare, which one writer and one
  reader thread turned into `RuntimeError: dictionary changed size during
  iteration` in 1.5 s. `get_all_pools()` snapshots under the lock, so the shape is
  gone rather than bounded.

  The registry then stopped being module state. It is
  `endpoints.EndpointRegistry`, and `odoo.db.registry` is the one the process
  uses; `__init__.py` is the public surface and nothing else. The keying
  argument above is unchanged — what changed is that a test can build an
  isolated registry instead of saving, clearing and restoring `_pools` and
  `_budgets` around every case, which is what `test_endpoints.py` did for
  all thirty of them.

  The residual trade is unchanged where it still applies: within one server a
  single budget can starve itself (a request holding a R/W cursor while opening
  a read-only one), but `db_borrow_timeout` bounds that to a `PoolError`, and a
  saturated budget now names its holders (see the checkout tracker above).
- **Budget accounting**: a permit is taken in
  `ConnectionPool.borrow`/`_borrow_directly` and travels with the connection via
  the `_odoo_pool` marker; `give_back` claims the marker with an atomic
  `dict.pop` and releases exactly once. No helper touches the budget.
  **A borrow ends exactly two ways, and each has one release site**:
  `give_back` for a connection that reached the caller, `_unwind_failed_borrow`
  for one that did not — the latter routing a *marked* connection back through
  `give_back` and releasing directly only when the marker was never set. It
  matters that **every step after the permit is taken sits inside that guard**.
  The post-acquisition bookkeeping — the checkout tracker, the leak warning, the
  borrow-wait histogram — used to run *after* the `except` that releases, so
  anything raising there burned a permit and leaked the connection for the life
  of the process; `maxconn` such failures leave every later borrow timing out on
  "connection budget reached" with no way back. **No reachable trigger is known**
  — an earlier revision of this note claimed one, that `_warn_about_leaks` reads
  `tools.config["db_leak_detection"]` on every borrow and the option might be
  unregistered outside `odoo.init`; re-checked, `configmanager` registers every
  `db_*` option at import and it resolves to its default with no `parse_config`
  at all. The `KeyError` that killed a `maxconn=4` pool in four borrows was an
  injected demonstration of the mechanism, not an incident. The guard is kept on
  its own terms: it costs nothing, the failure it prevents is unrecoverable
  without a restart, and "nothing raises here today" is not a property anyone
  can hold still. Pinned in
  `tests/test_invariants.py::TestPermitAccounting`, which walks both paths
  and asserts the permit is released on every exit.
- **A saturated pool names its culprits**: every borrow records the connection
  in a `CheckoutTracker` with the holding thread and the borrow site, and every
  return removes it, so what is left is by definition still out. `db_maxconn`
  exhaustion therefore raises `PoolError: … budget (64) reached … oldest
  checkouts: 312.4s by odoo.service.http.request.5 at addons/x/models/y.py:42`
  instead of only the limit that was hit, and `db_leak_detection` warns about a
  checkout held past its threshold before the pool runs dry. The borrow site is
  captured unconditionally: the walk stops at the first application frame, so it
  costs 300 ns — less than the tracker's own 413 ns insert/delete pair — and
  gating it would have left the error mute exactly where it is needed. The leak
  warning has its own throttle, never the reaper's, or one would silence the
  other.
- **A replica is configured per keyword, and its failures decay**: all five of
  host/port/user/password/sslmode are overridable via `db_replica_*`, each
  falling back to the primary's `db_*` when unset, so a replica with its own
  role is expressible (only host/port used to be, and the inherited credentials
  failed with nothing to explain why). `ReplicaRouter.cursor(readonly=True)` —
  what `Registry.cursor` delegates to — gates the replica behind a
  `CircuitBreaker`: the flat 20-minute demotion it replaces
  cost that long for a transient blip and never re-checked, where the breaker
  opens for a second and doubles to the same 20-minute ceiling, so the worst
  case is unchanged and a blip recovers immediately. Measured against a real
  streaming replica: stopped mid-traffic and restarted, read-only cursors
  resumed **5.1 s** after the outage. One caller probes at a time, or a dead
  replica draws a connection attempt from every request that arrives while it
  is out.

  **A replica borrow never waits out `db_borrow_timeout`.** It has a
  fallback, so `ReplicaRouter` opens it with `borrow_timeout=REPLICA_BORROW_TIMEOUT`
  (5 s) and `fail_fast=True`. Measured before that against a refused port:
  the first read-only request blocked **30.00 s** — the probe files a refused
  connect as *transient*, which is right for the primary (a restart should be
  waited out) and hands the whole deadline to `getconn`, which retries a
  server that is not listening; and the breaker re-probed on every cooldown,
  so a request stalled 30 s at each half-open attempt. `fail_fast` ends the
  borrow the moment the probe reports a transient failure, and it also
  re-probes a *surviving* pool whose proof is gone and which has nothing
  idle: psycopg_pool keeps counting the connections it cannot open in
  `pool_size`, so the pool object outlives the outage and, without that,
  every attempt walked into `getconn` again. Traced through a killable TCP
  proxy in front of the socket: replica dies → the first borrow costs the 5 s
  `getconn` deadline (the timeout revokes the proof), every attempt after that
  falls back in 0.00 s, and the replica serves again on the first half-open
  attempt after it returns. The one 5 s is the proven-key case, where nothing
  before `getconn` can know the backend is gone; a replica that dies within
  `db_healthcheck_grace` of a return hands its dead connection out once
  unchecked, which is that window's documented trade.
- **Staleness is bounded, not merely tolerated**: read-only routes are chosen
  because they tolerate stale reads, but "tolerates any amount, unmeasured" is
  not a guarantee. `db_replica_max_lag` (0 = off) demotes reads to the primary
  while the replica's *apply* lag exceeds it, sampled at most every
  `max(1, value/4)` seconds on a cursor already borrowed for the request — so an
  enabled ceiling costs one query per sample, not per request, and a disabled
  one costs nothing. The measurement is the subtle part:
  `pg_last_xact_replay_timestamp()` grows without bound on an *idle* primary
  (measured 43 s against a standby with nothing left to apply), so `LAG_SQL`
  reports zero whenever the standby has replayed everything it received and
  falls back to the replay timestamp only when WAL is genuinely outstanding. It
  therefore bounds apply lag and not receive lag: WAL the standby has not
  received is indistinguishable from an idle primary without querying
  `pg_stat_replication` on the primary, which would defeat the point of reading
  elsewhere. A measurement that fails is recorded as healthy — a replica that
  cannot answer is one whose failure the breaker sees anyway, and demoting on
  a failed *question* would demote on no evidence. **WAL received and not
  replayed on a standby that has replayed no transaction yet is infinite
  lag, not zero**: `pg_last_xact_replay_timestamp()` is NULL until the first
  replayed commit, the `ELSE` arithmetic came out NULL and the `coalesce`
  called 1.5 s of outstanding WAL "caught up" (measured on a fresh standby
  with replay paused: receive `F9/7101E310`, replay `F9/71000000`, answer
  `0`). The query answers `'infinity'` there, the gate demotes on it, the
  warning says "an unknown amount", and the first replayed commit turns it
  into a number. Found because the standby contract test, run inside the
  whole suite, met a standby that had nothing to replay since its start.
- **The trades this layer makes are countable**: a shared budget that can
  starve itself, and a probe that trades a connect for a fast permanent
  failure, are only defensible if an operator can watch them. **Both borrow
  paths therefore end in one guard, and that guard counts.** `_borrow_directly`
  had four exits and only the last of them called `record_borrow_failed`, so a
  maintenance endpoint refusing every connect read `borrows_failed: 0` while
  the pooled path counted the same failure as 1 — and `db_connect("postgres")`
  is the cron's heartbeat, so an unreachable maintenance DB is exactly what
  `db.get_pool_health()` is read to find. The permit was always released
  correctly; what was missing was the ability to see that it had been. `PoolStats`
  records the borrow-wait histogram, pool churn and probe outcomes; the budget
  counts its own exhaustions (it is shared, so the count belongs to it, not to
  whichever pool asked last); `ConnectionPool.get_health()` and `db.get_pool_health()`
  render both alongside the live per-DSN psycopg_pool view. Cost on the borrow
  path is 230 ns, against a ~140 µs cursor cycle.
- **The pre-flight probe answers a question once**: it converts a permanent
  connect failure into a millisecond error instead of a ~30s `PoolTimeout`, at
  the cost of a full extra connect. A DSN that has connected is recorded in
  `ReachabilityProbe` as proven, so a pool *rebuild* (idle reaper, `PoolClosed` race) skips
  it — with the default `db_pool_reap_idle` (300s) below `db_conn_max_idle`
  (600s), a quiet database is reaped and rebuilt repeatedly and used to re-probe
  every time. The proof is revoked wherever its premise could have changed:
  `close_database` (Odoo's drop/rename path), stale-credential eviction, and any
  connect failure. `mark_proven` runs on every borrow and looks before it
  locks: set membership is one atomic read (27 ns against 157 ns with the
  lock), and a stale miss only takes the lock it would have taken anyway.
- **Reaping is edge-triggered on a return, so every return triggers it.**
  `_reap_idle_pools_if_due` has no timer, deliberately: a timer is a thread and
  this class already carries `db_pool_workers + 1` of them per database. That
  makes the set of returns that reach it the whole of the reaper's schedule, and
  the maintenance branch of `give_back` used to `return` before it. The direct
  path is not exotic — `db_connect("postgres")` is the cron's heartbeat, the
  only periodic activity an otherwise idle worker has — so a server whose
  tenants had gone quiet reaped nothing while the one call that kept arriving
  was the one that could not. Measured with `db_pool_reap_idle=2`: five
  maintenance cursors moved nothing, a single pooled return collected both idle
  pools. Note what this does *not* leak: psycopg's own per-pool scheduler closes
  idle connections after `db_conn_max_idle` with no traffic at all, so the
  residue was always pool objects and their threads, never backends.
- **`db_pool_workers` is a per-database number.** psycopg's default of 3 workers
  plus its scheduler thread is a per-*pool* figure, and this class holds one pool
  per database: measured, 12 databases in one process held 49 threads and 40 held
  161 — 4.0 each — for +135 KB RSS apiece and 0.35% of one core while completely
  idle. The workers now run `AddConnection` only (see the next entry), so the
  extra two buy parallelism between connection *opens* of the same database.
  The default is 1, which is 2.0 threads per database.
- **The session reset runs on the returning thread, and the psycopg pool is
  built with `reset=None`.** With a `reset=` callback, `putconn` hands every
  return to the pool's worker and the next `getconn` finds nothing idle — so
  psycopg_pool *grows* the pool rather than wait for the connection in flight.
  Measured: a single-threaded open/`SELECT 1`/close loop held **14 backends**,
  and 8 request threads held **63**, the `maxconn` ceiling, with every return
  for the database queueing behind one worker thread. `give_back` resets
  first (`_reset_returned_connection`; a reset that raises discards the
  connection the way a failed rollback does) and `putconn` then files an idle
  connection synchronously. Same loops afterwards: **1 backend**, and backends
  equal to the thread count at 8/16/32 threads, with +20% / +7% / +13% more
  cycles per second in that loop. Against a running `odoo-bin` (16 and 32
  client threads of `res.partner.search_count` over JSON-RPC, `pg_stat_activity`
  sampled every 50 ms) the throughput is unchanged — 282 → 280 req/s, the
  server is bound elsewhere — and the peak backend count goes **64 → 16** and
  **64 → 31**: the old shape reached the `maxconn` ceiling with 16 request
  threads. The one number that goes the other way is the serial loop,
  **117 → 140 µs per cycle**: the returning thread now waits for the round
  trip that seven spare backends used to hide.
- **A pooled connection's transaction flags are set once, and the session
  reset goes through libpq's simple-query call.** `Cursor.__init__` used to
  set `isolation_level` and `read_only` on every borrow and `_reset_connection`
  set both back to `None` on every return: four psycopg setters, 2.5 µs per
  cursor cycle, to re-establish the same two values. A pooled connection serves
  one pool for its whole life, so `_configure_connection(conn, readonly=…)`
  sets them once and `_reset_connection` compares before it sets (50 ns) —
  only `enforce_readonly()` ever changes one, and the comparison is what puts
  it back. The reset string itself is sent with `conn.pgconn.exec_`: one
  simple-query round trip with no BEGIN folded in, so the `autocommit` toggle
  that bracketed it is gone too, and none of `execute()`'s per-statement
  machinery runs — **14 µs against 24 µs**, measured. Its `status` is a bare
  `int`, never the `ExecStatus` member: an identity comparison passed against a
  fake and failed every live reset (each return discarded the connection and
  the cycle read 2.2 ms), which is why `tests/test_lifecycle.py`'s fake returns
  the `int`. The liveness `check` sends the same empty simple query
  psycopg_pool's own `check_connection` does, minus the `autocommit` toggle it
  wraps around `execute()` (8 µs against 12.7); a terminated backend answers
  `FATAL_ERROR` once and raises after, and `_probe_liveness` raises on
  anything but `EMPTY_QUERY` so the pool discards. Cycle (open, `SELECT 1`,
  close) before the inline reset below: **160 µs → 134 µs**. The
  `__init__` guard also no longer re-reads `pool.readonly` for its own debug
  line — a pool attribute that raised there escaped before `give_back` ran.
- **A cursor close only discards a DAMAGED connection**: `Cursor._close` asks
  `transaction_status` (`_is_connection_clean`) rather than treating any
  exception from `_rollback` as connection damage — that method also runs
  `transaction.clear()` and the rollback hooks, so an application bug there used
  to cost a warm pooled connection on top of the error.
- **One borrow, one deadline**: `db_borrow_timeout` is taken at the top of
  `ConnectionPool.borrow` and every step that can block derives its own timeout
  from it — the cold path's pre-flight probe (and its `is_database_absent`
  fallback), the semaphore wait, `getconn`, and the direct maintenance connect.
  `get_libpq_connect_timeout` clamps each libpq connect and returns `0` to mean
  *skip this connect*, never a value to pass on: libpq reads `connect_timeout=0`
  as "wait forever", so handing it a shrinking budget would make the tail of a
  deadline unbounded.
- **Maintenance databases are never pooled** (`postgres`, templates,
  `db_template`): `borrow` routes them to `_borrow_directly`, `give_back`
  closes them outright. A psycopg_pool cannot keep a database
  connection-free — it replaces every discarded connection to hold its count —
  and one idle connection to a template blocks
  `CREATE DATABASE … TEMPLATE`.
- **DDL needs client-side params**: PostgreSQL rejects `$N` in DDL structural
  positions, so `Cursor.execute` detects DDL (`ddl.py`) and inlines params as
  quoted literals. Schema-changing DDL additionally clears this connection's
  auto-prepared statements and this cursor's `TransactionSchemaCache`, and
  arms `_schema_changed` so that **`commit` drains this process's other pooled
  connections** for that database; *other processes* are healed via registry
  signaling → `drain_db`. The drain is taken at commit, not per statement, for
  two reasons. An uncommitted schema change is invisible to every other
  connection, so there is nothing to heal until it lands — and draining earlier
  would hand out a fresh connection that then warms a plan against the *pre*-DDL
  schema. And `psycopg_pool`'s `drain()` closes each idle connection **and
  schedules a replacement**, so per-statement draining churns the whole pool once
  per DDL statement: measured over a `base` install's 999 schema-changing
  statements, 31.6 ms per-statement against 2.1 ms per-transaction. Without this,
  a sibling connection that had auto-prepared `SELECT id, a FROM t` before an
  `ALTER COLUMN a TYPE` keeps the stale plan and raises `FeatureNotSupported:
  cached plan must not change result type` — *intermittently*, only when the next
  borrow happens to draw that backend. A connection checked out by another thread
  when the DDL commits stays poisoned for the rest of its transaction (which is
  already racing a schema change), but cannot pool it: `drain()` stamps
  `_drained_at`, so it is discarded on return.
  Two different questions, two functions: `_get_ddl_keyword` reports the **leading**
  keyword (all param inlining needs — psycopg cannot bind server-side params
  into a multi-statement string at all), while `_has_schema_changing_statement` scans **every**
  statement, because `BEGIN; ALTER …; COMMIT` would otherwise slip past
  invalidation and make the next `SELECT *` raise `FeatureNotSupported`.
- **Binary COPY reads the catalog under COPY's own lock**: binary COPY encodes
  values client-side from `pg_attribute` types, so a type read *before* the
  lock is not authoritative — a concurrent `ALTER` can commit while our `COPY`
  waits on that lock, and a same-width change (`int4`→`date`) is then written
  with no error. `_lock_table_for_bulk` takes `ROW EXCLUSIVE` (the mode `COPY`
  needs anyway) *before* the catalog read, and the facts it guards live on the
  cursor only until the transaction — hence the lock — ends. That is why
  `close_db`/`drain_*` carry no schema-cache invalidation: no process-global
  schema state exists to go stale.
- **The schema cache holds two different lifetimes**: the memoized catalog
  reads expire whenever DDL lands (`invalidate_catalog_facts`, called from
  `invalidate_cached_plans`), but the lock ledger — which tables this
  transaction has already locked — expires only where the locks themselves
  do. DDL does not end a transaction, so the `ROW EXCLUSIVE` lock survives it
  and re-issuing `LOCK TABLE` is a wasted round-trip. A `ROLLBACK TO SAVEPOINT`
  *does* release locks taken inside the savepoint (verified against PG 18) —
  but only those: a table locked before the savepoint opened keeps its real
  lock and must keep its ledger entry too. `_on_rollback_to_savepoint` tracks
  the savepoint depth each table was locked at
  (`TransactionSchemaCache.mark_locked`/`is_locked`) and releases the ledger
  entry *and* that table's cached facts together, per table, for every table
  locked at or after the depth being rolled back to
  (`release_locks_since_depth`) — never the whole cache, and never gated on
  whether *this* cursor's own DDL ran: dropping the real lock is what can let
  a concurrent session's DDL become visible, regardless of which cursor
  issued it.
- **One resolution of the caller's table name**: `bulk._get_table_identifier`
  splits on `.` and builds a `psycopg.sql.Identifier`, and every consumer uses
  it — `LOCK TABLE`, `COPY`, and (via `Identifier.as_string()`) the
  `%s::regclass` catalog reads and `pg_get_serial_sequence`. They used to
  disagree: the lock and the COPY quoted the name as one identifier while the
  catalog lookups passed the raw string to casts that parse and case-fold, so
  `MyTable` locked `"MyTable"` but read its column types from `mytable` (an
  `int4` column read as `oid` stored `4000000000` as `-294967296`, silently),
  and `s1.t` became the single identifier `"s1.t"`, which matches no
  schema-qualified table.
- **`binary=True` means "the faster encoding", not "binary"**: `copy_from`
  degrades to text on two independent grounds, both decided in
  `_is_binary_copy_worthwhile` where the column OIDs already are. psycopg has no binary
  dumper for extension/composite/range types (`_can_dump_binary`); and it has
  no float→numeric binary dumper, so each numeric cell costs a `Decimal`
  conversion. Measured, 20k rows × 20 columns: binary beats text at 0–5 numeric
  columns (−60% to −9%) and loses from 6 (+15%, +291% at 20), so
  `_BINARY_NUMERIC_MAX_FRACTION` puts the crossover at a quarter of the row.
  The ORM used to duplicate this as "any numeric column at all", which forfeited
  9–56% on the ordinary Odoo row shape (a few Monetary/Float fields among many
  char/int/date/m2o columns). Both fallbacks insert identical rows for the same
  input, so a caller never has to know its column *types* — but it does have to
  hand over the right Python *values*; see below.
- **One envelope for every statement entry point**: `execute`, `executemany`,
  `cr.copy()` and `copy_from` each used to carry their own timing, query-hook
  fan-out, DEBUG line, error tier and counting decision — four copies of one
  shape, and each had drifted into a defect of its own.
  `executemany` never called `_invalidate_cached_plans_if_stale`, so the replay
  `service.transaction.retrying` performs for `execute` did not happen for it
  (same table, same `ALTER COLUMN … TYPE`, same connection: `execute` raised
  `FeatureNotSupported` marked, `executemany` raised it unmarked, and through
  `retrying()` the first recovered on its second call while the second
  propagated — and `res_users` batches its writes with `executemany` on the
  request path). `copy_from` recorded nothing when the COPY failed, against the
  round-trip rule below, on the ORM's own bulk-create path. And `cr.copy()`
  timed the construction of psycopg's `@contextmanager` rather than the
  transfer — 200 000 rows, 120.4 ms of work reported as 0.008 ms — while having
  no `except` at all, so a failed COPY was the one statement failure this layer
  never reported. `_statement_failed` and `_statement_done` are that envelope
  and all four route through both; a statement counts when it succeeded or when
  it failed *at the server*, and the stale-plan mark is taken once for every
  path.

  **It is two plain methods and not one `@contextmanager`, and that is
  measured.** The first version was a generator, which is the obvious shape and
  the wrong one on a path this hot: per statement, wire stubbed out,
  **984.7 ns before the consolidation, 1802.8 ns behind the generator,
  980.7 ns behind the pair** — +818 ns, 83%, in a function where 64 ns has been
  thought worth banking. `_statement_failed` owns the `except` branch, where
  two of the three defects lived, and costs nothing at all on the success path
  because it is not called; `_statement_done` owns the `finally`, and takes
  `debug` from its caller rather than asking `isEnabledFor` a second time.
  The remaining copy — the `try/except/finally` that `execute` and
  `executemany` each wrap around those two — was measured too (2026-09-13):
  a `_run_statement(run, …)` helper taking a closure, all-positional, read
  **1518 → 1860 ns** per statement wire-stubbed, +340 ns for the frame and the
  closure. The two copies stay, and the seam pins hold them to one shape.
- **`executemany` counts toward arming the pipeline**: `pipeline()` enters
  psycopg's mode on the second *statement*, and the counter was called from
  `execute` alone, so a block made of `executemany` calls never armed. Not
  unpipelined — psycopg's `executemany` opens its own pipeline when none is
  active and rides an existing one when there is — but one sync per call where
  the caller asked for one for the block. Interleaved, 25 reps: +17% at
  20×50 rows, +32% at 50×10, +14% at 5×200, the win scaling with the call
  count. Arming sooner makes `in_pipeline` true sooner and so could push ORM
  creates off COPY; it cannot, because the ORM never calls `executemany`.
- **The deduplicated probe hands out one exception, so it must hand out one
  traceback too**: the followers waiting on a failed probe re-raise the
  leader's object, and a `raise` *appends* to that object's `__traceback__`.
  Eight followers on a dead DSN — the case the dedup exists for — grew it to
  19 frames of the same two frames from unrelated threads, each keeping its
  thread's locals alive. `.with_traceback(None)` bounds it at 2 whatever the
  number of waiters, and keeps the object, so the type and SQLSTATE callers
  dispatch on are untouched. psycopg does the same in `Cursor.copy`.
- **Two questions, one scan**: `Cursor.execute` asks of every statement both
  "what DDL keyword leads it" and "is it a `ROLLBACK TO`", and each answer used
  to do its own `lstrip`, its own two-character prefix test and its own
  frozenset lookup. Microbenchmarked over 200k iterations on a typical ORM
  SELECT — a live round trip (~14 µs) cannot see this — `_get_ddl_keyword` cost
  120 ns and `_is_rollback_to_savepoint` 113 ns against `_has_schema_changing_statement`'s
  47 ns, so the duplicated prefix dance was most of the classification cost.
  `classify_statement` answers both in one pass; the DDL keywords and
  `ROLLBACK` share no two-character prefix (`RE`VOKE against `RO`LLBACK), so
  only a comment-led statement runs both regexes.
- **The statement entry points are marked, and the marks are enforced**: every
  method that puts a statement on the wire (`execute`, `executemany`,
  `execute_values`, `copy_from`, `copy`) calls `_before_statement()`, a no-op
  in this layer whose purpose is to *name* that set. `odoo.tests.cursor.
  TestCursor` takes its rollback savepoint before the first statement of a
  test; only its `execute()` override did so, and the bulk APIs it does not
  override reach the real cursor via `__getattr__`, so their writes landed
  outside the savepoint and survived the rollback. The scan matches statements
  on **both** `self._obj` and `self._cnx`: `invalidate_cached_plans` used to reach
  the connection directly for its `DEALLOCATE ALL` fallback, a wire call the
  `_obj`-only scan could not see. That branch goes through `self.execute` now,
  so it is counted and marked like any other statement. `TestCursor` now forwards
  each marked name explicitly and two tests pin the lists against each other,
  so a write API added without a forwarder fails rather than escaping. It
  cannot be done by hooking the wrapped cursor instead: several `TestCursor`s
  share one real cursor, so such a hook opens whichever is innermost rather
  than the one the caller holds. Argument validation runs before the mark — a
  rejected call issues no statement and must not open a savepoint.
- **`BaseCursor` declares only what it has**: it used to inherit
  `psycopg.Cursor` under `TYPE_CHECKING` and `object` at runtime, so mypy
  believed every cursor flavour — including `TestCursor`, which forwards by
  `__getattr__` — had psycopg's whole API. `cr.stream(...)` type-checked clean;
  that is how the bulk-write bypass above stayed invisible to the type checker.
- **Binary COPY types are OIDs, and `binary=True` is only a hint**: the catalog
  read returns `pg_attribute.atttypid`, not `pg_type.typname`, because
  `Copy.set_types()` resolves a *name* through psycopg's registry — which knows
  only built-in scalars, so an array column (`typname` `_int4`) raised
  `KeyError` even though psycopg dumps `int4[]` fine by OID. Domains resolve to
  their ultimate base type and enums to `text` (identical wire format); anything
  psycopg still has no binary dumper for — an extension type such as pgvector's
  `vector` or PostGIS's `geometry`, a composite, a range — is detected by
  `_can_dump_binary` *before* the COPY context opens and silently degrades to
  text COPY, which writes identical rows.

  **`binary=True` is safe against the column type and NOT against the value
  type, and an earlier revision of this entry claimed both.** The degradation
  above means a caller never has to know what its columns are — verified
  against PG 18 for every shape this fork can meet: an `int4[]` array and a
  `bytea` encode binary by OID, a domain resolves to its base type, an enum
  reports `text` (oid 25), and pgvector's `vector`, PostGIS's `geometry` and a
  composite are all refused by `_can_dump_binary` and written as text. What
  does not carry over is the Python side: binary encoding needs the exact type
  where text hands the string to PostgreSQL to parse. Same table, same rows,
  the two modes measured against each other:

      uuid  <- str   text ok, binary AttributeError
      int   <- "42"  text ok, binary TypeError
      date  <- str   text ok, binary TypeError
      inet  <- str   text ok, binary AttributeError

  The ORM is unaffected — `convert_to_column` already produces typed values —
  and re-running as text on an encoding failure is the wrong repair, because a
  caller passing `"42"` for an `int4` column has a bug that text COPY happens
  to hide. `copy_from` instead adds a note to the exception naming binary COPY
  as the reason the value was rejected, so the failure says what to change.
  **The note is attached around `write_row` and nowhere else**: the `except`
  that used to add it wrapped the whole COPY block, so a `KeyError` raised by
  the caller's own row generator arrived explaining psycopg's client-side
  encoding — traced live, the note was on it. The rows are the caller's; only
  the encoding is ours.

  **`cr.copy()` refuses pipeline mode the way `copy_from` does**, before
  `_before_statement` and through the same `_prepare_copy_in_pipeline_error`.
  Left to psycopg the refusal is the same `NotSupportedError`, but it arrives
  through the seam and is logged as `bad COPY` with the statement, for a
  client-side rejection that never reached the wire.
- **db→ORM dependency is one-directional**: the ORM injects
  `_OrmFlushingSavepoint` (as `BaseCursor._flushing_savepoint_cls`) and the
  `transaction` attribute at import; `cursor.py` guards that a
  transaction-bearing cursor never runs a non-restoring savepoint.
- **Odoo's session GUCs set defaults, they do not override the operator**:
  `_prepare_session_gucs` renders `db_session_gucs` (`jit=off,work_mem=16MB`) into `-c`
  switches, skipping any GUC already named in the operator's `options` kwarg,
  URI `?options=`, or `PGOPTIONS`. libpq lets the last `-c` win, so appending
  unconditionally silently overrode them — `PGOPTIONS='-c work_mem=64MB -c
  jit=on'` arrived as `work_mem=16MB`/`jit=off`, with nothing in any log.
  `idle_session_timeout` is still applied unconditionally: it is derived from
  `db_conn_max_idle` and is what keeps the server from reaping a connection the
  pool still considers warm. A comma starts the next entry only when a `name=`
  follows it, so a list-valued GUC (`search_path=public,pg_catalog`) is one entry;
  `db_session_gucs` used to be split on every comma and could not carry one.

  **`ODOO_FAKETIME_TEST_MODE` pins `search_path=public,pg_catalog` the same way,
  as a startup `-c` after the operator's options** (`_get_forced_gucs`), for the
  databases `-d` names. `Cursor.__init__` used to issue `SET search_path` and a
  `COMMIT` on every cursor — two round trips per cursor in that mode, and a
  statement in the constructor's window where a failure has no owner. As a
  startup option it costs nothing per cursor and survives the `RESET ALL` on
  every return, which a `SET` would not have (it is re-issued only because the
  constructor runs again). Pinned live in
  `TestFaketimeSearchPathIsAStartupOption`: `current_schemas(true)` answers
  `[public, pg_catalog]` on a fresh cursor and after a return, at one statement.
  **Maintenance connections are exempt from `db_session_gucs`, deliberately**,
  and both borrow paths now render options through one `_prepare_connection_options`
  where `_borrow_directly` passes `session_gucs=None`. They used to build the
  string twice and the direct copy simply never gained `_prepare_session_gucs`, which
  reads like drift — but applying them there "for consistency" is a regression,
  measured: under `db_session_gucs = statement_timeout=50ms` a `CREATE DATABASE
  … TEMPLATE` dies with `QueryCanceled`, and under
  `default_transaction_read_only=on` a `DROP DATABASE` raises
  `ReadOnlySqlTransaction`; both succeed without the GUCs. `statement_timeout`
  is one of the commonest things an operator puts there and a template copy
  legitimately runs for minutes, so a policy tuned for application queries must
  not follow administrative DDL. The duplication was still worth removing: what
  it cost was the ability to *see* the exemption. `idle_session_timeout` is
  outside it and still applied to both.
- **A stale cached plan is recoverable, and is recovered one layer up**: after a
  committed schema change, a sibling connection re-executing an auto-prepared
  statement gets `FeatureNotSupported: cached plan must not change result type`.
  It **cannot** be retried where it happens — measured, the transaction is left
  `INERROR`, so both a bare retry and a `invalidate_cached_plans()` + retry raise
  `InFailedSqlTransaction`, and recovering inside `Cursor.execute` would need a
  savepoint per statement: two extra round trips on every query in core. The
  replay is safe (the plan check runs *before* execution, so a failing prepared
  `INSERT` leaves no row) and it already exists in
  `service.transaction.retrying`, so the cursor's only job is to **name** the
  condition. It is the one place that can: SQLSTATE `0A000` also covers
  permanent failures such as "cannot alter type of a column used by a view", and
  the message text is translated under `lc_messages`. `_invalidate_cached_plans_if_stale`
  therefore marks the exception when the connection held auto-prepared
  statements — the necessary condition — and clears them so the replay
  re-prepares. Over-inclusion is bounded by the retry budget; under-inclusion is
  impossible. `retrying` has to name `PG_STALE_PLAN_EXCEPTIONS` in its `except`
  explicitly, because `FeatureNotSupported` is **not** an `OperationalError` and
  was never caught at all. Measured, six readers against a writer altering a
  column they read: **6832 failed requests → 0**. A stale plan met by *this*
  connection came from a schema change this process never saw land — a DBA's
  `ALTER`, another process's migration, anything outside the registry
  signal — so the idle siblings hold the same plans and would each burn a
  retry of their own; `_drain_siblings_after_stale_plan` drains the
  database's idle connections once per `_STALE_PLAN_DRAIN_INTERVAL` (5 s), so
  a burst of requests heals the pool once rather than draining it once each.
- **Pipeline mode does not exempt a statement from the seam**: psycopg does
  not raise where a pipelined statement was issued — it queues the command and
  surfaces the server's error at the next sync, which is `Cursor.pipeline`'s
  `ExitStack` exit, outside every entry point's own `try/except`. The whole of
  `_statement_failed` was therefore skipped for the whole of pipeline mode.
  Measured on one connection across one committed `ALTER COLUMN … TYPE`, the
  same statement twice:

      plain cr.execute                 FeatureNotSupported, MARKED
      cr.execute inside cr.pipeline()  FeatureNotSupported, unmarked

  The mark is what `service.transaction.retrying` dispatches on, and end to
  end that is the whole difference — the same pipelined SELECT through
  `retrying()` **raised `FeatureNotSupported` on attempt 1 before this and
  recovered on attempt 2 after**.

  **Which statements can reach it is narrower than "everything the ORM
  pipelines", and an earlier revision of this entry got that wrong.**
  PostgreSQL raises `cached plan must not change result type` only when the
  altered column is in the statement's *result descriptor*: measured, a plain
  `UPDATE`, an `INSERT` without `RETURNING`, and `UPDATE … RETURNING id`
  where `id` is not the altered column are all silently revalidated. So the
  748 plain UPDATEs `write.py::_update_rows_*_sql` contributes — the bulk of
  what the ORM pipelines — cannot reach it at all, and citing them was the
  error. What can, counted over `/base` + `/test_orm` + `/test_new_api`, is
  every *result-returning* statement the ORM runs inside an armed block: 44
  SELECTs from `orm/runtime/environment.py::execute_query`, 25 and 9 from
  `addons/base/models/ir_default.py`, 26 `UPDATE … RETURNING` from the
  parent-store maintenance, and `create.py::_prepare_create_values`.

  The logging half is reachable from the ordinary write path regardless of
  result descriptors, and is the more common loss: a `ForeignKeyViolation`
  raised out of a pipelined `res.partner` write logged **nothing at all**
  before this and logs `constraint violation (surfaced to the user):
  ForeignKeyViolation on res_partner_parent_id_fkey` after. `pipeline` now routes the deferred
  error through the seam, gated on `has_reached_server` so that whatever the
  caller's own block raised — a plain Python error carries no SQLSTATE — is
  none of the seam's business. Only the outermost block hooks it; a nested one
  syncs nothing and can observe nothing.

  **The seam is idempotent, and that is what makes two call sites safe.**
  `mark_handled_by_seam` / `is_handled_by_seam` in `errors.py` sit beside the stale-plan
  marker and answer a different question, so a statement whose error *did*
  surface at its own entry point — the first statement of a block, which runs
  before `_arm_pipeline` enters the mode; a client-side rejection — passes the
  pipeline exit untouched instead of being logged a second time. The counting
  half is not fixable the same way and is not claimed to be. In pipeline mode
  `obj.execute` returns before the server has answered, so `counts` records
  "queued", not "accepted", and after an error PostgreSQL discards the rest of
  the batch: measured, five statements issued with the third failing and the
  last two never executed still count **5**. That over-count predates this and
  survives it — psycopg reports *that* a queued command failed and not
  *which*, so there is nothing to attribute the correction to.

  `execute_values` carried a third of the seam inline for this reason — a bare
  `_log_sql_error` on its pipelined path — which is the drift the envelope
  above exists to prevent, and it left the stale-plan mark off the bulk write
  path that `account_partial_reconcile`, `account_full_reconcile`,
  `website_sale`, `planning` and `hr_attendance` all reach. **It carries no
  seam of its own now.** Every page it issues goes through `self.execute`,
  whose `except` is the seam, and a deferred pipelined error surfaces at the
  exit of the `self.pipeline()` block it opened; the `except` it kept for a
  while between the two only ever short-circuited on the mark — traced on
  both paths (pipelined, and `fetch=True` which never pipelines), each logged
  exactly one `cursor.statement_failed` from its entry point followed by one
  `cursor.statement_seam_short_circuit` from `execute_values`. `Cursor.pipeline`
  takes `log_exceptions` and `query` so the block keeps honouring its caller's
  flag and keeps naming its caller's SQL — psycopg reports *that* a queued
  command failed and not *which*, so a block of unrelated statements can only
  say so, while one whose statements share a template should pass it.
- **A pipeline's server wait is measured where psycopg waits, never inferred
  from the block's wall time.** In pipeline mode `execute` returns once the
  command is queued, so a statement's own `delay` is client time and the server
  work lands in whichever call syncs: the first `fetch*()` after a queued
  statement (`Cursor._wait_in_pipeline`) or the block exit (`Pipeline.__exit__`).
  The previous accounting booked `wall − Σ statement delays` as query time,
  which is right for `execute_values` — a block of nothing but statements — and
  wrong for every ORM block: `Transaction._flush_as` wraps the whole
  `flush_model` loop in `cr.pipeline()`, so field conversion and value building
  were reported as `query_time` in the request log. Measured, 50 ms of
  `time.sleep` between two pipelined statements read **52.5 ms of query time
  before and 1.7 ms after**. `_wait_in_pipeline` times the fetches while the
  mode is entered, an `ExitStack` callback pushed right after
  `enter_context(self._cnx.pipeline())` — so it runs first on the LIFO exit —
  stamps when the pipeline's own exit starts, and the block books the sum.
  `execute_values` over 20 000 rows still accounts for 88% of its wall time;
  the remainder is the Python that renders 100 batches, and it is client time.

  **`rowcount` and `description` sync on demand for the same reason.** psycopg's
  `rowcount` reads a field that the pipeline has not filled yet: measured, every
  statement after the mode arms answered **−1**, and `bool(-1)` is `True`, so an
  `if cr.rowcount:` in a pipelined path passes for zero rows. `Cursor.rowcount`
  and `Cursor.description` sync through the public `Pipeline.sync()` of the
  pipeline the block entered when the cursor has queued a statement since the
  last sync, and the sync counts as a wait. The condition is the cursor's own
  `_pipeline_pending` flag, not psycopg's `pgresult`: after a pipelined
  `executemany(returning=False)` psycopg keeps `pgresult` at `None` even once
  synced, so that test both missed the sync when it was due and would have
  re-synced on every later read. What psycopg then reports is psycopg's:
  measured on the raw cursor, an `executemany` queued behind an *unfetched*
  SELECT folds that SELECT's row into its count (3 for two inserts) in pipeline
  mode and not outside it. Pinned in
  `tests/test_cursor.py::TestPipelineAccountsForTheSyncCost`.

  **How big the over-report was on real work, not on a `sleep`**: a JSON-RPC
  `res.partner.create` of 300 records, three runs each against the same
  database, read `query_time` **0.041 / 0.032 / 0.046 s before and 0.029 /
  0.024 / 0.026 s after** on identical query counts (331 / 320) — about a third
  of the reported figure, some 12 ms of a ~150 ms request. In-process, the same
  shape showed 50 pipeline blocks whose wall was 57 ms against 19 ms of
  statements and 16 ms of measured waits; the difference is the ORM's own value
  building inside `_flush`, not compute methods — traced with the
  `recompute` and `db.cursor` channels, 0 of 312 recompute events fell inside
  an entered block, because `flush_until_converged` recomputes before it
  flushes.
- **The libpq health parameters are ones every supported libpq accepts.**
  `_HEALTH_PARAMS` reaches libpq as keywords on every connect, pooled and
  direct, and libpq rejects a keyword it does not know outright — not with a
  warning, with a failed connect. `min_protocol_version` (libpq 18) sat in that
  dict at its own default of `3.0`: measured, a connect with it and without it
  both negotiate protocol 30000, so it bought nothing and made the whole layer
  refuse to connect through any wheel built on libpq 17. The youngest keyword
  left is `tcp_user_timeout` (libpq 12); `tests/test_utils.py` pins the set.
- **`execute_values` never asks the server for more than 65 535 bind parameters.**
  The extended protocol counts them in a uint16, and PostgreSQL refuses the
  statement outright (`number of parameters must be between 0 and 65535`) —
  measured on the raw cursor with one column and 65 536 rows. A page closes
  when the next row — a tuple's width, or one parameter for a scalar row —
  would push it past the ceiling, decided per row so the rows are walked
  once and mixed widths pack by what each row binds; the caller's page size
  is a hint about round trips, not a contract about statements.
- **A savepoint is never opened inside a pipeline**: a savepoint exists to make
  the next failure recoverable, and in pipeline mode it cannot. PostgreSQL
  discards every queued command after an error until the next sync, and the
  `ROLLBACK TO SAVEPOINT` the failure is supposed to trigger is one of them.
  Measured on a live cursor, the same `UniqueViolation` under the same
  savepoint: outside a pipeline the transaction stays usable (`SELECT count(*)`
  answers), inside one the next statement raises `InFailedSqlTransaction`. It
  is silent — the caller's `except UniqueViolation` runs exactly as written and
  the transaction it believes it repaired is dead — and it takes out
  `get_or_create_row`, whose whole contract is that branch, so
  `BaseCursor.savepoint` refuses, the way `copy_from` refuses pipeline mode for
  its own reasons.

  **The refusal is not free and the cost was measured, not assumed**:
  `get_or_create_row` inside a pipeline *works today on the happy path* —
  `ir.config_parameter.set_param` inside a `cr.pipeline()` returns normally
  when no conflict occurs, because the savepoint is opened and released
  without ever rolling back — and this turns that into a `RuntimeError`. The
  trade is taken because the case that works is the one where the savepoint
  was never needed, while the case the helper exists for is the one that
  corrupts the transaction; nothing in the tree composes the two (4870 tests
  across `/base`, `/test_orm` and `/test_new_api` pass with the guard in
  place); and failing at the composition point is far easier to read than
  `InFailedSqlTransaction` three frames later. The supported shape is
  unaffected and pinned: a savepoint *around* a pipeline recovers, because the
  block syncs before the `ROLLBACK TO` is issued. The question is asked with
  `getattr` rather than a `BaseCursor` attribute, because `odoo.tests.cursor.
  TestCursor` forwards by `__getattr__`, which runs only for names the class
  does not have.
- **`Cursor.__init__` is a borrow with no owner until its last line**:
  `__del__` short-circuits on `_closed`, which is True for the whole of the
  constructor, so a failure between `pool.borrow` and `_closed = False` is the
  one case no `close()` can reach. Its guard caught `Exception`, which misses
  the interrupt and a worker watchdog's `SystemExit` — measured with a
  `KeyboardInterrupt` injected at `_cnx.cursor()`, the permit and the checkout
  were still held afterwards (`budget_in_use=1, checked_out=1`) with nothing
  left to release them, and `maxconn` of those leave every later borrow timing
  out on "connection budget reached". It catches `BaseException` now, and asks
  `_is_connection_clean` before pooling the connection for the same reason
  `_close` does: a constructor that raised after a statement leaves a failed
  transaction behind.
- **A dropped cursor gives its connection back whatever state the connection is
  in.** `__del__` used to return early when `_cnx.closed` — inherited from
  upstream, where a psycopg2 pool counted connection *objects* and a dead one
  simply fell out of the count. Here the permit and the checkout are released
  in `give_back` and nowhere else, so the early return leaked both: measured,
  a cursor whose backend was `pg_terminate_backend`ed and that was then
  dropped without `close()` left `budget_in_use=1, checked_out=1` after
  `gc.collect()`, and `maxconn` of those leave every later borrow timing out on
  "connection budget reached". It now warns in both cases — the cursor was not
  closed, and that is the bug whichever came first — and on a dead connection
  skips the rollback (nothing to roll back to) but still hands the connection
  to `give_back(keep_in_pool=False)`. Pinned against a fake pool in
  `tests/test_invariants.py` and live in
  `TestCursorDelReclaimsConnection.test_del_reclaims_the_permit_of_a_dead_connection_too`.
- **One fact per attribute.** `in_pipeline` is `_pipeline is not None`; the
  `_pipeline_entered` flag that shadowed it was set and reset in the same two
  places and existed only to be kept in step. `_backend_pid` is a property
  over `conn.info.backend_pid` (a libpq call, 115 ns) read by debug lines only,
  instead of a per-cursor fetch that every cursor paid for. `EndpointRegistry`
  hands `ConnectionPool` its `settings` and nothing the constructor already
  reads from them.
- **A connection lost before the transaction's first statement completed is
  replayed on a fresh borrow.** Nothing has happened server-side, so the
  statement is the same request it was: `_replace_lost_connection` gives the
  dead connection back (`keep_in_pool=False`), borrows another from the same
  pool, rebuilds the psycopg cursor and re-issues the statement — `execute`
  and `executemany` both. It is refused once a statement has run
  (`_transaction_touched`, set by `_statement_done` and cleared with the
  transaction caches), inside a savepoint, or once psycopg's pipeline has
  been entered — the block's *second* statement; its first is an ordinary
  statement on an idle connection, and the ORM's flush opens such a block, so
  it is replayed like any other first statement (measured: the block's first
  statement on a killed backend replayed, its third with the pipeline entered
  propagated). Those transactions have state only the caller can rebuild,
  and the loss propagates as before. Eligible losses are `OperationalError`s that left the
  connection closed or never reached the server (a terminated backend, a
  dead idle connection handed out inside `db_healthcheck_grace`, a broken
  socket). Measured: a backend killed before the first statement → replayed
  on a new pid; killed after one → `AdminShutdown` propagates; killed inside
  a savepoint → propagates; permits and checkouts balanced through all of it.
  This closes the grace window's one failure mode for the common case — a
  request's first statement — and leaves `retrying`'s contract untouched.
  The dead connection goes back **before** the replacement is borrowed: its
  permit is the one the replacement needs when the budget is spent, and
  `maxconn=1` is the limit case (measured: replayed in 0.01 s there). A
  replacement that still cannot be had ends the cursor — its connection is
  gone and nothing is left to give back — and the loss propagates, not a
  `PoolError` dressed as a statement error.
- **A running statement can be cancelled from another thread, and a
  transaction's statements bounded**: `db.cancel_queries_of(thread_name)`
  walks every pool's `CheckoutTracker` for that thread's checkouts and calls
  psycopg's `cancel_safe()` on each — libpq's `PQcancel` from the client
  side: no borrow (a saturated pool is when this is needed), no
  `pg_signal_backend` privilege, and it reaches a replica connection. A
  cancel reaches whoever runs on the backend *now*, and the previous cancel
  in the walk may have waited `_CANCEL_TIMEOUT` (2 s), long enough for a
  connection to be returned and borrowed by another request: each cancel
  re-checks the tracker's owner first and skips a rehomed connection
  (`pool.cancel_skipped reason=rehomed`); the window left is the cancel
  call itself.
  `Cursor.set_statement_timeout(seconds)` remembers the budget on the cursor
  and arms it as `SET LOCAL statement_timeout` (through the inliner) before
  the next statement of every transaction: `SET LOCAL` dies at each commit
  and rollback and is reverted by the rollback of a savepoint it was issued
  in, so an eager one would have covered a request only until its first
  `cr.commit()`. Arming does not count as touching the transaction and the
  lost-connection replay re-arms on the replacement, so a budgeted request
  keeps the replay window (an eager `SET LOCAL` was the transaction's first
  statement and spent it). `set_statement_timeout(None)` lifts an armed
  budget at once (`SET LOCAL statement_timeout = 0`) and is silent when none
  is armed; `TestCursor.close()` lifts it because the real cursor outlives
  every test cursor. Both are primitives: the serving tier decides which
  requests get which budget and cancels on client disconnect. Measured: a
  10 s `pg_sleep` cancelled in 0.30 s with the cursor usable after
  `rollback()`; a 0.2 s budget cancelled at 0.20 s in the first
  transaction, after `rollback()`, after `commit()`, after a savepoint
  rollback with the budget armed inside it, and on the replacement
  connection after the backend was terminated before the first statement
  (`SHOW statement_timeout` = `200ms` in each), and `0` after clearing.
- **What the replica log lines say, `/web/metrics` says too.**
  `ReplicaRouter.get_health()` existed and nothing read it: a breaker that
  had opened, a lag gate that had demoted, were WARNING lines and nothing
  else. Routers live in ORM registries, which this package does not read,
  so every router built with a replica joins a module-level `WeakSet` and
  `db.get_replica_health()` reports each under its primary's database name;
  `odoo/service/metrics.py` renders them as
  `odoo_replica_{breaker_closed,breaker_failures,breaker_trips,breaker_cooldown_remaining_seconds,lag_seconds,lagging,write_pins}{database=…}`.
  Measured: a server started with `--db_replica_port 1`, one page served,
  `odoo_replica_breaker_closed{database="odoo64_db"} 0`, `failures 2`,
  `trips 1`, `cooldown_remaining_seconds 1.991`. A collected router leaves
  the table (weak reference; pinned by a test).
- **A session reads its own writes, on the primary, for `db_replica_write_pin`
  seconds.** A replica that has not applied a client's own commit would show
  that client its write as missing. `ReplicaRouter.cursor(pin_key=…)` routes
  a read-only request for a pinned key to the primary (`ro->rw`,
  `reason=pinned`), and every primary cursor handed out with a key — the
  read-write route, the pinned read, and the breaker-open or lagging
  fallback — registers `Cursor.on_commit_if_written` (`_primary_cursor`), so
  a session that writes through a reused cursor refreshes its pin — at
  commit, one
  `SELECT txid_current_if_assigned() IS NOT NULL` (an xid is assigned on the
  first write and never otherwise) says whether the transaction wrote, so a
  request that only read pins nothing and keeps the replica. The round trip
  is paid only when an observer is registered and something ran. `WritePins`
  prunes past 1024 entries. `Registry.cursor(pin_key=…)` passes the key
  through; the http layer supplies the session id. Measured against the
  observer: a read-only transaction and an empty one fired nothing, a write
  fired once.
- **A transaction left idle is ended by the server, not only reported.**
  `db_idle_in_transaction_timeout` (0 = off) becomes
  `idle_in_transaction_session_timeout` in the connection's startup options
  beside `idle_session_timeout`; a cursor forgotten inside a transaction
  holds locks, a permit and a backend until then, and the leak detector only
  says so. Measured at 0.3 s: `SHOW` answered `300ms` on the connection and
  the next statement after 0.6 s idle raised
  `IdleInTransactionSessionTimeout`.
- **A statement that failed still cost a round trip**: `_record_metrics` ran
  after the `try/except`, so every server-side failure counted as zero queries —
  in `sql_log_count`, in the process-wide `sql_counter`, and therefore in
  `assertQueryCount`, which reads the first. Any test wrapping a constraint
  violation in `assertRaises` under-reported its cost. Client-side rejections
  must stay uncounted, because psycopg raises before anything reaches the wire,
  and `has_reached_server` is the discriminator that separates them: the server
  supplies a SQLSTATE, psycopg's own errors do not. Blast radius was measured
  before landing it — `/base` gained no query-count failure, and the mail suite,
  which carries this fork's query-count debt, still reads 17 failed.
- **`SET` takes client-side params; `TRUNCATE` and `LOCK` deliberately do
  not.** PostgreSQL rejects `$N` in a `SET` value as in every DDL position, so
  `cr.execute("SET LOCAL statement_timeout = %s", (ms,))` reached the server
  only to come back `syntax error at or near "$1"`. What separates it from the
  other unclaimed statement kinds is the *shape of the slot*: a `SET` value is
  a value, and inlining rescues it (`SET statement_timeout = '5s'` runs),
  where `TRUNCATE TABLE %s` and `LOCK TABLE %s` want an **identifier** that
  the inliner quotes into a literal — `TRUNCATE TABLE 'vp_t'` is a syntax
  error just as `$1` was. All verified against PG 18; claiming those two would
  buy nothing.

  **`SET` is answered without a regex, and that is why it is answered at all.**
  Putting it in `_DDL_KEYWORDS` shares `SE` with `SELECT`, so every SELECT in
  the tree enters `_RE_DDL`: 152.5 ns → 370.7 ns, and a dedicated `SE`-only
  regex still costs 301 ns because the leading-comment group has to be tried.
  `SELECT` and `SET` part at the *third character* and nothing else in SQL
  begins `SE` in statement position, so one slice settles it — and reading the
  head inside `classify_statement` instead of through a helper pays for that
  slice and more: **SELECT +5.4 ns, UPDATE −11.5, INSERT −15.9, CREATE −12.4,
  `ROLLBACK TO` −19.5**. A comment can never lead a `SET` seen by that branch,
  because `--` and `/*` are in `_DDL_PREFIXES` and have already been matched
  against the real keyword list.
- **A gauge that is rendered as a pair is written as a pair.**
  `ReplicaLagGate.record` set `last_lag` and `_lagging` from one measurement
  with no lock, and `get_snapshot` renders them side by side, so an operator could
  read a 99 s lag beside `lagging: false`. That is not theoretical on the GIL —
  the two stores are separated by a `max()` and a comparison, and one writer
  against one reader produced exactly that pair within 2 s. `record` and
  `get_snapshot` take the lock; `is_replica_usable()` stays lock-free because it
  reads one flag and runs per read-only cursor.

  The leak-report throttle (`CheckoutTracker.acquire_report_interval`) is guarded on
  policy rather than on evidence, and says so: 16 threads released from a
  barrier onto the unguarded body still produced exactly one winner, because
  its compare and store are adjacent bytecodes. `track`/`release` stay
  lock-free — single dict operations.
- **`sql_counter` is the one counter without a lock, and that is measured
  rather than overlooked.** 12 threads × 80 000 increments at
  `setswitchinterval(1e-9)` lost 0, and the harness is not blind — the same
  run against a deliberately non-atomic `read; call; write` lost 774 303 of
  960 000. The lock would cost **68.6 ns per statement against 157.1 ns for
  all of `_record_metrics`**, +44% on the hottest path in the framework, for a
  race that cannot fire here. A free-threaded build is what makes it wrong;
  the note beside the counter says so, and says the fix there need not be a
  lock.
- **A probe that connected has answered its question.** `probe_connectable`
  spelled it `psycopg.connect(...).close()`, which put the teardown inside the
  `try` that classifies the outcome — so a DSN that opened a connection, which
  is the entire thing being asked, was filed as a *transient* probe failure
  whenever the close raised, and the pool then paid the full borrow budget
  behind it. Only the connect is guarded now; the close is in the `else`.
  `check_connectable` also took the lock twice (`is_proven`, then the
  in-flight registration), leaving a window where a key proven between them
  started a second probe — a full extra connect on the path whose whole
  purpose is to avoid one. One acquisition answers both.
- **`acquire_attempt()` must not read through `closed`.** `CircuitBreaker._lock`
  is a plain `threading.Lock`, and `acquire_attempt` read `closed` from inside
  it, so a `closed` property that took the lock would deadlock every caller —
  demonstrated, it hung past a 2 s join. The lock-held path reads
  `_open` directly; the property exists for callers outside the lock. The
  cooldown expression that `cooldown_remaining` and `get_snapshot` had a copy of
  each is now `_get_cooldown_remaining_locked`, which does not take the lock
  because both of its callers already hold it.
- **A bug is not an unavailable database.** `_get_connection_with_retry` ended in
  `except Exception: raise PoolError(str(e)) from e`, and `PoolError` is the
  one exception `ir_cron`, `ir_job`, `orm/runtime/registry.py` and
  `bus/websocket.py` all catch and treat as "carry on, the database is down" —
  so an `AttributeError` from anywhere under `getconn` arrived as a `PoolError`
  with its type and traceback gone, and was swallowed by four call sites.
  Nothing operational needed the clause: everything psycopg_pool raises from
  `getconn` for a real reason is a `psycopg.Error` answered by the branches
  above it. `PoolTimeout` and `PoolClosed` both subclass `OperationalError`;
  **"the pool is not open yet" is a `PoolClosed`, not the `RuntimeError` it
  reads like** — that misreading is why an earlier pass left this alone; a
  failed connect arrives through `WaitingClient.wait` as the error the worker
  recorded; and a `check` callback that raises is swallowed by psycopg_pool's
  own retry loop until it gives up with `PoolTimeout`. Measured with a bug
  injected at `getconn`: `PoolError`, caught by `except PoolError` → the
  `AttributeError` itself, uncaught, with the permit still released either way.

- **The saturation error reads one consistent pair.** `_prepare_budget_exhausted_error`
  printed `len(self._pools)` and `self._direct_out` in one sentence, read
  half a microsecond apart with no lock between them, so the two halves of the
  message an operator gets when the pool is exhausted could add up to more
  than `maxconn` and send them looking for a leak that was an artefact of the
  message.
- **The counters own their lock**: `PoolStats` exposes one `record_*` method per
  counter and holds `_lock` for the whole update, and `pool.py` contains no raw
  `self.stats.x += 1` at all. `x += 1` on an attribute is a non-atomic
  read-modify-write, so the counters that exist to diagnose concurrency were the
  ones losing increments, and the borrow-wait histogram could drift out of step
  with the total it summarises because they were separate writes. `get_snapshot()`
  reads them all under the same lock for the same reason. The pin that used to
  record this counted how many raw sites happened to sit inside the *pool's*
  lock — which guards `_pools`, not the counters, so any protection was
  accidental — and it counted them wrongly besides.
- **`ConnectionBudget` is a `Condition`, not a `BoundedSemaphore`**: `available`,
  `in_use` and `exhausted` are exact and are read under the lock that hands the
  permits out — and the health view reads the three through one
  `get_snapshot()`, one acquisition, so `budget_available + budget_in_use`
  always equals `budget_maxconn` on the page an operator reads; three property
  reads half a microsecond apart did not promise that (the lag gauge's rule,
  applied here). The semaphore version derived them from
  `threading.BoundedSemaphore._value`, a private CPython attribute read without
  the semaphore's own lock, on the path that renders `db.get_pool_health()`. A
  `BoundedSemaphore` is itself a `Condition` plus a counter, so this costs the
  lock acquisition it always cost.
- **Connect-error classification is locale-dependent, and that is bounded not
  ignored**: libpq reports connect failures with **no SQLSTATE** (psycopg's
  `sqlstate` and `diag` are both `None`), so message text is the only signal and
  PostgreSQL translates it. What can be made locale-proof is:
  `_LOCALE_INDEPENDENT_AUTH_MARKERS` keys on `pg_hba.conf`, a filename no
  catalogue translates, and it classifies correctly in English, Spanish, French
  and German. The missing-database case does not depend on text at all — the
  probe falls back to `is_database_absent`, which asks `pg_database`. What remains
  is an **authentication** failure on a server with translations installed: it
  used to be unrecognised and cost the full `db_borrow_timeout` (measured,
  0.02 s against 30.00 s), and `options='-c lc_messages=C'` cannot help
  because authentication happens *before* the server processes `options`.
  **libpq's own account of where the connect died does not go through a
  catalogue**: the failed `PGconn` rides on psycopg's `OperationalError`
  (`e.pgconn`), and `needs_password` / `used_password` say whether the server
  reached the password stage. `needs_password` alone is conclusive. A refused
  port or a dead host never gets there; a *missing database* is refused
  **after** the password, which is why `ask_maintenance_db` is consulted first
  — `absent` wins, and only a maintenance connect that is itself turned away
  at the password stage (`auth_failed`) makes `used_password` an
  authentication failure. Measured with every English marker disabled: a
  wrong password over scram is `InvalidAuthorizationSpecification` in
  **0.03 s**, a missing database still `InvalidCatalogName`, a refused port
  still transient.
- **One mechanism invalidates the catalog cache on a savepoint rollback**: the
  `ROLLBACK TO` detection in `Cursor.execute`. `Savepoint.rollback` used to call
  the hook itself as well; counted per host flavour that call was never the one
  doing the work — on a `Cursor` it double-fired behind the scan, on a raw
  psycopg cursor the attribute does not exist, and on a `TestCursor` it resolved
  to `BaseCursor`'s no-op while `TestCursor._close_savepoint` called the real
  hook by hand. The scan cannot be dropped instead: addons issue raw
  `ROLLBACK TO SAVEPOINT` (`tests/contract/test_raw_savepoint_hook.py` pins it),
  so it is the only mechanism that covers every caller.
- **Password hygiene**: every DSN consumer routes through
  `dsn._expand_conninfo`; pool keys carry only a BLAKE2s fingerprint, and
  `Connection.dsn` strips the secret before logging.
- **A pool key spells the database as libpq does, `dbname`.** The key used to
  rename it `database` — a psycopg2-era alias with no reader that wanted it —
  and every consumer then rebuilt a `dict` from the frozenset to read one
  field. `_get_key_dbname` walks the key once and is the only reader; nothing
  else takes a key apart.

## Re-deriving the figures

Every number above came from a measurement, and `tooling/` — which used to
rerun them — is gone. `odoo/db/tests/bench.py` re-derives the ones that
matter, on this machine, against a database with `base` installed:

```bash
PYTHONPATH=odoo p314o19m/bin/python -m odoo.db.tests.bench -c p314o19m.conf -d <db>
```

Wire-stubbed rows (`execute()`, `fetchone()`, `classify_statement`) measure
Python only and are the ones to compare across a change to the statement
path; the round-trip rows move with the host's load, so compare them within
one run (reset string against `DISCARD ALL`, prepared against unprepared).
The storm rows print backends held beside cycles per second, which is the
inline-reset property in one line. Run it before believing a figure and
after touching the path it describes; a figure here that the bench no longer
reproduces is stale, not wrong by definition — say which in the entry.

## Tracing (campaign instrumentation, temporary)

Every module carries `_debug = DebugLog(__name__)` (`odoo/libs/debug_log.py`) and logs
on four channels named `odoo.debug.<channel>.db.<module>` — `logic` (which branch, on what
input), `perf` (spans with `ms=` and `queries=`, and counters), `pipeline` (hand-offs),
`lifecycle` (opened / committed / closed / reaped). Off by default; nothing prints at
`log_level = info`. Enable the whole package on every channel with four handlers,
`--log-handler odoo.debug.<channel>.db:DEBUG`, one channel with
`odoo.debug.perf.db:DEBUG`, one module with `odoo.debug.perf.db.schema:DEBUG`.

The lines to start from: `cursor.statement` (one per statement — `head= kind= table= ms=
rows= ok= in_pipeline=`), `cursor.fetch` (rows returned), `pool.borrow` / `pool.give_back`
(wait and hold time, backend pid, thread), every `schema.*` verb (a span with `queries=`)
and catalog probe (its answer), `cursor.pipeline` (statements queued, whether pipeline mode
was entered, sync cost). Correlate on `db=`, `table=`, `name=sp<n>`, `backend_pid=`.
`odoo/db/tests` runs green with everything on (`pytest odoo/db/tests --log-level=DEBUG`),
so a full trace is readable without a database. The sites are removed together when the
campaign ends; the recipe, the cost figures and the first findings are in
`agromarin-knowledge/reference/dev/debug-logging-campaign.md` under "Core packages / db".

## Tests

- **Invariants are enforced, not just described** — `odoo/db/tests/test_invariants.py`
  turns the rules on this page into structural checks: only the two borrow paths
  touch the budget, `borrow` diverts maintenance databases, both borrow paths
  track their checkout and `give_back` releases it before any early exit, the
  leak warning uses its own throttle rather than the reaper's, both borrow paths
  raise the one saturation error and that error names its holders, a password
  never reaches a pool key, `conninfo_to_dict` has one caller, `get_libpq_connect_timeout`
  never returns a value libpq would read as "wait forever", the budget is keyed
  on the resolved endpoint rather than the presence of `db_replica_host`, the
  two schema-cache clears keep their distinct call sites, `_has_schema_changing_statement`
  cannot miss a hidden statement, the `SE` branch that claims `SET` runs no
  regex and `SET` stays out of `_DDL_KEYWORDS`, the lag gauge's pair is
  written and rendered under one lock while `is_replica_usable()` stays lock-free, the
  leak throttle owns a lock that `track`/`release` do not take, the
  saturation error reads its two counters under one acquisition, the probe
  asks proof-and-in-flight in one acquisition and classifies only the
  connect, a bug under `getconn` keeps its type instead of arriving as the
  `PoolError` four call sites swallow, `acquire_attempt()` never reads through the `closed` property and the
  cooldown expression exists once, no method or property reached from inside a
  `with self._lock:` block takes that lock itself (checked across
  `ConnectionPool`, `ReachabilityProbe`, `CircuitBreaker` and `ReplicaLagGate`,
  with a control asserting the check can see both shapes -- the call and the
  bare property read that the first version of it missed), both entry points read a statement's text
  through the one `_get_statement_text` (`executemany` spelled it `str(query)`,
  which turns a `bytes` DDL statement into the repr `b'CREATE …'` and hides it
  from `classify_statement`), the pipeline exit routes a deferred error through
  the seam and the seam short-circuits on its own mark, `savepoint` refuses
  pipeline mode and asks through `getattr` so a test cursor forwards, the
  cursor's construction guard catches `BaseException` and returns the
  connection on the same terms as `_close`, a schema change arms a flag rather
  than draining inline and only `commit` consumes it, both borrow paths render their
  libpq options through the one `_prepare_connection_options` with only the maintenance
  path opting out, nothing follows the guard that releases a permit, the cursor
  names a stale cached plan rather than re-listing the family, the failure seam
  takes that mark and every entry point routes through both halves, a URI that
  omits its host defaults to the configured one and does it from the config
  rather than the environment, and `pool.py` contains no raw counter mutation
  at all. Added 2026-09-15: a dropped cursor gives its connection back
  whatever the connection's state, the construction guard asks the pool
  nothing before it releases, the transaction flags are set once and re-set
  only when a cursor changed them, the reset and the liveness probe go
  through libpq with a fake that returns the `int` libpq returns, the psycopg
  pool is built with `reset=None` and `give_back` reaches the reset, a reset
  that raises discards, `execute_values` carries no seam of its own and packs
  pages to the bind ceiling, the replica borrow carries its short deadline and
  `fail_fast`, a fail-fast borrow ends on a transient probe answer and
  re-probes a surviving unproven empty pool, `get_tables_existing`'s relkinds
  derive from `TableKind`, and the two layer contracts (`imports-only-libs`,
  `resilience-below-connectivity`) are scanned with a control each. Added
  2026-09-16: the statement budget is armed before the first statement and
  not when set, survives commit and rollback on the same cursor, does not
  spend the replay window and is re-armed on the replacement, is re-armed
  after a savepoint rollback that reverted it and kept across one that did
  not, is lifted at once when armed or set in a touched transaction and
  silently otherwise (`test_invariants`, plus the `TestCursor` boundary in
  `base/tests/test_db_cursor.py`); a cancel walk skips a connection rehomed
  to another thread (`test_pool`); scalar rows count against the bind
  ceiling (`test_bulk`); `replica.pinned` never carries the key, a router
  with a replica reports under its database and leaves the table when
  collected, and the router's lag ceiling and pin window follow the settings
  slot unless given (`test_replica`); the backend ceiling trims the least
  recently borrowed pool first and FIFO within it, counts checked-out
  connections without trimming them and never goes below `min_size`
  (`test_reaper`), with the four psycopg_pool attributes it reads pinned
  against the installed release in `tests/contract/test_psycopg_pool_internals.py`.
  Each was verified to fail when its invariant is violated.
  Add the check here when you add an invariant above. One class per invariant:
  a behavioural check against a fake and the structural one (`co_names`, AST)
  sit together, with the AST helpers in `tests/_source.py`; `test_source_pins.py`
  keeps the pins that have no behavioural twin (the lock-discipline scanner, the
  seam's shape, the schema-cache call sites).

- **Every DDL verb in `schema.py` is pinned to the statement it emits** —
  `tests/test_schema_ddl.py` runs each one against a recording cursor that
  renders the `SQL` it receives and answers scripted rows, so a quoting,
  escaping or catalog-query change shows up as a diff of the statement, not as
  a red module install somewhere. A DDL function without a pin there is the
  omission to fix when touching it.
- **Tier 2 real-import, no DB (ms)** — `odoo/db/tests/`, run from `odoo/` as
  `pytest odoo/db/tests` (it is in no `testpaths` and shares the Tier-2
  invocation of `pytest.ini`, because a handful of its tests reach state in the
  package `__init__.py` that the Tier-1 stubs replace; measured 2026-09-16,
  708 passed + 206 subtests named alone). One class, `TestPipelineAccountsForTheSyncCost`,
  needs a local `createdb` and skips without it:
  pure modules (`ddl`, `dsn`, `errors`, `schema_cache` bookkeeping, `savepoint`
  depth accounting, `bulk`'s argument validation and encoding cost model,
  `utils`' DSN/maintenance-db resolution, `budget`/`stats` accounting, `reaper`
  policy and throttle, `leaks` checkout bookkeeping, `lag` ceiling and its
  sampling, `replica` routing — which connection a
  cursor request lands on and the mode it reports, against two fake
  connections — one budget per resolved endpoint in `test_endpoints`)
  plus the two that only need stand-ins — `pool` (budget clamps and sharing,
  idle-pool reaping, permit accounting, reachability proof, close/drain
  matching, against a fake `psycopg_pool.ConnectionPool`) and `lifecycle`
  (what the session reset closes and spares, the health-check grace window,
  against a recording fake connection). Uses `sys.modules` stubs
  (`conftest.py`) so leaf modules import without executing
  `odoo/db/__init__.py`. What needs a real backend — lock-before-read and
  transaction scoping of the catalog facts, which types binary COPY can encode,
  borrow behaviour against an unreachable host — lives in the integration
  suite.
- **Tier 2 (real `import odoo`, no DB)** —
  `odoo/orm/tests/test_replica_breaker.py`: that `Registry.cursor` hands the
  decision to its `ReplicaRouter` and records the mode it came back with on
  the worker thread, and nothing more — the breaker and the lag gate are
  exercised through the router in `odoo/db/tests/test_replica.py`.
- **A concurrency test must not take its cursors from `registry().cursor()`.**
  Under `--test-enable` that returns an `odoo.tests.cursor.TestCursor`, and
  every `TestCursor` for a database serialises on one lock
  (`_lock.acquire(timeout=test_cursor_lock_timeout)`), so threads written to
  race each other queue instead — the test passes or fails for reasons that
  have nothing to do with what it means to measure. Take them from
  `db_connect(common.get_db_name()).cursor()`, as
  `TestConcurrentDdlDuringBinaryCopy` and
  `TestInsertOrExistingUnderARealRace` do. Found the hard way: a race written
  against `registry().cursor()` failed under `odoo-bin` while the same logic
  passed as a standalone script.

- **A real standby, built and torn down by the test** —
  `tests/contract/test_replica_standby.py` runs `pg_basebackup -R` against
  the reachable primary into a temp directory, starts it on a scratch port
  with its own socket directory, and exercises the router against it:
  read-only routing lands on the standby, a write there raises
  `ReadOnlySqlTransaction`, apply lag past the ceiling demotes and catching
  up restores (replay paused with `pg_wal_replay_pause()` — and waited for,
  `pg_get_wal_replay_pause_state() = 'paused'`, because the pause is only
  *requested* and a commit sent before recovery honours it is replayed
  anyway), a session that wrote reads from the primary for the pin window
  and one that only read keeps the standby. Skips without `pg_basebackup`.
  ~4 s; run with `ODOO_CONTRACT_REQUIRE_DEPS=1 pytest tests/contract`.
- **Integration (live DB)** —
  `odoo/addons/base/tests/test_db_cursor.py` (run with
  `--test-file … --stop-after-init` on a DB with `base` installed): cursor
  semantics, pool lifecycle/races, COPY, session reset, registry-drain wiring.

Put new tests in the lowest tier that can express them
(`doc/coding_guidelines.rst` §6).
