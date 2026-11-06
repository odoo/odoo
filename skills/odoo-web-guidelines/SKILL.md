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
| [End a sort comparator on a unique key](guidelines/javascript.md#end-a-sort-comparator-on-a-unique-key) | writing a comparator for `sort()` or `toSorted()` |
| [Batch RPCs](guidelines/javascript.md#batch-rpcs) | calling the server from a loop, or more than once for one user action |
| [Give every icon a role and a label or aria-hidden](guidelines/templates.md#give-every-icon-roleimg-and-a-label-or-aria-hidden) | adding or changing an icon in a template |
| [Avoid getters](guidelines/javascript.md#avoid-getters) | adding a computed value to a class or a component |
| [Avoid patching JavaScript code](guidelines/javascript.md#avoid-patching-javascript-code) | extending or overriding behaviour that already exists |
| [Use `window` members directly](guidelines/javascript.md#use-window-members-directly-not-the-browser-object) | writing `browser.`, or importing from `@web/core/browser/browser` |
| [Pair every absence check with a positive one](guidelines/tests.md#pair-every-absence-check-with-a-positive-one) | asserting in a Hoot test or a tour that an element is absent |
| [Use the Owl 3 hooks](guidelines/javascript.md#use-the-owl-3-hooks-not-the-owl-2-compatibility-ones) | adding or converting an Owl hook: an effect, a sub-env, a forced render |
| [SCSS and CSS](guidelines/scss.md#scss-and-css) | touching `*.scss` |
| [Assets](guidelines/assets.md#assets) | adding an image, font, or library |

To add a guideline, follow [AUTHORING.md](AUTHORING.md).
