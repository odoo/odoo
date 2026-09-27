# Manifest

- `name` is required; `version` should follow semantic versioning.
- `depends` lists every module whose features or resources are used, direct
  dependencies only. Don't list `base`: a manifest without `depends` gets
  `['base']` injected, and upgrading `base` upgrades every installed module
  whether or not it lists it.
- `data` files are always installed/updated; `demo` files load only in demo
  mode. Keep load order correct (a record's dependencies first).
- `license` defaults to `LGPL-3`; set it deliberately and correctly.
- `auto_install` is only for "link" modules (installed automatically when their
  dependencies are); it can also be a *subset* of `depends` that triggers the
  auto-install (an empty list: always installed).
- `application` is `True` only for full apps, not technical modules.
- Declare non-Odoo requirements in `external_dependencies` (`python`/`bin`).
- `assets` declares how static files load into bundles (don't register assets
  ad-hoc elsewhere).
