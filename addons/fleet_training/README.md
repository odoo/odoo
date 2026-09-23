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

---

## Chapter 5 — Finally, Some UI To Play With

**Concept.** A **window action** (`ir.actions.act_window`) tells the web client
*what* to display (a model, in which view modes); a **menu item**
(`ir.ui.menu` / `<menuitem>`) tells it *where* to put a clickable entry point to
that action. Neither requires a hand-written view yet — Odoo auto-generates a
default list and form from the model's fields if none is defined.

**Why?** This is the fastest way to get from "a model exists" to "I can click
around in it" — useful for prototyping, and it's exactly what happens if a
module never bothers to define custom views at all.

**Where?** [`views/fleet_vehicle_menus.xml`](views/fleet_vehicle_menus.xml)

**Code explanation.** `view_mode = "list,form"` (Odoo 20 renamed the old `tree`
view type to `list` everywhere, including here) means: open on a list, and allow
drilling into a form. The root `<menuitem>` with no `action` and no `parent`
becomes the app's top-level entry (and the app icon on the Apps grid, since the
manifest set `application: True`); the child menu attaches the action to it.
The root menu also declares `groups="fleet_training.group_fleet_user"`
explicitly — Odoo would already hide it from a user with zero access to the
underlying model, but spelling the group out directly on the menu is the
convention core modules use (e.g. the built-in `fleet` app's own root menu),
and it's easier to read straight from the view than to infer from ACL rows.

**Fleet functionality.** The Fleet Training app is now visible and clickable:
Apps > Fleet Training > Vehicles opens an auto-generated list/form where
vehicles can be created and edited through the UI, no code required.

**What changed.** Added `views/fleet_vehicle_menus.xml`; manifest now loads it.

**Testing.** Upgrade the module, refresh the browser, open the Fleet Training
app from the Apps grid, click Vehicles, and create a record from the UI.

---

## Chapter 6 — Basic Views

**Concept.** Views are `ir.ui.view` records whose `arch` is an XML architecture
tree. The three workhorses are **list** (rows/columns), **form** (one record,
laid out with `<sheet>`/`<group>`) and **search** (filters and group-by options
available above a list).

**Why?** Hand-writing the layout lets you show only the relevant fields, group
them logically, and give users fast filters — instead of the raw, unordered
auto-generated view from Chapter 5.

**Where?** [`views/fleet_vehicle_views.xml`](views/fleet_vehicle_views.xml)

**Code explanation.** The list view picks 5 columns instead of every field. The
form view wraps everything in `<sheet>`, puts `name` in the title area (the
common "record name as `<h1>`" pattern), and uses two side-by-side `<group>`
blocks inside an outer `<group>` for a two-column layout. The search view adds
a text-searchable `name`/`license_plate`/`vin_sn`, an `Archived` filter (records
with `active = False` are hidden by default — this is what makes the `active`
field from Chapter 3 actually useful), and a "group by Model Year" filter.

**Odoo 20 note.** The list view's root tag is `<list>`, not the legacy `<tree>` -
consistent with the `view_mode` change in Chapter 5.

**Fleet functionality.** Vehicles now have a proper, readable form and list
layout, and can be searched, archived/unarchived, and grouped by model year.

**What changed.** Added `views/fleet_vehicle_views.xml`; manifest loads it
before the menu file (the action needs the views to exist... actually the
views just need to exist by the time the action is *used*, but loading order
here keeps the module's data files in a natural reading order).

**Testing.** Upgrade the module, open Fleet Training > Vehicles: confirm the
list shows the 5 chosen columns, the form shows the two-column layout, and the
search bar's filter dropdown offers "Archived" and "Model Year" group-by.

---

## Chapter 7 — Relations Between Models

**Concept.** The three relational field types: **Many2one** (this record points
to one record of another model), **One2many** (the reverse side — all records
of another model pointing back here; always paired with a Many2one), and
**Many2many** (both sides can relate to several of each other, via a hidden
join table).

**Why?** Real data is relational. A vehicle has one driver at a time but a
driver may have several vehicles over time (Many2one/One2many pair); a vehicle
can carry several free-form tags and a tag can apply to many vehicles
(Many2many) — no single field type covers both shapes.

**Where?**
- [`models/fleet_driver.py`](models/fleet_driver.py) — new `fleet_training.driver` model
- [`models/fleet_category.py`](models/fleet_category.py) — new `fleet_training.category` and `fleet_training.tag` models
- [`models/fleet_vehicle.py`](models/fleet_vehicle.py) — `driver_id`, `category_id`, `tag_ids`
- [`views/fleet_driver_views.xml`](views/fleet_driver_views.xml), [`views/fleet_category_views.xml`](views/fleet_category_views.xml), [`views/fleet_vehicle_views.xml`](views/fleet_vehicle_views.xml)

**Code explanation.** `vehicle.driver_id = fields.Many2one('fleet_training.driver')`
is the owning side. `driver.vehicle_ids = fields.One2many('fleet_training.vehicle', 'driver_id')`
is purely a UI/ORM convenience — it stores nothing on the driver's table, it is
computed on the fly from the matching `driver_id` column on vehicles (the second
argument is the name of *that* Many2one field). `vehicle.tag_ids = fields.Many2many('fleet_training.tag')`
needs no such pairing — the ORM auto-creates a `fleet_training_vehicle_fleet_training_tag_rel`
join table under the hood.

**Fleet functionality.** Vehicles can now be assigned a driver, classified by
category, and labelled with colored tags; a driver's form shows all vehicles
currently assigned to them in an embedded list; the vehicle search view can
filter "Unassigned" vehicles and group by driver/category.

**What changed.** Added `models/fleet_driver.py`, `models/fleet_category.py`,
`views/fleet_driver_views.xml`, `views/fleet_category_views.xml`; updated
`models/fleet_vehicle.py` (3 new fields), `models/__init__.py`,
`views/fleet_vehicle_views.xml` (list/form/search updated), `security/ir.access.csv`
(rows for the 2 new models).

**Testing.** Upgrade the module; in the UI, create a driver and a category,
then create a vehicle and assign both plus a tag — the tag appears as a colored
pill, and the driver's form now lists that vehicle under "Assigned Vehicles".
Verified the same round-trip via the Odoo shell (`driver.vehicle_ids`,
`vehicle.driver_id`, `vehicle.tag_ids` all resolve correctly).

---

## Chapter 8 — Computed Fields And Onchanges

**Concept.** A **computed field** (`compute=...`, `@api.depends(...)`) derives
its value from other fields in Python instead of being typed in by a user.
An **onchange** (`@api.onchange(...)`) runs client-side, in the form, the
moment a field changes — before saving — to adjust other fields or warn the
user.

**Why?** Some data shouldn't be typed by hand because it's always derivable
(a vehicle's age from its acquisition date) — computing it keeps it correct by
construction. Onchanges give live feedback *while filling the form*, which a
stored computed field alone cannot do (it only reacts on save).

**Where?**
- [`models/fleet_vehicle.py`](models/fleet_vehicle.py) — `age_years` (compute) and `_onchange_driver_id` (onchange)
- [`models/fleet_driver.py`](models/fleet_driver.py) — `vehicle_count` (compute)

**Code explanation.** `age_years` is `store=True`: it is written to the
database column and kept in sync automatically whenever `acquisition_date`
changes (declared via `@api.depends`), which also makes it sortable/groupable
in views and searches. `vehicle_count` on the driver is **not** stored — it's
cheap to compute from the already-loaded `vehicle_ids` and rarely needs to be
searched on, so recomputing on read is simpler and avoids an extra DB column.
`_onchange_driver_id` returns a `{'warning': {...}}` dict, which the web client
turns into a dialog the moment a driver without a phone number is picked —
purely advisory, it does not block saving.

**Fleet functionality.** The vehicle list/form now shows a live "Fleet Age"
column; a driver's list shows how many vehicles they currently have; assigning
a driver with no phone on file now visibly warns the user in the form.

**What changed.** Updated `models/fleet_vehicle.py` (`age_years`,
`_onchange_driver_id`), `models/fleet_driver.py` (`vehicle_count`),
`views/fleet_vehicle_views.xml`, `views/fleet_driver_views.xml`.

**Testing.** Upgrade the module. In the shell: create a vehicle with
`acquisition_date='2018-01-01'` and confirm `age_years` computes to the correct
number of years; set its `driver_id` to a driver with no phone and call
`_onchange_driver_id()` — confirm it returns the warning dict. In the UI: pick
a driver with no phone on a vehicle form and see the warning dialog appear.

---

## Chapter 9 — Ready For Some Action?

**Concept.** A **button** in a view with `type="object"` calls a plain Python
method on the model (`name="method_name"`) when clicked, passing the current
record(s) as `self`. A **server action** (`ir.actions.server`) is the same
idea, but launched from the list view's Action (gear) menu on a selection of
records instead of from a single record's form, via `binding_model_id`.

**Why?** Not every operation should be a raw field edit — "send this vehicle to
maintenance" is a business action with a name and a single place to add
side-effects later (chapter 13 will make it also log to the chatter). Buttons
and server actions are how Odoo exposes such actions to users, on one record or
on a bulk selection, without writing any JavaScript.

**Where?**
- [`models/fleet_vehicle.py`](models/fleet_vehicle.py) — `state` field, `action_set_maintenance`, `action_set_available`
- [`views/fleet_vehicle_views.xml`](views/fleet_vehicle_views.xml) — header buttons + statusbar, badge/filter/group-by for `state`
- [`views/fleet_vehicle_menus.xml`](views/fleet_vehicle_menus.xml) — the bulk server action

**Code explanation.** `state` is a `Selection` field with a `statusbar` widget
in the form header, driven entirely by two plain methods that just reassign
`self.state`. `invisible="state == 'maintenance'"` on a button is a view-level
condition (no Python involved) that hides "Send to Maintenance" once already
there. The `ir.actions.server` record has `state = "code"` and a one-line
`code` field: `records` is a magic variable bound to the selected recordset
when the action runs from a list view.

**Fleet functionality.** Every vehicle now has a status (Available / Assigned /
In Maintenance) shown as a colored badge in the list and a statusbar in the
form; a single vehicle can be sent to/back from maintenance via header
buttons, and several vehicles at once via "Send to Maintenance" in the list's
Action menu. The search view can filter "In Maintenance" and group by status.

**What changed.** Updated `models/fleet_vehicle.py` (`state`,
`action_set_maintenance`, `action_set_available`); updated
`views/fleet_vehicle_views.xml` (header, badge, filter, group-by); updated
`views/fleet_vehicle_menus.xml` (server action).

**Testing.** Upgrade the module. In the shell: create a vehicle, call
`action_set_maintenance()` and confirm `state` changes; run the server action
via `env.ref('fleet_training.action_fleet_training_vehicle_send_maintenance').with_context(active_model=..., active_ids=[...]).run()`
and confirm the same. In the UI: open a vehicle, click the header buttons, and
from the Vehicles list select several rows and use Action > Send to
Maintenance.
