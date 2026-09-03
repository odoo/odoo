# Fields

- Relational suffixes: `Many2one` → `_id`, `One2many`/`Many2many` → `_ids`.
- `index=True` on fields that are both searched and selective (many distinct
  values). An index on a low-cardinality field — a boolean, a state — is wasted
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
- A field and a method can't share a name (same namespace) — flag collisions.
- `related` fields can't chain `One2many`/`Many2many` in the dependency path —
  the ORM does not reject it, it *silently truncates each x2many hop to its
  first record* and returns wrong data; reach the target through a `Many2one`
  (ending the chain on an x2many is fine). Reusing one compute for several
  fields is fine; reusing one **inverse** is discouraged — while the inverse
  runs, every field sharing it is protected and reads as `False` when not
  cached, so the method sees wrong sibling values.
