# The CI of a pull request and the mergebot

Read when a status of a PR is red, when a staging failed, or to know whether a PR merged (a
fixing PR, a breaking PR, a forward port).

## Did the PR merge?

The mergebot merges Odoo PRs: it pushes the commits itself and closes the PR. GitHub then shows
a merged PR as `CLOSED`, never `MERGED`, and its close event may name no one.

Read the mergebot page of the PR, `https://mergebot.odoo.com/odoo/odoo/pull/<n>`: a merged PR
shows `Merged at <sha>`, else `Closed`. The same page has the forward-port table, one row per
version, with the state of each hop (merged, ready, or not ready). A forward-port branch that
still exists is no proof that its hop is open: the bot does not always delete it.

`https://mergebot.odoo.com/runbot_merge/<branch id>` lists the stagings of a target branch, with
their PRs and their runbot batch (`/runbot_merge` lists the ids). A failed staging names its PRs
there; older ones are reached with `?until=YYYY-MM-DD%20HH:MM:SS&state=failure`.

## Staging failed: "inconsistent integration"

robodoo can comment "staging failed: inconsistent integration - succeeded for ... but failed for
odoo/odoo, odoo/enterprise" on every PR of a staging whose builds were all green: the mergebot
could not push the result to the target branch. Sign: green builds, the same comment on every
PR of the staging, and a target branch that did not move. No change to the code: once the
mergebot integrates again, someone with the rights on the PR writes `@robodoo retry`.

## Finding the PR of a branch

The PRs of odoo/odoo and odoo/enterprise have their head on the odoo-dev fork, so `gh pr view
<branch> --repo odoo/odoo` looks for a branch of odoo/odoo and says that no PR exists. Use `gh
pr list --repo odoo/odoo --head <branch> --state all`, or the PR number. Check it before opening
a second PR for the same branch.

## Red statuses that are not the change

- **`ci/codeowner` on a draft.** It is in error with "Some pr are draft, skipping" while the PR
  is a draft; once the PR is ready for review, it waits for the code owners. When every other
  status is green, the CI of the draft is green: change nothing for it.
- **`ci/style`.** It runs ruff with `--select ALL --preview` and a list of ignored rules, on the
  changed lines only; the configuration of a build is in its `logs/ruff_config.txt`. So it can
  flag a new line for a fault the old code around it has too, for example an import inside a
  function (PLC0415), parentheses in a dict subscript (RUF031), or one blank line before a
  top-level def where it wants two (E302). Run ruff on the changed file with that configuration,
  and format only the new block (`ruff format --range=START-END <file>`), so that the rest of the
  file stays as it is.
- **`ci/security` PY004.** Every newly touched line that uses `os.` or `subprocess.` gets PY004
  (seen on `subprocess.Popen`, `os.waitid`, `subprocess.TimeoutExpired`). It is a gate for the
  security team to acknowledge, not a fault: do not rewrite the code around it (a hand-written
  poll loop in place of `Popen.wait` was refused in review). Say in the PR description which
  lines carry it and why they need it, and leave the acknowledgement to the reviewers. Other
  findings can be real: PY026 flagged `ChromeBrowser(type(self))` in a test, and passing the
  test class by name cleared it.
