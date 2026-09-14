# Quality attributes — the numbers a design change is judged against

> One of the views indexed by [`ARCHITECTURE.md`](ARCHITECTURE.md).
> The *Forces* table there says what the architecture optimises for. This page
> says **how much**, so a change can fail one of those forces instead of merely
> disappointing it.

A force with no number cannot reject anything. "Write throughput" is a value;
"10,000 writes must cost ~100 statements, not 10,000" is a constraint. Every
figure below is dated and carries the command that reproduces it.

**These are observations, not SLOs.** They are the current cost of the design,
recorded so a change that moves one by an order of magnitude is visible as a
decision rather than a surprise. Where a figure *is* load-bearing — the batching
ratio, the registry-per-database cost — the scenario says what would falsify it.

Each scenario is stated as **stimulus**, **environment**, **response**,
**measure**. One missing the environment is not reproducible; one missing the
measure is a wish.

## The measurement environment

Absolute values belong to one machine and one configuration. The *ratios* are
the portable part.

| | |
|---|---|
| CPU / RAM | Intel Core Ultra 9 185H, 22 logical cores, 30 GB |
| PostgreSQL | 18.x, unix-socket peer auth, local |
| Python | 3.14.4 (venv, with `odoo_rust` built in) |
| Server mode | `workers = 0` (threaded), `log_level = info`; Scenarios 5 and 6 state their own — `workers = 4`, prefork |
| Databases | `base` alone, and `sale_management,purchase,stock,account`. Both grow with the tree: `base` held 154 models on 2026-08-08, 162 (19 modules) on 2026-08-28, 166 (18 modules) on 2026-09-11; the four-module set held 105 modules / 529 models on 2026-08-08 and 114 / 597 on 2026-08-28 |

Two registry sizes throughout, because one number would mislead: the framework's
costs scale with the *installed module set*, not with the framework, and a
`base`-only figure understates a real deployment by roughly the ratio between
the two columns.

## Scenario 1 — Write throughput

> **Stimulus** A loop assigns one field on each of 10,000 records.
> **Environment** One process, one transaction, no concurrent writers, `base`.
> **Response** Writes accumulate in the field cache; SQL is issued once, at
> flush, batched.
> **Measure** Statements issued, and the ratio to the un-batched equivalent.

| | Write statements | Wall 2026-08-08 | Wall 2026-09-11 |
|---|---:|---|---|
| **Deferred (the design)** | **100** | 1.454 s | 1.708 s |
| Per-record flush (counterfactual) | 10,000 | 4.099 s | 4.269 s |
| **Ratio** | **100 : 1** | 2.8 × | 2.5 × |

**The loop issues no writes, not no statements.** Every write lands at flush;
reads do not. The loop also issues prefetch `SELECT`s before the flush, scaling
with the number of prefetch batches rather than with the records: 2 at
N=2,000 and 10 at N=10,000 (2026-09-11). Count writes, not statements: a
regression that makes the loop issue *writes* is what this scenario exists to
catch, and the total buries it at 110 against 10,010 where the write count is
100:1.

The batched form is not `WHERE id IN (…)` but a multi-row join:

```sql
UPDATE "res_partner"
   SET "comment" = "__tmp"."comment"::text, "write_date" = …, "write_uid" = …
  FROM (VALUES (%s, %s, %s, %s), …) AS "__tmp"
```

which is why 10,000 *different* values still collapse into 100 statements rather
than needing one per distinct value.

**What would falsify this:** any change that makes the loop issue SQL *writes* —
an implicit flush inside `write()`, a recompute that reads across the dirty set,
a constraint evaluated per record. The counterfactual row is what that regression
looks like, and it is 100× worse on statements before it is 3× worse on time, so
statement count is the earlier signal.

Reproduce: create 10k `res.partner` rows and flush, then assign `comment` in a
loop with a counting wrapper on `Cursor.execute`, flushing once at the end
versus once per record, and count the loop and the flush separately.

## Scenario 2 — Registry build and boot

> **Stimulus** A process starts and must serve a database.
> **Environment** Cold (schema created, modules installed) versus warm (registry
> assembled from an installed database).
> **Response** The module graph is loaded and the runtime model classes are
> composed.
> **Measure** Registry build time (`Registry loaded in …s`), process wall time,
> peak RSS.

| | `base` 2026-08-08 (154 models) | `base` 2026-09-11 (166 models) | 105 modules 2026-08-08 (529 models) | 105 modules 2026-08-09 (531 models, loaded box) |
|---|---|---|---|---|
| Install + build, registry | 7.16 s | 6.72 s | **35.85 s** | 42.92 s |
| Install + build, wall | 8.35 s | 7.85 s | 37.53 s | — |
| Install peak RSS | 262 MB | 263 MB | 508 MB | 519 MB |
| **Warm registry load** | 0.187 s | **0.55 s** | **0.72 s** | 0.746 / 0.765 s |
| Warm boot, wall | 1.06 s | 1.53 s | 1.78 s | 1.82 / 1.84 s |
| Warm steady RSS | 164 MB | 173 MB | 224 MB | 228 MB |
| **cold ÷ warm** | 38× | 12× | **50×** | 58× |

Building a registry costs an order of magnitude more than loading one: the cold
path runs DDL and module data loading, the warm path only composes classes and
reads `ir_model*`. Anything that forces a rebuild — a schema-affecting change, a
module install — pays the upper number, which is why registry invalidation is
signalled rather than assumed.

**The warm `base` load is dominated by a one-time probe.** Of the 0.55 s on
2026-09-11, 0.35 s is `_get_text_transforms`
(`orm/runtime/_registry_capabilities.py`): one query over every Unicode code
point (`generate_series` × `unaccent` × `lower`, 0.33 s in `psql`) that builds
the in-memory `ilike`/`unaccent` tables and is cached per process and database.
A second `Registry.new()` for the same database in the same process takes
0.14 s. The warm column therefore measures first-registry cost; a signalling
rebuild pays the smaller number.

Reproduce:

```bash
odoo-bin -c <conf> -d <db> -i <modules> --stop-after-init   # cold
odoo-bin -c <conf> -d <db> --stop-after-init                # warm
```

under `/usr/bin/time -f "wall=%e s maxrss=%M KB"`, and read `Registry loaded
in …s` from the log.

## Scenario 3 — Multi-tenancy cost

> **Stimulus** One process is asked to serve a second database.
> **Environment** Same process, both registries resident. Measured 2026-08-28,
> three runs each way, on `base` (19 modules, 162 models) and
> `sale_management,purchase,stock,account` (114 modules, 597 models).
> **Response** A second, independent registry is built and held.
> **Measure** Resident memory added by the second registry (`ru_maxrss` delta).

| First registry | Second registry | Second adds | MB per model of the second |
|---|---|---:|---:|
| `base`, 162 models | 597 models | **+72.0 MB** | **0.120** |
| 597 models | `base`, 162 models | **+6.1 MB** | **0.037** |

**The second registry pays for what the process does not already hold, not for
its own size.** `base`'s models are very nearly a subset of the larger schema's,
and loading it second costs 6 MB rather than the 92.6 MB it costs first
(0.57 MB per model). First registries are the expensive ones: 162 models cost
+92.6 MB loaded into an empty process and 597 cost +160.2 MB (0.27 MB per
model), because the first registry pays every once-only cost the rest inherit.
A capacity estimate built by multiplying tenants by a per-registry figure
over-counts by however much the tenants' schemas share; **+0.12 MB per model
of *distinct* schema is the figure to plan with.**

Method caveat: both are deltas of `ru_maxrss`, a *peak* that never falls. They
are lower bounds on growth and cannot observe memory being released.

**What would falsify this:** a shared, copy-on-write or interned representation
of field/model metadata across distinct registries would collapse the +72 MB; a
per-registry cache growing with *data* rather than schema would make it
unbounded. Neither is visible in a single measurement, which is why this
scenario states a condition rather than a rate.

Reproduce: install two databases, read
`resource.getrusage(RUSAGE_SELF).ru_maxrss` as a baseline, then in **one**
process construct `Registry(db)` for each in turn, reading the peak again after
each and asserting the two registry objects are distinct. Run it in both orders
— the pair is the measurement, not either number.

```bash
odoo-bin -c <conf> -d <db_a> -i base --stop-after-init
odoo-bin -c <conf> -d <db_b> -i sale,purchase,stock,account --stop-after-init
```

## Scenario 4 — Request latency

> **Stimulus** An unauthenticated HTTP request arrives.
> **Environment** Threaded server (`workers = 0`), warm registry, loopback
> client, 200 requests after a 30-request warm-up over one keep-alive
> connection. Measured 2026-08-08 on 529 models and 2026-08-09 on 154
> (`base,web`).
> **Response** The request is dispatched; a full route additionally opens a
> transaction, queries, and renders.
> **Measure** Latency percentiles.

| Route | Models | p50 | p95 | p99 | max |
|---|---:|---|---|---|---|
| `/web/health` (dispatch only) | 529 | 2.0 ms | 2.7 ms | 3.6 ms | 3.8 ms |
| `/web/login` (transaction + ORM + QWeb) | 529 | 12.6 ms | 13.9 ms | 15.2 ms | 18.7 ms |
| `/web/health` | 154 | 2.0 ms | 2.4 ms | 3.6 ms | 7.1 ms |
| `/web/login` | 154 | 12.7 ms | 14.5 ms | 16.0 ms | 16.5 ms |

The **~10.6 ms difference at p50 is the cost of everything the framework adds
over bare HTTP dispatch** — cursor acquisition, environment construction, the
ORM reads behind the template, and rendering. That figure, not the absolute
latency, is what a change to the request lifecycle moves. **Registry size does
not drive request latency** — the per-request work does: 375 additional models
moved neither route measurably.

The distributions are tight (p99 within 1.5× of p50 on both). That is the
threaded, single-process, no-contention case by construction; contention is
Scenario 5.

Reproduce: install `base,web`, serve on a free port, then 200 requests per route
after a 30-request warm-up over one keep-alive connection, timing each
round-trip and reading percentiles off the sorted samples.

## Scenario 5 — Contention and retry

> **Stimulus** Sixteen clients write the same field on the **same record**,
> concurrently and without pause.
> **Environment** `PreforkServer`, `workers = 4`, `max_cron_threads = 0`,
> `db_maxconn = 24`, `base,web`, XML-RPC `res.partner.write` over loopback,
> 16 threads × 200 calls. Measured **2026-08-28**, two runs each way.
> **Response** PostgreSQL raises `SerializationFailure`; `retrying()` sleeps a
> uniform backoff and re-runs the handler, up to
> `MAX_TRIES_ON_CONCURRENCY_FAILURE` (5).
> **Measure** Throughput, latency percentiles, the retry rate, and how many
> requests exhaust the budget and reach the client as a 500.

The control is the same load on **sixteen different records**: identical
concurrency, identical request, only the row differs — so what separates the two
columns is contention and nothing else.

| | 16 rows (control) | 1 row (contended) |
|---|---|---|
| Throughput | 601.5 / 613.8 per s | **177.1 / 198.6 per s** |
| p50 | 26.3 / 25.5 ms | **67.1 / 61.3 ms** |
| p95 | 30.2 / 30.5 ms | 91.2 / 74.8 ms |
| p99 | 33.8 / 32.8 ms | **347.8 / 158.0 ms** |
| max | 165 / 186 ms | **2677 / 2028 ms** |
| Requests retried | **0** | 145 of 6,400 (2.3 %) |
| Failed to the client | **0 of 6,400** | **32 of 6,400 (0.5 %)** |

Contention on one row costs **~3× the throughput, ~2.5× the p50 and 5–10× the
p99**, and turns a run with no failures into one with a floor of half a percent.

**The retry ladder barely converges.** Every re-run logs one line, so the depth
distribution is countable. Across both contended runs:

| Attempt | Requests still failing | Survived to here |
|---|---:|---:|
| 1st retry | 145 | — |
| 2nd | 97 | 67 % |
| 3rd | 69 | 71 % |
| 4th | 45 | 65 % |
| budget exhausted | **32** | 71 % |

Two thirds to three quarters of the requests that need one retry need another,
at **every** depth: 22 % of the requests that ever retried failed outright.

**`retrying()` is a burst absorber, not a queue.** `delay()` draws
`uniform(0, ceiling)` with the ceiling doubling from
`BASE_CONCURRENCY_BACKOFF_SECONDS` (0.2) to `MAX_CONCURRENCY_BACKOFF_SECONDS`
(2.0), which spreads a *burst* of writers apart. Under a load that never stops
offering, a retry lands back into the same contention it left, and the
mechanism converges to a fixed loss rate instead of to zero. Retry budgets
protect against transient conflict; no budget converts sustained same-row write
contention into success.

**What would falsify this:** a workload where the retried requests drain — where
the per-rung survival falls sharply rather than staying near 70 % — would mean
the backoff is doing what it looks like it does. A *lower* failure rate at
higher concurrency would mean the loss is queueing, not serialization; it is
not, since the control at the same concurrency loses nothing.

Reproduce: boot prefork on a free port, create enough records for the control,
then drive N client threads through XML-RPC `execute_kw(..., "res.partner",
"write", ...)` — all on one id for the contended column, one id each for the
control — timing every round trip, and count the server's retry lines.

```bash
odoo-bin -c <conf> -d <db> --http-port 8171 --workers 4 \
    --max-cron-threads 0 --db_maxconn 24
grep -c "tries left, try again" <server log>          # retries
grep -c "maximum number of tries reached" <server log>  # budget exhausted
```

## Scenario 6 — Cross-process invalidation

> **Stimulus** One worker clears a named cache — `ir.config_parameter.set_param`
> calls `registry.clear_cache("stable")`, which `INSERT`s a row into
> `orm_signaling_stable` and keeps the id the database generated.
> **Environment** `PreforkServer`, `workers = 4`, `max_cron_threads = 0`,
> `base,web`, loopback, measured **2026-08-28**. Two conditions: eight client
> threads keeping every worker busy, and no traffic at all.
> **Response** Every other worker reads the sequence on its next
> `check_signaling()` and drops the LRUs behind that key, logging one line.
> **Measure** How long that takes, and how many of the other workers it reaches.

| | 8 background clients | no traffic |
|---|---|---|
| Other workers reached per signal | **3 of 3**, on 9 of 10 rounds | **none** |
| p50 | **1 ms** | — |
| p95 / max | 3 ms / 3 ms | — |

**The placement is the point.** `check_signaling()` is called from
`_acquire_registry_cursor` (`odoo/http/_serve.py`), on the read-only cursor the
request was already taking, **before the request is dispatched**. So it is a
poll at request start, not a push — which is why the idle column is empty, and
why that is correct rather than a defect: a worker serving nothing has no
opportunity to serve a stale cache, and the first request it does take clears
the cache before dispatch. Staleness is bounded by "before the next request",
not by a propagation delay.

**The tax is one query, not nine.** `get_sequences` builds a single `SELECT`
of nine scalar subqueries, one per signalling table — **1.08 ms from `psql`**
(2026-08-28), **0.05 ms p50 in-process** on an open cursor (2026-09-11, 50
calls, `base`).

**A quoted propagation figure belongs to a traffic level.** The 1 ms above is
what a *busy* worker shows; a deployment with uneven traffic has workers whose
caches are arbitrarily old and none of them can serve one.

**What would falsify this:** a worker dispatching a request on a registry older
than the sequence in the database — which would mean the check has moved off the
cursor-acquisition path, or that the read-only cursor is landing on a replica
far enough behind to report no change. The second is described in
[`data.md`](data.md#2-the-signalling-tables--cross-process-coordination):
signalling read through a replica reads *below* the local sequence as staleness
and ignores it, but a replica merely behind reads as "nothing has changed".

Reproduce: boot prefork on a free port, keep N clients calling any cheap route
so every worker is serving, then call `set_param` from one more client and read
the deltas out of the server's own log — the access line for the signalling
request and the `Invalidating caches after database signaling` line each worker
writes. Both carry the pid, so no clock alignment with the client is needed.

```bash
odoo-bin -c <conf> -d <db> --http-port 8172 --workers 4 --max-cron-threads 0
grep "Invalidating caches after database signaling" <server log>
```

## What this page does not measure

- **Contention on anything but one row.** Scenario 5's two columns are the
  extremes: total conflict and none. Realistic workloads sit between, and where
  the retry ladder starts converging is not measured.
- **Flush fixpoint depth.** How many passes a realistic write takes is
  unmeasured, and non-convergence is an error the architecture asserts but this
  page does not characterise.
- **Cold filestore and large attachments.** No I/O-bound scenario appears here.
- **Upgrade of a populated database.** Scenario 2's cold path installs into an
  empty database; migrating one with data is a different, larger cost.

A number added to this page must arrive with its command and its date, in the
same form as the rest.
