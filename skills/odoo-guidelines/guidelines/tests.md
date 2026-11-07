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
route answers with a real status, so its status code is worth checking.

# Run the postcommit hooks a test depends on

A test never commits its own cursor, so the functions that the code it calls queues
on `self.env.cr.postcommit` (the NOTIFY of the bus, a webhook, a sync with an outside
service) never run unless the test runs them. A test that checks their effect calls
`self.env.cr.flush()`, which runs the precommit hooks that queue some of them, then
`self.env.cr.postcommit.run()`, which runs each function once and empties the queue
and its `data`.

Never run the functions of a copy of `cr.postcommit._funcs`: they stay queued and run
again at the next call, and a hook that pops its key from `cr.postcommit.data` then
fails with a `KeyError`.

A hook queued during an HTTP request of an `HttpCase` (`url_open`,
`make_jsonrpc_request`, a tour) needs none of this: it runs when that request commits
its test cursor.

# Clear the cache before acting as a restricted user

Call `self.env.invalidate_all()` right before the step a test runs as a restricted
user or company (`with_user`, `with_company`, `@users`). A field value already in
cache is returned without checking the model access rights or the record rules, and
the setup leaves in cache every record it created or read. Without the invalidation,
the test passes on code that raises an `AccessError` for that user in production,
where each request starts with an empty cache.

`assertRaises(AccessError)` already clears the cache before its block. Field `groups`
are checked on every read, from the cache or not.
