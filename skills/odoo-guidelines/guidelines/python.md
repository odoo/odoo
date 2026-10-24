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

# Compare floats with the precision they are shown with

No `==`, `!=`, `<`, `>` or truthiness test on a float amount, price or quantity. Use the
core helpers with the precision the value is displayed or stored with:

- amounts: `currency.compare_amounts(a, b)`, `currency.is_zero(a)`, `currency.round(a)`;
- quantities: `float_compare(a, b, precision_rounding=uom.rounding)`,
  `float_is_zero(...)`, `float_round(...)` from `odoo.tools`;
- other values: the same helpers with
  `precision_digits=self.env["decimal.precision"].precision_get("<name>")`.

```python
# bad: 10.001 != 10.0 although both print as 10.00
book.show_old_price = book.old_price and book.old_price != book.price
# good
currency = book.currency_id
book.show_old_price = (
    not currency.is_zero(book.old_price)
    and currency.compare_amounts(book.old_price, book.price) != 0
)
```

## Why

Floats carry binary rounding errors and more digits than the UI or PDF shows. A raw
comparison can disagree with what the user sees: a total that "is" zero but isn't, a
price flagged as changed that prints the same.

## Exceptions and notes

- Add the currency or uom field to `@api.depends` when a compute uses it.
