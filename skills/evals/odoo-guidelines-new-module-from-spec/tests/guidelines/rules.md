# The house rules, as the skills state them

===== odoo-guidelines/guidelines/architecture.md =====

# Put code in the module that owns its concern

Every piece of a feature goes in the module whose concern it is. Decide it
before writing code, piece by piece, in this order:

1. **An existing module owns the concern**: extend that module. An
   improvement to invoicing goes in `account`; a new option of operation types
   goes in `stock`.
2. **No module owns it, and other apps may use it**: create a module for it,
   depending only on what the capability itself needs (`base`, `mail`, `web`).
   A reusable capability, such as printing reports, tagging records or
   reaching a device, is its own module, never part of one business app.
3. **It connects two apps**: put it in a **bridge**. Use the existing module
   that already depends on both when there is one; otherwise create
   `<app>_<app>`, depending on both, with `auto_install` on them, so it is
   installed exactly when both apps are.

```
# a library app gets reservations and a reusable "notify by SMS" capability

library/                  # owns books and loans: reservations go here (1)
sms_notify/               # reusable, depends on base and sms only (2)
library_sms_notify/       # notifies borrowers by SMS: bridge, auto_install (3)

# bad: the reusable capability inside the app, so any other app that wants
# SMS notifications must install the library
library/models/sms_notify.py
```

## Why

- A module's `depends` is its install footprint: a capability placed in a
  business app drags that app into every database that wants the capability.
- Bridges keep apps independent: each installs alone, and the code connecting
  them is installed only where both are, without a feature flag.
- Ownership tells the next developer where to look, and keeps one module per
  concern to review, upgrade, and override.

## Exceptions

- A module combining two apps that is a feature in its own right, one a
  customer chooses to install (an online shop on top of the website and
  sales), sets no `auto_install`: it is installed on purpose, not whenever
  both apps are.
- An existing module may depend directly on a small capability module that
  itself depends on nothing heavy, instead of going through a bridge, when
  installing it everywhere that module is installed costs nothing.
- A capability that belongs to the framework itself (every model, every view)
  goes in `base` or `web`, the modules that own the framework.
- On a released version, new modules are not added (localizations aside):
  follow the `odoo-stable-policy` skill.

===== odoo-guidelines/guidelines/comments.md =====

# Plain ASCII punctuation in comments and messages

Write code comments, docstrings, user-facing strings and commit messages with
ASCII punctuation only. The character that keeps showing up is the em dash
(`—`): replace it with a comma, a colon, a semicolon, parentheses, or two
sentences, whichever the sentence actually needs. Same for the en dash (`–`),
curly quotes (`“ ” ‘ ’`) and the ellipsis character (`…`): write `-`, `"`, `'`
and `...`.

```python
# bad
# recompute the totals — the taxes may have changed
raise UserError(self.env._("Book %s is already borrowed — return it first", book.name))

# good
# recompute the totals: the taxes may have changed
raise UserError(self.env._("Book %s is already borrowed, return it first", book.name))
```

## Why

- The em dash is not on the keyboard layouts the codebase is written with, so
  in practice it arrives by copy-paste or from a generation tool. A diff full
  of them reads as text nobody typed.
- ASCII punctuation is greppable and diffable. A comment or a commit message
  is searched for with what a reviewer can type.
- A translatable literal is keyed on its exact source string, so two variants
  of the same sentence that differ only in the dash are two terms to translate
  (see [Translate only static literals](python.md#translate-only-static-literals)).

## Exceptions

- Data, not prose: a test fixture, a localization file, or a string whose
  content is the character itself.
- Existing text in a stable branch. Fixing punctuation is a cosmetic change,
  and rewording a translatable term breaks its translations (see
  [Changes in a stable version](../../odoo-stable-policy/SKILL.md#changes-in-a-stable-version)).

# Comment a deviation the requirements force

When a requirement makes code break a guideline (the task's spec, a ticket,
a caller that cannot change), the code says so where it happens: a comment at
that spot names the guideline it departs from and the requirement that forces
it. Everywhere else, the guideline applies as written.

```xml
<!-- good: the reader and the reviewer see why, and where the decision comes from -->
<!-- XML ids: keeps its old id rather than library_book_action, because the
     mobile app opens this action by its id and cannot be updated with us. -->
<record id="action_book_list" model="ir.actions.act_window">
```

## Why

- A reviewer applies the guidelines to the code in front of them; without
  the comment, a deviation the requirements asked for reads as a mistake, and
  gets flagged or "fixed".
- The comment ties the deviation to its reason: the day the requirement
  changes, the next developer knows the code can follow the guideline again.

## Exceptions

- Rules that already say how to justify themselves keep their own form: a
  `sudo()` or a commit carries its comment as `odoo-security` and the
  [Transactions and exceptions](orm.md#transactions-and-exceptions) section
  say.

===== odoo-guidelines/guidelines/controllers.md =====

# Controllers

- Routes are methods decorated with `@route` on a `http.Controller` subclass.
  Always re-decorate an **override** with `@route` (an undecorated override
  still works: the framework auto-decorates it and logs a warning). An empty
  `@route()` keeps the parent's arguments and any argument overrides the
  parent's, except `type`, which an override can never change (ignored with
  a warning; loosening `readonly` is likewise reverted).
- Set the right `auth` on each route (`user`, `bearer`, `public`, or `none`):
  a `public` route must not expose internal data or perform privileged writes
  (see the `odoo-security` skill). `auth='bearer'` requires `bearer_scope`
  (which is only valid there).
- Route `type` is `'http'`, `'jsonrpc'`, or `'json2'`; `type='json'` is a
  deprecated 19.0 alias of `'jsonrpc'`.

===== odoo-guidelines/guidelines/fields.md =====

# Fields

- Relational suffixes: `Many2one` → `_id`, `One2many`/`Many2many` → `_ids`.
- `index=True` on fields that are both searched and selective (many distinct
  values). An index on a low-cardinality field (a boolean, a state) is wasted
  space and slows every write. `index` also accepts
  a type (`'btree_not_null'`, `'trigram'` for `like` searches); multi-column or
  custom indexes are model attributes (`_x_idx = models.Index("(a, b)")`,
  `models.UniqueIndex`; the attribute name must start with `_`).
- Restrict sensitive fields with the `groups` attribute (comma-separated external
  ids); restricted fields are dropped from views and `fields_get`, and raise on
  direct read/write.
- Check relational definitions: correct `comodel_name`, sensible `ondelete`,
  `required`, and a currency companion for monetary fields.
- Use **reserved** fields for their built-in behavior rather than reinventing
  them: `active` for archiving (via `action_archive`, not a custom boolean),
  `state` for lifecycle, `parent_id` + `parent_path` (`index=True`, with
  `_parent_store`) for trees, `company_id` for multi-company (consistency via
  `_check_company`). Keep `_log_access` enabled on a `TransientModel`.
- A field and a method can't share a name (same namespace); flag collisions.
- `related` fields can't chain `One2many`/`Many2many` in the dependency path:
  the ORM does not reject it, it *silently truncates each x2many hop to its
  first record* and returns wrong data; reach the target through a `Many2one`
  (ending the chain on an x2many is fine). Reusing one compute for several
  fields is fine; reusing one **inverse** is discouraged: while the inverse
  runs, every field sharing it is protected and reads as `False` when not
  cached, so the method sees wrong sibling values.

===== odoo-guidelines/guidelines/manifest.md =====

# Manifest

- `name` is required; `version` should follow semantic versioning.
- `depends` lists every module whose features or resources are used, direct
  dependencies only. Don't list `base`: a manifest without `depends` gets
  `['base']` injected, and upgrading `base` upgrades every installed module
  whether or not it lists it.
- `data` files are always installed/updated; `demo` files load only in demo
  mode. Keep load order correct (a record's dependencies first).
- `license` defaults to `LGPL-3`; set it deliberately and correctly.
- `auto_install` is only for "link" modules (installed automatically when their
  dependencies are); it can also be a *subset* of `depends` that triggers the
  auto-install (an empty list: always installed).
- `application` is `True` only for full apps, not technical modules.
- Declare non-Odoo requirements in `external_dependencies` (`python`/`bin`).
- `assets` declares how static files load into bundles (don't register assets
  ad-hoc elsewhere).

===== odoo-guidelines/guidelines/module_structure.md =====

# Module structure and file naming

- Standard directories: `models/`, `views/`, `controllers/`, `data/`,
  `security/`, `static/`, and optional `wizard/`, `report/`, `tests/`,
  `populate/`.
- One model class per file, named after the model with dots as underscores
  (`res_partner.py`), whether the class defines a new model or extends an
  existing one with `_inherit`.
- Suffix conventions: backend views `*_views.xml`, portal/QWeb pages
  `*_templates.xml`, menus optional `*_menus.xml`, data `*_data.xml`, demo
  `*_demo.xml`, wizards `<transient>.py` + `<transient>_views.xml`.
- Security files: access rows in `security/ir.access.csv`; groups and other
  security records in `security/<module>_security.xml`.
- Controllers: feature-named files, or `<inherited_module>.py` when extending
  another module's controller (e.g. `portal.py`); `main.py` is legacy (still
  widespread in core).
- Reports: a statistics (SQL-view) report is `<model>_report.py` +
  `<model>_report_views.xml`; a printable report splits `<model>_reports.xml`
  (report actions, paperformat) from `<model>_templates.xml` (QWeb templates).
- `populate/` holds `populate.blueprint` XML records (`populate_demo.xml`,
  `benchmarks.xml`); an `__init__.py` makes it an importable package for
  custom populate generators.
- File and directory names are Python identifiers: lowercase, `[a-z0-9_]`.

===== odoo-guidelines/guidelines/orm.md =====

# Recordsets, domains and context

- Use recordset methods (`filtered`, `grouped`, `mapped`, `sorted`) where they
  read better than a loop.
- Recordsets/collections are booleans: write `if records:` / `if some_list:`,
  not `if len(...)`.
- Don't read a non-relational field on a multi-record set (it raises); iterate
  or `mapped`. Conversely, guard single-record assumptions with `ensure_one()`.
- Combine domains with `odoo.fields.Domain`: the `&`, `|`, `~` operators for
  domains written inline, `Domain.AND`/`Domain.OR` for a list of domains you
  already hold. Never hand-build `'&'`/`'|'` prefix-notation lists.
- Propagate context with `with_context(...)` (it's a frozendict, immutable);
  name custom context keys carefully and prefix module-specific ones (a stray
  `default_<field>` in context leaks into unrelated `create` calls).
- Delegation inheritance (`_inherits`) inherits fields but **not** methods; avoid
  it where you can (chained `_inherits` is unsupported).

# Computes, onchange and constraints

- `create` must accept a list of vals (`@api.model_create_multi`); don't call
  `create` per record in a loop (see [Batch ORM calls](performance.md#batch-orm-calls)).
- `@api.depends` must list **every** field the compute reads; stored computes
  need correct dependencies and no side effects.
- `@api.onchange` is UI-only: never rely on it for data integrity; enforce
  invariants with `@api.constrains` or SQL constraints declared as model
  attributes (`_x_check = models.Constraint("CHECK (...)", "msg")`; the
  attribute name must start with `_`). Indexes are declared the same way
  (`_x_index = models.Index(...)`, `models.UniqueIndex(...)`). Flag
  `_sql_constraints`: on master it is **ignored** with a log warning, the
  constraint is never created.

# Methods and extension points

- Methods are private (`_` prefix) by default. A public name is an RPC entry
  point: make one only when it must be callable from outside, and decorate
  with `@api.private` a public name that must not be exposed.
- Logic that another module actually overrides goes in its own small method
  (`self._get_partner_domain()`); other modules extend methods, not lines.
  Don't pre-split for extension points that don't exist yet.
- Don't use `odoo.http.request` in models: it is absent in crons, RPC, tests
  and the shell. Pass what the model needs in from the controller.

# Transactions and exceptions

- **Never** call `cr.commit()` / `cr.rollback()` unless you opened your own
  cursor; the framework owns the transaction. Any unavoidable commit needs an
  explicit comment justifying it.
- Catch **specific** exceptions over the smallest possible block; let unexpected
  ones propagate to the framework. To recover from framework exceptions, wrap the
  work in `with self.env.cr.savepoint():` (note: >64 savepoints per transaction
  degrades PostgreSQL, so bound batch sizes).

===== odoo-guidelines/guidelines/performance.md =====

# Batch ORM calls

Make **one** ORM call for the whole collection; an ORM call inside a
`for` loop over records or vals is a query per iteration. This covers
`search`, `search_count`, `_read_group` and `create` alike.

```python
# bad: one INSERT round-trip per record
for vals in vals_list:
    self.env['library.book'].create(vals)

# good: one batched create (and decorate overrides with @api.model_create_multi)
self.env['library.book'].create(vals_list)
```

```python
# bad: one aggregate query per author
for author in authors:
    author.book_count = Book.search_count([('author_id', '=', author.id)])

# good: one grouped query, then a dict lookup
counts = {
    author.id: count
    for author, count in Book._read_group(
        [('author_id', 'in', authors.ids)], ['author_id'], ['__count'],
    )
}
for author in authors:
    author.book_count = counts.get(author.id, 0)
```

## Why

- Each call is a full round-trip (Python → SQL → Python); a loop turns O(1)
  queries into O(n) and dominates response time on real data volumes.
- Reading fields batches too: iterate a recordset (or `browse` all ids
  first) and the ORM prefetches each field for the whole set in one query;
  a record-by-record `browse(id)` loop defeats the prefetch.

## Exceptions

- A loop that only computes in memory on already-read fields is fine; the
  rule is about calls that hit the database.
- When a per-record call is truly unavoidable (e.g. an external API per
  record), bound the batch size.

# Performance conventions

- Put conditions in the search domain, not in `filtered()` on the result:
  `filtered` runs in Python on records already fetched. Reserve it for
  predicates a domain cannot express.
- **Reduce complexity.** Pre-map results into a dict (`{r['id']: r}`) instead of
  nested loops; cast membership-test collections to `set` (or use recordset
  arithmetic like `self - invalid`) to avoid O(n²).
- Index searched fields (`index=True`), selectively, per
  [Fields](fields.md#fields).

===== odoo-guidelines/guidelines/python.md =====

# Imports

PEP 8 applies; the `ruff.toml` at the repository root is the reference for what
is enforced.

- Four groups, each alphabetically sorted (the ruff isort order):
  1. stdlib
  2. third-party libs
  3. `odoo` submodules (`from odoo import Command, api, fields, models`)
  4. `odoo.addons.*` (rarely, only if necessary)

# Naming and model layout

- Model `_name`: dotted, prefixed by module, **singular** (`sale.order`, not
  `sale.orders`). Transient/wizard: `<base_model>.<action>` (avoiding the word
  "wizard" is a soft preference; core ships many `.wizard` names). SQL-view report model: `<base_model>.report.<action>`.
- A variable holding a model class is PascalCase (`Partner =
  self.env['res.partner']`). Suffix a var holding a record id / list of ids
  with `_id` / `_ids` (don't name a `res.partner` record `partner_id`).
- Method-name patterns: compute `_compute_<field>`, search `_search_<field>`,
  default `_default_<field>`, selection `_selection_<field>`, onchange
  `_onchange_<field>`, constraint `_check_<name>`, object action `action_*`
  (acts on one record, so start it with `self.ensure_one()`).
- Model body order: private attrs (`_name`, `_description`, `_inherit`) → default
  methods → field declarations → `models.Constraint`/`models.Index` attributes
  (core also places these right after the private attrs) → compute/inverse/search
  (field order) → selection methods → `@api.constrains`/`@api.onchange` → CRUD
  overrides → action methods → other business methods.

# Translate only static literals

Translate only **static literals**, passing interpolation values as
arguments; in model code the current API is `self.env._(...)`.

```python
# good
raise UserError(self.env._("Record %s cannot be modified", record.display_name))

# good (several variables): name them so translators keep them straight
msg = self.env._("%(count)s records imported by %(user)s", count=len(records), user=user.name)

# good: a list argument is formatted per language ("a, b and c")
raise UserError(self.env._("Missing fields: %s", missing_names))

# bad (formats before the lookup): the dynamic string matches no exported term
raise UserError(self.env._("Record %s cannot be modified" % record.display_name))

# bad (formats after the lookup): bypasses placeholder validation and reordering
raise UserError(self.env._("Record %s cannot be modified") % record.display_name)

# bad: manual join ignores the user's language and its list rules
raise UserError(self.env._("Missing fields: %s", ", ".join(missing_names)))
```

## Why

- Translations are keyed on the exact source literal, at export (building the
  `.pot`) and at runtime lookup. Concatenation, f-strings, or `%`-formatting
  inside `_()` produce strings that exist in neither.
- Named placeholders let translators reorder words per language; passing them
  as `_()` arguments lets the framework validate them per translation and
  apply Markup-aware escaping (post-lookup `%` formatting loses that safety).

## Exceptions and notes

- Bare `_` (imported from `odoo`) is the backward-compatible API: it locates
  the environment by inspecting the caller's frame; in plain functions and
  comprehensions it silently returns the untranslated (or wrong-language)
  string with only a logged warning; prefer `self.env._`.
- Never call `_()` at module or class level: it runs at import time with no
  user language and silently doesn't translate. Translate inside the method
  when you can; if a module-level constant is unavoidable, make it lazy
  (`_lt = LazyTranslate(__name__)`; `LABEL = _lt("...")`) and resolve it where
  the language is known, by passing it through `self.env._(LABEL)`.
- Field *values* are translated via the field's `translate` flag, never `_()`.
- Prefer `%`-style placeholders over `.format()`.

===== odoo-guidelines/guidelines/reports.md =====

# QWeb PDF reports

- A custom report's `_get_report_values` must add the default `docs` / `doc_ids`
  / `doc_model` itself if the template needs them; they are not auto-included.
- For translated reports use `t-lang`: it is only valid on a node that also
  carries `t-call` (anywhere else QWeb raises a `SyntaxError` at template
  compile time); to translate part of a report,
  extract that part into its own template and `t-call` it with `t-lang`. Only
  re-browse records in the target language when the template reads
  translatable fields (otherwise it is a needless performance cost).

===== odoo-guidelines/guidelines/security.md =====

# Access rights

Master unifies the old `ir.model.access` ACLs and `ir.rule` record rules into
a single `ir.access` model, declared in `security/ir.access.csv` with columns
`id,name,model_id,group_id/id,operation,domain`.

- `operation` is required: a subset of `crud` letters (`r`, `cru`, `crud`, ...);
  a row applies to exactly the operations it lists. The optional `domain`
  restricts the row to matching records (what record rules used to do).
- Rows **with** a group are *permissions*: OR-ed together (union over the
  user's groups); a row's domain limits only what that row grants. Rows
  **without** a group are *restrictions*: AND-ed onto **every** user; they
  never grant anything, and non-overlapping restrictions can lock everyone
  out.
- Default deny: a model with no permission row is inaccessible. Granting to
  everyone (portal/public included) is done via `base.group_everyone`; flag
  any `c`/`u`/`d` granted to `base.group_everyone`, `base.group_portal`, or
  `base.group_public`.
- Multi-company models need a group-less restriction row with a company
  domain: `"[('company_id', 'in', company_ids)]"` (`company_ids` evaluates to
  the user's allowed companies; append `+ [False]` when the company is
  optional).

For auditing beyond the data files (`sudo()`, SQL, public methods, ...), use the
`odoo-security` skill.

===== odoo-guidelines/guidelines/tests.md =====

# Tests

- Use `TransactionCase` (or `HttpCase` for web); start new business tests from
  `odoo.addons.base.tests.common.BaseCommon` (independent non-admin user and
  company, mail side effects disabled), or
  `TransactionCaseWithUserDemo`/`HttpCaseWithUserDemo` when demo data is
  needed (it is not guaranteed present). Assert behavior, not implementation.
- Tests are tagged `standard` and `post_install` by default (fully-loaded
  registry); set exactly one of `at_install`/`post_install`; the check is
  only a log warning, and *both* tags makes the class run twice while
  *neither* makes it never run. Opt into
  `@tagged('at_install', '-post_install')` only when the test must run before
  other modules load, with a comment justifying it: `at_install` prevents
  runbot parallelization, and an `HttpCase` must stay `post_install`. Tests
  run only for installed modules.
- Silent skips: a test file must be named `test_*.py` **and** imported from
  `tests/__init__.py`; the test class must be *defined* in that file (a class
  merely imported into it is skipped); and inherited `test_*` methods are not
  collected: a subclass defining no tests of its own runs nothing unless it
  sets `allow_inherited_tests_method = True`.
- `assertQueryCount` only when strictly necessary, and never inside a business
  test: it breaks on any unrelated ORM change. Keep it to dedicated
  performance tests, paired with `@warmup` (and `@users`); only *exceeding*
  the budget fails; a lower count merely logs, so keep budgets exact.
- Wrap expected-error and warning logs in `mute_logger(...)` so the expected
  ERROR or WARNING never reaches the runbot log.
- Tours: a step that triggers a page unload must set `expectUnloadPage: true`,
  and the last step must leave the client in a stable state (no pending edits
  or in-flight requests) to avoid teardown race conditions.

===== odoo-guidelines/guidelines/xml.md =====

# Views, actions and data records

- Record format: put `id` before `model`; inside a `field`, `name` first, then
  the value (tag body or `eval`), then other attributes by importance. Group
  records by model.
- Prefer the syntactic-sugar tags `<menuitem>`, `<template>`, and `<asset>`
  over raw `<record>`. Trap: an `active` attribute on `<template>`/`<asset>`
  is applied at record creation and module *install/re-install* (`-i`) only;
  a module **update** (`-u`) updates the arch but never changes `active`, so
  it can't deactivate an already-installed record.
- `<data noupdate="1">` only for non-updatable data; if the whole file is
  noupdate, set `noupdate="1"` on `<odoo>` and drop `<data>`.
- XML id patterns: view `<model>_view_<type>` (`form`/`list`/`kanban`/`search`),
  action `<model>_action[_<detail>]`, window-action view
  `<model>_action_view_<type>`, menu `<model>_menu[_<do_stuff>]`, group
  `<module>_group_<name>`, rule `<model>_rule_<group>`. The record `name` mirrors
  the id with dots instead of underscores; actions get a real display name.
- CSS classes in views and templates: prefix with `o_<module>` (`o_` alone is
  reserved for the web client), never style through ids, and keep names flat
  (`o_element_entry`) rather than mirroring the DOM nesting.
- Inheriting a view: see
  [Anchor view inheritance on names, never on position](#anchor-view-inheritance-on-names-never-on-position).

# Anchor view inheritance on names, never on position

Anchor a view inheritance on a **stable, identifying attribute** (an
element's `name`), never on document position.

```xml
<!-- good: the shorthand form, which matches a field by name alone -->
<field name="partner_id" position="after">
    <field name="delivery_instructions"/>
</field>

<!-- good: xpath when the shorthand can't express the match -->
<xpath expr="//page[@name='other_information']//field[@name='user_id']" position="attributes">
    <attribute name="readonly">1</attribute>
</xpath>

<!-- bad: breaks as soon as the parent view inserts or reorders anything -->
<xpath expr="//group[2]/field[3]" position="after">
    <field name="delivery_instructions"/>
</xpath>
```

Shorthand matching is asymmetric: a `field` element matches the first field
with the same `name`, in document order at **any** depth (use xpath when the
name recurs in an embedded subview), other locator attributes ignored. Any
**other** tag matches the first node with the same tag carrying all the
locator's attributes with equal values (`position` excepted); extra attributes
on the target are fine.

## Why

- The parent view belongs to another module that changes it freely; a
  positional match silently lands the change on the wrong element or raises
  at install on every parent reorganization.
- The shorthand form reads as "this element, changed", and fails loudly if
  the anchor disappears.

## Record conventions

- An inheriting view reuses the **same xml id** as the original record; its
  `name` carries an `.inherit.<details>` suffix.
- A new **primary** view (a variant, not an extension) sets `mode="primary"`
  and needs no inherit suffix.
- Don't re-add fields the parent view already renders.

===== odoo-web-guidelines/guidelines/assets.md =====

# Assets

- Every resource a page needs ships in the codebase: copy images, fonts and libraries
  into the addon instead of linking them by URL.
- Third-party libraries go in `static/lib/`, unminified, so they can be read and diffed.

===== odoo-web-guidelines/guidelines/javascript.md =====

# Organize files by feature, not by type

Code is organized by feature, not by type. Instead of folders like `components/`,
`plugins/`, `services/` or `hooks/`, each feature gets one folder holding all of its
files: `notification/` contains the notification component, its plugin, its template
and its styles.

# Avoid getters

A getter hides the fact that a computation happens, and only saves a pair of
parentheses. Write a plain function instead: the call site then shows that code runs,
and it can take an argument the day the computation needs one.

When the value is derived state, an Owl `computed` is the better answer: unlike a
getter, it recomputes only when what it reads changes.

# Avoid patching JavaScript code

Patching (the `patch` function) is strongly discouraged inside Odoo itself. It is fine
outside of Odoo. A patch makes the code hard to reason about, since reading a snippet
no longer tells you what will run, and harder to maintain, since the patch and the code
it targets drift apart. Usually there is a better solution: design a proper extension
point.

===== odoo-web-guidelines/guidelines/scss.md =====

# SCSS and CSS

- Formatting: 4-space indent (no tabs), ~80-column lines, opening brace on the
  selector line, closing brace on its own line, one declaration per line.
- Order properties from the outside in (start at `position`, end with decorative
  rules like `font`/`filter`); put scoped SCSS and CSS variables at the top,
  separated by a blank line.
- Class naming: avoid `id` selectors; prefix classes with `o_<module>` (just
  `o_` for the webclient). Use the flat "grandchild" approach
  (`o_element_entry`), not hyper-specific nested names. Classes use
  underscores (`o_`); SCSS variables, mixins and functions below use hyphens
  (`o-`).
- Variable conventions: SCSS `$o-[root]-[element]-[property]-[modifier]`, scoped
  SCSS `$-[name]`, mixins/functions `o-[name]` (imperative verbs) with
  optional arguments named in scoped form (`@mixin o-avatar($-size: 1.5em)`), CSS variables
  in BEM `--[root]__[element]-[property]--[modifier]`. Don't define CSS variables
  on `:root` (use SCSS for global design; core's few `:root` definitions are
  deliberate utility APIs); CSS variables are for contextual DOM adaptation.
  The variable conventions bind *new* code; much of core (plain mixin
  arguments, `--ComponentName-property` CSS variables) predates them.

===== odoo-security/SKILL.md =====

---
name: odoo-security
description: >-
  Security audit of Odoo addon code: access control (ir.access, field groups,
  sudo), injection (SQL, domain, eval, XSS via Markup/markup()), untrusted
  public methods/RPC,
  controller auth/CSRF, file access, deserialization, returning complex
  objects, getattr/setattr, timing attacks. Use when auditing an addon, or
  judging whether a specific construct (a sudo, raw SQL, a route, ...) is safe.
---

# Security audit of Odoo code

Audit Odoo addons for the framework-specific ways access control and injection
go wrong. When a feature needs more access than the rules give, it gets the
minimum, in the narrowest scope, with a comment saying why; a silent widening
(a bare `sudo()`, a loosened access row) is a finding.

## Process

- Review the `security/` data files against [Access control](#access-control).
- Sweep the addon for every pattern in the table below; judge each hit against
  its section. A hit is not a finding by itself; the sections say what makes
  it one.
- Report each finding with severity, exact file/line, and a minimal fix.

The audit is complete when every pattern has been swept and every hit judged.

| Sweep for | Judge against |
| --- | --- |
| `sudo(`, `with_user(`, `with_company(` | [Don't over-sudo](#dont-over-sudo) |
| `cr.execute`, `SQL(`, `.format`/`%`/f-string near SQL | [Use the ORM; parameterize SQL](#use-the-orm-parameterize-sql) |
| domain built from request, RPC, or stored field values | [Domain injection](#domain-injection) |
| public (non-`_`) model methods | [Default to private methods](#default-to-private-methods) |
| `@http.route(`, bare `@route(` | [Routes: auth, POST, CSRF](#routes-auth-post-csrf) |
| `innerHTML`, `insertAdjacentHTML`, `markup(` (JS), `Markup(` (Python), `t-raw` (dead code) | [Prevent XSS](#prevent-xss-escape-on-the-way-into-the-dom) |
| password/token/secret fields | [Field-level access](#field-level-access) |
| `related=` crossing models (sudo-computed by default) | [Field-level access](#field-level-access) |
| `open(` | [Open files with `file_open`](#open-files-with-file_open-not-open) |
| `eval(`, `exec(`, `safe_eval` | [`eval` is evil](#eval-is-evil) |
| `pickle` | [Never `pickle`](#never-pickle) |
| `getattr(`, `setattr(` on records | [`getattr`/`setattr`](#getattrsetattr-are-not-your-friends) |
| `==` comparing a secret/token | [Timing attacks](#timing-attacks) |
| `def f(..., x=[])` / `x={}` | [Mutable default arguments](#mutable-default-arguments) |
| methods returning rich objects | [Don't return complex objects](#dont-return-complex-objects-from-model-methods) |

## Access control

Mechanics of `ir.access` rows and field `groups` are in the `odoo-guidelines`
skill ([Access rights](../odoo-guidelines/guidelines/security.md#access-rights),
[Fields](../odoo-guidelines/guidelines/fields.md#fields)); audit `security/` with
the attacker's reading:

- Flag any `c`/`u`/`d` operation granted to `base.group_everyone`,
  `base.group_portal`, or `base.group_public`; scrutinize even `r` on models
  holding personal or business-sensitive data.
- A permission row's `operation` set is what it grants; a *restriction*
  (group-less) row covering only some operations leaves the others governed by
  the permission rows alone: if any permission grants `write`, an attacker
  can alter records the read restriction hides (`write` checks write access
  only, never read). Cover **all** CRUD operations that need restricting.
- Multi-company models need a company restriction row; sensitive models need
  domain restrictions, not just group permissions.

## Field-level access

- A field's `groups` attribute removes it from views and `fields_get` and
  raises on explicit read/write. Use it for sensitive fields instead of
  relying on the UI to hide them.
- **Passwords and API tokens**: restrict them with `groups="base.group_system"`,
  or `groups=fields.NO_ACCESS` to hide the field from everyone, admins
  included. A token field on a model with a permissive access row is readable
  by any user via `search_read`.
- **`related` fields are sudo-computed by default** (`related_sudo=True`): a
  related field reaching sensitive data through a user-writable `Many2one`
  lets the user point the M2o at an arbitrary record and read the related
  value with elevated rights; set `related_sudo=False` on sensitive chains.
  (`readonly=False` write-through is a separate concern: it runs in the
  user's environment and is access-checked.)

## Default to private methods

- **Any public method is callable via RPC** with attacker-chosen arguments;
  the records in `self` and the parameters **cannot be trusted** (access
  control is only enforced on CRUD, not method calls). More public methods =
  bigger attack surface. **Prefix methods with `_` by default**; drop the `_`
  only when the method is genuinely meant to be called externally, and then
  validate inputs. (Privacy alone isn't a control: a `_`-method fed untrusted
  data is still dangerous.)
- The RPC guard (`get_public_method`) blocks `_`-prefixed names,
  classmethods/staticmethods, and anything decorated `@api.private` anywhere
  in the MRO. Check that before flagging a public-named method as exposed;
  `@api.private` is the sanctioned fix when renaming would break callers.

## Use the ORM; parameterize SQL

- Never use the cursor directly when the ORM can do it: raw SQL bypasses
  access control, translations, field invalidation, and `active` handling.
  Prefer `search`/`_read_group` and direct field access (not `read()`). For
  custom SQL over ORM-filtered rows, build the query with `_search(...)` and
  `Query.select(SQL(...))`: access rules and `active` handling stay in force.
- When you must write SQL, **never** interpolate with `+`/`%`/`.format`. Pass
  values as **parameters** (psycopg2 formats them, including a tuple for
  `IN %s`), or use the `odoo.tools.SQL` wrapper. For dynamic **identifiers**
  (table/column names, which can't be parameters) use `SQL.identifier(name)`,
  which validates the name (via `assert`, so a `-O` deployment skips the
  check; still never feed it raw user input).

## Domain injection

- Build/extend domains with `fields.Domain` (`domain &= Domain(...)`), never
  by concatenating a user-provided list with a security domain. Domains are
  prefix notation: a user list placed first (`user + security`) can start
  with `'|'` and turn the whole domain into "anything OR security"; placed
  after, it stays ANDed, but its conditions can still follow relations,
  which under `sudo()` probes records the user cannot read. Validate or
  whitelist user-provided domains either way.

## Don't over-sudo

- `sudo()` is the top risk: review every use twice, especially in controllers
  and public methods, never use it to mask an access error. For each `sudo()`,
  confirm there is no attacker-controlled:
  - **read**: arbitrary model / record / field;
  - **create**: arbitrary model / values;
  - **write**: arbitrary model / record / values;
  - **search**: arbitrary model / domain / injection.
- Controllers: never `record.sudo().write(post)` with raw request params;
  whitelist keys (`{k: post[k] for k in ('name', 'email') if post.get(k)}`).
- Under `sudo()`, x2many `Command` payloads in `vals` execute with sudo **on
  the comodel** (unless it sets `_allow_sudo_commands = False`): a sudo
  write with raw request values pivots the privilege into other models, so
  whitelist command lists too.
- Avoid sudo-computed `related` fields onto `ir.attachment` (arbitrary
  `attachment_id` → arbitrary file read). Prefer a plain `fields.Binary`, or
  create/search `ir.attachment` records so the ORM enforces its access rights.
- `with_user` / `with_company` switches must be intentional, not
  attacker-driven.

## Routes: auth, POST, CSRF

- Match `auth` to the route's exposure: a `public`/`none` route must not
  expose internal data or perform privileged writes.
- A route that writes must use `methods=['POST']`; on a `type='http'` route
  keep CSRF on (never `csrf=False`, except dedicated webhooks);
  `jsonrpc`/`json2` routes have no token check by design, their protection is
  the JSON content type. State-changing logic on a **GET** route is a CSRF
  hole: an attacker can auto-submit a hidden form / crafted
  link and perform the action as the logged-in victim.
- Templates that POST must include `<input type="hidden" name="csrf_token"
  t-att-value="request.csrf_token()"/>`.

## Prevent XSS (escape on the way into the DOM)

- Reflected (script in URL/params) and stored (script saved by a
  low-privileged user) both execute with the victim's session, far more than
  `alert()`.
- Server/QWeb: render with `t-out` (escapes by default). `t-raw` no longer
  exists in either server QWeb or OWL: flag any occurrence as broken legacy
  code; the raw-HTML vector today is a `Markup`/`markup()` value reaching
  `t-out`. Build HTML by wrapping **literals** in `markupsafe.Markup` and
  formatting user content in (Markup auto-escapes; `escape()`/`html_escape`
  turns `str` into escaped `Markup`). f-strings defeat escaping
  (`Markup(f"<p>{x}</p>")`); use `Markup("<p>{x}</p>").format(x=...)`.
  `_()` escapes when any argument is `Markup`, so keep HTML out of the
  literal. (`t-esc`: deprecated-but-escaping alias in OWL; server QWeb
  ignores it and renders nothing, a bug to flag, though not an XSS.)
- JS: the sinks are `el.innerHTML = ...`, `insertAdjacentHTML`, and owl
  `markup()` on a non-literal; never feed them user/low-privilege strings.
  Escape with `htmlEscape` (`@odoo/owl`) or use the tagged-template form
  ``markup`<td>${name}</td>` `` (placeholders auto-escape; plain
  `markup(str)` marks raw HTML), use the `@web/core/utils/html` helpers
  (`setInnerHtml`, `htmlJoin`), or render through OWL `t-out`.
- **Escaping vs sanitizing**: escaping (TEXT→CODE) is always mandatory when
  mixing data with code, even for trusted data. Sanitizing (CODE→safer CODE)
  is only for **untrusted** CODE and only works **after** escaping (sanitizing
  raw TEXT corrupts it). `fields.Html`/`html_sanitize` options
  (e.g. `strip_classes`) tune the level.

## Open files with `file_open`, not `open`

- Never use the builtin `open()` on a path that can be influenced: it can
  read *or write* arbitrary files on the host (config, ssh keys, executable
  Python → RCE). Use `odoo.tools.file_open()`, which confines access to the
  addons paths, the Odoo root, and registered temporary directories. It
  refuses to *create* files but will open an existing one in write mode; it
  is a path confinement, not a write protection.

## `eval` is evil

- Never `eval`/`exec`. To parse data use `json.loads()` or
  `ast.literal_eval()`; only at worst `odoo.tools.safe_eval.safe_eval` with a
  constrained namespace, and only for trusted privileged users (it still
  gives broad capabilities, and plain `eval` allows
  `__import__('os').popen(...)` RCE; master's extra `--unsafe-policy`
  whitelist sandbox is observe-only by default).

## Don't return complex objects from model methods

- A public model method that **returns** a rich object (a crypto key, a
  backend handle) is exploitable from `safe_eval`'d code (server actions,
  automation rules): the evaluated code calls it and walks single-underscore
  internals (`._backend._ffi`) to read files or run code. (Dunders are
  blocked there, and over RPC the return dies in marshalling, so safe_eval is
  the live vector.) Don't factor such logic into a model method if not
  needed; use a standalone module-level function, or dunder-prefix the
  method name: dunder names are unreachable from safe_eval, `_`-names over
  RPC.

## `getattr`/`setattr` are not your friends

- Don't access record fields by dynamic name with `getattr`/`setattr`: it
  exposes private attributes and methods (`__class__` → `__globals__` →
  `__import__` → RCE). Use `record[name]` (safe `__getitem__`); still
  validate the record id and field name, otherwise restrict.

## Never `pickle`

- Builtin `pickle` executes arbitrary code on load (via `__reduce__`). Never
  unpickle untrusted data; store/exchange with `json` (the framework no
  longer ships a restricted pickle wrapper).

## Timing attacks

- Compare secrets/tokens in constant time with `odoo.tools.consteq`, not `==`
  (which short-circuits and leaks length/content via timing). Better, look
  the token up in the database (`search([('access_token', '=', token)])`).

## Mutable default arguments

- Don't use mutable default parameters (`def f(x, vals=[])`); they persist
  across calls and can leak/accumulate data.
