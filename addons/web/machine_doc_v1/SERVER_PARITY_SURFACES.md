# Server-Parity Surfaces — Inventory & Verification Record

Status: **Inventoried and verified. Four defects fixed, two surfaces newly
gated.** Date: 2026-08-09.
Scope: every place `addons/web`'s JavaScript re-implements a rule the server
also implements, and must therefore agree with.

## Why this exists

Several modules in `static/src` are hand-written mirrors of server logic. Their
comments say so — *"Mirrors `odoo.libs.numbers.float_utils.float_round`. The two
must agree"*, *"Mirrors the server's own rule (`models._check_qorder`)"* — but a
comment is not a gate, and a divergence in one of these is not a rendering bug:
it is the client computing a **different answer** from the server for the same
input, and then displaying it, filtering on it, or saving it.

This document is the inventory, so the next audit does not re-derive it.

## The surfaces

| Surface | Client | Server | Gated by |
|---|---|---|---|
| Python expression evaluation | `core/py_js/` | `tools/safe_eval` + CPython | `tests/core/py_js/py_cpython_differential.test.js` (2,141 rows) |
| Domain matching | `core/domain.js` `Domain.contains` | `filtered_domain()` / `_to_sql` | `tests/core/domain_server_parity.test.js` (3,331 cases) |
| Decimal rounding | `core/utils/format/numbers.js` `roundPrecision` | `libs/numbers/float_utils.float_round` | `tests/core/utils/float_round_server_parity.test.js` (860 rows) |
| `order` string validation | `core/utils/order_by.js` `stringToOrderBy` | `models._check_qorder` / `regex_order` | **not gated** — see *Known divergences* |
| View IR ↔ arch element | `views/ir/view_ir.js` `irToElement` / `elementToIR` | `odoo.tools.view_ir.from_arch` / `to_arch` | `tests/views/view_ir.test.js` + `odoo/tools/tests/test_view_ir_fixture.py` over the same frozen fixture (`tests/views/view_ir_fixture.js`, 14 archs incl. the largest form in the checkout and four edge cases: comment tails, `&nbsp;` literals, namespaces, CDATA) |

The view IR row is the newest (2026-09-13): `get_view()` now ships the tree it
postprocessed as `ir` next to `arch`, and `View.loadView` materialises the
element the parsers and compilers walk from that tree instead of parsing the
string. Both readers are held to one fixture — Python asserts
`from_arch(arch).to_dict() == ir`, HOOT asserts `elementToIR(parseXML(arch))`
deep-equals `ir` and that `irToElement(ir)` serialises identically to the parsed
arch — so a divergence in either fails on the same file.

A sixth pair is client-internal rather than client/server, and has the same
character: `registry.category("formatters")` and `("parsers")` must invert each
other, or editing a field and saving it untouched moves the value. Gated by
`tests/core/formatter_parser_roundtrip.test.js`.

## What verification found

**`py_js` — four defects, now fixed** (`dcdcc23c61e`). `round()` decided its
half-to-even tie-break on `abs.toPrecision(17)`, the exact width at which a
near-tie becomes indistinguishable from a tie; `date.weekday()` did not exist,
which killed the "since Monday" filter two `agromarin` views ship; date
arithmetic could leave the 1..9999 range; and `inf`/`nan` printed with
JavaScript's spellings while `%F` and `%c` were rejected outright. 109 of the
2,141 corpus rows fail against the pre-fix code.

**`roundPrecision` — sound** (`ae74a5b9d01`). Zero divergences over 233,550
cases: five rounding methods × ten precisions, exact ties, the 2^49/2^50/2^51
clamp boundaries, money shapes, 4,000 pseudo-random magnitudes. No fix was
needed; the commit exists to turn the comment into a gate.

**Formatter/parser pairs — one defect** (`1abdb120173`). `formatInteger`
rendered `"-0"` for anything in (-1, 0), because `toFixed(0)` keeps the sign.

## Method

Both `core/py_js/` and `core/utils/format/numbers.js` load under plain Node —
the first has one non-relative import (`@web/core/l10n/luxon`, and the vendored
`static/lib/luxon/luxon.js` is already ESM), the second needs three trivial
shims. So they can be diffed against the workspace CPython directly, thousands
of expressions per second, with no browser, DB or hoot involved.

Three rules make the result mean something:

1. **Harvest real inputs, don't invent them.** 11,545 distinct client-evaluated
   expressions exist across `odoo/addons`, `enterprise`, `agromarin` and
   `design-themes` (`domain=`, `context=`, `invisible=` … in non-`static/` XML).
   All of them parse but one, and that one is a harvest artifact: a
   `t-attf-context` whose `#{…}` QWeb interpolation is substituted before the
   result is ever a context. Running them is also how `weekday()` surfaced — it
   is the only gap production actually reached.
2. **Check reachability before calling a bug user-visible.** `round()` and the
   `%` operator appear **zero** times in those 11,545 expressions, so the
   rounding defect, though real, is unreachable from any shipped view.
3. **Mutation-test the corpus.** A generated corpus reporting zero divergences
   proves nothing until it is shown to fail on a defect. The first date corpus
   survived a leap-year mutation (`year % 400` → `% 500`) because it contained
   no century years. Every corpus here was checked against deliberate mutations
   of the code it guards.

## What is irreducible

JavaScript has one number type. An integral float is indistinguishable from an
int, so `str(1.0)` is `'1'` here, `'%x' % 1e20` formats where CPython raises,
and floats at or above 1e16 print as digits rather than in scientific notation.
After the fixes, a 28,800-case `%`-format sweep goes from 3,328 divergences to
672, and **every survivor involves `1e20`**. "JS raises where Python does not"
is zero. Do not reopen these.

## Known divergences, deliberately not closed

`stringToOrderBy` rejects `nulls first` / `nulls last`, which `regex_order`
accepts, and accepts field names (`field-name`, `field!`) that it rejects.
Neither is live: **zero** model `_order` attributes and **zero** view
`default_order` attributes in the fork use NULLS ordering. Throwing is also the
documented intent here — the function's docstring records that silently coercing
an unrecognised direction used to reverse the sort — so accepting and dropping
the clause would be worse than the current loud failure. If a model ever needs
such an `_order`, the fix is to carry the nulls position through `OrderTerm` and
`orderByToString`, not to relax the check.

## Reproducing

```bash
# py_js under Node (work on a COPY of core/py_js/)
echo 'export * from "<repo>/addons/web/static/lib/luxon/luxon.js";' > luxon_shim.mjs
sed -i 's#"@web/core/l10n/luxon"#"./luxon_shim.mjs"#' py_date.js

# harvest every client-evaluated expression: domain=/context=/invisible=/... in
# non-static XML, html.unescape'd, skipping eval= and %(xmlid)s forms
```

The three harvest bugs worth avoiding, each of which manufactures fake
divergences: not unescaping `&gt;`/`&quot;`; scraping OWL templates under
`static/src`, where `context=` is a component prop; and scraping `eval=`, which
is server-side `safe_eval` at data load and never reaches the client.
