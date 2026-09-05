# Adding a guideline

- One numbered file per rule or per domain of conventions, named
  `guidelines/NNNN_snake_case_title.md`. `NNNN` is the next free number and is never
  reused, even if a guideline is deleted. It is an identifier, not a priority: the order
  of the numbers means nothing.
- Say each rule so that following it is checkable, then why it exists, then the
  exceptions.
- Two kinds of file. A convention is a choice that can be stated in one line and
  followed as stated: 4-space indent, `o_<module>` class prefix. Conventions are bullets,
  grouped in one file per domain (one kind of file or one topic). A rule needs an
  explanation to be applied correctly: a why, an example, exceptions. A rule gets its own
  file: the rule, code that follows it, the same code breaking it, why, then the cases
  where it does not apply. A convention that keeps being violated despite being loaded
  has shown it needs the explanation; promote it to a rule file.
- Examples are schematic: the smallest tree or snippet that carries the concept. Do not
  copy real code or point at real files or directories; nothing checks them, and a stale
  reference is worse than none.
- Add a row to the table in `SKILL.md`. The "Read it when" cell names the files or the
  activity that should trigger reading the guideline, not every edit of every file.
