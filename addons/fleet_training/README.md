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
