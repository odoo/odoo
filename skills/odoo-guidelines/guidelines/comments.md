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
  [Changes in a stable version](../../odoo-stable-policy/SKILL.md#changes-in-a-stable-version)).

# Comment a deviation the requirements force

When a requirement makes code break a guideline (the task's spec, a ticket,
a caller that cannot change), the code says so where it happens: a comment at
that spot names the guideline it departs from and the requirement that forces
it. Everywhere else, the guideline applies as written.

```xml
<!-- good: the reader and the reviewer see why, and where the decision comes from -->
<!-- XML ids: keeps its old id rather than library_book_action, because the
     mobile app opens this action by its id and cannot be updated with us. -->
<record id="action_book_list" model="ir.actions.act_window">
```

## Why

- A reviewer applies the guidelines to the code in front of them; without
  the comment, a deviation the requirements asked for reads as a mistake, and
  gets flagged or "fixed".
- The comment ties the deviation to its reason: the day the requirement
  changes, the next developer knows the code can follow the guideline again.

## Exceptions

- Rules that already say how to justify themselves keep their own form: a
  `sudo()` or a commit carries its comment as `odoo-security` and the
  [Transactions and exceptions](orm.md#transactions-and-exceptions) section
  say.
