---
name: odoo-web-guidelines
description: >-
  House rules for the web framework code of Odoo addons: the JavaScript,
  Owl templates and SCSS in static/src/ and static/tests/ of any addon
  (community, enterprise, or custom). Use when writing, reviewing, or
  moving files under static/ in an Odoo addon.
---

# Odoo web guidelines

These rules apply to the web framework code an addon ships in `static/src/` and
`static/tests/`: JavaScript, Owl templates (XML) and SCSS. They do not apply to
`static/lib/`, which holds vendored or library-style code, nor to the images and
`static/description/` an addon ships alongside. They are house rules, not general web
development advice.

Each rule lives in its own numbered file in `guidelines/`. The number is an identifier, not
a priority: no rule outranks another. Read the ones that match the code you are touching
instead of loading all of them.

| Guideline | Read it when |
| --- | --- |
| [0001 Organize files by feature](guidelines/0001_organize_files_by_feature.md) | creating a file, or deciding where new code lives |

To add a guideline, follow [AUTHORING.md](AUTHORING.md).
