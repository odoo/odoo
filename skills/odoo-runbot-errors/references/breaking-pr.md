# Finding the breaking PR

Read when the breaking commit does not stand out (step 4).

## Date the first red build

Count the `runbot.build.error.link` records of the error per day (`references/read-runbot.md`).
The breaking commit merged before the first red build and after the last green build of the same
configuration.

- **A first red build in a staging.** `first_seen_batch_ids` of the error gives its batch, and the
  bundle of that batch tells which kind: a `staging.<version>` bundle ran pull requests that were
  not merged yet. The breaking PR is one of that staging, and it may merge hours later, after
  more failed stagings, so its merge date can fall a day after the start of the graph. Say which
  staging went red first. The mergebot page of a PR lists its stagings.
- **A rare failure** gives no clean edge in the red builds. A behaviour change usually moves the
  duration of the test in every run, passing ones included: compare the duration of the test in
  the build logs before and after each candidate commit, with a test of the same file as a
  reference for the load.
- **A test only the all-modules nightly runs**: the last green and the first red nightly bound
  the window. Bisect it locally on one database built with the module set of the failing build,
  and confirm each end of the bisect with a few runs: a race decided by timing can point at the
  wrong commit after a single run.

## From the commit to the PR

- Date commits with the committer date (`git log --format='%h %cd %s'`), never the author date:
  a commit is often authored days before it lands, and `git log` prints the author date by
  default.
- The PR is the `closes odoo/odoo#<n>` trailer of the commit. A commit with `Part-of:
  odoo/odoo#<n>` and no `closes` is one commit of a PR of several: its PR is that number.
- On a forward port, `closes` names the PR of the failing version and `X-original-commit` the
  source. Give the first; add the source PR when the defect came with it.
- A new test that is flaky from its first build has its own PR as the breaking one.
- `duplicate_breaking_pr_count` of the error tells how many other errors already name the same
  breaking PR: read them, they may share the cause.
