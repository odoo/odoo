# Call `super()` in an override, change only what differs

An override of a method that another module defines calls `super()` and
changes only what differs: it adds to the result of `super()`, or calls it
with other arguments. It does not copy the body of the parent method.

```python
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
  [Methods and extension points](orm.md#methods-and-extension-points)).

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
[Computes, onchange and constraints](orm.md#computes-onchange-and-constraints)).

```python
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
