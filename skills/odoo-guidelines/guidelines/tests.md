# Tests

- Use `TransactionCase` (or `HttpCase` for web); start new business tests from
  `odoo.addons.base.tests.common.BaseCommon` (independent non-admin user and
  company, mail side effects disabled), or
  `TransactionCaseWithUserDemo`/`HttpCaseWithUserDemo` when demo data is
  needed (it is not guaranteed present). Assert behavior, not implementation.
- Tests are tagged `standard` and `post_install` by default (fully-loaded
  registry); set exactly one of `at_install`/`post_install`; the check is
  only a log warning, and *both* tags makes the class run twice while
  *neither* makes it never run. Opt into
  `@tagged('at_install', '-post_install')` only when the test must run before
  other modules load, with a comment justifying it: `at_install` prevents
  runbot parallelization, and an `HttpCase` must stay `post_install`. Tests
  run only for installed modules.
- Silent skips: a test file must be named `test_*.py` **and** imported from
  `tests/__init__.py`; the test class must be *defined* in that file (a class
  merely imported into it is skipped); and inherited `test_*` methods are not
  collected: a subclass defining no tests of its own runs nothing unless it
  sets `allow_inherited_tests_method = True`.
- `assertQueryCount` only when strictly necessary, and never inside a business
  test: it breaks on any unrelated ORM change. Keep it to dedicated
  performance tests, paired with `@warmup` (and `@users`); only *exceeding*
  the budget fails; a lower count merely logs, so keep budgets exact.
- Wrap expected-error and warning logs in `mute_logger(...)` so the expected
  ERROR or WARNING never reaches the runbot log.
- Tours: a step that triggers a page unload must set `expectUnloadPage: true`,
  and the last step must leave the client in a stable state (no pending edits
  or in-flight requests) to avoid teardown race conditions.

# Assert only on the records the test created

A search, a count or a name lookup that a test asserts on must not depend on
records the test did not create: give the test records a name no demo or data
record carries, restrict the domain to them, or assert the difference from a
count taken before. Never unlink or archive the records already there to get
an empty model.

```python
# bad: a demo book named "Dune" is found too, demo books are counted too
book = Book.create({'name': 'Dune'})
self.assertEqual(Book.search([('name', 'ilike', 'Dune')]), book)
self.assertEqual(Book.search_count([]), 1)

# good
count_before = Book.search_count([])
book = Book.create({'name': 'Dune Test Edition'})
self.assertEqual(Book.search([('name', 'ilike', 'Dune Test Edition')]), book)
self.assertEqual(Book.search_count([]), count_before + 1)
```

## Why

- Demo data is not installed by default, so the CI of a pull request runs
  without it, but some runbot builds install it. There the search also finds
  the demo records of every installed module: the test is green on the pull
  request and red after the merge.
- The data records of other modules are there whenever those modules are
  installed, as on the builds that install every module.
- Unlinking or archiving the existing records in the setup ties the test to the data of
  other modules: which records must be canceled first, which fields exist
  without the enterprise modules.

## Exceptions

- A model that only the test creates records of, such as a model of a test
  module.
