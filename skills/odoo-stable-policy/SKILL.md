---
name: odoo-stable-policy
description: >-
  What a change may and may not do on a released Odoo version (17.0, 19.0,
  saas-19.4, ...): only bug fixes, no signature or data-model change, and a
  fix that works on databases that are not updated. Also how to tell a
  released version from master by reading odoo/release.py. Use before writing
  any bug fix or other change in an Odoo checkout, whatever the source of the
  request, and when reviewing one.
---

# Odoo stable policy

A released version runs in production on databases that get new code with a
pull and a restart, most of them without a module update. A change there is
held to the rules below. On master they do not apply. Find out which one the
checkout is before designing the change.

## Find out whether the checkout is a released version

Read `version_info` in `odoo/release.py`, at the root of the community
checkout:

    grep '^version_info' odoo/release.py

| `version_info` | Version | Policy |
| --- | --- | --- |
| `(19, 0, 0, FINAL, 0, '')` | 19.0, released | stable |
| `('saas~19', 4, 0, FINAL, 0, '')` | saas-19.4, released | stable |
| `(20, 1, 0, ALPHA, 1, '')` | master, the future 20.1 | master |

- `FINAL` means released: the stable policy applies, saas versions included.
  `ALPHA`, `BETA` or `candidate` means master or a version not released yet:
  it does not.
- Decide from `release.py`, not from the request or the branch name. A
  request rarely names the version, a branch is often named after a ticket,
  and a branch name can be wrong for the code it holds. When `release.py`
  and the branch name disagree, say so and ask which version the change
  targets.
- An enterprise or customer addons repository has no `release.py`: read the
  one of the community checkout it runs with.
- Say which version you found and which policy follows, in your reasoning
  and in your reply, before writing the change.
- A fix for a released version goes to the oldest supported version that has
  the bug; see the odoo-git skill, Branches and pull requests.

## Changes in a stable version

Only bug fixes and localizations go to a released version; improvements and
features go to master. A fix merged in a released version is forward-ported
by the bots, never re-submitted per branch.

- Value over risk: keep the change minimal and strictly about the bug. If the
  risk is high or the value low, it belongs in master.
- No improvements, technical or functional, and no purely cosmetic changes
  (formatting, PEP 8, restyling). Match the surrounding code's style.
- Public model methods (no `_` prefix) are API for integrators: never change
  their signature. Avoid changing private signatures too, extension modules
  override them.
- No data-model change: stored columns are never added, removed, or changed
  to an incompatible type. Compatible tweaks (`ondelete`, `size`) are allowed
  when needed; a non-stored computed field may be added if really necessary.
- Keep XML ids of existing data, and don't delete data records that user data
  may reference, unless essential and the records were `noupdate` from the
  start.
- Don't modify existing translatable source terms, even for a typo; that
  breaks existing translations. Correct a term in master, or add an
  English-to-English translation in stable. Adding or deleting terms is fine;
  don't ship `.pot` updates, they are exported and synced automatically.

## The fix must work on a database that is not updated

After a pull and a restart without `-u`, a database runs the new Python and
JavaScript, but keeps the views, QWeb templates (mail and report templates
included), menus, and data records it was installed with. Records in a
`noupdate` block stay as they are even after an update. So:

- The fix must work from the code alone. Python must never depend on a
  changed XML view, template, or record: no new class, attribute, field
  reference, or markup in XML that the Python code then relies on.
- Change XML only when inevitable, and then the database that keeps the old
  XML must keep working and still get the fix.
- To change what a template renders, produce the change in Python or
  JavaScript instead, even if that duplicates the template's markup. Leave a
  comment saying it is a stable fix, so master can move it back.
- A fix may need an explicit module update as long as users who don't run it
  are safe. A critical security fix must work with a pull and a restart
  alone.

## On master

None of the stable rules apply. Fix the cause where it belongs: add the
field, change the signature and its callers, edit the template. Don't carry
a stable workaround into master code; when one was forward-ported, master is
where it gets cleaned up.
