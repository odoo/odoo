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

Guidelines are grouped by domain, one file per domain in `guidelines/`, one section per
guideline. No rule outranks another. Read the sections that match the code you are
touching instead of loading whole files.

| Guideline | Read it when |
| --- | --- |
| [Organize files by feature](guidelines/javascript.md#organize-files-by-feature-not-by-type) | creating a file, or deciding where new code lives |
| [Avoid getters](guidelines/javascript.md#avoid-getters) | adding a computed value to a class or a component |
| [Avoid patching JavaScript code](guidelines/javascript.md#avoid-patching-javascript-code) | extending or overriding behaviour that already exists |
| [SCSS and CSS](guidelines/scss.md#scss-and-css) | touching `*.scss` |
| [Assets](guidelines/assets.md#assets) | adding an image, font, or library |

To add a guideline, follow [AUTHORING.md](AUTHORING.md).
