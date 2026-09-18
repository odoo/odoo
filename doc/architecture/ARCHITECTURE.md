# Odoo Framework Core — Architecture

Scope: the framework core in `odoo/` — ORM, persistence, HTTP, server, module
system, utilities. This page carries context, forces, cross-cutting mechanisms
and the index of the views. Per-addon maps live in
`addons/*/machine_doc_v1/ARCHITECTURE.md`.

| If you are… | Read |
|---|---|
| new to the core | *Context* and *Forces* below, then [`module.md`](module.md) |
| placing new code | *Where to add code* below |
| debugging a runtime path | [`runtime.md`](runtime.md) |
| changing a boundary | [`module.md`](module.md), *Dependency rules* |
| judging a change's cost | [`qualities.md`](qualities.md) |

## Context

The core is not an application. It is the machine that turns a set of installed
*addons* into a running, multi-tenant, database-backed web application.

```
      browser (OWL client)          odoo-bin CLI            cron / queue
             │  HTTP/JSON-RPC             │                      │
             ▼                            ▼                      ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │  FRAMEWORK CORE  (odoo/)                                          │
   │    http/  serving · routing · sessions                            │
   │    service/  process lifecycle · the servers · cron · retrying()   │
   │    orm/  models · fields · domains · Environment/Registry/Txn      │
   │    modules/  the module graph and what loads it                   │
   │    db/  pool · cursors · DDL · resilience                         │
   └───────────────────────────────────────────────────────────────────┘
        │                    │                      │
        ▼                    ▼                      ▼
   PostgreSQL          filestore              addons on disk
   (N databases,       (attachment            (odoo/addons/, addons/,
    one registry        bytes)                 enterprise/, agromarin/…)
    each)                                      = the extension surface
```

Four properties explain more of the core than any module boundary:

| Property | Consequence |
|---|---|
| **Addons are the product** | the framework ships extension machinery, almost no business behaviour |
| **One process serves many databases** | each with its own registry, schema and installed-module set; no per-process cache without a database key |
| **One deployment runs many processes** (`workers > 0`) | no shared memory; every cross-process signal goes through PostgreSQL |
| **The schema is data** | models, fields and views are rows in `ir_model*`; installing a module mutates the schema at run time; nothing is frozen by a build step |

## Forces

What the architecture optimises for. A design change that makes one worse needs
a reason.

| Force | What it demands | Where it shows up |
|---|---|---|
| **Third-party extensibility** | a module must add fields, override methods and inherit views on a model it does not own, without patching it | `_inherit` registry assembly; the `odoo.api`/`fields`/`models` façades; string-keyed model lookup |
| **Upgrade safety** | an installed database must survive its addons changing shape | `Registry.new()` phases; `ir_model*` as a meta-schema; the migration hooks in `modules/` |
| **Multi-tenancy** | N databases per process, isolated | registry per database; `check_signaling` keyed per DB |
| **Horizontal scale** | N processes with no shared memory | database-mediated registry/cache signaling |
| **Write throughput** | a loop that touches 10k records must not issue 10k `UPDATE`s | deferred writes; the flush fixpoint loop; `cr.pipeline()` |
| **Correctness under contention** | concurrent requests must not corrupt or silently lose writes | `retrying()` on serialization/deadlock; savepoints; the RO→RW promotion |
| **Testability without a database** | the hardest logic must be exercisable in milliseconds | `orm/components/` as pure Python; `InMemoryBackend` behind the `env.backend` port with no lossy or blocking branch; the ORM's dependence on `addons/base` behind six port objects. Measured on 2026-09-13 (odoo `f7e799ce3578`, frozen): the share of a module's tests that touch nothing storage-specific is base 81 %, stock 95 %, mail 68 %, account 67 % |
| **A refactorable core** | internal layout must move without breaking hundreds of addons | the façade boundary and the layer contracts |

## Non-goals

Each buys something above. An argument appealing to one is already settled.

| Non-goal | What it buys |
|---|---|
| **Merge-compatibility with upstream Odoo** | `19.0-marin` never merges from `19.0` (*Scope and precedence*, `doc/coding_guidelines.rst`), so "it complicates the upstream merge" is not a cost this fork pays — which is what makes core refactoring affordable |
| **Stability of core internals** | the *façade* is the public surface — `odoo.api` / `odoo.fields` / `odoo.models`, each with an explicit `__all__`; everything behind it is free to move, and the layer contracts say in which direction |
| **Business behaviour in the core** | behaviour belonging to a business process belongs in an addon |
| **A build step that freezes shape** | the contributor set is unknown until the module graph is loaded, so nothing resolves at import time |
| **Database-driver portability** | psycopg 3 only — `odoo/db/` imports `psycopg` exclusively, and `psycopg2` is neither declared in `requirements.txt` nor installed, so a stray import fails at import time |

## Mechanisms

Five behaviours that cut across every view.

### Models are assembled per database, not defined

A model class in the tree is a *definition*. `orm/registration.py::add_model_to_registry`
composes the runtime class for a database by multiple inheritance over every
installed module's contribution to that `_name`; `_inherit` collects parents,
`_inherits` sets up delegation, `setup_model_classes(env)` resolves fields across
the graph. `env["res.partner"]` in one database is a different class from the
same name in another.

Consequences: fields cannot be resolved at import time; the framework cannot
import addon-owned models, so it names them by string key (`env["res.users"]`).
The framework's largest coupling to its consumer produces no import edge.

### Writes do not reach SQL where you write them

`create()`/`write()` update the field cache, mark ids dirty and schedule
dependent recomputes. The database sees nothing until a flush. A flush is a
fixpoint loop — recomputing one field can dirty another — and non-convergence
raises. Detail: [*Transaction, cache and
flush*](runtime.md#transaction-cache-and-flush).

### Cross-process invalidation runs through PostgreSQL

A registry change is published by `INSERT`ing into a signaling table and keeping
the id the database generated. Every other worker notices on its next
`check_signaling()` and rebuilds its registry or clears the named caches. Any
process-lifetime cache must be registered in `CACHES_BY_KEY`. Detail:
[*Concurrency, and why the process model is
architectural*](runtime.md#concurrency-and-why-the-process-model-is-architectural).

### A field's query behaviour is declared on the field, not dispatched by the model

Where a field's SQL is not its column, the field says so: `value_sql`,
`group_by_sql` and `order_by_sql` name the model method that composes the
expression, the GROUP BY term or the ORDER BY term, and `group_by_field` /
`order_by_field` name the stored field that stands in. An aggregate of a
non-stored compute needs no declaration at all: `_read_group` selects the
group's ids and folds the computed values in Python
(`_aggregates_through_records`). The alternative — overriding
`_field_to_sql`, `_read_group_groupby`, `_order_field_to_sql` or the
`_read_group_select` pair on the model for one field and deferring to `super()`
for the rest — is model-wide by construction: a reader looking for where one
field gets its SQL finds a method every field goes through, and a tool that
reads the model by its methods (the Rust engine's routing gate, which keys on
method identity) must treat the whole model as Python. Declared, the same SQL
is a static fact per field; the engine's export drops such a field from the
kernel's registry so a query naming it falls back, and every other field on the
model routes. Rule and signatures: `coding_guidelines.rst` §2.4.1.

### Access control is a model-layer concern, applied per operation

Every model carries `AccessMixin` (`orm/models/mixins/access.py`), so checks are
methods on the recordset: model-level permissions per CRUD operation,
record-level rules contributing a domain, field-level (`_has_field_access`,
`check_field_access_rights`) and multi-company (`_check_company`).
`_check_access(operation)` returns the accessible subset plus the callable that
explains the refusal, so one code path serves both filtering and raising. The
answers themselves -- may this model be touched, which records may this user
read -- come from `registry.access_policy`, the one object that names
`ir.model.access` and `ir.rule`; both storage backends ask it, so record rules
filter an in-memory search as they filter a PostgreSQL one.

Superuser is not a bypass flag: `sudo()` returns an environment whose `su` is
part of the `(cr, uid, su, context)` interning key. Two recordsets differing
only in privilege are different objects by construction. `uid == SUPERUSER_ID`
forces `su`, so the superuser has one environment per `(cr, context)`.

### The ORM talks to `addons/base` through six objects

The framework cannot import the models it needs from `base`, and for years it
named them by string at every site. It now names them in six files: the
meta-schema (`registry.metaschema`), access (`registry.access_policy`), external
ids (`registry.xmlids`), files (`registry.file_store`), settings
(`registry.settings`) and the locale (`registry.locale`), each a small object
whose methods are the questions the ORM asks. A PostgreSQL install runs the same
calls it always did; the in-memory registry carries the same six and answers
from its own storage where it can. What this buys is a place: a new need of the
ORM's is a method on a port, and a site that names a base model elsewhere is a
regression the ORM's own tests report
([`module.md`](module.md#the-set-of-addon-owned-models-the-framework-may-name-is-closed)).

### A request is a transaction, and it may run twice

`retrying()` (`service/transaction.py`, not a model method) re-runs the handler
on PostgreSQL serialization and deadlock errors, and a `readonly` route that
writes is re-run on a read/write cursor. Non-transactional side effects — mail,
outbound calls — must not precede the first write. Detail: [*Request
lifecycle*](runtime.md#request-lifecycle-http).

## The views

| View | Answers | File |
|---|---|---|
| **Module** | what exists, who owns it, who may import whom | [`module.md`](module.md) |
| **Runtime** | what runs when — boot, registry build, request, transaction, concurrency | [`runtime.md`](runtime.md) |
| **Data** | what persists, who owns it, what is authoritative when stores disagree | [`data.md`](data.md) |
| **Deployment** | how many processes, what each may do, and how it degrades | [`deployment.md`](deployment.md) |
| **Gates** | what is mechanically enforced, and what "enforced" is worth | [`gates.md`](gates.md) |
| **Scenarios** | end-to-end threads — installing a module, upgrading a populated database | [`scenarios.md`](scenarios.md) |
| **Qualities** | how much the forces cost, measured — so a change can fail one | [`qualities.md`](qualities.md) |
| **Risks** | where the implementation and the design demonstrably disagree | [`risks.md`](risks.md) |

Rationale is not a view. Investigation write-ups are in
`agromarin-knowledge/research/`.

Two subsystems document themselves deeper than any view:
`odoo/db/README.md` and `odoo/http/README.md` — the latter carries the
canonical, unflattened HTTP call graph.

Every figure in these pages carries the date it was measured. Nothing re-derives
one; a figure is as of that date.

## Where to add code

| You are adding | It goes in | The constraint |
|---|---|---|
| A dependency-free helper | `odoo/libs/<area>/` | no `odoo` imports; if it needs model data, take it through a `Protocol` (see `libs/locale/number_format.py`) |
| An Odoo-coupled helper | `odoo/tools/` | may use ORM values and types, never the ORM runtime |
| A new field type | `odoo/orm/fields/` | Layer 1: no `models`/`runtime` imports; reach the model layer through `_recordset.py` |
| Model behaviour | a mixin under `odoo/orm/models/mixins/` | prefer a leaf nothing else in the composition depends on |
| Cache / compute logic | `odoo/orm/components/` | pure Python, collaborators injected, no `pool` or `env` reach |
| A persistence primitive | `odoo/db/` | no ORM import; cross the boundary by injection |
| Something the ORM needs from a `base` model | the matching port in `odoo/orm/runtime/` (`metaschema`, `access_policy`, `xmlids`, `filestore`, `settings`, `locale`) | a method on the port, implemented for both registries; never a new `env["ir.*"]` in a mixin or field |
| A statement the ORM must run | `odoo/orm/runtime/backend.py` and `_backend_memory.py` | a `StorageBackend` method with a PostgreSQL body in the first and an in-memory body in the second; the protocol test refuses one without a caller |
| A view type | the addon's own module | `register("<root tag>")` an `ElementHandler` from `odoo/addons/base/models/ir_ui_view_arch.py`; do not inherit `ir.ui.view` for it |
| An HTTP feature | `odoo/http/` `[features]` | must not import `[serving]` |
| A third-party patch | `odoo/_monkeypatches/<module>.py` | expose `patch_module()` (names starting with `_` are helpers) |
| An addon | `odoo/addons/<module>/` | import through `odoo.api` / `odoo.fields` / `odoo.models` — `test_lint` rule `orm-import` (`E8508`) fails any other |
| A package README module index | `odoo/db/README.md`, `odoo/http/README.md` | kept in step with the package by hand |

Two rules over all of the above: a new module must appear in the **Subsystem
map** in [`module.md`](module.md) if its package's contents are enumerated
there, and a new number must say when it was measured.
