# Tests

- Use `TransactionCase` (or `HttpCase` for web); start new business tests from
  `odoo.addons.base.tests.common.BaseCommon` (independent non-admin user and
  company, mail side effects disabled), or
  `TransactionCaseWithUserDemo`/`HttpCaseWithUserDemo` when demo data is
  needed (it is not guaranteed present). Assert behavior, not implementation.
- Tests are tagged `standard` and `post_install` by default (fully-loaded
  registry); set exactly one of `at_install`/`post_install` — the check is
  only a log warning, and *both* tags makes the class run twice while
  *neither* makes it never run. Opt into
  `@tagged('at_install', '-post_install')` only when the test must run before
  other modules load, with a comment justifying it — `at_install` prevents
  runbot parallelization, and an `HttpCase` must stay `post_install`. Tests
  run only for installed modules.
- Silent skips: a test file must be named `test_*.py` **and** imported from
  `tests/__init__.py`; the test class must be *defined* in that file (a class
  merely imported into it is skipped); and inherited `test_*` methods are not
  collected — a subclass defining no tests of its own runs nothing unless it
  sets `allow_inherited_tests_method = True`.
- `assertQueryCount` only when strictly necessary, and never inside a business
  test: it breaks on any unrelated ORM change. Keep it to dedicated
  performance tests, paired with `@warmup` (and `@users`); only *exceeding*
  the budget fails — a lower count merely logs, so keep budgets exact.
- Wrap expected-error and warning logs in `mute_logger(...)` so the expected
  ERROR or WARNING never reaches the runbot log.
- Tours: a step that triggers a page unload must set `expectUnloadPage: true`,
  and the last step must leave the client in a stable state (no pending edits
  or in-flight requests) to avoid teardown race conditions.
