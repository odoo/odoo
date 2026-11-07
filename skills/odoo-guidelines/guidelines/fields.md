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

# Save a written non-stored computed field through its inverse or create and write

When a value written on a non-stored computed field must be saved, the field has
an `inverse` that writes the fields its compute reads, or a `create` or `write`
override takes the value out of `vals`. An editable field that is only a form
input, whose `@api.onchange` sets the stored fields its compute reads, needs
neither. Code that needs another value writes the fields the compute reads, not
the computed field.

## Why

A non-stored field has no column. Writing it only puts the value in the cache
(on an x2many, only a `Command.update` of an existing line reaches the
database), with no error and no warning, and the next recompute replaces it. The form still
shows the typed value after the save, and the value is gone when the record is
opened again; an imported value is dropped the same way. A read right after the
write still returns the value, so a test that writes the field and reads it back
passes.
