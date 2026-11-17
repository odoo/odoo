# odoo-review-guideline-recall

Review of one PR seeded with a violation of every rule of the
`odoo-guidelines` and `odoo-web-guidelines` skills, of the `odoo-security`
skill, and of what `odoo-review` adds (code the diff never shows, the merits
pass). It measures how many of the 142 seeded issues a review reports, and
in which areas.

- Checkout: master at c8d7430e (20.1 alpha), with John Doe's commit on
  `master-equipment-booking-jdoe`, `[ADD] equipment_booking: book shared
  equipment`. The new module lets employees and portal customers book
  maintenance equipment: backend views, a booking board (an Owl client
  action with its SCSS), portal pages, a label report, a reminder cron, an
  extend wizard, tests. The commit also changes
  `maintenance`: `serial_no` is renamed `serial_number` and
  `_get_owner_methods_by_equipment_assign_to` takes a `date`, which breaks
  `stock_maintenance`, `fleet_maintenance` and `hr_maintenance`, none of
  them in the diff.
- The module installs (with demo data), its tests pass, and the booking
  board renders in the webclient without console errors; every issue is in
  code that loads. Each issue sits on its own spot, so a finding maps to
  one entry of the answer key.
- Instruction: a complete review of the last commit, written to
  `/app/review.md`, without changing the code.
- Graded on:
  - recall, per area: one LLM judge per area, one binary criterion per
    seeded issue (`tests/<area>/judge.toml`). An area's score is the share
    of its issues the review reports at their spot;
  - `reward`: the share of all 142 issues. Every issue weighs the same (the
    guidelines rank no rule above another), so each area weighs its number
    of issues;
  - `precision`: a judge rates the share of the review's findings that are
    true of the PR, seeded or not. It is reported, and kept out of the
    reward.
- An empty or missing review scores 0 on every dimension, judges skipped.

| Area | Issues | Rules |
| --- | --- | --- |
| structure | 8 | guidelines/module_structure.md |
| manifest | 6 | guidelines/manifest.md |
| python | 13 | guidelines/python.md (imports, naming, layout, translations) |
| comments | 3 | guidelines/comments.md |
| orm | 16 | guidelines/orm.md |
| fields | 12 | guidelines/fields.md |
| controllers | 2 | guidelines/controllers.md |
| xml | 12 | guidelines/xml.md |
| reports | 3 | guidelines/reports.md |
| access | 4 | guidelines/security.md |
| performance | 5 | guidelines/performance.md |
| tests | 9 | guidelines/tests.md |
| javascript | 4 | odoo-web-guidelines guidelines/javascript.md |
| scss | 12 | odoo-web-guidelines guidelines/scss.md |
| assets | 3 | odoo-web-guidelines guidelines/assets.md |
| security | 23 | odoo-security |
| consumers | 2 | odoo-review, Code the diff never shows |
| merits | 5 | odoo-review, Merits pass (no guideline) |

Rules left out:
- the ones a new module cannot break: the `active` trap of `<template>`,
  `populate/`;
- tours, and the manifest's `assets` key (the module declares its bundle
  there, as the rule asks);
- the ~80-column SCSS lines, which no spot of their own seeds;
- the stable policy (the target is master);
- the soft preferences: "wizard" in model names, `main.py`;
- those whose violation stops the module from loading on master: data
  file load order, a `version` that is not 2 to 5 parts, `_log_access =
  False` on a TransientModel, a Monetary without a currency field.

## The answer key

`answer_key/catalogue.py` lists the issues: area, file, an anchor string on
the issue's line, and what the judge looks for. `answer_key/generate.py`
writes `tests/<area>/judge.toml`, `tests/reward.toml` and the oracle review
`solution/review.md` from it. After changing the module or the catalogue,
regenerate against a checkout with the PR applied:

    python3 answer_key/generate.py <checkout> .

The PR itself is `environment/change.patch` and
`environment/commit_message.txt`.
