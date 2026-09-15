# Generated model type declarations

TypeScript `.d.ts` files for every Odoo model, emitted from server
`fields_get`. The goal is for `record.data.partner_id` to type-check as
`Many2one<"res.partner">` instead of `any`.

## Layout

```
@types/models/
├── _runtime.d.ts          # hand-written brand types (Many2one, One2many, …)
├── README.md              # this file
└── <module>/
    └── <model>.d.ts       # GENERATED — one per (module, model) pair
```

Each `<model>.d.ts` declares an interface keyed by the PascalCase model
name and registers it into the global `Models` map via TypeScript
declaration merging. Multiple modules contributing to the same model
each emit their own file; TS unions them at compile time.

## Regenerating

```bash
# From a running odoo-bin shell (preferred):
./addons/odoo/odoo-bin shell -c conf/odoo.conf -d $DB <<'PY'
from addons.core.addons.web.tooling.scripts.generate_model_types import generate
generate(env)  # all installed modules
# or:
generate(env, modules=["sale", "sale_team"])
generate(env, models=["res.partner"])
PY

# Standalone (slower — bootstraps Odoo internally):
python addons/odoo/tooling/codegen/generate_model_types.py \
    --config conf/odoo.conf --db $DB --modules sale,stock
```

Re-run after any `_fields` change, and after installing/uninstalling a
module.

## How it composes with `RelationalRecord`

Today (`record.data` typed `Record<string, unknown>`):

```js
const partner = record.data.partner_id;  // any
partner[0];                               // any — no error
partner.bogus;                            // any — no error
```

After typed `RelationalRecord<TModel>`:

```ts
const record: RelationalRecord<"sale.order"> = ...;
const partner = record.data.partner_id;
//    ^? Many2one<"res.partner">
partner[0];                               // number — ok
partner.bogus;                            // ✗ Property 'bogus' does not exist
```

Migration is per-call: existing untyped sites stay valid (the default
`TModel = string` makes them resolve to the open base map). Hot paths
opt in.

## Why brand types instead of fully-resolved values

A `Many2one<"res.partner">` is `[number, string] | false` at the wire
level. The brand carries the model name as a *phantom* string-literal
type parameter — runtime values are unchanged. This is the same pattern
as `branded number` types in Effect-TS / Zod.

The phantom lets downstream APIs walk the relation graph without
loading actual records:

```ts
async function fetchRelated<K extends keyof Models["res.partner"]>(
    record: RelationalRecord<"res.partner">,
    field: K,
): Promise<Models["res.partner"][K] extends Many2one<infer M> ? RelationalRecord<M> : never>
```

## Things deliberately NOT done

- **No custom `x_*` fields**: per-deployment, would couple type repo
  to a database. Skipped.
- **No transient/wizard models**: they don't have `RelationalRecord`
  shapes worth typing in this loop. Worth revisiting.
- **No translation-of-help-text into JSDoc**: too noisy, rots fast.
  IDE hover surfaces field name + type, which is the load-bearing
  information.
- **No runtime use of brands**: pure compile-time. Bundle size unchanged.

## Lifecycle

Generated files are **committed** (this is the type contract). PRs that
add a server-side field need to regenerate the affected model and commit
the diff. The companion CI job (planned, not yet built) diffs generated
output against committed files and fails PRs whose `fields_get` differs
from what's checked in — same strict-ratcheting pattern as
`tooling/typecheck/scope_gate.py`.
