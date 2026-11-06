# Tests

- Use `TransactionCase` (or `HttpCase` for web); start new business tests from
  `odoo.addons.base.tests.common.BaseCommon` (independent non-admin user and
  company, mail side effects disabled), or
  `TransactionCaseWithUserDemo`/`HttpCaseWithUserDemo` when demo data is
  needed (it is not guaranteed present). Assert behavior, not implementation.
- Reuse the records the common test class already builds, and build the
  other records the tests of a class share once, in `setUpClass`: each test
  runs in a savepoint rolled back after it, so a test that needs another
  value writes it on one of those records instead of creating a new one,
  unless creating it is what the test checks. A
  record only one test uses is created in that test. Keep `setUp` for what
  must be new in each test (a per-test `patch`) or needs the `HttpCase`
  opener (`authenticate`, `url_open`), which does not exist in `setUpClass`.
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

# Freeze the cursor time with mock_datetime_and_now

A test that checks `create_date`, `write_date`, or any value the code takes from
`self.env.cr.now()` sets the time with `self.mock_datetime_and_now(dt)`, not with
`freeze_time` alone.

`freeze_time` moves `datetime.now()`, not the cursor. The cursor of a `TransactionCase`
asks PostgreSQL for `now()` once per transaction, and that transaction lasts the whole
test class: under `freeze_time`, records still get the real time at which the class
started, the same for every test of the class. `mock_datetime_and_now` freezes both.

The two clocks also differ with no `freeze_time` at all: `self.env.cr.now()` is the
time at which the class started, while `datetime.now()` and `date.today()` give the
time of the test. A test that compares a Python `date.today()` with a `create_date` or
a `cr.now()` value passes while both fall on the same day, and fails when the class
starts before midnight and the test runs after it: such a test also sets the time with
`mock_datetime_and_now`, so both clocks agree.

```python
# bad: datetime.now() is in 2024, create_date stays on the real clock
with freeze_time("2024-01-01 10:00:00"):
    book = self.env["library.book"].create({"name": "Dune"})

# good: both clocks say 2024-01-01 10:00:00
with self.mock_datetime_and_now("2024-01-01 10:00:00"):
    book = self.env["library.book"].create({"name": "Dune"})
```

`now()` written in an SQL query still answers the real time under
`mock_datetime_and_now`: the code under test passes `self.env.cr.now()` as a query
parameter instead.

Not needed for what a request of an `HttpCase` writes (a tour, `url_open`): that
request runs on a test cursor that takes its time from `datetime.now()`, which
`freeze_time` moves.

# Check a JSON-RPC call by its result, never by its status

Call a `type='jsonrpc'` route with `self.make_jsonrpc_request(route, params)`: it
returns the `result` and raises `JsonRpcException` when the response holds an `error`.
A raw `url_open(...)` checked only on `status_code == 200` proves nothing.

A JSON-RPC route answers HTTP 200 when it raises, a refused access included: the
error is in the `error` key of the body. Only a body that is not JSON gets a 400, and
a path that matches no route a 404.

```python
# bad: green when the access is refused
res = self.url_open("/library/book/lend", json={"params": {"book_id": book.id}})
self.assertEqual(res.status_code, 200)

# good: raises JsonRpcException on an error
result = self.make_jsonrpc_request("/library/book/lend", {"book_id": book.id})
```

When the test needs the raw response (a header, a cookie), assert on
`res.json()["result"]` or `res.json()["error"]`. A `type='http'` or `type='json2'`
route answers with a real status: check it with `res.raise_for_status()`. A
`type='http'` route with `auth='user'` redirects to `/web/login` when the session is
missing, and `url_open` follows it to a 200: pass `allow_redirects=False` and assert
the status code, as `raise_for_status()` lets the 303 through.

# Run the postcommit hooks a test depends on

A test never commits its own cursor, so the functions that the code it calls queues
on `self.env.cr.postcommit` (the NOTIFY of the bus, a webhook, a sync with an outside
service) never run unless the test runs them.

Run that code in a cursor that commits, as in production: in registry test mode,
`self.registry.cursor()` returns a test cursor whose commit runs the precommit and
postcommit hooks. A cron run with `method_direct_trigger()` in that mode, and an HTTP
request of an `HttpCase` (`url_open`, `make_jsonrpc_request`, a tour), commit such a
cursor already. An `HttpCase` is already in that mode: open `self.registry.cursor()`
directly, a second `registry_test_mode()` fails its assertion.

```python
with self.registry_test_mode(), self.registry.cursor() as cr:
    self.env(cr=cr)["library.book"].browse(book.id).action_lend()
```

When the code must run on the test's own cursor, run it in registry test mode too:
most hooks open `self.registry.cursor()`, which outside of it is a real cursor that
sees none of the test's records and commits for real. Then do what a commit does, in
this order: `self.env.cr.flush()` runs the precommit hooks, which queue some of the
postcommit ones, `self.env.transaction.clear()` drops the cache, then
`self.env.cr.postcommit.run()` runs each function once and empties the queue and its
`data`.

Never run the functions of a copy of `cr.postcommit._funcs`: they stay queued and run
again at the next call, and a hook that pops its key from `cr.postcommit.data` then
fails with a `KeyError`.

# Clear the cache before acting as a restricted user

Call `self.env.invalidate_all()` right before the step a test runs as a restricted
user or company (`with_user`, `with_company`, `@users`). A field value already in
cache is returned without checking the model access rights or the record rules, and
the setup leaves in cache every record it created or read. Without the invalidation,
the test passes on code that raises an `AccessError` for that user in production,
where each request starts with an empty cache.

`assertRaises(AccessError)` already clears the cache before its block. Field `groups`
are checked on every read, from the cache or not.
