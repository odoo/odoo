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
