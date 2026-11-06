# Recordsets, domains and context

- Use recordset methods (`filtered`, `grouped`, `mapped`, `sorted`) where they
  read better than a loop.
- Recordsets/collections are booleans: write `if records:` / `if some_list:`,
  not `if len(...)`.
- Don't read a non-relational field on a multi-record set (it raises); iterate
  or `mapped`. Conversely, guard single-record assumptions with `ensure_one()`.
- No record found is an empty recordset, never `None`:
  `return self.env['library.book']`,
  `books_by_author.get(author, self.env['library.book'])`.
  `env.ref(xmlid, raise_if_not_found=False)` does return `None`: test it before
  using it.
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

# Set a state, never flip it

A method that changes a state sets a fixed state, named by the method
(`action_confirm`) or passed as an argument. A state that goes both ways gets
one method per direction (`action_archive` and `action_unarchive`), or one
method that takes the state to reach. No method reads the current value to
write its opposite.

```python
# good
def action_publish(self):
    self.is_published = True

def action_unpublish(self):
    self.is_published = False

# bad
def action_toggle_published(self):
    for book in self:
        book.is_published = not book.is_published
```

A button that shows both states is two buttons, each one visible in one state
and calling the method of its direction.

## Why

- A flip is not idempotent. A double click or a retried request sends the
  same call twice, and the second call undoes the first one.
- The caller decides from the state it shows. When the record changed since
  the caller read it, in a second tab or by another user, a flip writes the
  state the caller wanted to leave.
- Only the server knows the state a flip reached, so it must send it back for
  the client to show it.

## Exceptions

- The rule is for new methods. An override or a call of an existing flip
  method keeps its name and its behaviour.

# Transactions and exceptions

- **Never** call `cr.commit()` / `cr.rollback()` unless you opened your own
  cursor; the framework owns the transaction. Any unavoidable commit needs an
  explicit comment justifying it.
- Catch **specific** exceptions over the smallest possible block; let unexpected
  ones propagate to the framework. To recover from framework exceptions, wrap the
  work in `with self.env.cr.savepoint():` (note: >64 savepoints per transaction
  degrades PostgreSQL, so bound batch sizes).
