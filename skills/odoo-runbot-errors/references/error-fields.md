# The fields of the error

Read for the fields of step 8, whether you fixed the error, someone else did, or no code was
needed.

## The fields

| Field | Label on the form | Value |
| --- | --- | --- |
| `fixing_pr_id` | Fixing PR | the PR of the fix, a `runbot.branch` that is a PR |
| `breaking_pr_id` | Breaking pr | the PR that brought the error (step 4) |
| `responsible` | Assigned fixer | the person who fixes it |

- Read the three fields before writing. Write only sure values, into an empty field. A value
  someone else set stays: what you found instead goes in the chatter of the error.
- Runbot knows a new PR a few minutes after it opens: set the other fields first, and the fixing
  PR once runbot lists it. On an error with `test_tags`, that field is what makes the CI of the
  fix run the test (`runbot-events.md`).
- `team_id` comes from the module or the file of the failure. A wrong team can be changed on the
  form; say why in the chatter.

## Fixed by someone else

- The `closes odoo/odoo#<n>` trailer of the fixing commit is the fixing PR, even when the title
  of that PR is about something else: a fix can ride as an extra commit on another PR. Check the
  `Part-of:` siblings of the commit.
- Set `fixing_pr_id` and `breaking_pr_id` when they are empty. `responsible` is whoever works on
  the error, set as soon as the work starts; a fix by someone else leaves it as it is.

## Closing an error

`active` is the "Open (not fixed)" flag. An error with `test_tags` stays open until a runbot
admin closes it once the fix shows in the builds that ignore the tags: the fixer does not close
it, and the close is what stops the skip.

A new failure only joins an open error with the same fingerprint, so an error closed too early
comes back as a new one, with `previous_error_id` set.

## Two errors that are one

One failure can be split into several errors by the text of its message. Linking them is done by
someone with the error manager rights, and the result depends on which error survives:

- "Merge build errors" merges the selection into the first one of the sort
  `(not test_tags, not responsible, error_count, id)`. `error_count` counts contents, not builds,
  and the sort is ascending: a fresh one-content error with a responsible beats an old
  unassigned one.
- The merge is refused when the errors carry a different `responsible`, `fixing_pr_id` or
  `breaking_pr_id`. Do not fill the fields of an error that is about to be linked: check its
  siblings first (step 1).
- To pick the survivor, set "Linked to" (`error_id`) on the contents of the other errors.
