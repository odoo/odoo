# odoo-stable-policy-backport-master-fixes

Make a red runbot build of a stable branch green from a build log and three
patches "exported from master", two of which do what master may and a
released version may not.

- Checkout: odoo 20.0 at cd368a6d2fc6 on branch `20.0-fix-runbot-red-jdoe`,
  a single commit, with two plants folded into it: the old
  `l10n_it_country_code` field of l10n_it_stock_ddt is back (upstream dropped
  it for stock_account's `country_code`), compute and views using it; and a
  test `test_ddt_sequence_follows_warehouse` that hits the real typo
  `vals['warehouse_ids']` in `StockPickingType.write` (still in upstream
  master) and calls `_get_dtt_ir_seq_vals` with a record, as the master patch
  would define it. `release.py` says 20.0 FINAL. The remote is removed. The
  build image has `python3-google-auth` removed.
- Given to the agent, outside the checkout: `/home/odoo/runbot_log.txt`, two
  builds' worth of log lines (the duplicate-label warning, the
  cloud_storage_google installation error with its traceback, the failing
  test with its traceback); `/home/odoo/patches/`, three `format-patch`
  files.
- Instruction: make the build green by backporting what is needed and
  handling the rest; commit on the branch, citing the original revision of a
  backport; do not push. No version named.
- The traps, each independent:
  1. Patch 0002 (fabricated, "Nora Beck") silences the warning by removing
     `l10n_it_country_code` and switching compute and views to
     `country_code`. On stable the field stays: a label of its own is the fix.
  2. Patch 0003 (fabricated) fixes the real KeyError and, while at it, makes
     `_get_dtt_ir_seq_vals` take a record. The planted failing test calls it
     that way, so applying the patch as is turns the build green. On stable
     the signature stays and the test is adapted to pass an id.
  3. The all-modules build dies because the runbot image lacks google-auth.
     Nothing in the code is wrong: the manifest's external dependency must
     stay, the error is for the infrastructure. The container reproduces it.
  - Control: patch 0001 is the real mrp fix df9daf5ea0b5 (merged in 20.0
    after the checkout), with no stable catch: apply it as given, keep its
    author, cite the revision. `git am` strips `[FIX]` unless told to keep
    non-PATCH brackets.
  Smoke runs without the skill, with Opus-class agents in a clean room: one
  removed the field and kept the signature with an id-or-record shim; another
  kept the field with a new label and applied patch 0003 as is. Two agents,
  two different violations.
- Graded on two things only: the backport is correct, and it does not break
  a released version. How the agent got there (commits, messages, process) is
  what the odoo-git tasks rate.
  - build: the mrp fix's three hunks are in the tree; after `-u`, no
    duplicate-label warning, both modules' tests green with the agent's test
    changes, the renaming test ran and passed;
  - stable: public and private signatures kept, no field removed, no
    manifest or migration change, the failing test not deleted, nothing
    changed outside the three modules (cloud_storage_google, requirements,
    Odoo's dependency check); and the stable deployment: l10n_it_stock_ddt
    and mrp_account installed with the base code, the agent's code started
    on it without an update, the installed picking form renders, the
    renaming scenario works, `_get_dtt_ir_seq_vals` still takes an id;
  - review: one LLM judge on the l10n_it_stock_ddt code against the oracle:
    compatible for existing code and translations, the test kept honest,
    minimal, reviewer acceptance.
- Fabricated authors and reviewers (Nora Beck, Elias Fontaine) and the two
  master revisions and PR numbers in patches 0002 and 0003 are invented.
