# Adding a guideline

## Files

- Guidelines live in `guidelines/`, one file per domain: `orm.md`, `xml.md`, `tests.md`,
  and a new file the day a domain has guidelines of its own.
- Inside a file, one guideline per `#` section. The title states the rule: "Batch ORM
  calls", not "Loops".
- Order inside a file means nothing. No rule outranks another.

## Two kinds of guideline: conventions and rules

- A **convention** is a choice that fits in one line and can be followed as stated.
  - Examples: `_id` suffix on a `Many2one`, one model class per file.
  - Needs no explanation.
  - Written as a bullet.
  - Conventions are grouped by topic, one section per topic.
- A **rule** needs an explanation to be applied correctly.
  - Written as its own section: the rule, then why it exists, then the cases where it
    does not apply.
  - A few sentences is the normal size. Sub-headings and code blocks are allowed, not
    required.
- Promote a convention to a rule when it keeps being violated even though the
  convention was loaded. That shows it needs the explanation.

## Writing the rule itself

- State the rule as something a reviewer can check against code with a yes or no.
  - Good: "no `create` call inside a loop".
  - Bad: "write efficient code".
- The why and the exceptions come after the rule. They do not replace a clear rule.
- Name the alternative. A rule that forbids something says what to write instead.

## Examples

- An example is optional. Add one when the rule is hard to state without it, and keep
  it schematic: the smallest tree or snippet that carries the concept.
- Show the same code both ways when seeing it break the rule is what makes the rule
  clear.
- Do not copy real code. Use schematic model names such as `library.book`, never a
  real one: a real name makes the guideline show up in every grep for that model.
- Do not point at real files or directories. Nothing checks them, and a stale
  reference is worse than none.

## Registering the guideline

- Add a row to the table in `SKILL.md`.
- The "Read it when" cell names the files or the activity that should trigger reading
  the guideline. Not every edit of every file.
- The link points at the section title. Renaming a title changes the anchor, so update
  the row with it.
