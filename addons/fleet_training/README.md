# Fleet Training

A **Fleet Management** application for Odoo 20.0, built **chapter by chapter** as a
hands-on companion to the official [Server Framework 101](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101.html)
tutorial.

Each chapter below corresponds to one concept from the tutorial, one git commit, and
one working increment of the Fleet Management app. Read this file top to bottom during
the training session: it doubles as the course notes and as the module's own README.

> Note: Odoo ships a built-in `fleet` app (`fleet.vehicle`, ...). This module is
> intentionally independent of it (`fleet_training.*` models) so the training can
> freely evolve the schema without touching a production app.

---

## Chapter 1 — Architecture Overview

**Concept.** Before writing code, understand the shape of an Odoo installation: a
Python **server** (the ORM, business logic, web controllers) talks to a single
**PostgreSQL database per instance**, and renders a **web client** (owned by the
`web` module) that is entirely driven by data describing UI (views, actions, menus)
stored in that same database. Business features are packaged as **modules**
("addons"): self-contained folders with a manifest, Python models, XML data, and
security rules, discovered on the server's `addons_path`.

**Why?** This client/server/DB split, plus "UI is data", is what lets us build an
entire application declaratively — a view is a database record, not a compiled
template — and what lets one module extend another module's models and views
without touching that module's source.

**Where?** Nothing to run yet — this is the mental model for every chapter that
follows.

**Fleet functionality.** None yet — this chapter sets up *why* the rest of the
module is organized the way it is.

**What changed.** `README.md` only.

**Testing.** N/A.

---

## Chapter 2 — A New Application

**Concept.** An Odoo module is a folder with a `__manifest__.py` (its identity card:
name, version, dependencies, which data files to load) and an `__init__.py` (the
Python package entry point). `'application': True` tells Odoo this module is a
top-level app, not just a technical extension.

**Why?** The manifest is how Odoo's module loader knows what a module needs
(`depends`), what to load and in what order (`data`), and how to present it in the
Apps list — all without hardcoding anything in the core.

**Where?**
- [`__manifest__.py`](__manifest__.py)
- [`__init__.py`](__init__.py)

**Code explanation.** `depends: ['base']` means this module only needs Odoo's core
(`res.partner`, `res.users`, security, ...). `data: []` is empty for now — there is
no model, view or security file yet, so there is nothing to load. The manifest
doesn't set `installable` at all — it already defaults to `True`; setting it
explicitly is a no-op that Odoo's own manifest linter flags as noise.

**Fleet functionality.** None yet — an empty, installable shell.

**What changed.** Added `__manifest__.py`, `__init__.py`.

**Testing.** Update the apps list and install: the module installs cleanly with no
errors (it declares nothing yet, so there is nothing to see in the UI — that's
expected, and exactly what Chapter 5 fixes).
```
./odoo-bin -d fleet_training_demo -i fleet_training --addons-path=addons,odoo/addons --stop-after-init
```

---

## Chapter 3 — Models And Basic Fields

**Concept.** A model is a Python class inheriting `models.Model`, declaring `_name`
(its unique technical identifier) and `_description` (its human label). Fields are
class attributes (`fields.Char`, `fields.Integer`, `fields.Date`, `fields.Boolean`,
`fields.Text`, ...); the ORM turns them into a PostgreSQL table and columns
automatically the moment the module is installed/upgraded.

**Why?** This is Odoo's core promise: describe *what* data looks like in Python,
and the framework generates the schema, the CRUD methods, and (later) the UI - no
hand-written SQL migrations for a simple field addition.

**Where?**
- [`models/fleet_vehicle.py`](models/fleet_vehicle.py) — the `fleet_training.vehicle` model
- [`models/__init__.py`](models/__init__.py), [`__init__.py`](__init__.py) — wiring so the model is actually imported
- [`security/ir.access.csv`](security/ir.access.csv) — access so the model can be used at all

**Code explanation.** `fleet_training.vehicle` uses a dotted `_name` (Odoo
convention: `<module>.<model>`) so it can never collide with core Odoo's own
`fleet.vehicle` model — this training app deliberately stays independent of the
built-in Fleet app. `name` is `required=True` because every record needs an
identifier; `active` (default `True`) is a magic field name the ORM automatically
uses to support archiving records instead of deleting them.

**Odoo 20 note.** Access control changed in 20.0: the old `ir.model.access.csv` /
`ir.model.access` model is gone, replaced by a single unified `ir.access` model
(file `ir.access.csv`). A row with a `group_id` is a **permission** (who may do
what); a row with no group but a `domain` is a **restriction** (what records
apply, regardless of group) — the very mechanism that used to be the separate
`ir.rule`. Chapter 4 uses this to show both sides of the same model.

**Fleet functionality.** A vehicle can now be created, read, updated, deleted (via
the ORM/shell — there is still no menu, Chapter 5 adds that) with a name, plate,
chassis number, color, model year, seat count, acquisition date and notes.

**What changed.** Added `models/fleet_vehicle.py`, `models/__init__.py`; updated
`__init__.py` to import `models`; added `security/ir.access.csv`; manifest now
loads that access file.

**Testing.** Upgrade the module, then use the Odoo shell to prove the model works
end-to-end:
```
./odoo-bin shell -d fleet_training_demo --addons-path=addons,odoo/addons --no-http
>>> env['fleet_training.vehicle'].create({'name': 'Fleet-001', 'license_plate': 'KA01AB1234', 'model_year': 2022})
```

---

## Chapter 4 — Security: A Brief Introduction

**Concept.** Odoo restricts *who* can do *what* through **groups**
(`res.groups`) and **access records**. A user's rights are the union of the
groups they belong to; every group grants operations on models via `ir.access`
rows that reference it.

**Why?** Data access has to be declarative and additive, not scattered `if
user.is_admin` checks in code — a new group can grant more without touching a
single line of business logic, and the same model can serve read-only users and
full managers from the same codebase.

**Where?**
- [`security/fleet_training_groups.xml`](security/fleet_training_groups.xml) — the `Fleet User` / `Fleet Manager` groups
- [`security/ir.access.csv`](security/ir.access.csv) — which group can do what on `fleet_training.vehicle`

**Code explanation.** `Fleet User` implies `base.group_user` (an internal
employee) and gets `cru` (create, read, update — no delete). `Fleet Manager`
implies `Fleet User` (so a manager automatically has everything a user has) and
gets `crud` (full control, including delete). Both groups are declared under one
`res.groups.privilege` record — this is the Odoo 20 mechanism that makes them
mutually-exclusive radio choices on a user's form (a user is either a User or a
Manager for this app, not both at once — `implied_ids` is what actually grants
the *combined* rights).

**Odoo 20 note.** `res.groups` no longer has a `category_id` field directly:
grouping/display in the Settings > Users form now goes through
`res.groups.privilege`, which itself points to the `ir.module.category`. This
replaced the older direct `category_id` on the group itself.

**Fleet functionality.** Two roles now exist for the app. A plain `Fleet User`
can register and edit vehicles but not remove them; only a `Fleet Manager` can
delete a vehicle record — protecting fleet history from accidental data loss.
(A domain-based **restriction** — the modern replacement for `ir.rule` — is
introduced later in Chapter 7 once drivers exist, so it can restrict on something
meaningful: a driver seeing only their own assigned vehicle.)

**What changed.** Added `security/fleet_training_groups.xml`; rewrote
`security/ir.access.csv` to grant `cru` to Fleet User and `crud` to Fleet
Manager instead of blanket access; manifest loads the groups file before the
access file (groups must exist before rows can reference them).

**Testing.** Upgrade the module, then in Settings > Users & Companies > Users,
open a test user and confirm "Fleet Training" now shows the User/Manager choice
under Other. As a Fleet User (no Manager), attempting `unlink()` on a vehicle
from the shell raises an `AccessError`; as a Fleet Manager it succeeds.
