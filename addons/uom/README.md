# uom — Units of Measure

Defines `uom.uom` and the conversion arithmetic every quantity and price in
the system passes through. It has no dependencies beyond `base` and `web`, and
roughly everything downstream (`product`, `stock`, `sale`, `purchase`, `mrp`,
`account`) depends on it, so a change here is never local.

## The model in one paragraph

A unit is defined *relative to another unit*: `relative_uom_id` names the
parent and `relative_factor` says how many of the parent one of these contains
(`Dozens` = 12 `Units`). Following that chain to its root gives the
**dimension** — weight, length, time. Two units are convertible if and only if
they share a root. There is no `uom.category` model; 19.0 replaced it with this
tree.

Three stored, indexed columns hold what the tree implies, so nothing has to
walk it at runtime:

| field | meaning |
|---|---|
| `factor` | quantity of the *root* unit in one of this unit (`Ton` → 1000000 g) |
| `reference_uom_id` | the root itself — the dimension. A root is its own. |
| `parent_path` | `_parent_store` ancestry, used for `child_of` searches |

`relative_factor` and `factor` are declared `digits=0`, which means an
**unlimited-precision NUMERIC column**, not zero decimals. That is deliberate:
`Minutes` is stored as exactly `1/60` so that 60 of them convert back to one
hour.

## Precision is global, and it is a policy

`uom.rounding` is *not* per-unit. It is a compute over the single
`decimal.precision` row named **"Product Unit"**, and `round`, `compare` and
`is_zero` all read the same source through `_precision_digits()`. A unit does
not carry its own precision; changing that one row changes every unit at once.

Two consequences worth knowing before you touch conversion code:

- **The precision does double duty.** At `digits = 2` it reads as *resolution*
  ("show me two decimals"). At `digits = 0` it is a *legality rule* — whole
  units only — and `stock`'s reservation logic depends on that reading
  (`stock/tests/test_move.py::test_availability_6`). Any change to the rounding
  rule has to serve both, which is why the obvious "add decimals for large
  factor ratios" fix does not work.
- **A conversion is quantised in the *destination* unit.** The smallest
  representable result is `10^-digits` of `to_unit`, however fine the source
  is, and `_compute_quantity` rounds **UP** by default. 1 kg becomes 0.01 Ton,
  not 0.001. `TestUomConversionScale` pins this behaviour; read it before
  assuming a conversion is lossless.

**If a converted quantity feeds a comparison rather than a record, pass
`round=False`.** That is the difference between a pricelist tier matching
correctly and a 0.5 kg order being charged the 10 kg price.

## Conversion API

`_compute_quantity` and `_compute_price` are **strict**: converting between
units of different dimensions raises `UserError`, because scaling by a ratio of
unrelated factors produces a plausible number that is silently wrong.

Call sites that must degrade instead pick a named wrapper, so the intent is
greppable per bucket rather than hidden behind a boolean:

| wrapper | for values that feed |
|---|---|
| `_get_quantity_report` / `_get_price_report` | a screen, PDF or aggregate |
| `_get_quantity_estimate` / `_get_price_estimate` | a forecast or pricing estimate |
| `_get_quantity_reconcile` | a stored reconciliation compute (`qty_transferred`/`qty_invoiced`) |

Anything that creates or sizes a real record — moves, MOs, order lines,
valuation — stays on the strict base method. The opt-out is forced: a
caller-supplied `raise_if_failure` is discarded by the wrappers.

`_get_quantity_reconcile` escalates back to strict under the
`uom_reconcile_strict` context key, so a stored compute stays lenient while an
order is browsed but fails loudly at the invoicing boundary.

## Degenerate recordsets are legal

`compare`, `is_zero`, `round`, `_has_common_reference`, `_compute_quantity` and
`_compute_price` all accept an **empty** `uom.uom`. Call sites reach a
`product_uom_id` that is legitimately unset on a half-filled record, and the
first four never read `self` anyway. More than one unit stays a caller error.

## Master data

Units carrying an `ir.model.data` row from **any** module are protected from
deletion, minus the explicit `_unprotected_uom_xml_ids()` list. Override that
method by calling `super()` and filtering — returning a literal discards
whatever the base list gains later, and makes the result depend on MRO order
when two modules protect the same unit.

Deleting a unit that others are defined against is refused outright:
`relative_uom_id` is `ondelete="cascade"`, so Postgres would remove the whole
subtree without any of it passing through `unlink()`.

## Tests

```bash
odoo-bin -c <conf> -d <db> -i uom --test-enable --test-tags /uom --stop-after-init
cd tooling/hoot && ./hoot '@uom'      # the many2one_uom / many2many_uom_tags widgets
```

Changing conversion behaviour means running the downstream suites too — at
minimum `/stock`, `/mrp`, `/product`, `/sale_stock`, `/purchase_stock`. The
tests that constrain this module most tightly do not live in it.
