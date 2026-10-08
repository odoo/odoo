---
name: odoo-git
description: >-
  Odoo's git conventions: commit message format ([TAG] scope: header, a
  why-first body, reference trailers), which branch a change targets, branch
  naming, and pull request hygiene. Use when writing or amending a commit
  message, choosing the branch a fix or feature goes to, or opening or
  updating a pull request on an Odoo repository.
---

# Odoo git conventions

These conventions apply to every commit and pull request on an Odoo repository
(community, enterprise, and their forks). They are house rules, not general git
advice.

## Commit message

A commit message is a header `[TAG] scope: summary`, a blank line, a body that
says **why** the change is made, and reference trailers last, one per line.

```
[FIX] bookshop: keep open orders visible after a book is archived

Steps to reproduce:
- Archive a book that still has open orders
- Open the customer's portal page

The open orders of that book are gone from the page, so the customer
loses track of what they are still waiting for. They should stay listed
until they are delivered.

The order list was searched through the book with the default active
filter, so archiving the book filtered its orders out.

After this commit, the order list searches orders directly, with
active_test disabled on the book relation, so an archived book still shows
its open orders until they are delivered.

task-1234
opw-5678
```

```
[IMP] bookshop, *: bugfix and improvements

Fixed the order list and improved the portal page. Also updated the tests.
```

The second message mixes fixes with improvements, uses a vague noun phrase
for the summary, and says what changed without explaining why.

### Header

- `[TAG]`, a space, the scope, a colon, a space, then the summary. Use the
  module's technical name or the relevant framework or repository subsystem
  (`orm`, `core`, `tools`, `skills`). Several modules:
  `[FIX] bookshop, portal:`. Many modules: the main one then `*`
  (`[REF] bookshop, *:`), or `*` alone for a transversal change; the body
  then lists the modules the `*` stands for.
- The summary completes the sentence "if applied, this commit will ...": an
  imperative verb, no trailing period, about 50 characters.
- The entire header should fit 70ish characters (closer to 80 when the module
  name is long).
- "bugfix", "improvements", "changes" are not summaries.
- Tags:

  | Tag | Use |
  | --- | --- |
  | `[FIX]` | bug fix, in stable or in master |
  | `[IMP]` | incremental improvement, the default in master |
  | `[REF]` | refactoring, a feature heavily rewritten |
  | `[ADD]` | new module |
  | `[REM]` | removed resources: dead code, views, modules |
  | `[MOV]` | files or code moved without content change, so history follows |
  | `[REV]` | revert of an earlier commit |
  | `[PERF]` | performance: speed, memory, query or RPC count |
  | `[CLN]` | cleanup |
  | `[LINT]` | lint pass |
  | `[I18N]` | translation files |
  | `[REL]` | release |
  | `[MERGE]` | merge commit |
  | `[CLA]` | signing the contributor license agreement |

### Body

The diff gives the what. The rest of the message comes from outside it: the
why and who it affects from the task, ticket, or reporter; the reported
scenario from the ticket; benchmark figures from a measurement; the reason
for a revert from the regression it answers. Reading the code tells you what
it can do wrong, never what was reported. Ask the author for what the
message needs and the conversation does not hold: for a fix, the ticket or
issue and the reported scenario; for a feature, the task and who asked for
it. When the answer is not at hand, write from what the code and the tests
show, then tell the author which parts are derived and which are missing,
and offer to amend. A plausible guess presented as the report is worse than
a question; a missing section is a review round trip.

- Why first: the purpose of the change, what was wrong for whom. The diff
  already shows what changed; describe the what only for a technical choice,
  and then say why that choice. "The PO team asked for it" is not a why.
- For a feature or an improvement, describe what it does and for whom.
- For a bug fix, give the steps that reproduce the bug: what to do, what
  happens, what should happen. Lead with the reported case; the test shows
  which cases the fix covers, and the other ones can follow. A fix message
  without the reported steps is not finished.
- "Before this commit, ... After this commit, ..." is a common shape for the
  why and the outcome; use it when it fits.
- For `[PERF]` commits, include a Benchmark section in the commit message.
  Describe the workload and relevant record counts, and report before/after
  measurements with the speedup or reduction for the metric improved.
  Include several dataset sizes when useful to demonstrate scaling. The
  figures come from a run, yours or the author's; ask for them when you
  have none.
- Wrap at about 72 characters. Be complete rather than short: the message is
  the whole change for most readers, and a linked task or ticket is not
  readable outside Odoo. Several paragraphs is normal.
- ASCII punctuation only, header included: no em dash, curly quotes or
  ellipsis character. A message is searched for with what a reviewer can type;
  see [Plain ASCII punctuation in comments and messages](../odoo-guidelines/guidelines/comments.md#plain-ascii-punctuation-in-comments-and-messages).

### Trailers

- Include applicable references, one per line, after the body: `task-123`
  (task), `opw-123` (support ticket), `runbot-123` (runbot error), `Fixes #123`
  (a GitHub issue this commit closes), `Co-authored-by: Name <email>`. Ask
  the author for the task, ticket, or issue; link what exists and leave the
  trailer out otherwise. Never invent a reference.
- Leave generated metadata to the bots: the merge bot adds PR linkage
  (`closes odoo/odoo#123` or `Part-of: odoo/odoo#123`), `Signed-off-by`, and
  `Related: odoo/enterprise#123`. Forward-port tooling adds provenance such as
  `X-original-commit` and `Forward-port-of`; the latter may appear in the PR
  body rather than the commit message. Preserve generated metadata and
  tooling-generated merge and release messages.

## Branches and pull requests

- Target: a bug affecting supported stable versions goes to the oldest
  affected supported stable version where the fix meets stable policy. Find
  the oldest affected version by checking the older stable branches for the
  faulty code; ask the author which versions are still supported when
  unsure. Fix bugs specific to master on master. A feature or any unstable
  change goes to master; a localization goes to either. A fix merged in a
  stable version is forward-ported to the newer versions by the bots.
- One pull request per patch: never open the same patch against several
  branches. If the forward-port needs manual help, do it in the forward-port
  PR the bot opened.
- Branch name: `<target>-<topic>` (`19.0-order-archive-fix`). Odoo employees
  append their Odoo handle (`master-bookshop-portal-chgo`); the handle need
  not be three letters. Take the handle from the user's existing branches,
  and ask when none shows it. The bots suffix their forward-ports with
  `-fw`.
- One logical change per commit, and one module per commit unless the change
  is inseparable; a move is its own `[MOV]` commit before the `[REF]` that
  edits the moved code.
- Development branches live on `odoo-dev` for Odoo employees and on a
  personal fork for external contributors; the PR is opened against `odoo`.
  Update the target locally with `git fetch origin <target>:<target>`: a
  target branch only fast-forwards and never carries local commits. Rebase
  the branch on it and push with `--force-with-lease`; when the push is
  rejected because the remote branch moved, `git pull --rebase` the branch
  first. Never merge the target into the branch.
- Rebase on the target branch before submitting and whenever it conflicts;
  squash fixups into the commit they fix. A PR carries only the commits that
  should land, never "address review" commits or merge commits.
- A change to a stable version follows
  [Changes in a stable version](../odoo-guidelines/guidelines/stable.md#changes-in-a-stable-version)
  of odoo-guidelines; a PR description explains why, as the commit message
  does, and links the relevant task, ticket, or issue when one exists.
- A bug fix comes with a test that reproduces it when one is possible.
- An external contributor signs the CLA in the PR, once.
