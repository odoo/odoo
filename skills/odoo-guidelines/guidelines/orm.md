# Recordsets, domains and context

- Use recordset methods (`filtered`, `grouped`, `mapped`, `sorted`) where they
  read better than a loop.
- Recordsets/collections are booleans: write `if records:` / `if some_list:`,
  not `if len(...)`.
- Compare records, not their ids: `line.partner_id == partner`,
  `partner in lines.partner_id`. `==` on records also checks the model;
  `.id == .id` is true for two records of different models that share a
  number. Combine recordsets you already hold with `|`, `&`, `-` and take
  `.ids` once at the end (`(partners | users.partner_id).ids`), not a list of
  ids joined by hand. A membership test inside a loop stays on a `set` of ids
  (see [Performance conventions](performance.md#performance-conventions)).
- Write x2many values with the `Command` helpers (`Command.create(vals)`,
  `Command.link(id)`, `Command.set(ids)`), in Python and in XML `eval`, not
  the `(0, 0, vals)`, `(4, id)`, `(6, 0, ids)` tuples.
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

# Raw SQL: flush, invalidate, recompute

Before writing data with raw SQL, ask why the ORM does not do it. When the
reason is speed, benchmark it against the ORM version.

Run the query with `env.execute_query(SQL(...))` and name its fields through
`query.table.<field>` or `SQL.identifier(table, column, to_flush=field)`:
`execute_query` flushes the fields the `SQL` object names. Call `flush_model`
only for the fields the query uses without naming them that way.

A query that only reads needs no invalidation. For a query that writes:

- Invalidate the fields it writes, on the records it changes when you hold
  them (`invalidate_recordset`), else on the model (`invalidate_model`). Both
  flush those fields first, and the query does not use the ORM, so this can be
  done before it.
- When stored fields depend on the written ones, call `modified` on the changed
  records after the query. For a relational field, also call
  `modified(fnames, before=True)` after the flush (or the invalidation) and
  before the query, so that the records linked through the old value are
  recomputed too. `modified` needs the records in memory, before the query for
  a relational field: at that point, the ORM is most probably the better
  choice.
- Without `modified`, nothing of what `write` does runs (see Why): make sure
  that is what you want, and still invalidate the written fields before the
  query.

```python
Book = self.env['library.book']
query = Book._search([('author_id', '=', author.id)])
Book.invalidate_model(['state'])
self.env.execute_query(SQL(
    "UPDATE %s SET state = 'lost' WHERE id IN %s",
    SQL.identifier(Book._table), query.subselect(),
))
```

## Why

- The ORM keeps writes and pending recomputes in memory until a flush: a query
  run before it reads the old values, and a write it makes is overwritten by
  the flush that follows.
- The cache keeps the values read before the query: the next read of the field
  returns the value the query just replaced.
- Raw SQL skips what `write` does: the stored computes that depend on the
  written field keep their old value, in the cache and in the database, and
  the Python constraints, the `write` overrides of other modules and the
  tracking do not run.
- `invalidate_model()` flushes and drops the cache of every record of the
  model: every record accessed after it is read again.

## Exceptions

- Tables that no model and no many2many field map, and a `pre_init_hook`,
  which runs before any record of the module is loaded.
