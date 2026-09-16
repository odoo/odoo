# odoo.tests — Conventions & Gotchas

## Where the framework's own tests live

| Suite | Runs via | Covers |
|-------|----------|--------|
| `odoo/addons/base/tests/test_test_suite.py` | odoo-bin `--test-tags` | runner logging, cleanups, skip, retry, `TestCursor` stack, `compute_stats` |
| `odoo/addons/base/tests/test_tests_tags.py` | odoo-bin | `tagged`, `TagsSelector` parser + selection |
| `odoo/addons/base/tests/test_form_create.py` | odoo-bin (post_install) | `Form` on real views, modifier merge, o2m `mode="form"` |
| `odoo/addons/base/tests/test_http_case.py` | odoo-bin (spawns Chrome) | `browser_js`, console error handling, screencasts |
| Tier-1/Tier-2 pytest (`cd addons/odoo && pytest` / `pytest odoo/orm/tests`) | pytest | do NOT cover odoo/tests directly; keep green anyway |

Quick battery after touching this package (disposable DB):

```
--test-tags /base/tests/test_test_suite.py,/base/tests/test_tests_tags.py,\
/base/tests/test_form_create.py,/base/tests/test_http_case.py,\
/base/tests/test_db_cursor.py,/base/tests/test_basecase.py
```

The whole-file specs are deliberate: the classes pinning the framework's own
behaviour live in those four files and are added to over time, so naming
classes individually silently stops covering new ones.

## Tagging rules

- Every test class must end up **either** `at_install` **or** `post_install`
  (`tagged()` warns otherwise). `HttpCase` should be `post_install`
  (registry must be fully loaded for assets/routes).
- `test_tags` is a plain set inherited through subclassing; `@tagged("-x")`
  removes. Position (`at_install`/`post_install`) is itself just a tag.
- `@tagged` also works on a single test **method**, and is applied over the
  class's tags by `BaseCase.__init__` — so `@tagged("post_install",
  "-at_install")` on one method moves just that method. `tagged()` stores the
  include and exclude halves separately for a method target
  (`test_tags`/`test_tags_exclude`) and issues no at_install/post_install
  warning there, because the resulting position is not knowable from the
  function alone.
- `test_sequence` (int attr) orders tests inside a suite.

## Public API surface

- `odoo.tests` re-exports exactly `common.__all__` + `Form`/`O2MProxy`/
  `M2MProxy`. **Adding a public helper to `common.py` requires adding it to
  `__all__`** or `from odoo.tests import X` won't resolve.
- `Command`, `patch`, `mute_logger` are *sanctioned* convenience re-exports;
  don't remove.
- `odoo.tests.common.ChromeBrowser` must remain a valid attribute (mock
  target used by bus/base tests and web tooling), even though the class
  lives in `browser.py`.  Likewise `HttpCase`/`Opener`/`Transport`/
  `JsonRpcException` live in `http.py` but stay re-exported from `common`;
  `http.browser_js` must keep instantiating via `common.ChromeBrowser`.
  - **Those four http names are resolved by a module-level `__getattr__`, not
    by an import.** `http.py` reaches `common` at module scope for
    `common.ChromeBrowser`; `common` importing `http` back was a real cycle,
    closed by an import on `common.py`'s last line. That placement also made
    the file order load-bearing -- every name `http.py` takes from `common` had
    to be defined above that line, with nothing enforcing it. Deferring drops
    the edge and the rule together. Adding a fifth such name means adding it to
    `_HTTP_EXPORTS`, to `__all__`, and to the `TYPE_CHECKING` block that keeps
    ruff's `F822` and the type checker satisfied.
    `TestCommonHasNoImportEdgeToHttp` pins all of it.

## Gotchas (hard-won)

- **Do not commit/rollback/close `cls.cr`** in a TransactionCase — it is
  patched to raise. Open another cursor (`self.registry.cursor()`) or use
  savepoints.
- `TestCursor._cursors_stack`: close order matters; `close()` removes the
  cursor itself and warns on out-of-order close. Never `pop()` blindly. A
  cursor still in the stack at class teardown is released by
  `release_stranded_test_cursors` (a module-level function, so it is testable
  without standing a suite up) — which must release the registry lock too, or
  every later HttpCase request stalls 20s and 500s, blamed on the wrong test.
- Every environment failure raises `InfrastructureUnavailable`, not bare
  `SkipTest`: it subclasses SkipTest for runner compatibility, but Odoo counts it
  apart, names it in the summary, and treats it as an error by default. Setting
  `ODOO_REQUIRE_INFRA=0` explicitly permits an incomplete local run and emits a
  warning; ordinary deliberate skips are unchanged. A host with no Chrome used
  to run zero tour assertions and exit 0.
  This covers `browser.py` throughout and `HttpCase.setUpClass` in `http.py`,
  which raises it when there is no HTTP server (`--no-http`, a port-bind
  failure, a crashed `spawn_http_server`).
- `@unittest.expectedFailure` is **refused**, not honoured: `run()` implements
  `__unittest_skip__` but not `__unittest_expecting_failure__`, and
  `OdooTestResult` has neither `addExpectedFailure` nor `addUnexpectedSuccess`.
  A decorated method raises `TypeError` at class-definition time; a decorated
  class is reported as an error when it runs. Assert the failure explicitly, or
  skip with a reason.
- `setUp` runs once per **attempt**, not once per test — `BaseCase.run` re-runs
  it on the same instance for every retry. Never derive an instance attribute
  from itself there (`self._logger = self._logger.getChild(...)` compounded),
  and never bind a cleanup to an object a later call replaces
  (`addCleanup(self.opener.close)` left `authenticate()`'s opener unclosed).
- `TestSuite.run` calls `_removeTestAtIndex` like the stdlib it vendors, so a
  finished test — and its env, registry, opener and proxies — is collectable.
  Ask `has_http_case()` **before** running a suite; a spent one answers False.
- HTTP requests during tests need `allow_requests` (lock release + cookie);
  requests without the current `test_request_key` cookie get HTTP 400 by
  design (`assertCanOpenTestCursor`).
- `assertQueriesContain` is **not** a subset check: exact query count,
  substring match per query. Both it and `assertQueries` share
  `_assert_queries`, differing only in the comparison they pass it.
- `assertQueries`/`assertQueriesContain` record **every** statement entry point
  (`common._STATEMENT_RECORDERS`), one entry per *call* — a bulk `create()`
  above `COPY_THRESHOLD` shows as `COPY "table" (...) FROM STDIN`, an
  `executemany` as its single query text. `execute_values` is listed in
  `_DELEGATING_STATEMENTS` instead because it reaches the server through
  `execute()`; recording it too would double-count. Adding a statement API to
  `Cursor` without putting it in one of those two sets fails
  `TestPatchExecuteStatementApi`. Captures are normalised to `str`, so a
  psycopg `Composable` no longer turns a mismatch into a `TypeError`.
  `assertQueryCount` still counts SQL *work* (N-row `executemany` = N,
  N-row `COPY` = 1), so the two numbers legitimately differ.
- `set_registry_readonly_mode` is restored at the end of the test that called
  it (snapshot taken in `BaseCase.setUp`). Calls from `setUpClass` still apply
  to the whole class. Do not hand-restore it in a `finally`.
- `testsRun` counts tests, not attempts: `BaseCase.run` wraps retries in
  `OdooTestResult.retry()`. Do not gate the counter on `soft_fail` — a test
  that passes on its first (soft) attempt would never be counted at all.
- `warmup`/`assertQueryCount`: the warm-up run executes the whole test body
  once with `self.warm = False`; assertions must be conditional on nothing —
  the framework skips the count checks itself.
- `assertQueriesConstant(run, small, large)`: `run(n)` at both sizes, each in
  a savepoint after `invalidate_all`, one warm-up run first; equal counts or
  the assertion fails. It pins the shape (no N+1) where `assertQueryCount`
  pins the number.
- Retry mode (`ODOO_TEST_FAILURE_RETRIES`) treats **any ERROR-level log**
  during a soft run as failure (`lower_logging`), not just assertions.
- `benchmark.compute_stats`: mean/median/percentiles are outlier-trimmed
  (indices trimmed jointly across time/db/query lists); `min_us`/`max_us`
  are raw extremes.
- Integer env vars (`ODOO_TEST_FAILURE_RETRIES`, `ODOO_TEST_MAX_FAILED_TESTS`,
  `ODOO_TOUR_DELAY_TO_CHECK_UNDETERMINISMS`, `ODOO_BROWSER_CPU_THROTTLING`)
  are read via `utils.env_int` — empty-but-set (common in CI) means default,
  never ValueError.  `ODOO_TEST_MAX_FAILED_TESTS <= 0` means unlimited.
- `allow_requests(all_requests=True)` restores the flag on exit
  (patch.object) — a plain assignment leaked it and disabled the cookie
  guard for the rest of the test.
- Ruff config marks `F401` unfixable — remove unused imports by hand.
- Py 3.14 / PEP 758: `except A, B:` (no parens, no `as`) is valid and is
  the enforced style — don't "fix" it back to parenthesized form.
- Chrome flakiness: `Thread.start()` can transiently refuse
  (`pthread_create`) under load — `ChromeBrowser.__init__` retries with
  fresh Thread objects; keep that pattern if touching the receiver setup.

## Debug loggers (campaign scaffolding, 2026-09-12)

Every module but `__init__.py` carries `_debug = DebugLog(__name__)` from
`odoo/libs/debug_log.py` and `_debug.<channel>("test.<area>.<event>", k=v)` sites —
`logic` (which branch), `perf` (spans with `ms=` and `queries=`), `pipeline` (hand-offs),
`lifecycle` (open / close / settle). Off under the default `log_level = info`; enable one
package-channel with `--log-handler odoo.debug.<channel>.tests:DEBUG`, all four with
four handlers. Per-test lines carry `test=<canonical_tag>`; a label read off an object a
test may replace with a double goes through `getattr` (`http._tag`). They are temporary
and removed together when the campaign ends — do not build on them, do not "clean them
up"; the removal recipe and the readings live in the knowledge vault under
reference/dev/debug-logging-campaign.md (section *tests*). One test knows about them:
`TestRunnerLoggingCommon._addError` in `odoo/addons/base/tests/test_test_suite.py` drops
`odoo.debug.*` records from the capture it asserts on.

## What NOT to do

- Don't import business-addon code here; `common.py` logs an error if the
  framework is imported by a non-test server process.
- Don't add state to `BaseCase` instances that survives across tests —
  environments/caches are reset per test by cleanups in
  `TransactionCase.setUp`.
- Don't make `browser.py` import `common.py` at runtime (only under
  `TYPE_CHECKING`) — the split exists so the CDP client stays importable
  without the framework; shared helpers go in `utils.py`.
