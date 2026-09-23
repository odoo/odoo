# odoo.tests — Machine Documentation v1

## Purpose

`odoo/tests` is the **test framework** of this fork: vendored unittest
machinery (case/suite/result), the Odoo test-case hierarchy
(`BaseCase → TransactionCase → HttpCase`), the savepoint-based `TestCursor`,
the server-side `Form` emulator, tag-based test selection, and a headless
Chrome (CDP) driver for browser/tour tests.

It is **framework, not an addon**: no models, no manifest. Tests *for* this
package live in `odoo/addons/base/tests/` (see Conventions).

## Files at a Glance

| File | Purpose |
|------|---------|
| `__init__.py` | Re-exports `common.*` (per `common.__all__`), `Form`, proxies |
| `case.py` | Vendored `unittest.TestCase` (trimmed run loop, traceback surgery) |
| `suite.py` | Vendored `TestSuite` + `OdooSuite` (class setup/teardown, stats) |
| `result.py` | `OdooTestResult`: log-as-you-fail, counters, per-test stats, `soft_fail` |
| `loader.py` | Discover test modules per addon, build/run suites (`prepare_suite`/`run_suite`) |
| `tag_selector.py` | `TagsSelector`: parses `--test-tags` specs, filters tests |
| `common.py` | The public façade: decorators (`tagged`, `users`, `warmup`, `no_retry`, `freeze_time`, `standalone`), `new_test_user`, `test_xsd`, and the re-exports `__all__` names |
| `transaction_case.py` | `BaseCase`/`TransactionCase`/`SingleTransactionCase`, their assertions, and the registry-lock, statement-recorder and stranded-cursor machinery they own |
| `in_memory_case.py` | `InMemoryCase`: hosts a module's own `TransactionCase` class on the DB-free tier -- a `model_test_env` for the class with `hosts_modules`' data files loaded, `allow_inherited_tests_method` so the hosted methods are collected, and the per-test snapshot plus the cache clears a dict rollback does not cover |
| `matchers.py` | `Like`, `Approx`, `WhitespaceInsensitive`, `RecordCapturer` and the XML normaliser — value comparison, no dependency on the case hierarchy |
| `http.py` | `HttpCase`/`Opener`/`Transport`/`JsonRpcException` (extracted from common; still re-exported there) |
| `browser.py` | `ChromeBrowser` CDP client, `Screencaster`, Chrome discovery |
| `utils.py` | `HOST`, `get_db_name`, `save_test_file`, `env_int` (shared by common+http+browser, no cycle) |
| `cursor.py` | `TestCursor`: savepoint-simulated commit/rollback over one real cursor |
| `form.py` | `Form`/`O2MForm` + x2many proxies: server-side form-view emulation |
| `shell.py` | `run_tests(env, tags)` for interactive `odoo-bin shell` use |
| `benchmark.py` | `BenchmarkStats`/`compute_stats`/timers for perf suites |
| `module_operations.py` | CLI: install/uninstall/cycle modules, `@standalone` runner |

## Entry Points

- Module loading runs tests via `loader.prepare_suite` + `run_suite`
  (called from `odoo/modules/loading.py` when `--test-enable`/`--test-tags`).
- `odoo-bin shell` → `odoo.tests.shell.run_tests(env, test_tags)`.
- `python -m odoo.tests.module_operations -d db [cycle|uninstall|standalone]`.

## Read Next

- [`architecture.md`](architecture.md) — execution flow, cursor/lock model, tag grammar, browser stack
- [`conventions.md`](conventions.md) — tags, tiers, gotchas, what NOT to do
