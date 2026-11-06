---
name: odoo-runbot-errors
description: >-
  Investigate and fix a runbot error (runbot.odoo.com/odoo/error/<id>): read
  the error and its builds over JSON-RPC, check that nobody already handles
  it, rule out a runbot event, find the breaking PR, pick the first affected
  version, reproduce, fix with a test, and fill the fixing PR, breaking PR and
  assigned fixer of the error. Use when a test fails on runbot (nightly,
  staging, or the CI of a pull request), or when asked to look at a runbot
  error.
---

# Fixing a runbot error

A runbot error is a bucket of failed builds that share a fingerprint. The
steps below go in order. Steps 1 to 5 read only runbot and git: no database
is built before the error is known to be new, real, and on the right version.
`references/` holds the details; each step names the page to read.

## Reading runbot

The HTML pages of runbot (build, batch, bundle, error) run a Turnstile check
that a script does not pass. Read the records over JSON-RPC instead, with the
`session_id` cookie of your own runbot session:

```bash
curl -s https://runbot.odoo.com/web/dataset/call_kw/runbot.build.error/read \
  -H 'Content-Type: application/json' -b "session_id=$RUNBOT_SESSION" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"runbot.build.error",
  "method":"read","args":[[<id>],["name","random","test_tags","first_seen_date",
  "first_seen_batch_ids","build_count","version_ids","responsible","fixing_pr_id",
  "fixing_bundle_id","breaking_pr_id","previous_error_id","error_content_ids"]],
  "kwargs":{}}}'
```

The models to read, the build logs and the nightlies:
[references/read-runbot.md](references/read-runbot.md).

## Steps

1. **Read the error and one failing build.** The traceback is the `content`
   of the `runbot.build.error.content` records; `runbot.build.error.link`
   lists every build of the bucket. The name of the error is its first
   sample, not the bucket: read a few recent builds before trusting it. One
   failure can also sit in several errors, split by the text of the message:
   search `runbot.build.error` on the test method, closed ones included, to
   find who was asked before. The first red build is the oldest `log_date`
   of the links: `first_seen_date` only points at the first batch. In a run
   with many failures, read the first error, not the most frequent one. A
   message that points elsewhere (a translation error, a browser shutdown, a
   script timeout): [references/known-errors.md](references/known-errors.md).

2. **Check it is not already handled.** Before any code:
   - `fixing_pr_id` of the error, and of `previous_error_id` (a closed
     error that fails again comes back as a new one); `fixing_bundle_id`
     is the bundle of that PR, with its enterprise branch if any;
   - a PR or branch that names the error id
     (`gh search prs --owner odoo <id>`);
   - the commits since the failing build, on the test file and on the source
     of the feature: `git log --oneline <build commit>..odoo/<version> --
     <files>`. A commit the last failing build did not have yet
     (`git merge-base --is-ancestor <fix> <build commit>` fails) is a
     candidate: read it, check that it addresses this traceback and that
     the error has had no build since it landed. Then fill the fields
     (step 8) and stop.

   When nobody handles it (`responsible` empty or yours), set `responsible`
   to yourself now, before step 3: it tells the others that the error is
   taken. When step 1 found an error to link it to, leave it empty; when
   step 3 shows it, take your name off again: the link refuses two
   different `responsible`.

3. **Rule out a runbot event.** A frozen host, a build killed by load, one
   red hour on many bundles, or a test that the CI of pull requests skips is
   not a bug of the test, and no code change fixes it. Check before building
   anything: [references/runbot-events.md](references/runbot-events.md). When
   the evidence says infrastructure, write it on the error (the host, the
   hour, the sibling builds) and stop.

4. **Find the breaking PR.** The breaking commit merged before the first red
   build and after the last green build of the same configuration.
   `git log -S'<culprit line>' --format='%h %cd %s' odoo/<version> -- <file>`
   finds it; its PR is the `closes odoo/odoo#<n>` trailer. Date commits with
   the committer date (`%cd`), never the author date. When no commit lines
   up, say "breaking PR not found" and what was checked; never guess.
   Stagings, rare failures and nightly-only tests:
   [references/breaking-pr.md](references/breaking-pr.md).

5. **Pick the first affected version.** The version where runbot saw the
   error is not where the fix goes: the fix targets the oldest affected
   supported version where the fix meets stable policy (see the target rule
   of the `odoo-git` skill), and the forward port carries it up.
   `version_ids` of the error is a floor, never the answer. With a known
   breaking commit, the first affected version is the oldest supported
   branch that holds it; without one, run the test on each candidate
   version.
   [references/first-affected-version.md](references/first-affected-version.md).

6. **Reproduce** on that version before claiming a cause. A test that is
   `random`, ends on a timeout, or passes alone is a race or an order
   dependency: reproduce it under the same conditions as the build (repeated
   runs, a loaded CPU, the module set of the failing build) before changing
   code.

7. **Fix the cause.** Fix the code at fault, not the test that shows it, and
   keep the meaning of the test. A timeout raise or a retry is a fix only
   when the numbers show it would have saved the failing build. The fix
   comes with a test that is red without it: run it once on the code without
   the fix. The commit follows the `odoo-git` skill, with the full URL of
   the error as its last line (`https://runbot.odoo.com/odoo/error/<id>`),
   not `runbot-<id>`. When the error has `test_tags`, runbot skips the
   test in the CI of pull requests, except in the bundle of the PR set as `fixing_pr_id`: set
   that field (step 8) once runbot lists the PR, then rebuild, so that the
   CI of the fix runs the test.

8. **Fill the error.** Set what you know on the error, as soon as you know
   it:
   - `fixing_pr_id`: the PR of the fix (in the repository of the failing
     test when the fix spans odoo and enterprise);
   - `breaking_pr_id`: the PR of step 4;
   - `responsible`: whoever works on the error, set at the end of step 2
     and not once the fix exists.

   Write only sure values, and only into an empty field: a value someone
   else set stays, and a disagreement goes in the chatter of the error. An
   error left with an empty fixing PR keeps being picked up by the next
   person. Cases (fixed by someone else, linked errors, `test_tags`):
   [references/error-fields.md](references/error-fields.md).

## References

| Read | When |
| --- | --- |
| [read-runbot.md](references/read-runbot.md) | any read of an error, build, batch, bundle, log or nightly |
| [runbot-events.md](references/runbot-events.md) | a timeout, a stall, a red hour, a dead browser, a killed install, a network drop, a test the CI of a PR skips (step 3) |
| [breaking-pr.md](references/breaking-pr.md) | the breaking commit does not stand out (step 4) |
| [first-affected-version.md](references/first-affected-version.md) | the version of the fix (step 5) |
| [error-fields.md](references/error-fields.md) | the fields of step 8, and two errors that are one |
| [known-errors.md](references/known-errors.md) | a message whose cause is in another test, the browser shutdown, or the host |
| [pr-ci-and-mergebot.md](references/pr-ci-and-mergebot.md) | a red status of a PR, a failed staging, whether a PR merged |
