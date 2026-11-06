# The first affected version

Read before picking the version of the fix (step 5). The target rule itself is in the `odoo-git`
skill: the oldest affected supported version, then the forward port. This page is how to find
that version for a runbot error.

## The walk

- `version_ids` of the error lists where runbot saw it. It is a floor for the walk, never the
  answer: an older version can have the same defect and no error yet, because a test only runs
  in some configurations, or came later on that version.
- Find where the failing test exists: `git grep -c '<test name>' odoo/<version> -- <test file>`
  on each supported version.
- **Breaking commit known**: the first affected version is the oldest supported branch that
  holds it. No measure is needed on the newer ones.
- **No breaking commit**: run the test on each candidate version, from the oldest that has it,
  and keep the oldest where it fails. Reading the code is not enough: a version can hold every
  piece of the bug and still pass.
- Say which versions were measured and which were not.

## A forward port has another sha on each version

Forward ports are cherry-picks: each version holds its own copy of a commit, with its own sha and
an `X-original-commit:` trailer. `git branch -r --contains <sha>` and `git merge-base
--is-ancestor <sha> odoo/<version>` only see the versions that hold that very sha, so they call
an affected older version clean.

Search by content instead: `git log -S'<line>' odoo/<version> -- <file>`, `git log
--grep='<subject>' odoo/<version>`, or grep the file on that version, and follow the chain with
the `X-original-commit` trailers.

## Dead versions keep their refs

A version that is no longer supported keeps its branch on the remote, and runbot may still build
it, so neither git nor runbot tells it from a supported one. A fix committed there reaches no
forward-port chain. When unsure which versions are supported, ask (see the `odoo-git` skill). A
walk that lands on a dead version enters the chain at the next supported one.

## A move hides where the line came from

`git log -L` follows a line range of one file and stops where the lines were moved in from
another place. It then names a refactor on a newer version, while the defect was already on an
older one under another path. Sign: the commit named as the origin only moves or reorganizes
code, on a newer version than expected. Grep the line itself on each supported version (`git
grep -n '<line>' odoo/<version>`), and run `git log -S'<line>'` on the oldest one that has it:
the first affected version is the oldest that holds the line, not where `-L` stopped.
