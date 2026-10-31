# Put code in the module that owns its concern

Every piece of a feature goes in the module whose concern it is. Decide it
before writing code, piece by piece, in this order:

1. **An existing module owns the concern**: extend that module. An
   improvement to invoicing goes in `account`; a new option of operation types
   goes in `stock`.
2. **No module owns it, and other apps may use it**: create a module for it,
   depending only on what the capability itself needs (`base`, `mail`, `web`).
   A reusable capability, such as printing reports, tagging records or
   reaching a device, is its own module, never part of one business app.
3. **It connects two apps**: put it in a **bridge**. Use the existing module
   that already depends on both when there is one; otherwise create
   `<app>_<app>`, depending on both, with `auto_install` on them, so it is
   installed exactly when both apps are.

```
# a library app gets reservations and a reusable "notify by SMS" capability

library/                  # owns books and loans: reservations go here (1)
sms_notify/               # reusable, depends on base and sms only (2)
library_sms_notify/       # notifies borrowers by SMS: bridge, auto_install (3)

# bad: the reusable capability inside the app, so any other app that wants
# SMS notifications must install the library
library/models/sms_notify.py
```

## Why

- A module's `depends` is its install footprint: a capability placed in a
  business app drags that app into every database that wants the capability.
- Bridges keep apps independent: each installs alone, and the code connecting
  them is installed only where both are, without a feature flag.
- Ownership tells the next developer where to look, and keeps one module per
  concern to review, upgrade, and override.

## Exceptions

- A module combining two apps that is a feature in its own right, one a
  customer chooses to install (an online shop on top of the website and
  sales), sets no `auto_install`: it is installed on purpose, not whenever
  both apps are.
- An existing module may depend directly on a small capability module that
  itself depends on nothing heavy, instead of going through a bridge, when
  installing it everywhere that module is installed costs nothing.
- A capability that belongs to the framework itself (every model, every view)
  goes in `base` or `web`, the modules that own the framework.
- On a released version, new modules are not added (localizations aside):
  follow the `odoo-stable-policy` skill.
