# Data view — what state exists, who owns it, and how it survives

> One of the views indexed by [`ARCHITECTURE.md`](ARCHITECTURE.md).
> The module view says what code exists; the runtime view says what runs. This
> one says **what persists** — because the framework's hardest constraints come
> from state it does not hold in memory.

Four stores hold everything, with different owners, lifetimes, and consequences
when they disagree. **Only one is authoritative for schema, and it is not the
Python source.**

```
   ┌──────────────────────── PostgreSQL (one database per tenant) ─────────────┐
   │  business tables          the meta-schema             the signalling tables│
   │  res_partner, …           ir_model, ir_model_fields,  orm_signaling_*      │
   │  (rows the user owns)     ir_model_data, ir_ui_view…  (8 of them)          │
   └──────────────────────────────────────────────────────────────────────────┘
              │                          │                        │
              │ ir_attachment.store_fname│ drives DDL             │ version counter
              ▼                          ▼                        ▼
   ┌────────────────────┐   ┌─────────────────────┐   ┌────────────────────────┐
   │  FILESTORE         │   │  the running        │   │  every other worker's  │
   │  <data_dir>/       │   │  Registry           │   │  check_signaling()     │
   │   filestore/<db>/  │   │  (in memory, per    │   │                        │
   │   b3/<2>/<digest>  │   │   process, per db)  │   │                        │
   └────────────────────┘   └─────────────────────┘   └────────────────────────┘

   ┌────────────────────┐   ┌────────────────────┐
   │  SESSIONS          │   │  DOWNLOADED ADDONS │
   │  <data_dir>/       │   │  <data_dir>/addons/│
   │   sessions/        │   │                    │
   └────────────────────┘   └────────────────────┘
```

## 1. The meta-schema — the schema is data

| Model | Holds |
|---|---|
| `ir.model` | one row per model |
| `ir.model.fields` | one row per field — **this is what column DDL is derived from** |
| `ir.model.fields.selection` | selection values, as rows |
| `ir.model.data` | the XML-id ↔ database-id map, which is what makes upgrades idempotent |
| `ir.model.relation` | many2many join tables |
| `ir.model.constraint` | SQL constraints the ORM created and therefore may drop |
| `ir.model.inherit` | the resolved inheritance graph |
| `ir.model.access` | model-level permissions |
| `ir.ui.view` | view architecture, as XML in a column |
| `ir.module.module` | which modules are installed **in this database** |

Two consequences the rest of the architecture is built around:

**Installing a module mutates the schema at run time.** There is no build step
and no migration file that is the source of truth: the Python field declarations
are *inputs*, `ir_model_fields` is the record, and the DDL is derived by
comparing them. This is why `Registry.new()` has phases, and why a cold registry
build costs ~50× a warm load
([qualities.md](qualities.md#scenario-2--registry-build-and-boot)).

**`ir_module_module` is per database, so "installed" is not a property of the
deployment.** Two databases served by one process have different model sets,
different columns, and genuinely different runtime classes for the same `_name`.
Nothing may be cached per process without a database key.

The ORM reads and writes this meta-schema through one object, `registry.metaschema`
(`orm/runtime/metaschema.py`): reflection at model init, the manual models and
fields, a model's translated description and a field's labels and selection, a
model's defaults and a column's company fallbacks, the constraint messages. The
same object answers on the in-memory registry from its own storage, which is what
lets a DB-free environment reflect its models into `ir.model` and `ir.model.fields`
rows and register their external ids through `registry.xmlids`.

## 2. The signalling tables — cross-process coordination

Ten tables, one for the registry and one for each key in `CACHES_BY_KEY`
(`default`, `assets`, `stable`, `templates`, `routing`, `groups`,
`product_variants`, `actions`, `mail`), each created as:

```sql
CREATE TABLE orm_signaling_<name> (id SERIAL PRIMARY KEY, date TIMESTAMP DEFAULT now())
```

**There is no message and no payload — the row's generated `id` *is* the version
number.** To invalidate, a worker inserts a row and keeps the id PostgreSQL
assigned; every other worker compares the serial's last value (one sequence read
per table, not a `max(id)` scan) against the one it last saw, on its next
`check_signaling()`, and rebuilds its registry or clears the named caches
accordingly. A serial moves even when the inserting transaction rolls back, so a
rolled-back registry change costs the other workers one spare reload — rare, and
cheaper than planning eleven subselects on every request.

This is why the process model is architectural rather than a deployment knob
(`workers > 0` means no shared memory), and why any process-lifetime cache must
be registered in `CACHES_BY_KEY` — an unregistered cache has no table, therefore
no version, therefore no way to be told it is stale.

`setup_signaling` creates each table **and inserts one row**: an empty table
would read back as "no version", and a local sequence starting at `-1` would then
treat every check as a change. `get_sequences` reads all ten in one `SELECT`
of ten scalar subqueries.

## 3. The filestore — content-addressed, and its layout is not fixed

Attachment bytes live at `<data_dir>/filestore/<dbname>/`, keyed by content
digest, sharded on the first two characters:

| `ALGO_TAG` | Path shape | Digest length |
|---|---|---|
| `b3` (blake3 available) | `b3/<first-2>/<digest>` | 64 |
| `s1` (fallback) | `<first-2>/<digest>` | 40 |

`ALGO_TAG = "b3" if HAS_BLAKE3 else "s1"` (`odoo/libs/hashing.py`). **The layout
depends on an optional dependency**, and the legacy `s1` form has no algorithm
prefix, so the two shapes coexist in one filestore rather than one superseding
the other. A path is not portable between deployments that disagree about
blake3.

Content addressing means identical bytes are stored once and **an attachment row
is not the owner of its bytes** — deleting one row must not delete a file another
row still references.

### The dual-storage seam

`ir.attachment` can hold its bytes in *either* place:

- `store_fname` — a path into the filestore
- `db_datas` — the bytes, in the database

They are alternatives, not layers; which one is used is a per-attachment
decision, and one column carries both *which store* and *which key* — which
is why nothing can map a store back to the content it holds.
**Any backup that captures PostgreSQL without the filestore, or the reverse,
captures a torn state** — the most common way a restored database comes back
subtly broken.

## 4. Sessions and downloaded addons

| Path | Holds | Lifetime |
|---|---|---|
| `<data_dir>/sessions/` | HTTP sessions, as files (`FilesystemSessionStore`) | garbage-collected; safe to lose — users re-authenticate |
| `<data_dir>/addons/` | modules downloaded at run time | rebuildable |

Sessions are the one store here **not** partitioned per database by directory,
and losing the directory is an availability event, not a data-loss one. That
asymmetry is worth knowing before treating `data_dir` as one unit.

## What is authoritative for what

The question to ask of any change: *if these disagreed, which one wins?*

| Subject | Authority | Not authoritative |
|---|---|---|
| Which fields a model has **in this database** | `ir_model_fields` | the Python class |
| Which modules are installed | `ir_module_module` | `addons_path` contents |
| Whether a cached value is stale | `orm_signaling_*_id_seq` last value | process uptime |
| An attachment's bytes | `store_fname` **xor** `db_datas` | either alone |
| The identity of a record across upgrades | `ir_model_data` XML id | the numeric `id` |
| A company's name, address, identifiers and image | `res_partner`, through `res_company.partner_id` (`_inherits`) | a column on `res_company` — there is none |

### The tenant and its party

`res.company` is the tenant: the row that `env.company`, the access scope, `company_dependent`
storage and every `company_id` foreign key are keyed on. It `_inherits` `res.partner`, its party,
exactly as `res.users` does, so identity is read and written through the delegation and never
copied. What `res_company` stores is tenant fact only: `code`, `sequence`, `active`, `currency_id`,
the branch hierarchy (`parent_id` shadows the contact hierarchy of the party), `user_ids`, and the
derived `logo_web` / `uses_default_logo`. The party behind a tenant has no contact parent and its
name is unique among tenants (`res.partner._check_company_party_name_unique`). Two model
attributes say who may read what through a delegation: `_inherits_rules = False` keeps the
party's record rules off the tenant's rows (a portal user reads the tenant it belongs to even
though its party is outside the user's partner rules), and `_inherits_sudo_fields` names the
party fields that are the tenant's public identity, read under the tenant's access; every other
delegated field is read under the party's rules. Configuration that an
application keys on the company is the application's, not the tenant's: it lives on the
application's `mixin.company.config` model, one row per company (`report.config`,
`account.config`), reached from the company through one `<app>_config_id` link. The link is
computed and searchable, so a domain reads `("account_config_id.chart_template", "!=",
False)`; a company create or write that names a configuration field is routed to that
configuration (`_split_config_vals`), while a read of the field on the company raises. A branch
takes its root's delegated configuration at create and is held to it. See
`agromarin-knowledge/plans/2026-09-19-company-tenant-party-architecture.md`.

## Lifecycle and the operations that cross stores

| Operation | Crosses |
|---|---|
| **Create** | `_create_empty_database` clones `db_template`, so extensions are inherited rather than installed |
| **Install / upgrade** | business tables, the meta-schema and the filestore, one transaction per module, then signals |
| **Backup / restore** | PostgreSQL **and** the filestore, together — see the dual-storage seam above |
| **Drop** | the filestore directory for that database is a separate deletion |

## What this view does not cover

- **Replica topology.** There is a read-only replica path with a breaker —
  `libs/breaker.py` owns the mechanism, `db/replica.py` the policy
  (`ReplicaRouter`, and `REPLICA_RETRY_TIME`, the cooldown ceiling it
  constructs the breaker with). Two facts about what a replica read may
  return *are* settled, because the router enforces them: the staleness
  window is bounded by `db_replica_max_lag` (apply lag, sampled; a standby
  with WAL outstanding and nothing replayed yet counts as infinitely
  behind), and a session reads its own writes — for `db_replica_write_pin`
  seconds after a transaction of its own assigned a transaction id, its
  read-only requests go to the primary (`WritePins`, keyed by the session id
  the http layer passes). Which data is *appropriate* to read from a
  replica beyond that — a route's `readonly=True` — is the route author's
  claim, not this view's.
- **Retention.** Nothing here says how long sessions, attachments or log-like
  tables are kept.
- **Encryption at rest**, for any of the four stores.
