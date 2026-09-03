---
name: odoo-review
description: >-
  Review Odoo addon code against the house rules, dispatching each changed
  file to the matching odoo-guidelines, odoo-web-guidelines, and
  odoo-security material. Use when reviewing a diff, commit, PR, or module.
---

# Reviewing Odoo code

Review against Odoo's framework conventions, not generic Python style alone.
Flag issues with file/line and a concrete fix; do not auto-fix anything
ambiguous.

## Process

- Read the module's `__manifest__.py` first to understand scope and `depends`.
- For each changed file, read the guidelines that match it and apply every
  rule that fits:
  - [`odoo-guidelines`](../odoo-guidelines/SKILL.md) — module structure,
    manifest, Python/ORM, fields, controllers, XML, access rights,
    performance, tests; its table maps file types to guideline sections.
  - [`odoo-web-guidelines`](../odoo-web-guidelines/SKILL.md) — everything
    under `static/`: JavaScript, Owl templates, SCSS.
- If the diff touches controllers, access rules (`ir.access` records), `sudo()`, raw SQL,
  `eval`, or public/RPC-callable methods, also apply the
  [`odoo-security`](../odoo-security/SKILL.md) skill.
- **Stable vs master.** In a *stable* version, the existing file style
  supersedes the guidelines — never restyle existing code; keep the diff
  minimal, and check the change against
  [Changes in a stable version](../odoo-guidelines/guidelines/stable.md#changes-in-a-stable-version). In *master*,
  apply guidelines to new code, or to existing code only when a file is under
  major change (do a separate *move* commit first).
- **Version traps.** Odoo's ORM and view/template syntax change between major
  versions (`attrs=`, `<tree>`, `name_get`, `read_group` are all gone from
  recent versions). Before flagging — or writing — an API or attribute,
  confirm it exists in this checkout (`git grep` the ORM source or a current
  usage); don't trust a remembered API.

## Code the diff never shows

Odoo modules extend each other: any method can be overridden by another module,
and any field, XML id, or view element can be referenced by one, including
modules outside this repository (enterprise, customer addons). A change in
behaviour, signature, or name can therefore break code that is not in the diff.

- For each changed method, `git grep "def <name>("` across every addons path
  available, and read the overrides: do they still call `super()` with valid
  arguments, and does the new behaviour hold with their additions?
- For each renamed or removed field, XML id, or method, grep for its name in
  Python, XML, and JavaScript; a stale reference in a view or a domain fails
  only at runtime.
- In a stable version, treat a signature change as a bug on its own (see
  [Changes in a stable version](../odoo-guidelines/guidelines/stable.md#changes-in-a-stable-version)).

Checking the guidelines and the code around the diff is the floor of a review,
not the end of it. Then review the change on its merits as you would any code.
