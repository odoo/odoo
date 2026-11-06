# Plain ASCII punctuation in comments and messages

Write code comments, docstrings, user-facing strings and commit messages with
ASCII punctuation only. The character that keeps showing up is the em dash
(`—`): replace it with a comma, a colon, a semicolon, parentheses, or two
sentences, whichever the sentence actually needs. Same for the en dash (`–`),
curly quotes (`“ ” ‘ ’`) and the ellipsis character (`…`): write `-`, `"`, `'`
and `...`.

```python
# bad
# lxml removes the tail text with the node — move it to the parent first
raise UserError(self.env._("Book %s is already borrowed — return it first", book.name))

# good
# lxml removes the tail text with the node: move it to the parent first
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

# No comment unless the code cannot show why

Write no comment by default. Add one only where a reader of the file cannot
see why the code below is written this way:

- a reason outside the file forces lines that look wrong or useless, or that
  depart from a guideline: a library or browser bug, a standard or a
  law (name it and its section), a spec or a ticket, a caller that cannot
  change;
- a workaround meant to go away: say when, `To remove when ...`;
- in a test, the scenario the next steps simulate, or the state a wait waits
  for when the wait only exists to avoid a race;
- the comments other guidelines ask for: a `sudo()` (`odoo-security`), an
  unavoidable commit
  ([Transactions and exceptions](orm.md#transactions-and-exceptions)), an
  `at_install` test ([Tests](tests.md#tests)).

Such a comment is one or two lines, says why, and describes the code as it is
now. The rest goes where it is checked or found:

- what the code does: a clearer name, or a smaller function;
- why the code changed, the bug it fixes, the alternatives dropped: the commit
  message, which `git blame` reaches from the line;
- what a test expects: an assertion.

```python
# bad: restates the filter, then tells the story of the fix
# Only keep the active books, as the archived ones were counted twice
# in the total before this fix.
books = books.filtered("active")

# good: the code says it
books = books.filtered("active")

# good: what forces the line lives outside the file
# The mobile app sends the due date in the user's timezone, not in UTC.
due_date = self._to_utc(due_date)
```

## Why

- A comment is code that no test runs. When the code under it changes, nothing
  tells the author the comment is now false, and the next reader trusts it.
- A comment that restates the code is one more thing to read and to keep in
  sync, and it says nothing the code does not.
- The story of a change is true on the day of the commit. In the commit
  message it stays tied to that day; in the file it is wrong as soon as the
  next change lands.

## Exceptions

- Docstrings and JSDoc that document a function for its callers (parameters,
  return value, types).
- An existing comment stays, unless the change makes it false: then the change
  fixes or removes it.
