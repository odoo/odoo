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

# Flush before raw SQL, invalidate after it writes

Before a raw SQL query, flush the fields it reads or writes. After a query that
writes, invalidate the fields it wrote, on the records it changed when you hold
them (`invalidate_recordset`), else on the model (`invalidate_model`). When
stored fields depend on the written ones, then call `modified` on the changed
records so those fields are recomputed.

```python
Book = self.env['library.book']
Book.flush_model(['author_id', 'state'])
self.env.cr.execute(SQL(
    "UPDATE library_book SET state = 'lost' WHERE author_id = %s RETURNING id",
    author.id,
))
books = Book.browse(row[0] for row in self.env.cr.fetchall())
books.invalidate_recordset(['state'])
books.modified(['state'])
```

## Why

- The ORM keeps writes and pending recomputes in memory until a flush: a query
  run before it reads the old values, and a write it makes is overwritten by
  the flush that follows.
- The cache keeps the values read before the query: the next read of the field
  returns the value the query just replaced.
- A stored compute that depends on the written field is not triggered by raw
  SQL: it keeps its old value, in the cache and in the database.
- `invalidate_model()` flushes and drops the cache of every record of the
  model: every record accessed after it is read again.

## Exceptions

- `env.execute_query(SQL(...))` flushes the fields the `SQL` object names
  (`SQL.identifier(table, column, to_flush=field)`, `model._field_to_sql`): no
  `flush_model` before it.
- Tables that no model and no many2many field map, and a `pre_init_hook`,
  which runs before any record of the module is loaded.
