import ast
import contextlib
import inspect
import os
import threading
import typing
import unittest
from types import SimpleNamespace
from unittest import mock

import psycopg

from odoo import tools
from odoo.db import bulk, cursor, ddl, dsn, endpoints, errors, leaks, pool, probe
from odoo.db.schema_cache import TransactionSchemaCache
from odoo.db.stats import PoolStats
from odoo.db.utils import SYSTEM_DBS

from ._source import _callees


class _FakePgconn:
    def __init__(self, conn):
        self.conn = conn

    def exec_(self, command):
        self.conn.reset_sql.append(command)
        return SimpleNamespace(status=int(psycopg.pq.ExecStatus.COMMAND_OK))


class _FakeConn:
    def __init__(self, transaction_status=cursor._TX_IDLE):
        self.closed = False
        self.info = SimpleNamespace(
            transaction_status=transaction_status, dsn="dbname=x"
        )
        self._odoo_pool: object = None
        self.isolation_level = None
        self.read_only = None
        self.reset_sql: list = []
        self.pgconn = _FakePgconn(self)
        self.rollback: typing.Any = mock.Mock()

    def close(self):
        self.closed = True

    def cursor(self):
        return mock.Mock()


class _FakePsycopgPool:
    closed = False

    def __init__(self):
        self.returned = []

    def putconn(self, conn):
        self.returned.append(conn)

    def get_stats(self):
        return {}


class _RaisingTracker(leaks.CheckoutTracker):
    def track(self, conn, caller=None):
        raise RuntimeError("tracker down")


class _PooledBorrow(contextlib.ExitStack):
    def __init__(self, connection_pool, fail_with=None):
        super().__init__()
        self.pool = connection_pool
        self.psycopg_pool = _FakePsycopgPool()
        self.conn = _FakeConn()
        self.fail_with = fail_with

    def __enter__(self):
        super().__enter__()
        self.enter_context(
            mock.patch.object(
                self.pool, "_get_or_create_pool", return_value=self.psycopg_pool
            )
        )
        self.getconn = self.enter_context(
            mock.patch.object(
                self.pool, "_get_connection_with_retry", side_effect=self._hand_out
            )
        )
        self.health_check = self.enter_context(
            mock.patch.object(self.pool, "_check_borrowed_connection")
        )
        return self

    def _hand_out(self, psycopg_pool, key, connection_info, deadline):
        if self.fail_with is not None:
            raise self.fail_with
        self.conn._odoo_pool = psycopg_pool
        return self.conn, psycopg_pool


class _DirectBorrow(contextlib.ExitStack):
    def __init__(self, connection_pool):
        super().__init__()
        self.pool = connection_pool
        self.conn = _FakeConn()

    def __enter__(self):
        super().__enter__()
        self.connect = self.enter_context(
            mock.patch("odoo.db.pool.psycopg.connect", return_value=self.conn)
        )
        self.enter_context(mock.patch("odoo.db.pool._configure_connection"))
        self.enter_context(
            mock.patch.object(pool.ConnectionPool, "_check_min_server_version")
        )
        self.options = self.enter_context(
            mock.patch(
                "odoo.db.pool._prepare_connection_options",
                wraps=pool._prepare_connection_options,
            )
        )
        return self


class TestPermitAccounting(unittest.TestCase):
    def test_a_pooled_borrow_holds_one_permit_and_one_checkout_until_give_back(self):
        p = pool.ConnectionPool(maxconn=2)
        with _PooledBorrow(p) as h:
            conn = p.borrow({"dbname": "some_db"})
        self.assertIs(conn, h.conn)
        self.assertEqual(p._budget.in_use, 1)
        self.assertEqual(len(p._checkouts), 1)
        p.give_back(conn)
        self.assertEqual(p._budget.in_use, 0)
        self.assertEqual(len(p._checkouts), 0)
        self.assertEqual(h.psycopg_pool.returned, [conn])
        self.assertFalse(conn.closed, "a clean connection goes back warm")
        self.assertEqual(
            len(conn.reset_sql),
            1,
            "the session reset ran on the returning thread, before putconn",
        )

    def test_a_connection_whose_reset_fails_is_discarded_not_pooled(self):
        p = pool.ConnectionPool(maxconn=2)
        with _PooledBorrow(p) as h:
            conn = p.borrow({"dbname": "some_db"})
        conn.pgconn.exec_ = mock.Mock(side_effect=psycopg.OperationalError("gone"))
        p.give_back(conn)
        self.assertTrue(conn.closed)
        self.assertEqual(p.stats.connections_discarded, 1)
        self.assertEqual(h.psycopg_pool.returned, [conn])
        self.assertEqual(p._budget.in_use, 0)

    def test_psycopg_pool_is_built_without_a_reset_callback(self):
        src = inspect.getsource(pool.ConnectionPool._get_or_create_pool)
        self.assertIn("reset=None", src)
        self.assertIn(
            "_reset_returned_connection",
            _callees(pool.ConnectionPool.give_back),
            "with reset= set, psycopg_pool hands every return to its one "
            "worker and getconn grows the pool rather than wait for it: 8 "
            "threads held 63 backends; reset on the returning thread instead",
        )

    def test_a_pooled_borrow_that_fails_after_the_connection_arrived_releases_it(self):
        p = pool.ConnectionPool(maxconn=2)
        p._checkouts = _RaisingTracker()
        with _PooledBorrow(p) as h, self.assertRaises(RuntimeError):
            p.borrow({"dbname": "some_db"})
        self.assertEqual(p._budget.in_use, 0, "the permit outlived the borrow")
        self.assertEqual(p.stats.borrows_failed, 1)
        self.assertEqual(p.stats.connections_discarded, 1)
        self.assertTrue(h.conn.closed, "a connection nobody received is discarded")
        self.assertEqual(h.psycopg_pool.returned, [h.conn])
        self.assertEqual(len(p._checkouts), 0)

    def test_a_pooled_borrow_whose_health_check_fails_releases_it_too(self):
        p = pool.ConnectionPool(maxconn=2)
        with _PooledBorrow(p) as h:
            h.health_check.side_effect = psycopg.OperationalError("dead on arrival")
            with self.assertRaises(psycopg.OperationalError):
                p.borrow({"dbname": "some_db"})
        self.assertEqual(p._budget.in_use, 0)
        self.assertEqual(p.stats.borrows_failed, 1)
        self.assertTrue(h.conn.closed)
        self.assertEqual(h.psycopg_pool.returned, [h.conn])

    def test_a_pooled_borrow_that_fails_before_a_connection_arrived_releases_it(self):
        p = pool.ConnectionPool(maxconn=2)
        with (
            _PooledBorrow(p, fail_with=pool.PoolError("no connection")) as h,
            self.assertRaises(pool.PoolError),
        ):
            p.borrow({"dbname": "some_db"})
        self.assertEqual(p._budget.in_use, 0)
        self.assertEqual(p.stats.borrows_failed, 1)
        self.assertEqual(h.psycopg_pool.returned, [], "nothing arrived to give back")
        self.assertEqual(len(p._checkouts), 0)

    def test_a_direct_borrow_holds_and_releases_its_permit_and_its_direct_count(self):
        p = pool.ConnectionPool(maxconn=2)
        with _DirectBorrow(p) as h:
            conn = p.borrow({"dbname": "postgres"})
        self.assertIs(conn, h.conn)
        self.assertIs(conn._odoo_pool, pool._DIRECT_CONNECTION)
        self.assertEqual(p._budget.in_use, 1)
        self.assertEqual(p._direct_out, 1)
        self.assertEqual(len(p._checkouts), 1)
        self.assertEqual(p.stats.borrows_direct, 1)
        p.give_back(conn)
        self.assertEqual(p._budget.in_use, 0)
        self.assertEqual(p._direct_out, 0)
        self.assertEqual(len(p._checkouts), 0)
        self.assertTrue(conn.closed, "a maintenance connection is never kept")

    def test_a_direct_borrow_that_fails_after_connecting_releases_its_permit(self):
        p = pool.ConnectionPool(maxconn=2)
        p._checkouts = _RaisingTracker()
        with _DirectBorrow(p) as h, self.assertRaises(RuntimeError):
            p.borrow({"dbname": "postgres"})
        self.assertEqual(p._budget.in_use, 0)
        self.assertEqual(p._direct_out, 0)
        self.assertEqual(p.stats.borrows_failed, 1)
        self.assertTrue(h.conn.closed)

    def test_the_direct_path_asks_for_no_session_gucs(self):
        p = pool.ConnectionPool(maxconn=2)
        with _DirectBorrow(p) as h:
            p.borrow({"dbname": "postgres"})
        h.options.assert_called_once()
        self.assertIsNone(h.options.call_args.kwargs["session_gucs"])
        self.assertIn(
            f"-c idle_session_timeout={pool._DIRECT_IDLE_SESSION_TIMEOUT_MS}",
            h.connect.call_args.kwargs["options"],
        )

    def test_a_maintenance_database_never_creates_a_pool(self):
        p = pool.ConnectionPool(maxconn=2)
        sentinel = object()
        with (
            mock.patch.object(p, "_borrow_directly", return_value=sentinel) as direct,
            mock.patch.object(p, "_get_or_create_pool") as pooled,
        ):
            for name in (*SYSTEM_DBS, tools.config["db_template"]):
                with self.subTest(dbname=name):
                    self.assertIs(p.borrow({"dbname": name}), sentinel)
        self.assertEqual(direct.call_count, len(SYSTEM_DBS) + 1)
        pooled.assert_not_called()
        self.assertEqual(p._pools, {})

    def test_an_exhausted_budget_fails_the_pooled_path_before_taking_a_connection(
        self,
    ):
        p = pool.ConnectionPool(maxconn=1, borrow_timeout=0.01)
        with _PooledBorrow(p) as h:
            held = p.borrow({"dbname": "some_db"})
            with self.assertRaises(pool.PoolError) as caught:
                p.borrow({"dbname": "some_db"})
            self.assertEqual(h.getconn.call_count, 1, "no second connection taken")
        message = str(caught.exception)
        self.assertIn("connection budget (1) reached", message)
        self.assertIn("oldest checkouts:", message, "the error must say who holds it")
        self.assertEqual(p._budget.in_use, 1)
        self.assertEqual(p.stats.borrows_failed, 1)
        p.give_back(held)
        self.assertEqual(p._budget.in_use, 0)

    def test_an_exhausted_budget_fails_the_direct_path_before_connecting(self):
        p = pool.ConnectionPool(maxconn=1, borrow_timeout=0.01)
        with _PooledBorrow(p):
            held = p.borrow({"dbname": "some_db"})
        with _DirectBorrow(p) as h, self.assertRaises(pool.PoolError) as caught:
            p.borrow({"dbname": "postgres"})
        h.connect.assert_not_called()
        self.assertIn("connection budget (1) reached", str(caught.exception))
        self.assertIn("oldest checkouts:", str(caught.exception))
        self.assertEqual(p._budget.in_use, 1)
        self.assertEqual(p._direct_out, 0)
        self.assertEqual(p.stats.borrows_failed, 1)
        p.give_back(held)

    def test_one_budget_is_shared_by_both_paths(self):
        p = pool.ConnectionPool(maxconn=2)
        with _PooledBorrow(p):
            pooled = p.borrow({"dbname": "some_db"})
        with _DirectBorrow(p):
            direct = p.borrow({"dbname": "postgres"})
        self.assertEqual(p._budget.in_use, 2)
        p.give_back(direct)
        self.assertEqual(p._budget.in_use, 1)
        p.give_back(pooled)
        self.assertEqual(p._budget.in_use, 0)

    def test_give_back_releases_the_checkout_of_an_unmarked_connection(self):
        p = pool.ConnectionPool(maxconn=2)
        stray = _FakeConn()
        p._checkouts.track(stray, "somewhere")
        p.give_back(stray)
        self.assertEqual(len(p._checkouts), 0, "released before the early return")
        self.assertTrue(stray.closed)
        self.assertEqual(p._budget.in_use, 0, "no permit was taken, none is released")

    def test_the_getconn_helpers_never_touch_the_budget(self):
        for helper in ("_get_connection_with_retry", "_check_borrowed_connection"):
            with self.subTest(helper=helper):
                self.assertNotIn(
                    "_budget", _callees(getattr(pool.ConnectionPool, helper))
                )


class TestStalePlanIsRetriedAtTheRequestLayer(unittest.TestCase):
    class _Prepared:
        def __init__(self):
            self._names = {"_pg3_0": b"stmt"}

        def clear(self):
            self._names.clear()

    class _Refusing:
        def __getattr__(self, name):
            raise AssertionError(f"SQL layer touched through .{name} on an aborted tx")

    def setUp(self):
        cursor.Cursor._stale_plan_drains.clear()
        self.drained: list[str] = []
        patcher = mock.patch.object(
            cursor.Cursor,
            "_drain_sibling_connections",
            lambda cr: self.drained.append(cr.dbname),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _cursor(self):
        cr = cursor.Cursor.__new__(cursor.Cursor)
        cr.dbname = "d"
        cr._cnx = SimpleNamespace(_prepared=self._Prepared(), execute=self._Refusing())
        cr._obj = self._Refusing()
        cr._schema_cache = TransactionSchemaCache()
        cr._schema_cache.set_id_sequence("t", "t_id_seq")
        return cr

    def test_the_idle_siblings_are_drained_once_per_window(self):
        exc = psycopg.errors.FeatureNotSupported("cached plan must not change")
        for _ in range(3):
            self.assertTrue(self._cursor()._invalidate_cached_plans_if_stale(exc))
        self.assertEqual(
            self.drained,
            ["d"],
            "a schema change that landed outside this process left every idle "
            "sibling with the same stale plans; one drain heals them, and a "
            "burst of requests must not drain the pool once each",
        )

    def test_it_clears_the_plans_so_the_retry_re_prepares(self):
        cr = self._cursor()
        exc = psycopg.errors.FeatureNotSupported("cached plan must not change")
        self.assertTrue(cr._invalidate_cached_plans_if_stale(exc))
        self.assertFalse(
            cr._cnx._prepared._names, "the cache must be empty after the mark"
        )
        self.assertIsNone(
            cr._schema_cache.get_id_sequence("t"),
            "catalog facts learned under the old plan must go too",
        )
        self.assertTrue(errors.is_stale_cached_plan(exc))

    def test_the_marker_issues_no_sql(self):
        cr = self._cursor()
        exc = psycopg.errors.FeatureNotSupported("cached plan must not change")
        self.assertTrue(cr._invalidate_cached_plans_if_stale(exc))

    def test_the_family_is_exported_for_the_request_layer(self):
        from odoo.db import errors as err

        self.assertTrue(err.PG_STALE_PLAN_EXCEPTIONS)
        self.assertTrue(callable(err.is_stale_cached_plan))

    def test_the_one_failure_seam_marks_it(self):
        self.assertIn(
            "_invalidate_cached_plans_if_stale",
            _callees(cursor.Cursor._statement_failed),
            "nothing else can tell a recoverable 0A000 from a permanent one",
        )

    def test_every_statement_entry_point_routes_through_that_seam(self):
        import inspect as _inspect

        for owner, name in (
            (cursor.Cursor, "execute"),
            (cursor.Cursor, "executemany"),
            (cursor.Cursor, "copy"),
            (bulk._BulkAccessMixin, "copy_from"),
        ):
            fn = _inspect.unwrap(getattr(owner, name))
            for seam in ("_statement_failed", "_statement_done"):
                with self.subTest(entry_point=name, seam=seam):
                    self.assertIn(
                        seam,
                        fn.__code__.co_names,
                        "each entry point used to carry its own copy of the "
                        "envelope: executemany's had dropped the stale-plan "
                        "mark, copy_from's the failed-statement count, and "
                        "cr.copy()'s the timing and the error log entirely",
                    )

    def test_the_marker_requires_prepared_statements(self):
        src = inspect.getsource(cursor.Cursor._invalidate_cached_plans_if_stale)
        self.assertIn("_prepared", src)
        self.assertIn("_names", src)
        self.assertIn(
            "PG_STALE_PLAN_EXCEPTIONS",
            src,
            "the family must come from errors.py, not be re-listed here",
        )


class TestPasswordNeverReachesAPoolKey(unittest.TestCase):
    SECRET = "s3cr3t-do-not-log"

    def _assert_absent(self, key):
        self.assertNotIn(self.SECRET, repr(key))
        self.assertNotIn(self.SECRET, str(dict(key)))

    def test_keyword_password_is_fingerprinted(self):
        key = dsn._get_dsn_key({"dbname": "d", "password": self.SECRET})
        self._assert_absent(key)
        self.assertIn("password_fp", dict(key))

    def test_uri_embedded_password_is_fingerprinted(self):
        key = dsn._get_dsn_key({"dsn": f"postgresql://u:{self.SECRET}@h/d"})
        self._assert_absent(key)

    def test_a_rotated_password_changes_the_key(self):
        base = {"dbname": "d", "user": "u"}
        first = dsn._get_dsn_key({**base, "password": "one"})
        second = dsn._get_dsn_key({**base, "password": "two"})
        self.assertNotEqual(first, second, "rotation must not reuse the cached pool")

    def test_the_fingerprint_is_stable_for_one_password(self):
        made = {"dbname": "d", "password": self.SECRET}
        self.assertEqual(dsn._get_dsn_key(made), dsn._get_dsn_key(made))


class TestLibpqTimeoutNeverLeaksZero(unittest.TestCase):
    def test_it_returns_zero_or_at_least_one_never_between(self):
        now = probe.monotonic()
        for offset in (-5, -1, -0.5, 0, 0.2, 0.9, 1.0, 1.5, 3, 10, 900):
            with self.subTest(offset=offset):
                got = probe.get_libpq_connect_timeout(now + offset, 5)
                self.assertTrue(
                    got == 0 or got >= 1, f"{got} would be read as 'wait forever'"
                )
                self.assertLessEqual(got, 5, "must never exceed the cap")

    def test_no_deadline_passes_the_cap_through(self):
        self.assertEqual(probe.get_libpq_connect_timeout(None, 5), 5)

    def test_every_call_site_guards_the_zero(self):
        guarded = 0
        skip_tests = 0
        for module in (pool, probe):
            source = inspect.getsource(module)
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    fn = node.value.func
                    if getattr(fn, "id", None) == "get_libpq_connect_timeout":
                        guarded += 1
            skip_tests += source.count("if not probe_timeout")
            skip_tests += source.count("if not connect_timeout")
        self.assertGreaterEqual(
            guarded, 3, "call sites must bind the result so they can test it"
        )
        self.assertEqual(
            skip_tests,
            guarded,
            "every get_libpq_connect_timeout result must be tested for the skip case",
        )


class TestSchemaCacheClearsHaveDistinctEffects(unittest.TestCase):
    def test_the_ddl_clear_keeps_the_lock_ledger_and_the_transaction_clear_drops_it(
        self,
    ):
        cache = TransactionSchemaCache()
        cache.set_id_sequence("t", "t_id_seq")
        cache.set_column_types("t", ["a"], [23])
        cache.mark_locked("t", 0)

        cache.invalidate_catalog_facts()
        self.assertIsNone(cache.get_id_sequence("t"))
        self.assertIsNone(cache.get_column_types("t", ["a"]))
        self.assertTrue(
            cache.is_locked("t"),
            "DDL does not end the transaction, so the ROW EXCLUSIVE lock this "
            "cursor already took is still held",
        )

        cache.set_id_sequence("t", "t_id_seq")
        cache.clear()
        self.assertIsNone(cache.get_id_sequence("t"))
        self.assertFalse(cache.is_locked("t"))


class TestDdlDetectionCannotMissAHiddenStatement(unittest.TestCase):
    HIDDEN = (
        "BEGIN; ALTER TABLE t ADD COLUMN c int; COMMIT",
        "SELECT 1; CREATE TABLE t (a int)",
        "SET x = 1; DROP TABLE t",
        "SELECT 1;\n  ALTER TABLE t DROP COLUMN c",
        "SELECT 1; DO $$ BEGIN END $$",
    )
    INNOCENT = (
        "SELECT * FROM t",
        "INSERT INTO t VALUES (1)",
        "UPDATE t SET a = 1",
        "SELECT 'CREATE TABLE' AS label",
    )

    def test_hidden_ddl_is_reported(self):
        for qs in self.HIDDEN:
            with self.subTest(qs=qs):
                self.assertTrue(
                    ddl._has_schema_changing_statement(qs, ddl._get_ddl_keyword(qs))
                )

    def test_ordinary_statements_are_not(self):
        for qs in self.INNOCENT:
            with self.subTest(qs=qs):
                self.assertFalse(
                    ddl._has_schema_changing_statement(qs, ddl._get_ddl_keyword(qs))
                )

    def test_over_reporting_is_the_only_allowed_error(self):
        qs = "SELECT 'a;CREATE' FROM t"
        self.assertTrue(
            ddl._has_schema_changing_statement(qs, ddl._get_ddl_keyword(qs)),
            "a semicolon in a literal may over-report; that costs a cache drop, "
            "which is safe, and is the documented direction of the trade",
        )


class TestOneConnectionOptionsAssembler(unittest.TestCase):
    def test_the_assembler_renders_the_session_gucs_by_default(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("odoo.db.pool._prepare_session_gucs", return_value="-c a=1"),
        ):
            self.assertEqual(
                pool._prepare_connection_options("", {}, 5, session_gucs="a=1"),
                "-c a=1 -c idle_session_timeout=5",
            )
            self.assertEqual(
                pool._prepare_connection_options("", {}, 5, session_gucs=None),
                "-c idle_session_timeout=5",
            )

    def test_both_borrow_paths_use_it(self):
        for path in ("_prepare_connect_args", "_borrow_directly"):
            with self.subTest(path=path):
                self.assertIn(
                    "_prepare_connection_options",
                    _callees(getattr(pool.ConnectionPool, path)),
                    "the two paths built the same libpq options string twice; "
                    "one assembler, or the exemption goes back to being an "
                    "accident nobody can see.",
                )
        self.assertIn(
            "_prepare_connect_args",
            _callees(pool.ConnectionPool._get_or_create_pool),
            "the pooled path reaches the assembler through its connect-args helper",
        )


class TestAListValuedGucIsOneEntry(unittest.TestCase):
    def test_a_comma_inside_a_value_does_not_split_the_entry(self):
        rendered = pool._prepare_session_gucs(
            "", "search_path=public,pg_catalog,work_mem=16MB,jit=off"
        )
        self.assertEqual(
            rendered,
            "-c search_path=public,pg_catalog -c work_mem=16MB -c jit=off",
        )

    def test_the_default_list_still_renders_two_entries(self):
        self.assertEqual(
            pool._prepare_session_gucs("", "jit=off,work_mem=16MB"),
            "-c jit=off -c work_mem=16MB",
        )


class TestFaketimePinsTheSearchPathAtStartup(unittest.TestCase):
    def test_a_forced_guc_is_appended_after_the_operator_options(self):
        rendered = pool._prepare_connection_options(
            "",
            {"options": "-c search_path=mine"},
            5,
            session_gucs=None,
            forced_gucs=("search_path=public,pg_catalog",),
        )
        self.assertEqual(
            rendered,
            "-c search_path=mine -c idle_session_timeout=5 "
            "-c search_path=public,pg_catalog",
            "libpq lets the last -c win, so a forced GUC comes last",
        )

    def test_only_a_configured_database_in_faketime_mode_is_pinned(self):
        from odoo.db.settings import PoolSettings

        settings = PoolSettings(db_names=("mine",))
        with mock.patch.dict("os.environ", {"ODOO_FAKETIME_TEST_MODE": "1"}):
            self.assertEqual(
                pool._get_forced_gucs("mine", settings), pool._FAKETIME_GUCS
            )
            self.assertEqual(pool._get_forced_gucs("other", settings), ())
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(pool._get_forced_gucs("mine", settings), ())

    def test_the_cursor_constructor_issues_no_search_path_statement(self):
        self.assertNotIn(
            "search_path",
            inspect.getsource(cursor.Cursor.__init__),
            "the pin is a startup option, so it costs no round trip per cursor "
            "and survives the RESET ALL on every return",
        )


class TestBudgetBelongsToAServer(unittest.TestCase):
    def test_budgets_are_kept_per_endpoint_not_as_one_global(self):
        registry = endpoints.EndpointRegistry()
        self.assertIsInstance(registry._budgets, dict)
        self.assertFalse(
            hasattr(registry, "_budget"),
            "the single process-wide budget was replaced by a per-endpoint map",
        )

    def test_the_package_no_longer_carries_the_registry_as_module_state(self):
        import odoo.db as package

        for gone in ("_pools", "_budgets", "_pool_lock"):
            with self.subTest(name=gone):
                self.assertFalse(
                    hasattr(package, gone),
                    "the registry is an object so a test can build an isolated "
                    "one; leaving the globals behind keeps the old seam alive",
                )
        self.assertIsInstance(package.registry, endpoints.EndpointRegistry)

    def test_the_key_is_the_resolved_endpoint(self):
        names = _callees(endpoints.EndpointRegistry.get_budget_for_readonly)
        self.assertIn("get_endpoint_for_readonly", names)
        self.assertNotIn(
            "db_replica_host",
            names,
            "keying on 'is a replica configured' hands one server two budgets "
            "whenever the replica resolves back to the primary",
        )

    def test_the_endpoint_comes_from_the_resolved_connection_info(self):
        self.assertIn(
            "get_connection_info_for_database",
            _callees(endpoints.EndpointRegistry.get_endpoint_for_readonly),
        )

    def test_the_replica_ceiling_is_gated_on_the_endpoint_differing(self):
        self.assertIn(
            "get_endpoint_for_readonly",
            _callees(endpoints.EndpointRegistry.get_maxconn_at_endpoint),
        )


class TestASavepointIsNeverOpenedInsideAPipeline(unittest.TestCase):
    def test_savepoint_refuses_pipeline_mode(self):
        cr = cursor.BaseCursor.__new__(cursor.BaseCursor)
        with (
            mock.patch.object(cr, "in_pipeline", True, create=True),
            self.assertRaisesRegex(RuntimeError, "inside cr.pipeline"),
        ):
            cr.savepoint()

    def test_it_asks_through_getattr_so_a_test_cursor_forwards(self):
        class _Forwarding(cursor.BaseCursor):
            def __getattr__(self, name):
                if name == "in_pipeline":
                    return True
                raise AttributeError(name)

        cr = _Forwarding.__new__(_Forwarding)
        with self.assertRaisesRegex(RuntimeError, "inside cr.pipeline"):
            cr.savepoint()

    def test_the_refusal_matches_the_precedent_copy_from_set(self):
        def check(in_pipeline):
            bulk._check_copy_args(
                SimpleNamespace(in_pipeline=in_pipeline),
                "t",
                ["a"],
                returning_ids=False,
                binary=False,
                on_error=None,
            )

        check(False)
        with self.assertRaisesRegex(
            psycopg.errors.NotSupportedError, "cannot run inside pipeline mode"
        ):
            check(True)


class TestOneDecodeOfAStatementsText(unittest.TestCase):
    def test_it_decodes_bytes_rather_than_repring_them(self):
        self.assertEqual(
            cursor._get_statement_text(b"CREATE TABLE t (a int)"),
            "CREATE TABLE t (a int)",
        )
        self.assertEqual(cursor._get_statement_text(b"\xff\xfe"), "")
        self.assertEqual(cursor._get_statement_text("SELECT 1"), "SELECT 1")

    def test_both_entry_points_read_the_text_through_one_function(self):
        for name in ("_prepare_ddl_statement", "executemany"):
            with self.subTest(entry_point=name):
                self.assertIn(
                    "_get_statement_text",
                    _callees(getattr(cursor.Cursor, name)),
                    "executemany used to spell it str(query), which turns a "
                    "bytes DDL statement into the repr b'CREATE …' and hides "
                    "it from classify_statement",
                )


class TestCursorConstructionNeverLeaksAPermit(unittest.TestCase):
    class _FakePool:
        readonly = False

        def __init__(self, conn):
            self.conn = conn
            self.given_back = []

        def borrow(self, dsn, key=None, **kw):
            return self.conn

        def give_back(self, conn, keep_in_pool=True):
            self.given_back.append((conn, keep_in_pool))

    def test_the_construction_guard_catches_baseexception(self):
        conn = _FakeConn()
        fake_pool = self._FakePool(conn)
        with (
            mock.patch.object(conn, "cursor", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            cursor.Cursor(
                typing.cast("pool.ConnectionPool", fake_pool), "db", {"dbname": "db"}
            )
        self.assertEqual(
            fake_pool.given_back,
            [(conn, True)],
            "an Exception-only guard misses the interrupt and the watchdog's "
            "SystemExit, which is the window where the leak is unrecoverable",
        )

    def test_it_gives_the_connection_back_on_the_same_terms_as_close(self):
        class _AbortedAfterAStatement(_FakeConn):
            def __init__(self):
                super().__init__(
                    transaction_status=psycopg.pq.TransactionStatus.INERROR
                )
                self.obj = mock.Mock()

            def cursor(self):
                return self.obj

        class _PoolThatFailsLate(TestCursorConstructionNeverLeaksAPermit._FakePool):
            @property
            def readonly(self):  # type: ignore[override]  # the failure injection point
                raise RuntimeError("setup failed after a statement")

        conn = _AbortedAfterAStatement()
        fake_pool = _PoolThatFailsLate(conn)
        with self.assertRaisesRegex(RuntimeError, "after a statement"):
            cursor.Cursor(
                typing.cast("pool.ConnectionPool", fake_pool), "db", {"dbname": "db"}
            )
        conn.obj.close.assert_called_once()
        self.assertEqual(
            fake_pool.given_back,
            [(conn, False)],
            "a connection whose setup raised after a statement sits in a "
            "failed transaction; handing it back as warm passes it on",
        )

    def test_the_guard_asks_the_pool_nothing(self):
        src = inspect.getsource(cursor.Cursor.__init__)
        guard = src[src.index("except BaseException:") :]
        before_release = guard[: guard.index("pool.give_back(")]
        self.assertNotIn(
            "pool.",
            before_release,
            "the guard used to re-read pool.readonly for its own debug line, "
            "so a pool attribute that raised escaped before give_back ran",
        )


class TestADroppedCursorAlwaysGivesItsConnectionBack(unittest.TestCase):
    def _dropped(self, conn):
        fake_pool = TestCursorConstructionNeverLeaksAPermit._FakePool(conn)
        cr = cursor.Cursor(
            typing.cast("pool.ConnectionPool", fake_pool), "db", {"dbname": "db"}
        )
        with self.assertLogs("odoo.db.cursor", level="WARNING") as cm:
            cr.__del__()
        self.assertTrue(any("not closed explicitly" in m for m in cm.output))
        return fake_pool.given_back

    def test_a_live_connection_is_rolled_back_and_pooled(self):
        conn = _FakeConn()
        conn.rollback = mock.Mock()
        self.assertEqual(self._dropped(conn), [(conn, True)])
        conn.rollback.assert_called_once()

    def test_a_dead_connection_is_still_given_back_so_the_permit_returns(self):
        conn = _FakeConn()
        conn.closed = True
        conn.rollback = mock.Mock(side_effect=AssertionError("never asked"))
        self.assertEqual(
            self._dropped(conn),
            [(conn, False)],
            "__del__ used to return early on a closed connection, and "
            "give_back is the only release of the permit and the checkout: "
            "measured live, a cursor dropped after pg_terminate_backend left "
            "budget_in_use=1 and checked_out=1 for the life of the process",
        )

    def test_a_closed_cursor_is_left_alone(self):
        conn = _FakeConn()
        fake_pool = TestCursorConstructionNeverLeaksAPermit._FakePool(conn)
        cr = cursor.Cursor(
            typing.cast("pool.ConnectionPool", fake_pool), "db", {"dbname": "db"}
        )
        cr.close()
        cr.__del__()
        self.assertEqual(len(fake_pool.given_back), 1)


class TestTheProbeAsksItsQuestionOnce(unittest.TestCase):
    class _CountingLock:
        def __init__(self):
            self.acquisitions = 0
            self._lock = threading.Lock()

        def __enter__(self):
            self.acquisitions += 1
            self._lock.acquire()

        def __exit__(self, *exc):
            self._lock.release()

    def test_a_proven_key_costs_one_lock_acquisition_and_no_connect(self):
        stats = PoolStats()
        reachability = probe.ReachabilityProbe(stats)
        key = frozenset({("dbname", "d")})
        reachability.mark_proven(key)
        counting = self._CountingLock()
        with (
            mock.patch.object(reachability, "_lock", counting),
            mock.patch("odoo.db.probe.psycopg.connect") as connect,
        ):
            reachability.check_connectable(key, "", {"dbname": "d"})
        connect.assert_not_called()
        self.assertEqual(stats.probe_skipped_proven, 1)
        self.assertEqual(
            counting.acquisitions,
            1,
            "two acquisitions left a window in which a key proven between "
            "them started a second probe -- a full extra connect on the path "
            "whose purpose is to avoid one",
        )

    def test_a_close_that_raises_does_not_fail_the_probe(self):
        stats = PoolStats()
        reachability = probe.ReachabilityProbe(stats)
        conn = mock.Mock()
        conn.close.side_effect = RuntimeError("close blew up")
        with mock.patch("odoo.db.probe.psycopg.connect", return_value=conn):
            reachability.probe_connectable("", {"dbname": "d"})
        conn.close.assert_called_once()
        self.assertEqual(stats.probe_run, 1)
        self.assertEqual(
            stats.probe_transient,
            0,
            "a connection that opened proves the DSN reachable; closing it is "
            "not part of that question and must not be able to fail it",
        )


if __name__ == "__main__":
    unittest.main()


class TestALostConnectionIsReplacedBeforeTheFirstStatementOnly(unittest.TestCase):
    class _DeadThenAlive:
        def __init__(self):
            self.handed: list = []
            self.given_back: list = []
            self.readonly = False

        def borrow(self, dsn, key=None, **kw):
            conn = _FakeConn()
            conn.cursor = lambda: _StatementRecorder(conn)  # type: ignore[method-assign]
            self.handed.append(conn)
            return conn

        def give_back(self, conn, keep_in_pool=True):
            self.given_back.append((conn, keep_in_pool))

    def _cursor(self):
        fake_pool = self._DeadThenAlive()
        cr = cursor.Cursor(
            typing.cast("pool.ConnectionPool", fake_pool), "db", {"dbname": "db"}
        )
        return cr, fake_pool

    def _kill(self, cr):
        cr._cnx.closed = True
        cr._obj.dead = True

    def test_the_first_statement_is_replayed_on_a_fresh_borrow(self):
        cr, fake_pool = self._cursor()
        first = cr._cnx
        self._kill(cr)
        with self.assertLogs("odoo.db.cursor", level="WARNING") as cm:
            cr.execute("SELECT 1")
        self.assertIn("replayed on a fresh connection", cm.output[0])
        self.assertEqual(fake_pool.given_back, [(first, False)])
        self.assertEqual(len(fake_pool.handed), 2)
        self.assertIs(cr._cnx, fake_pool.handed[1])
        self.assertEqual(cr._obj.executed, ["SELECT 1"])
        self.assertTrue(cr._transaction_touched)

    def test_a_statement_after_the_first_is_not(self):
        cr, fake_pool = self._cursor()
        cr.execute("SELECT 1")
        self._kill(cr)
        with self.assertRaises(psycopg.OperationalError):
            cr.execute("SELECT 2")
        self.assertEqual(len(fake_pool.handed), 1, "the transaction had state")

    def test_not_inside_a_savepoint_or_an_entered_pipeline(self):
        cr, _fake_pool = self._cursor()
        cr._savepoint_depth = 1
        self._kill(cr)
        with self.assertRaises(psycopg.OperationalError):
            cr.execute("SELECT 1")
        cr, _fake_pool = self._cursor()
        cr._pipeline_stack = contextlib.ExitStack()
        cr._pipeline = object()  # entered: the block's second statement onwards
        self._kill(cr)
        with self.assertRaises(psycopg.OperationalError):
            cr.execute("SELECT 1")

    def test_the_first_statement_of_a_pipeline_block_is_still_replayed(self):
        cr, fake_pool = self._cursor()
        self._kill(cr)
        with cr.pipeline():
            cr.execute("SELECT 1")
        self.assertEqual(len(fake_pool.handed), 2)
        self.assertEqual(cr._pipeline_statements, 1, "the arming count is untouched")

    def test_a_replacement_that_cannot_be_borrowed_leaves_the_loss_to_propagate(self):
        cr, fake_pool = self._cursor()
        first = cr._cnx

        def refuse(dsn, key=None, **kw):
            raise pool.PoolError("budget spent")

        fake_pool.borrow = refuse
        self._kill(cr)
        with self.assertRaises(psycopg.OperationalError):
            cr.execute("SELECT 1")
        self.assertEqual(
            fake_pool.given_back,
            [(first, False)],
            "the dead connection's permit goes back before the replacement is "
            "asked for -- at maxconn=1 it is the only permit there is",
        )
        self.assertTrue(cr.closed, "a cursor whose connection is gone is over")
        cr.close()
        self.assertEqual(len(fake_pool.given_back), 1, "and closes as a no-op")

    def test_a_server_side_error_is_never_a_lost_connection(self):
        cr, fake_pool = self._cursor()
        cr._obj.raise_next = psycopg.errors.UniqueViolation("dup")
        with self.assertRaises(psycopg.errors.UniqueViolation):
            cr.execute("INSERT ...")
        self.assertEqual(len(fake_pool.handed), 1)

    def test_commit_and_rollback_make_the_next_transaction_fresh_again(self):
        cr, fake_pool = self._cursor()
        cr.execute("SELECT 1")
        cr._cnx.commit = lambda: None  # type: ignore[attr-defined]
        cr.commit()
        self.assertFalse(cr._transaction_touched)
        self._kill(cr)
        cr.execute("SELECT 1")
        self.assertEqual(len(fake_pool.handed), 2)


class TestTheCommitWriteQuestionIsNeverAskedOfAFailedTransaction(unittest.TestCase):
    def test_a_failed_transaction_commits_as_before_and_pins_nothing(self):
        fake_pool = (
            TestALostConnectionIsReplacedBeforeTheFirstStatementOnly._DeadThenAlive()
        )
        cr = cursor.Cursor(
            typing.cast("pool.ConnectionPool", fake_pool), "db", {"dbname": "db"}
        )
        fired = []
        cr.on_commit_if_written(lambda: fired.append(True))
        cr.execute("INSERT ...")
        cr._cnx.info.transaction_status = psycopg.pq.TransactionStatus.INERROR
        cr._cnx.commit = lambda: None  # type: ignore[attr-defined]
        cr.commit()
        self.assertEqual(fired, [])
        self.assertEqual(
            cr._obj.executed,
            ["INSERT ..."],
            "no SELECT txid_current_if_assigned() on an aborted transaction: "
            "COMMIT there is a quiet rollback, the question would have been "
            "InFailedSqlTransaction",
        )


class _StatementRecorder:
    def __init__(self, conn):
        self.conn = conn
        self.executed: list = []
        self.dead = False
        self.raise_next = None
        self.description = None
        self.rowcount = -1

    def execute(self, query, params=None, prepare=None):
        if self.raise_next is not None:
            exc, self.raise_next = self.raise_next, None
            raise exc
        if self.dead:
            raise psycopg.OperationalError("the connection is closed")
        self.executed.append(query)

    def executemany(self, query, rows, returning=False):
        self.execute(query)

    def fetchone(self):
        return (1,)

    def close(self):
        pass


class TestStatementTimeoutIsOwnedByTheCursor(unittest.TestCase):
    _SET = "SET LOCAL statement_timeout = '1500ms'"
    _LIFT = "SET LOCAL statement_timeout = '0'"

    def setUp(self):
        fake_pool = (
            TestALostConnectionIsReplacedBeforeTheFirstStatementOnly._DeadThenAlive()
        )
        self.cr = cursor.Cursor(
            typing.cast("pool.ConnectionPool", fake_pool), "db", {"dbname": "db"}
        )
        self.fake_pool = fake_pool
        self.enterContext(
            mock.patch.object(
                cursor,
                "_inline_ddl_params",
                lambda qs, params, ctx: qs.replace("%s", repr(params[0])),
            )
        )

    def test_it_is_armed_before_the_first_statement_not_when_set(self):
        cr = self.cr
        cr.set_statement_timeout(1.5)
        self.assertEqual(cr._obj.executed, [], "nothing to bound yet")
        cr.execute("SELECT 1")
        self.assertEqual(cr._obj.executed, [self._SET, "SELECT 1"])
        cr.execute("SELECT 2")
        self.assertEqual(cr._obj.executed[2:], ["SELECT 2"], "armed once")

    def test_it_survives_commit_and_rollback_on_the_same_cursor(self):
        cr = self.cr
        cr._cnx.commit = mock.Mock()
        cr.set_statement_timeout(1.5)
        cr.execute("SELECT 1")
        cr.commit()
        cr.execute("SELECT 2")
        cr.rollback()
        cr.execute("SELECT 3")
        self.assertEqual(
            cr._obj.executed,
            [self._SET, "SELECT 1", self._SET, "SELECT 2", self._SET, "SELECT 3"],
            "SET LOCAL dies with each transaction; the cursor re-arms it",
        )

    def test_arming_does_not_spend_the_replay_window(self):
        cr = self.cr
        cr.set_statement_timeout(1.5)
        cr._cnx.closed = True
        cr._obj.dead = True
        with self.assertLogs("odoo.db.cursor", level="WARNING"):
            cr.execute("SELECT 1")
        self.assertEqual(len(self.fake_pool.handed), 2, "replayed")
        self.assertEqual(
            cr._obj.executed,
            [self._SET, self._SET, "SELECT 1"],
            "the replacement is armed, then the lost statement retried",
        )
        self.assertTrue(cr._transaction_touched)

    def test_a_savepoint_rollback_that_reverts_it_re_arms_the_next_statement(self):
        cr = self.cr
        cr.set_statement_timeout(1.5)
        with contextlib.suppress(RuntimeError), cr.savepoint(flush=False) as sp:
            cr._statement_timeout_armed = False  # as after a commit inside
            cr.execute("SELECT 1")
            raise RuntimeError
        cr.execute("SELECT 2")
        self.assertEqual(
            cr._obj.executed,
            [
                self._SET,
                f'SAVEPOINT "{sp.name}"',
                self._SET,
                "SELECT 1",
                f'ROLLBACK TO SAVEPOINT "{sp.name}"',
                self._SET,
                f'RELEASE SAVEPOINT "{sp.name}"',
                "SELECT 2",
            ],
            "armed inside the savepoint, reverted by its rollback, re-armed before "
            "the next statement (the RELEASE, which keeps it)",
        )

    def test_a_budget_armed_before_the_savepoint_survives_its_rollback(self):
        cr = self.cr
        cr.set_statement_timeout(1.5)
        with contextlib.suppress(RuntimeError), cr.savepoint(flush=False) as sp:
            cr.execute("SELECT 1")
            raise RuntimeError
        cr.execute("SELECT 2")
        self.assertEqual(
            cr._obj.executed,
            [
                self._SET,
                f'SAVEPOINT "{sp.name}"',
                "SELECT 1",
                f'ROLLBACK TO SAVEPOINT "{sp.name}"',
                f'RELEASE SAVEPOINT "{sp.name}"',
                "SELECT 2",
            ],
            "SET LOCAL issued before the SAVEPOINT is not reverted by it",
        )

    def test_a_rollback_to_a_deeper_savepoint_keeps_it(self):
        cr = self.cr
        cr.set_statement_timeout(1.5)
        cr.execute("SELECT 1")
        cr._savepoint_depth = 1
        cr._on_rollback_to_savepoint()
        cr._savepoint_depth = 0
        cr.execute("SELECT 2")
        self.assertEqual(cr._obj.executed, [self._SET, "SELECT 1", "SELECT 2"])

    def test_clearing_lifts_an_armed_budget_now_and_an_unarmed_one_silently(self):
        cr = self.cr
        cr.set_statement_timeout(None)
        cr.set_statement_timeout(1.5)
        cr.set_statement_timeout(None)
        self.assertEqual(cr._obj.executed, [], "never armed: nothing to lift")
        cr.set_statement_timeout(1.5)
        cr.execute("SELECT 1")
        cr.set_statement_timeout(None)
        cr.execute("SELECT 2")
        self.assertEqual(
            cr._obj.executed, [self._SET, "SELECT 1", self._LIFT, "SELECT 2"]
        )

    def test_clearing_a_set_budget_mid_transaction_lifts_it_even_when_disarmed(self):
        cr = self.cr
        cr.set_statement_timeout(1.5)
        cr.execute("SELECT 1")
        cr._statement_timeout_armed = False  # a savepoint rollback said so
        cr.set_statement_timeout(None)
        self.assertEqual(cr._obj.executed, [self._SET, "SELECT 1", self._LIFT])

    def test_set_mid_transaction_applies_now(self):
        cr = self.cr
        cr.execute("SELECT 1")
        cr.set_statement_timeout(1.5)
        cr.set_statement_timeout(0.5)
        self.assertEqual(
            cr._obj.executed,
            ["SELECT 1", self._SET, "SET LOCAL statement_timeout = '500ms'"],
        )
