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

---

## Chapter 10 — Constraints

**Concept.** Two ways to enforce data validity: a **SQL constraint**
(`models.Constraint`) — a database-level `CHECK`/`UNIQUE` rule, fast and
airtight but limited to what SQL can express; and a **Python constraint**
(`@api.constrains(...)` + raising `ValidationError`) — runs in Python after a
create/write, can express arbitrary business logic, but only what the ORM
enforces (not raw SQL/other DB clients).

**Why?** Some rules are naturally set-based ("no two vehicles share a plate" —
a `UNIQUE` index is the correct, race-condition-proof tool). Others need real
logic ("a model year has to be plausible") that SQL alone can't express cleanly
— that's what `@api.constrains` is for.

**Where?** [`models/fleet_vehicle.py`](models/fleet_vehicle.py) —
`_license_plate_unique`, `_check_model_year`, `_check_seats`

**Code explanation.** `_license_plate_unique = models.Constraint('unique(license_plate)', "...")`
is Odoo 20's declarative replacement for the old `_sql_constraints` list of
tuples — same idea (an actual PostgreSQL `UNIQUE` constraint on the table), new
syntax. `@api.constrains('model_year')` re-runs `_check_model_year` every time
`model_year` is written; it raises `ValidationError` (which the ORM turns into
a rollback + a user-facing error) for anything before 1980 or more than a year
in the future. `_check_seats` rejects zero/negative seat counts the same way.

**Fleet functionality.** The fleet's data is now self-protecting: duplicate
license plates, implausible model years, and zero-seat vehicles are all
rejected at the source instead of silently corrupting reports later.

**What changed.** Updated `models/fleet_vehicle.py` with the constraint and two
`@api.constrains` methods.

**Testing.** Upgrade the module. In the shell, inside savepoints: creating a
second vehicle with an already-used `license_plate` raises `UniqueViolation`
(SQL); creating one with `model_year=1900` or `seats=0` raises
`ValidationError` (Python) — all three verified. In the UI, try the same from
the vehicle form and see the corresponding error dialog.

---

## Chapter 11 — Add The Sprinkles

**Concept.** Small view features that make an app feel finished rather than
functional-but-raw: a **kanban** board view for a visual, drag-friendly
overview; a **ribbon widget** for an at-a-glance record status; **decorations**
(conditional colors/badges) so state is readable without opening a record.

**Why?** A list of rows is fine for data entry; a kanban board grouped by
status is how a fleet coordinator actually wants to *see* the fleet at a
glance. Ribbons and decorations move state from "a column you have to read" to
"a color you notice."

**Where?** [`views/fleet_vehicle_views.xml`](views/fleet_vehicle_views.xml) —
kanban view, form ribbons; [`views/fleet_vehicle_menus.xml`](views/fleet_vehicle_menus.xml) — `view_mode`

**Code explanation.** The kanban view's `default_group_by="state"` makes it
open as three columns (Available / Assigned / In Maintenance) out of the box.
Its card template (`<t t-name="card">`, Odoo 20's kanban card slot) shows a
`web_ribbon` widget that only becomes `visible` when `state == 'maintenance'`,
the driver as an avatar + name, and the same colored tag pills as the form.
The form gained its own `web_ribbon` for `invisible="active"` — the classic
"Archived" banner pattern, needing `active` pulled into the view as an
`invisible="1"` field so the ribbon's condition can read it without displaying
it as a normal field.

**Fleet functionality.** Fleet Training > Vehicles now opens on a kanban board
grouped by status; an archived vehicle's form clearly shows an "Archived"
ribbon instead of just being harder to find.

**What changed.** Added the kanban view and both ribbons in
`views/fleet_vehicle_views.xml`; `view_mode` on the action now starts with
`kanban`.

**Testing.** Upgrade the module. In the UI: open Vehicles, confirm it opens on
a kanban grouped by status, with a vehicle in Maintenance showing the ribbon;
archive a vehicle and open its form to see the "Archived" ribbon. Verified via
shell that both the kanban and form `arch` parse and render for an
active-test-disabled (archived) record.

---

## Chapter 12 — Inheritance

**Concept.** `_inherit = 'existing.model'` (with no `_name`) **extends** an
existing model in place — adding fields/methods to it, visible everywhere that
model is already used — as opposed to `_inherit` *and* a new `_name` (extension
+ new model that copies the parent) or `_inherits` (delegation: "has-a" that
behaves like "is-a" via automatic field proxying). This chapter uses classical
extension, on a model this module doesn't own.

**Why?** Odoo apps are meant to compose: `fleet_training` didn't write
`res.partner`, but it can still teach that model something new (how many fleet
drivers are linked to a contact) without forking or copy-pasting it — every
other app that touches `res.partner` still works unchanged.

**Where?**
- [`models/res_partner.py`](models/res_partner.py) — `_inherit = 'res.partner'`
- [`models/fleet_driver.py`](models/fleet_driver.py) — `partner_id`, the link this extension counts through

**Code explanation.** `fleet_training.driver` gets an optional `partner_id`
Many2one to `res.partner` (a driver may also be a company contact).
`ResPartner._inherit = 'res.partner'` then adds `fleet_training_driver_count`,
computed by grouping `fleet_training.driver` by `partner_id` — a cross-model
count with no stored relation on the partner side, so (following core's own
convention for this exact pattern, e.g. CRM's `opportunity_count` on
`res.partner`) it's deliberately **not** `store=True` and has no
`@api.depends`: cheap to compute fresh, no need to keep a synced column.

**A security trap this pattern walks straight into, and how the code avoids
it.** This field renders on *every* `res.partner` form in the system — not
just partners linked to a driver. If the compute read `fleet_training.driver`
unconditionally, a user with no Fleet Training access at all would get an
`AccessError` the moment they opened *any* contact, anywhere, because Odoo
computes every field declared in a view's arch, regardless of whether it ends
up visible. That's exactly the trap: extending `res.partner` means your code
now runs for every user of every app that touches contacts, not just your own
app's users. The fix is the first two lines of the method: default the count
to `0` and return immediately for anyone outside `group_fleet_user`, mirroring
the same defensive check CRM's own `opportunity_count` uses. **The lesson:** a
field added to a shared model can silently expose (or, as here, silently
break access to) another model — always ask "who else renders this view, and
do they have rights to what I'm computing?"

**A second, subtler trap: caching across users.** Odoo's field cache lives at
the transaction level, not per-user — so once *any* user's read computes and
caches this field's value for a given partner, the ORM assumes that value is
valid for everyone, and won't recompute it just because a different user asks
next. Since this compute's result genuinely depends on `self.env.user` (via
`has_group`), that stale value would leak across users: a plain employee
reading `0` first would make a real Fleet Manager see `0` too, right after,
for the same partner. `@api.depends_context('uid')` is what tells the ORM
"this value depends on who's asking" — without it, any field whose logic
branches on the current user needs this decorator, or it will silently share
one user's answer with everyone else.

**Fleet functionality.** A driver can now optionally be linked to a full
contact record; the underlying mechanism is in place for a future "Fleet
Drivers" smart button on the Contacts app (Chapter 13 wires up the view side).

**What changed.** Added `models/res_partner.py`; updated `models/fleet_driver.py`
(`partner_id`), `models/__init__.py`, `views/fleet_driver_views.xml`.

**Testing.** Upgrade the module. In the shell: create a `res.partner`, create
a driver with `partner_id` set to it, and confirm (as a Fleet user)
`partner.fleet_training_driver_count == 1`. Then confirm the safety guard: as
a plain internal user with no Fleet Training group, reading that same field on
*any* partner returns `0` with no error — never an `AccessError`.

---

## Chapter 13 — Interact With Other Modules

**Concept.** A module can depend on and build on another app's models and
views, not just `base`. `depends: ['base', 'mail']` pulls in Odoo's messaging
framework; inheriting `mail.thread`/`mail.activity.mixin` gets a model a
**chatter** (message log, followers, activities) for free; extending another
app's model *and* its view (Chapter 12's `res.partner` model extension, now
paired with a view extension) is how two independently-developed modules
compose into one coherent experience.

**Why?** A fleet app that can't show *why* a vehicle's status changed, or let
someone leave a note on a specific vehicle, is missing basic auditability.
Rather than build messaging/activities from scratch, `fleet_training` reuses
`mail` — exactly what real Odoo apps do.

**Where?**
- [`__manifest__.py`](__manifest__.py) — `depends: ['base', 'mail']`
- [`models/fleet_vehicle.py`](models/fleet_vehicle.py) — `_inherit = ['mail.thread', 'mail.activity.mixin']`, `tracking=True` on `state`/`driver_id`
- [`views/fleet_vehicle_views.xml`](views/fleet_vehicle_views.xml) — `<chatter/>`
- [`views/res_partner_views.xml`](views/res_partner_views.xml) — smart button, via `inherit_id="base.view_partner_form"`

**Code explanation.** `_inherit = ['mail.thread', 'mail.activity.mixin']`
alongside the model's own `_name` is *both* mechanisms from Chapter 12 at
once: it extends this module's own model with capabilities defined in another
module. `tracking=True` on a field makes every value change auto-logged in the
chatter as soon as the change is committed. `<chatter reload_on_post="True"/>`
is Odoo 20's one-line replacement for the old hand-built `oe_chatter` div. The
`res.partner` form gets a new smart button via `inherit_id` + an `xpath`-free
`position="inside"` on the existing `button_box` — the same view-inheritance
idea used for models, applied to XML. Its `icon="directions_car"` uses Odoo
20's Material Symbols icon set (a plain name, no CSS class) — the same icon
name core's own `fleet` module uses for its equivalent smart button; the old
FontAwesome `class="fa fa-car"` style is deprecated in 20.0 and flagged by
`test_lint`.

**Fleet functionality.** Every vehicle now has a full activity/message log;
changing its status or reassigning its driver is automatically recorded with
who/when/old→new value; the Contacts app can jump straight from a contact to
their linked fleet drivers via a new smart button.

**What changed.** Manifest depends on `mail`; `models/fleet_vehicle.py`
(mixin + `tracking=True`); `views/fleet_vehicle_views.xml` (`<chatter/>`);
added `views/res_partner_views.xml`.

**Testing.** Upgrade the module (a much larger dependency graph installs -
`mail` and everything it needs - verified clean). In the shell: create a
vehicle, **commit**, then write a new `state` - a tracking message with the
old→new value appears in `message_ids` (tracking only fires across a
transaction boundary, not within the same transaction as the record's own
creation - by design, to avoid a noisy "created, then immediately changed"
double-log). In the UI: change a vehicle's status and see it logged in the
chatter; open a driver's linked contact and click the new "Fleet Drivers"
smart button.

---

## Chapter 14 — A Brief History Of QWeb

**Concept.** **QWeb** is Odoo's XML templating engine — the same engine that
renders every web client view under the hood also renders **reports**: a
`<template>` with `t-*` directives (`t-foreach`, `t-if`, `t-field`, `t-call`)
that gets turned into HTML, and for PDF reports, piped through wkhtmltopdf.
An `ir.actions.report` record connects a template to a model and (via
`binding_model_id`/`binding_type="report"`) to that model's Print menu — the
same binding mechanism Chapter 9's server action used.

**Why?** Business documents (an info sheet, an invoice, a delivery slip) need
to be printable, and printing "the same data the form shows" from a second,
hand-maintained system would drift out of sync. Reusing QWeb means the report
is just another view of the same records, with the same `t-field`
formatting Odoo already uses everywhere else.

**Where?** [`reports/fleet_vehicle_report.xml`](reports/fleet_vehicle_report.xml)

**Code explanation.** Two templates, layered the way core reports do it:
`report_vehicle_info` wraps `web.html_container` around a `t-foreach="docs"`
loop (`docs` is the recordset the action was triggered on) and calls
`report_vehicle_info_document` once per vehicle; that inner template calls
`web.external_layout` (Odoo's standard header/footer/company-info frame) around
a plain info table using `t-field` for each value (so dates, selections, etc.
get formatted the same way the UI would show them). The `ir.actions.report`'s
`report_name` points at the *outer* template by its full XML ID.

**Fleet functionality.** Every vehicle can now be printed/downloaded as a PDF
"Vehicle Info Sheet" — identification, specs, status, driver and notes — from
the form's Print menu or in bulk from the list.

**What changed.** Added `reports/fleet_vehicle_report.xml`; manifest loads it.

**Testing.** Upgrade the module. In the shell:
`env.ref('fleet_training.action_report_fleet_vehicle_info')._render_qweb_pdf('fleet_training.report_vehicle_info', vehicle.ids)`
- confirmed it returns real PDF bytes (wkhtmltopdf is installed in this
environment). In the UI: open a vehicle, Print > Vehicle Info Sheet, confirm
the PDF downloads with the right data.

---

## Chapter 15 — The Final Word

**Concept.** This closes the official Server Framework 101 roadmap. Its own
"final word" is mostly conceptual (recap + pointers to Backend Framework 102,
JS framework, and testing) — so this chapter pairs that wrap-up with one more
genuinely useful, low-effort view type: **pivot** and **graph** views, built
from fields already defined in earlier chapters, to turn the vehicle list into
an actual fleet dashboard.

**Why?** Everything from Chapter 1 to 14 - models, security, views,
relations, computed fields, actions, constraints, inheritance, mail, reports -
is the complete toolkit for a real Odoo app. Pivot/graph views cost almost
nothing once the underlying fields exist, and they're what turns "a list of
vehicles" into "an overview a fleet manager actually wants to look at."

**Where?** [`views/fleet_vehicle_analysis_views.xml`](views/fleet_vehicle_analysis_views.xml)

**Code explanation.** The pivot view groups vehicles by `category_id` (rows)
and `state` (columns), measuring `seats` and `age_years` — both fields already
existed (Chapters 3 and 8). The graph view charts the same two dimensions as a
bar chart. Neither needed a single new field or method.

**Fleet functionality.** Fleet Training > Reporting > Fleet Analysis gives a
pivot table and bar chart of the fleet by category and status - a genuine
"dashboard" view, assembled entirely from Chapters already covered.

**What changed.** Added `views/fleet_vehicle_analysis_views.xml`.

**Testing.** Upgrade the module; open Reporting > Fleet Analysis and confirm
the pivot table and bar chart render with real data.

**Where the core tutorial ends, this project keeps going** — the chapters
below aren't in Server Framework 101, but were explicitly asked for to make
this a genuinely usable app: more models (maintenance/fuel), a wizard
(TransientModel), and a scheduled action (`ir.cron`).

---

## Chapter 16 — Maintenance Records (beyond the tutorial)

**Concept.** Applying everything from Chapters 3–15 to grow the app with a new
child model: `fleet_training.maintenance`, a One2many child of vehicle (same
Many2one/One2many pairing as driver in Chapter 7), with its own constraint
(Chapter 10's pattern) and a smart button + computed totals on the parent
(Chapter 9/12's patterns).

**Why?** A fleet app without a maintenance history isn't a fleet app - this is
the first "beyond the tutorial" chapter, proving the concepts already taught
are enough to keep building real features without learning anything new.

**Where?**
- [`models/fleet_maintenance.py`](models/fleet_maintenance.py)
- [`models/fleet_vehicle.py`](models/fleet_vehicle.py) — `maintenance_ids`, `maintenance_count`, `maintenance_cost_total`, `action_view_maintenance`
- [`views/fleet_maintenance_views.xml`](views/fleet_maintenance_views.xml), [`views/fleet_vehicle_views.xml`](views/fleet_vehicle_views.xml)

**Code explanation.** `fleet_training.maintenance` records a date, type
(service/repair/tires/other), odometer reading, cost (a `Monetary` field,
which needs a paired `currency_id` field to know how to format/round) and free
text. `maintenance_cost_total` and `maintenance_count` are computed together
in one method (both derive from the same `maintenance_ids.cost` dependency, so
one pass over the records is enough). The vehicle form's new smart button
opens the maintenance records already filtered to that vehicle, the same
"button that opens a filtered list" pattern as Chapter 13's partner button.

**Fleet functionality.** Every vehicle can now log maintenance history with
cost tracking; the form shows a running total and count via a smart button;
there's also a standalone Maintenance menu for browsing/filtering all records
fleet-wide.

**What changed.** Added `models/fleet_maintenance.py`,
`views/fleet_maintenance_views.xml`; updated `models/fleet_vehicle.py`,
`models/__init__.py`, `views/fleet_vehicle_views.xml`,
`security/ir.access.csv`.

**Testing.** Upgrade the module. In the shell: create a vehicle, add two
maintenance records with costs 1500/2500, confirm `maintenance_count == 2` and
`maintenance_cost_total == 4000.0`; confirm the smart button's domain filters
to that vehicle; confirm a negative `odometer` raises `ValidationError`.

---

## Chapter 17 — Wizards (`TransientModel`, beyond the tutorial)

**Concept.** A **wizard** is a model declared with `models.TransientModel`
instead of `models.Model`: its records live in a table that Odoo periodically
garbage-collects (they're a multi-step *interaction*, not permanent business
data). Opened with `target="new"` on its action, it renders as a dialog.

**Why?** "Send to Maintenance" (Chapter 9) is a one-click status flip with no
extra data. Logging a *real* maintenance event needs several fields at once
(type, cost, odometer, notes) collected together and applied as one atomic
action - exactly the shape a wizard is for, as opposed to either a bare button
(too little data) or a whole new permanent record type just for user input.

**Where?**
- [`wizard/fleet_maintenance_wizard.py`](wizard/fleet_maintenance_wizard.py)
- [`wizard/fleet_maintenance_wizard_views.xml`](wizard/fleet_maintenance_wizard_views.xml)
- [`views/fleet_vehicle_views.xml`](views/fleet_vehicle_views.xml) — the header button that opens it

**Code explanation.** `fleet_training.maintenance.wizard` mirrors the fields
of `fleet_training.maintenance` but adds nothing to the database that
survives past the interaction - its `action_confirm` method is what actually
`create()`s the permanent `fleet_training.maintenance` record and calls
`action_set_maintenance()` on the vehicle, then returns
`{'type': 'ir.actions.act_window_close'}` to close the dialog. The header
button uses `%(action_fleet_training_maintenance_wizard)d` (XML ID resolved to
a numeric action ID at view-load time) with `type="action"` and
`context="{'default_vehicle_id': id}"` so the wizard opens pre-filled with the
vehicle being viewed.

**Fleet functionality.** "Log Maintenance..." on a vehicle's header opens a
dialog to record a full maintenance event (type, odometer, cost, notes) in one
step, automatically flipping the vehicle to "In Maintenance" - a proper
workflow next to the earlier bare status-only buttons.

**What changed.** Added `wizard/fleet_maintenance_wizard.py`,
`wizard/fleet_maintenance_wizard_views.xml`, `wizard/__init__.py`; updated
`__init__.py`, `views/fleet_vehicle_views.xml`, `security/ir.access.csv`.

**Testing.** Upgrade the module. In the shell: create a wizard record with
`vehicle_id`, `cost=999`, `odometer=12345`, call `action_confirm()`, confirm
it returns `ir.actions.act_window_close`, the vehicle's `state` became
`'maintenance'`, and a matching `fleet_training.maintenance` record now exists
under `vehicle.maintenance_ids`. In the UI: click "Log Maintenance..." on a
vehicle form and confirm the dialog opens pre-filled with that vehicle.

---

## Chapter 18 — Scheduled Actions (`ir.cron`, beyond the tutorial)

**Concept.** An `ir.cron` record runs a model method on a fixed schedule with
no user involved - `state="code"` plus a `code` field (here,
`model._cron_check_insurance_expiry()`) that the scheduler executes as
`base.user_root` at the configured interval.

**Why?** "Insurance is expiring soon" is not something a user should have to
remember to go check - a document/reminder feature like this only works if
something runs in the background and surfaces it proactively.

**Where?**
- [`models/fleet_vehicle.py`](models/fleet_vehicle.py) — `insurance_expiry_date`, `_cron_check_insurance_expiry`
- [`data/ir_cron_data.xml`](data/ir_cron_data.xml)

**Code explanation.** `_cron_check_insurance_expiry` is an `@api.model`
method (it doesn't act on `self` as a recordset, it searches for the relevant
vehicles itself) that finds vehicles whose `insurance_expiry_date` is within
30 days, and calls `activity_schedule` (from `mail.activity.mixin`, Chapter
13) to create a "To-Do" activity - reusing Chapter 13's mixin instead of
inventing a new notification mechanism. It first checks for an existing
identical activity so re-running the cron daily doesn't create duplicates.

**Fleet functionality.** Vehicles with an insurance expiry date within 30 days
now automatically get a "Renew vehicle insurance" to-do activity, checked once
a day.

**What changed.** Updated `models/fleet_vehicle.py` (field + cron method,
`views/fleet_vehicle_views.xml`); added `data/ir_cron_data.xml`.

**Testing.** Upgrade the module. In the shell: create one vehicle expiring in
10 days and one in 90 days, run `_cron_check_insurance_expiry()`, confirm only
the 10-day vehicle gets an activity; run it again and confirm the count stays
at 1 (no duplicate). In the UI: Settings > Technical > Automation > Scheduled
Actions shows "Fleet Training: Insurance Expiry Reminder" and can be triggered
manually.

---

## Chapter 19 — Demo Data & Final Cleanup

**Concept.** The `demo` key in the manifest (as opposed to `data`) loads
sample records only when a database is created *with* demo data - it's
sandboxed from `data`, which always loads, so uninstalling/reinstalling never
depends on throwaway sample content being present.

**Why?** A training session needs the app to look alive the moment it's
installed, not empty. Realistic data also makes every earlier chapter's
feature demonstrable immediately (a vehicle already "In Maintenance" to show
the ribbon, one already assigned to show the driver relation, one with
insurance expiring soon to trigger the cron on demand).

**Where?** [`demo/fleet_training_demo.xml`](demo/fleet_training_demo.xml)

**Code explanation.** 3 categories, 2 tags, 3 drivers and 4 vehicles (Tata
Nexon, Mahindra XUV700, Hyundai Creta, Toyota Innova Crysta) covering all 3
statuses and different categories, plus 2 maintenance records. Dates use
`eval` with `DateTime`/`relativedelta` (both available in the XML data eval
context) so acquisition/insurance dates stay relative to "today" instead of
going stale. The whole file is wrapped in `noupdate="1"` - standard for demo
data - so users can freely edit or delete these records without a module
upgrade silently reverting them.

**Fleet functionality.** Installing with demo data now gives a fully populated
Fleet Training app: assigned and unassigned vehicles, one in maintenance, one
with insurance expiring in 20 days (ready to demo the cron on demand), driver
assignments, tags, and maintenance history - every feature from Chapters 1–18
has something real to show immediately.

**What changed.** Added `demo/fleet_training_demo.xml`; manifest `demo` key.

**Testing.** Fresh install with `--without-demo=False`: confirmed no errors;
in the shell, confirmed all 4 vehicles, 3 drivers (each with
`vehicle_count == 1`), categories/tags resolve correctly, and running
`_cron_check_insurance_expiry()` schedules exactly one activity (on the
Nexon, which expires in 20 days).

---

This closes the module: **15 chapters map directly to Server Framework 101**,
plus **4 chapters that grow it into a genuinely usable application**
(maintenance records, a wizard, a scheduled action, and demo data). See the
concept-to-code table and suggested live-demo flow below.
