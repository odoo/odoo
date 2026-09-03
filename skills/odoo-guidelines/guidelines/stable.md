# Changes in a stable version

A stable version is any released branch (`17.0`, `18.0`, ...): only bug fixes and
localizations go there; improvements and features go to master, and an LTS fix is
forward-ported by the maintainers, never re-submitted per branch.

- Value over risk: keep the change minimal and strictly about the bug. If the risk is
  high or the value low, it belongs in master, not in stable.
- No improvements, technical or functional, and no purely cosmetic changes
  (formatting, PEP 8, restyling). Match the surrounding code's style.
- Public model methods (no `_` prefix) are API for integrators: never change their
  signature. Avoid changing private signatures too, extension modules override them.
- No data-model change: stored columns are never added, removed, or changed to an
  incompatible type. Compatible tweaks (`ondelete`, `size`) are allowed when needed;
  a non-stored computed field may be added if really necessary.
- Keep XML ids of existing data, and don't delete data records that user data may
  reference, unless essential and the records were `noupdate` from the start.
- Change XML (views, menus, default data) only when inevitable, and then the Python
  code must not depend on the change: a database that has not been updated must
  keep working.
- A fix may need an explicit module update as long as users who don't run it are
  safe. A critical security fix must work with a pull and restart alone.
- Don't modify existing translatable source terms, even for a typo; that breaks
  existing translations. Correct a term in master, or add an English-to-English
  translation in stable. Adding or deleting terms is fine; don't ship `.pot`
  updates, they are exported and synced automatically.
