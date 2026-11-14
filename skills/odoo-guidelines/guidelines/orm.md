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

# End `_order` on a unique field

A model's `_order` ends with a field that is unique per record, usually `id`:
`sequence, id`, `name, id`, `date desc, id desc`. The default `_order = 'id'`
is unique already. When records sorted by `_order` come back in a random
order in a caller or a test, add the tiebreaker to `_order`; do not change the
test so it stops reading the order.

```python
# bad: two books with the same sequence come back in any order
class LibraryBook(models.Model):
    _name = 'library.book'
    _order = 'sequence'

# good
class LibraryBook(models.Model):
    _name = 'library.book'
    _order = 'sequence, id'
```

## Why

- The ORM adds no tiebreaker to `ORDER BY`. Records equal on every field of
  `_order` come back in the order PostgreSQL picks, and that order can change
  from one query to the next.
- A paged list runs one `LIMIT`/`OFFSET` query per page: with ties, a record
  shows on two pages and another one on none.
- `search(..., limit=1)`, `records[0]` and a test that reads a position get a
  different record from one run to the next.
- The tie spreads: `_order` also sorts the one2many and many2many fields that
  point to the model, and any order on a many2one to it.

## Exceptions

- Fields already unique together (a required `code` under a unique
  constraint) need no `id`.
- After a `desc` term that means "newest first", write `id desc`.

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

# Call `super()` in an override, change only what differs

An override of a method that another module defines calls `super()` and
changes only what differs: it adds to the result of `super()`, or calls it
with other arguments. It does not copy the body of the parent method.

```python
# bad: copies the parent, and drops what the other modules add
def _get_export_fields(self):
    return ['name', 'author_id', 'isbn']

# good
def _get_export_fields(self):
    return super()._get_export_fields() + ['isbn']
```

- To run the parent with more rights, call it on `self.sudo()`
  (`super(LibraryBook, self.sudo())._update_stock()`) rather than copy its
  code under a `sudo()`, when the whole parent may run as superuser (see
  odoo-security). A recordset it returns comes back in sudo:
  `.with_env(self.env)` before returning it.
- When the part to change sits in the middle of the parent, move that part to
  its own method and override that one (see
  [Methods and extension points](#methods-and-extension-points)).

## Why

Each module that overrides a method reaches the next one through `super()`.
An override that skips it also skips the overrides of the modules loaded
before it, without any warning: the code works while it is alone, and breaks
the day another module adds to the same method. A copy of the parent also
stops following it: a later fix of the parent never reaches the copy.

A path that returns before `super()`, or a `continue` that jumps over it in a
loop, skips it for that case just the same.

A parent that returns an empty default (`False`, `[]`, an empty recordset) is
still called: another module may fill the same placeholder for the same model,
and its values are lost without `super()`.

## Exceptions

- The parent raises `NotImplementedError`: there is nothing to keep.
- A path that raises may skip `super()`.

# Put what every path needs in `create`, `write` or `@api.ondelete`

Something that must happen each time a record is created, changed or deleted,
whatever the path (a bus notification, an unsubscription), goes in `create`,
`write`, or an `@api.ondelete` method. It does not go in the action method of
one button or wizard. A value derived from other fields is a compute, not an
override of `create` or `write` (see
[Computes, onchange and constraints](#computes-onchange-and-constraints)).

```python
# bad: only this button notifies, other deletions do not
def action_withdraw(self):
    self._notify_withdrawn()
    self.unlink()

# good
@api.ondelete(at_uninstall=False)
def _unlink_notify_withdrawn(self):
    self._notify_withdrawn()
```

## Why

The action is one path among many: the list view, an import, the code of
another module and the tests call `create`, `write` and `unlink` directly. An
effect put in the action runs for that path only, and every other path leaves
the data or the open clients out of date.

For a deletion, prefer an `@api.ondelete(at_uninstall=False)` method to an
`unlink` override: it is skipped when its module is uninstalled, when the
columns and models it reads may already be gone.

## Exceptions

- An effect meant for that action only, such as a chatter message that names
  who clicked, stays in the action method.
- An effect that needs the records gone, such as a recompute of the records
  they pointed to, stays in an `unlink` override, after `super().unlink()`:
  the ondelete methods run before the rows are deleted.
