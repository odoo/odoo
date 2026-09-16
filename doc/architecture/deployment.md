# Deployment view — what runs where, and how it degrades

> One of the views indexed by [`ARCHITECTURE.md`](ARCHITECTURE.md).
> The runtime view describes what happens *inside* one process. This one
> describes **how many processes there are, what each is allowed to do, and what
> happens when one stops being healthy.**

The framework ships three deployment shapes, chosen at startup by two config
values. They differ in ways that reach the architecture rather than the ops
runbook — most of all in whether memory is shared.

## Choosing the shape

`service/_factory.py::start` picks the server, in this order:

| Condition | Server | Concurrency | Shared memory |
|---|---|---|---|
| `odoo.evented` | `WebsocketServer` | Python threads on the websocket port (`gevent_port`); no gevent anywhere in the fork | one process |
| `workers > 0` | `PreforkServer` | forked OS processes | **none** |
| otherwise (default) | `ThreadedServer` | Python threads | one process |

The default is `workers = 0` — threaded, one process, debugger-friendly, and the
shape every measurement in [`qualities.md`](qualities.md) was taken under. The
threaded path additionally calls `_limit_malloc_arenas()`, which the forked path
does not need.

**The choice between threaded and prefork is architectural, not operational.**
Under `workers > 0` there is no shared memory, so every registry and every cache
exists once *per worker*, and a change made in one is invisible to the others
until it travels through PostgreSQL — see the signalling tables in
[`data.md`](data.md#2-the-signalling-tables--cross-process-coordination). Code
that is correct threaded and wrong prefork is code that assumed one process.

## The prefork worker mix

`PreforkServer` maintains three worker populations, not one:

| Worker | How many | Serves |
|---|---|---|
| `WorkerHTTP` | `workers` (the `population`) | HTTP requests |
| `WorkerCron` | `max_cron_threads` (default **2**) | scheduled jobs |
| `WorkerJob` | its own pool | queued jobs |

`--workers 4` does **not** mean four processes: four HTTP workers *plus* the
cron and job populations, each sized independently. The three populations are
sized separately and **timed separately too**: the table below carries a
per-job wall-time knob and two worker-lifetime knobs beside the cron ones, each
defaulting to *defer to the tier above it* rather than to a number, so a
deployment that tunes only `limit_time_real` has silently tuned all three. The
listen backlog is `8 * population`, and `SIGTTIN` / `SIGTTOU` move the
population up and down at runtime.

Cron workers hold registries and database connections exactly like an HTTP
worker, so they count against `db_maxconn` and against the per-registry memory
measured in [`qualities.md`](qualities.md#scenario-3--multi-tenancy-cost).

### Reload and worker retirement

Prefork reload keeps the original master as a stable supervisor. A replacement
inherits the listening socket, preloads its registries, and waits for its workers
to report startup completion before acknowledging readiness over an owned pipe.
An ordinary watchdog heartbeat during a listener reconnect is not that signal.
Failed preload or a readiness timeout discards the replacement and keeps the
current generation supervised and serving. Successful promotion drains the old
workers; later reload requests return to the original supervisor, avoiding a
growing chain of proxy masters. The stable supervisor owns the file watcher so
an edit does not schedule duplicate reloads. The replacement rereads configuration normally.

The websocket port is the master's too: it binds `gevent_port` once at start
and hands the listener to every evented child it spawns (as that child's own
HTTP listener, `ODOO_HTTP_SOCKET_FD`) and to its reload candidate
(`ODOO_WEBSOCKET_SOCKET_FD`). An evented child recycled over
`limit_memory_soft_gevent`, a crashed one, or a replacement generation's
child therefore never re-binds the port and never refuses a connection
(measured across a reload: 39 refused before, 0 after). What restarts with
the generation is the process; established WebSocket connections are not
preserved. Shutdown bounds generation draining and kills
remaining descendants in its owned process group after the generation exits.
`tests/process/test_reload_continuity.py` covers served requests during successful
reload and preservation of the current generation after rejected replacements.

SIGTTOU initiates graceful retirement of excess HTTP workers. Retiring workers
remain in the watchdog and reaping registries until exit, and are not signaled
repeatedly on subsequent supervision passes. A failed initial preload also
returns a failing exit status in serving mode, for both threaded and prefork
servers, before starting cron and job workers.

### Stopping a threaded server

A first SIGINT/SIGTERM (or a SIGHUP, which re-execs afterwards) runs
`ThreadedServer.stop()` in this order: the listener threads are told to stop
(an event plus a wakeup pipe every `CronListener` watches), the HTTP server
stops accepting and closes idle connections (`shutdown()`), then **waits for
the busy request threads** (`ThreadedHTTPServer.drain()`, bounded by
`ODOO_GRACEFUL_STOP_TIMEOUT`, 60 s; a request already over `limit_time_real`
is not waited for), closes the listening socket, runs the stop hooks, joins
the listener threads for whatever is left of that same bound (at least 1 s)
so each finishes its job and closes its own PostgreSQL session, and closes
the pools. A second signal forces an immediate exit. The evented
process drains the same way. Before 2026-09-15 the socket closed under every
in-flight request and the listener sessions were left to the kernel.

On a SIGHUP the listening socket is not closed at all: after the drain,
`ThreadedHTTPServer.bequeath_listener()` marks it inheritable and names its
descriptor in `ODOO_HTTP_SOCKET_FD` — the same handoff the prefork master
gives its reload candidate — so the `execve` that follows keeps the port bound
through the interpreter restart and the next `ThreadedHTTPServer` adopts it.
Connections that arrive meanwhile wait in the kernel backlog; none is refused
(`tests/process/test_reload_continuity.py`, 41 refused before, 0 after). A
socket-activated listener already survives as `LISTEN_FDS`.

## The limits that end a request or a worker

Defaults, from `odoo/tools/config.py`:

| Knob | Default | Bounds |
|---|---|---|
| `workers` | `0` | HTTP worker processes; `0` selects threaded |
| `max_cron_threads` | `2` | cron workers |
| `limit_request` | `65536` | requests a worker serves before it is recycled |
| `limit_memory_soft` | `2048 MB` | RSS above this stops the worker *after* the current request; the only memory limit the process enforces |
| `limit_memory_soft_gevent` | `None` | overrides `limit_memory_soft` on the `WebsocketServer` path only |
| `limit_memory_hard` | `2560 MB` | **deprecated, enforced by nothing in-process** — see below |
| `limit_memory_hard_gevent` | `None` | the `WebsocketServer` twin of the row above, and enforced by nothing for the same reason |
| `limit_time_cpu` | `60 s` | CPU time per request |
| `limit_time_real` | `120 s` | wall time per request |
| `limit_time_real_cron` | `-1` | wall time per cron job; `-1` defers to `limit_time_real` |
| `limit_time_real_job` | `-1` | wall time per background job; `-1` defers to `limit_time_real_cron`, which defers in turn |
| `limit_time_worker_cron` | `0` | how long a cron thread or worker lives before it is restarted; `0` disables |
| `limit_time_worker_job` | `-1` | the same for a job worker; `-1` defers to `limit_time_worker_cron` |
| `db_maxconn` | `64` | connections held, checked out and idle, **per PostgreSQL server** |

**There is one memory limit, not one of four.** `limit_memory_soft` is enforced at
three sites — `_worker.py`'s `check_limits`, and `_threaded.py` for the HTTP and
evented paths — each calling `get_memory_over_soft_limit()` (`_limits.py`) on the
process's RSS and, above it, clearing `alive` so the worker stops after the
current request. A fourth site reads the value for an unrelated purpose:
`lifecycle.py::_limit_resident_registries` divides it by the average registry
size to bound how many registries are held at once.

`limit_memory_hard` is read **nowhere in `odoo/service/`**. There is no
in-process `RLIMIT_AS`: the allocator and the thread stacks reserve multi-GB of
never-resident virtual address space, which that rlimit counts and RSS does
not. `config.py`'s help says "Deprecated/not enforced in-process" and directs
the hard cap to a cgroup v2 limit on the systemd unit (`MemoryMax=` with
`MemorySwapMax=0`).

A deployment sized on the 512 MB between the two has **no** hard ceiling unless
the unit file supplies one: past the soft limit a worker finishes its request and
exits, and a single request that allocates without bound is bounded by the OOM
killer, not by Odoo. A number that reads as a guarantee because it has a default and a row in a
table.

A deployment whose steady-state RSS is near the soft limit recycles constantly
and pays a registry rebuild each time. `limit_request` exists because a
long-lived Python process accumulates; recycling is the design, not a workaround.

### Over the wall-clock budget: cancel first, then recycle

A request or job past `limit_time_real` is not killed on the spot. Both
flavours act in two steps, one budget apart:

1. **Cancel the queries.** The supervisor (the worker's own monitor thread in
   prefork, `_worker.py`; the server's `check_limits` pass in threaded,
   `_threaded.py`) calls `odoo.db.cancel_queries_of(<thread>)`, a client-side
   `pg_cancel` on every connection that thread has checked out, and logs
   `cancelled N running quer(y|ies)` together with what the thread was doing
   (`serving GET /path (model.method)` or `sweeping <db>`). A request stuck in
   PostgreSQL fails with `QueryCanceled`, answers `500`, and the process that
   served it survives: no registry rebuild, no back-off, no lost in-flight
   neighbours.
2. **Recycle only what did not return.** Work still on the *same* unit
   afterwards — a Python stall, a lock no query holds — is the case a cancel
   cannot reach. A prefork worker ends itself after `_CANCEL_GRACE_S` (5 s),
   logging `Work did not return … recycling worker`, and exits `0` so the
   master's respawn back-off never engages; the master's own `timeout after
   Ns while <title>` SIGKILL stays as the backstop for a worker whose monitor
   thread is itself wedged. The threaded server, which has no worker to
   drop, reloads the process, logging `still on the same work … reloading`.

Keep `limit_time_real` at or above `SUPERVISION_BEAT_S` (4 s): an idle prefork
worker pings the master once per beat, so a smaller budget times out idle
workers before they serve anything.

### Descriptor budget

`lifecycle.py::_ensure_descriptor_budget` computes what the configuration can
open at once — threaded: `db_maxconn` + HTTP threads + idle connections +
listeners; prefork: the larger of a worker (`db_maxconn` + 1) and the websocket
child (`db_maxconn_gevent` or `db_maxconn`, plus its threads) — adds
`DESCRIPTOR_HEADROOM` (128), and raises the soft `RLIMIT_NOFILE` to the hard
one when that demand exceeds it. When even the hard limit is short it warns
naming `LimitNOFILE=`, the unit-file key that lifts it; nothing lowers a
configured value.

### systemd integration

Every flavour speaks `sd_notify` (`_sdnotify.py`) when `NOTIFY_SOCKET` is
set, and does nothing otherwise:

| State | When |
|---|---|
| `READY=1` | the threaded server after its cron and job threads are spawned; the prefork master before its first supervision pass. The same moment logs one `Ready: <flavour>, pid …; <capacity>; <budgets>; limit_memory_soft …; db_maxconn …` line (`CommonServer.log_ready`) |
| `RELOADING=1` + `MONOTONIC_USEC=` | a threaded `--dev=reload` re-exec, and a prefork SIGHUP, with `READY=1` again once the new generation serves |
| `STOPPING=1` | the stop path of either flavour |
| `WATCHDOG=1` | every supervision beat, at half the `WATCHDOG_USEC` interval when `WATCHDOG_PID` names this process |

A unit that wants the whole contract:

```ini
[Service]
Type=notify-reload
NotifyAccess=main
WatchdogSec=30
LimitNOFILE=65536
ExecStart=/opt/odoo/venv/bin/python /opt/odoo/odoo-bin -c /etc/odoo/odoo.conf
```

A balancer or orchestrator that cannot read sd_notify reads `/web/readyz`
(`addons/web/controllers/health.py`): 200 once PostgreSQL answers, `data_dir`
is writable and no registry preload is in progress in the answering process
(`odoo.service.server.is_ready()`, fed by `_process_state.preloading` from
`preload_registries`); 503 with `checks.registries = "loading"` otherwise. A
request for a database still loading waits on the registry lock, which is what
the 503 keeps a balancer from sending. `/web/healthz` is liveness only.

Socket activation (`LISTEN_FDS`/`LISTEN_PID`, `settings.py`) takes the
unit's sockets in the order its `[Socket]` section lists them: the first is
the HTTP port; a second, when the unit declares one, is the websocket port
and the prefork master adopts it as its own (`websocket_socket_activation`).
A unit that names the pid of another process activates nothing.

The prefork master's beat is 4 s, so any `WatchdogSec` above ~10 s is
comfortable; a threaded server bounds its sleeps to the same half-interval.
A prefork master running under its own reload supervisor (`_reload_supervisor`)
sends nothing — the supervisor is the process systemd sees.

## Degradation — the `db/` resilience tier

| Module | Handles |
|---|---|
| `budget.py` | `ConnectionBudget` — the shared `db_maxconn` cap, its permit semaphore, its saturation counter |
| `lag.py` | `ReplicaLagGate` + `LAG_SQL` — a sampled apply-lag ceiling that **demotes stale reads to the primary** |
| `reaper.py` | `IdlePoolReaper` — which quiet per-DSN pools to close, and how often to look |
| `probe.py` | `ReachabilityProbe` — is this DSN connectable, and **permanently or not**: a pre-flight connect that turns a missing database or a rejected password into a millisecond error instead of a `PoolTimeout` at the end of the borrow budget, plus the per-key proof that stops it re-asking |
| `leaks.py` | `CheckoutTracker` — which connections are out, since when, from which thread and borrow site |
| `metrics.py` | `_MetricsMixin` — the per-cursor SQL counters (`sql_from_log`, `sql_into_log`, `sql_log_count`), so a slow request can name its statements rather than report a total |
| `stats.py` | `PoolStats` — the counters behind `ConnectionPool.get_health()`: borrows, failures, and a bucketed borrow-wait histogram, each written under one lock because `x += 1` lost increments in exactly the concurrency they exist to diagnose |

**Four of the seven act and three only observe**: `lag`, `budget`, `reaper`
and `probe` change what a request gets, while `leaks`, `metrics` and
`stats` only say what happened — and the observers are what a capacity
decision is made from. The tier is `db-resilience-below-connectivity`'s
source list ([`module.md`](module.md#dependency-rules)).

Three properties for any capacity decision:

**The budget is per PostgreSQL server, not per process or per database.**
`db_maxconn` caps a *server's* checked-out connections (`db/endpoints.py` keys
the budget by endpoint): a budget per database over-commits the server, and a
single budget across two independent servers under-uses both.

**Backends track concurrency, not the budget.** A pool's session reset runs
on the returning thread (`ConnectionPool.give_back`), so a returned
connection is idle the moment `putconn` files it. With the reset in
psycopg_pool's worker instead, the next `getconn` found nothing idle and
grew the pool by every return in flight: measured against a running server,
16 request threads held **64** backends — the `db_maxconn` ceiling — and hold
**16** now (`db/README.md`, the entry on `reset=None`). Idle connections
count against the same ceiling: every return trims the oldest idle
connections of the least recently borrowed per-database pools until a
`ConnectionPool` holds no more than `db_maxconn` in total
(`db/reaper.py::trim_idle_to_ceiling`; four databases under `db_maxconn = 2`
hold two backends, not four). Size `max_connections` against
`db_maxconn` × workers × (one, or two once the read-only pool is a separate
`ConnectionPool`), and read `odoo_pool_connections_trimmed_total`: a working
set wider than `db_maxconn` reconnects on every switch, and the counter is
the signal to raise it.

**The replica is optional and self-demoting, and never waits the budget out.**
Lag is sampled, and reads that would be too stale go to the primary instead
of being served wrong; a replica that does not answer costs a read-only
request at most `REPLICA_BORROW_TIMEOUT` (5 s) once and nothing while the
breaker is open, where the primary keeps the full `db_borrow_timeout` because a
restart should be waited out (`db/README.md`, the replica entry). The breaker
backs off exponentially to a ceiling of `REPLICA_RETRY_TIME` (1200 s),
which the table above does not list because it is not the resilience tier's:
`libs/breaker.py` owns the `CircuitBreaker` (failure gating with exponential
backoff, an optional failure threshold and window, no framework dependency, so
the egress pipeline can use it too), and `db/replica.py` — connectivity,
since it holds the two connections — owns the constant and constructs the
breaker with it inside the `ReplicaRouter` that `Registry.cursor` delegates
to. The ceiling is the maximum a doubling backoff reaches, so a blip recovers
in about a second while the worst case is twenty minutes.

## The HTTP transport

`service/_transport.py` owns the connection: it parses requests with the strict
HTTP/1.1 parser in `libs/http1.py`, frames responses, and hands each request to
the WSGI `Application` unchanged; `service/httpd.py` is the threaded server built
on it (the selector, the worker pool, keep-alive), and a prefork worker calls the
transport directly. `werkzeug.serving` is not used; werkzeug's
request and response wrappers still are.

| Server | Connection handling |
|---|---|
| threaded (`workers = 0`) and the evented websocket port | one selector thread holds the listening socket and every idle connection and reads request heads without blocking; a request reaches a worker thread only once its head is complete. Connections are kept alive; a worker serves up to 16 pipelined requests inline before handing the connection back, and a head already buffered at that point is re-queued at once rather than parked. Malformed bytes left after a served request are answered by the parser (`400`/`431`), never raised out of the worker. A websocket leaves the pool at its `101` and runs on its own thread, named like a request thread so the test harness still waits for it |
| prefork (`workers > 0`) | one request per connection, answered `HTTP/1.1` with `Connection: close`. A single-threaded worker holding an idle connection would block its whole process. Workers never expose the socket, so a websocket handshake there gets the `503` that names the evented port |

Knobs, read from the environment:

| Variable | Default | Bounds |
|---|---|---|
| `ODOO_MAX_HTTP_THREADS` | `(db_maxconn - max_cron_threads - job_workers) // 2` | concurrent requests on the threaded server; `0` is unbounded |
| `ODOO_HTTP_SOCKET_TIMEOUT` | `2 s` (`5 s` under `test_enable`) | each blocking read or write of a body or a response; a pause inside the head is bounded by `ODOO_HTTP_HEAD_TIMEOUT` instead, on both servers |
| `ODOO_HTTP_HEAD_TIMEOUT` | `10 s` | from the first byte of a request head to its end; a partial head past it gets `408` |
| `ODOO_HTTP_KEEPALIVE_TIMEOUT` | `75 s` | an idle kept-alive connection is closed after this |
| `ODOO_HTTP_MAX_IDLE_CONNECTIONS` | `4096` | idle connections held; past it the oldest idle one is closed |
| `ODOO_HTTP_DRAIN_BYTES` | `1 MiB` | unread request body discarded, within one second, to keep a connection alive; beyond it the connection closes after a two-second lingering close |

**What the parser refuses**, each with the connection closed: conflicting
`Content-Length`, whitespace before a header colon, obsolete line folding,
control characters in a field, a missing or repeated `Host` on HTTP/1.1,
`Transfer-Encoding` on HTTP/1.0 or with a final coding other than `chunked`
(`400`), any other transfer coding (`501`), an unsupported `Expect` (`417`),
HTTP/2 request lines (`505`), heads over 64 KiB or 100 fields (`431`). A request
carrying both `Content-Length` and `chunked` is decoded as chunked and its
connection closed afterwards. Header names containing `_` are dropped from the
environ, because `X_Forwarded_For` and `X-Forwarded-For` would otherwise both
become `HTTP_X_FORWARDED_FOR`. `100 Continue` is sent only when the application
first reads the body.

**The access log** is the logger `odoo.service.http.access`, no longer
`werkzeug`. It keeps werkzeug's line and record shape (the request line is the
first argument, which is what a masking filter rewrites) and werkzeug's standing:
INFO by default even under `--log-level=debug`, quieted by the `warn`, `error`,
`critical` and `runbot` levels. A `log_handler` entry naming `werkzeug` no longer
reaches it, and the server warns at startup when one does. A logging filter sees
only records emitted on its own logger, so a filter that masks secrets in URLs
(`payment_stripe`'s client secret, `telegram_bot`'s webhook token) must be
attached to `odoo.service.http.access` itself.

**Behind a reverse proxy**, keep upstream connections alive and let the proxy
close them first, so it never reuses a connection Odoo is closing:

```nginx
upstream odoo { server 127.0.0.1:8069; keepalive 32; keepalive_timeout 60s; }
location / {
    proxy_pass http://odoo;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
}
```

`keepalive_timeout` there must stay below `ODOO_HTTP_KEEPALIVE_TIMEOUT`. The
websocket location still needs `Upgrade`/`Connection: upgrade` and, under
`workers > 0`, the evented port.

## What `/web/metrics` exposes

`odoo/service/metrics.py` renders the Prometheus exposition the `web` addon
serves at `/web/metrics` (bearer token `ODOO_METRICS_TOKEN`; 404 when unset).
Every sample carries `pid`; a prefork worker answering the route reports the
master's census, so the worker gauges are the master's numbers. This table is
gated: `tests/service/test_metrics_catalogue.py` fails when a family is
rendered and not listed here, or listed and no longer rendered.

**Process**

| Family | Kind | Meaning |
|---|---|---|
| `odoo_up` | gauge | 1 when the endpoint is serving |
| `odoo_server_info` | gauge | constant 1 with the `flavor` label (`threaded`, `prefork`, `evented`) |
| `odoo_registries` | gauge | registries held in memory |
| `odoo_threads` | gauge | live service threads by `type` (`http`, `cron`, `job`, `websocket`) — threaded and evented |
| `odoo_http_threads_max` | gauge | the bounded HTTP handler slots — threaded and evented |
| `odoo_limits_reached_threads` | gauge | threads over their time limit whose cancel did not free them, pending the reload — threaded |
| `odoo_overruns_cancelled_total` | counter | requests, sweeps and jobs over `limit_time_real` whose queries were cancelled — threaded |

**Prefork master** (absent on a threaded server)

| Family | Kind | Meaning |
|---|---|---|
| `odoo_workers` | gauge | live worker processes by `type` (`http`, `cron`, `job`) |
| `odoo_worker_population` | gauge | the configured HTTP worker count, after SIGTTIN/SIGTTOU |
| `odoo_worker_generation` | gauge | workers forked since the master started |
| `odoo_worker_exits_total` | counter | worker exits by `outcome`: `clean`, `terminated` (its SIGTERM), `timeout` (the watchdog's kill of a ready worker), `crash` — a crash loop is a rising `crash` beside a flat `clean` |
| `odoo_long_polling_alive` | gauge | 1 while the evented child runs |

**Connection pool** (`db.get_pool_health()`, one series per `pool` mode)

| Family | Kind | Meaning |
|---|---|---|
| `odoo_pool_borrows_total` | counter | connections borrowed |
| `odoo_pool_borrows_direct_total` | counter | borrows served outside the pooled path |
| `odoo_pool_borrows_failed_total` | counter | borrows that raised instead of yielding a connection |
| `odoo_pool_borrow_wait_seconds` | histogram | time borrows spent waiting for a connection |
| `odoo_pool_borrow_wait_seconds_max` | gauge | the longest single wait observed |
| `odoo_pool_created_total` / `odoo_pool_reaped_total` / `odoo_pool_evicted_stale_total` | counter | per-DSN pools created; closed by the idle reaper; evicted because their credentials changed |
| `odoo_pool_pools` | gauge | per-DSN pools open |
| `odoo_pool_connections_discarded_total` | counter | connections dropped rather than returned |
| `odoo_pool_connections_trimmed_total` | counter | idle connections closed to keep this process's backends within `db_maxconn` |
| `odoo_pool_backends` | gauge | server connections held (checked out + idle), trimmed on every return to `db_maxconn` per pool mode |
| `odoo_pool_checked_out` / `odoo_pool_checked_out_oldest_seconds` | gauge | connections a borrower holds now; the age of the longest-held one — a rising floor is a leak |
| `odoo_pool_direct_out` | gauge | unpooled connections outstanding |
| `odoo_pool_budget_maxconn` / `odoo_pool_budget_in_use` / `odoo_pool_budget_available` | gauge | the shared connection budget: ceiling, held, unclaimed |
| `odoo_pool_budget_exhausted_total` | counter | times the budget ran out |
| `odoo_pool_leaks_reported_total` | counter | connections found held past `db_leak_detection` |
| `odoo_pool_probe_run_total` / `odoo_pool_probe_permanent_total` / `odoo_pool_probe_transient_total` / `odoo_pool_probe_skipped_total` | counter | pre-flight connectability probes: run; concluded permanent; concluded transient; skipped for a DSN already proven |
| `odoo_db_pool_<stat>` | gauge | psycopg_pool's own per-database statistics, labelled `pool` and `database` |

**Replica routing** (`db.get_replica_health()`, one series per `database`)

| Family | Kind | Meaning |
|---|---|---|
| `odoo_replica_breaker_closed` | gauge | 1 while read-only cursors go to the replica; 0 while the breaker holds them on the primary |
| `odoo_replica_breaker_failures` / `odoo_replica_breaker_trips` | gauge | consecutive replica failures counted; times the breaker opened since the registry was built |
| `odoo_replica_breaker_cooldown_remaining_seconds` | gauge | seconds until one request may try the replica again |
| `odoo_replica_lag_seconds` | gauge | apply lag on the last sample; `+Inf` for a standby that has replayed nothing yet |
| `odoo_replica_lagging` | gauge | 1 while the lag gate routes read-only cursors to the primary |
| `odoo_replica_write_pins` | gauge | sessions reading from the primary because they wrote |

## What a deployment must provide

| Dependency | Why it is not optional |
|---|---|
| **PostgreSQL** | every cross-process signal travels through it; `MIN_PG_VERSION` (`odoo/release.py`) is 18 and `db/pool.py` refuses older servers |
| **The filestore** | attachment bytes; must be backed up *with* the database ([`data.md`](data.md#the-dual-storage-seam)) |
| **Addons on disk** | `addons_path`; earlier entries shadow later ones |
| **`odoo_rust`** | imported at startup; absent, the process warns and runs on the pure-Python twins behind `odoo/libs/accel.py` unless `ODOO_REQUIRE_NATIVE` or `CI` makes its absence fatal. A *stale* or *debug* build is always fatal. `odoo_lint`, the sibling extension carrying the `test_lint` source scanner, is **not** a deployment dependency: it is a separate wheel that only the lint gates import |

## What this view does not cover

- **The rest of the reverse proxy.** `proxy_mode` and TLS termination are not
  described here; connection reuse is, in [The HTTP transport](#the-http-transport).
- **Measured behaviour under `workers > 0`.** Every figure in
  [`qualities.md`](qualities.md) is single-process; the prefork path's latency,
  memory and signalling cost are unmeasured.
- **Cron contention across workers.** How `max_cron_threads` workers avoid
  running the same job is a runtime concern, not described in this view.
- **Database migrations during rolling upgrades.** Keeping a healthy generation
  running after a rejected replacement does not undo committed schema changes.
