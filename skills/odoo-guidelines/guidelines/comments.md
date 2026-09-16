# Plain ASCII punctuation in comments and messages

Write code comments, docstrings, user-facing strings and commit messages with
ASCII punctuation only. The character that keeps showing up is the em dash
(`—`): replace it with a comma, a colon, a semicolon, parentheses, or two
sentences, whichever the sentence actually needs. Same for the en dash (`–`),
curly quotes (`“ ” ‘ ’`) and the ellipsis character (`…`): write `-`, `"`, `'`
and `...`.

```python
# bad
# recompute the totals — the taxes may have changed
raise UserError(self.env._("Book %s is already borrowed — return it first", book.name))

# good
# recompute the totals: the taxes may have changed
raise UserError(self.env._("Book %s is already borrowed, return it first", book.name))
```

## Why

- The em dash is not on the keyboard layouts the codebase is written with, so
  in practice it arrives by copy-paste or from a generation tool. A diff full
  of them reads as text nobody typed.
- ASCII punctuation is greppable and diffable. A comment or a commit message
  is searched for with what a reviewer can type.
- A translatable literal is keyed on its exact source string, so two variants
  of the same sentence that differ only in the dash are two terms to translate
  (see [Translate only static literals](python.md#translate-only-static-literals)).

## Exceptions

- Data, not prose: a test fixture, a localization file, or a string whose
  content is the character itself.
- Existing text in a stable branch. Fixing punctuation is a cosmetic change,
  and rewording a translatable term breaks its translations (see
  [Changes in a stable version](stable.md#changes-in-a-stable-version)).

# Commit messages

The canonical rules are Odoo's
[git guidelines](https://www.odoo.com/documentation/master/contributing/development/git_guidelines.html).
What a review checks:

- Header: `[TAG] module: describe the change in a short sentence`, about 50
  characters, and a valid sentence once read as "if applied, this commit will
  <header>". Not a single word such as "bugfix" or "improvements".
- Tag, one of `[FIX]`, `[REF]`, `[ADD]`, `[REM]`, `[REV]`, `[MOV]`, `[REL]`,
  `[IMP]`, `[MERGE]`, `[CLA]`, `[I18N]`, `[PERF]`, `[CLN]`, `[LINT]`. `[ADD]`
  is for a new module and `[IMP]` for the incremental improvements that most
  master commits are; `[MOV]` changes nothing else, so move with `git mv` and
  change the content in a second commit.
- Module: the technical name, since the functional one changes over time.
  Several modules are listed, or `various` when the change is cross-module;
  split a commit per module where you can, so one can be reverted alone.
- Body: why the change is made, and the technical choices when there were any.
  What changed is in the diff. A reviewer reads the body to know what the code
  should do, and the review checks the code against that claim.
- References last, one per line: `task-123`, `opw-123`, `Fixes #123` (issue),
  `Closes #123` (PR).
