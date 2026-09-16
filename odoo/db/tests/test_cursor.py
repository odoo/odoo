import logging
import os
import subprocess
import threading
import typing
import unittest
from typing import Any

from odoo.db import metrics
from odoo.db.cursor import BaseCursor
from odoo.db.errors import CURSOR_LOGGER_NAME
from odoo.db.savepoint import Savepoint, _FlushingSavepoint
from odoo.libs.sql import SQL


class _Cursor(BaseCursor):
    def __init__(self):
        super().__init__()
        self.dbname = "fake"
        self.statements = []
        self.committed = 0
        self.closed_count = 0

    def execute(self, query, params=None, log_exceptions=True, prepare=None):
        self.statements.append(str(query))

    def commit(self):
        self.committed += 1

    def close(self):
        self.closed_count += 1
        self._closed = True


class _Transaction:
    def __init__(self, cr, rounds=0):
        self.cr = cr
        self.rounds = rounds
        self.flush_calls = 0
        self.cleared = 0
        self.reset_calls = 0

    def flush(self):
        self.flush_calls += 1
        if self.flush_calls <= self.rounds:
            self.cr.precommit.add(lambda: None)

    def clear(self):
        self.cleared += 1

    def reset(self):
        self.reset_calls += 1


def _attach(cr, rounds=0):
    txn = _Transaction(cr, rounds)
    cr.transaction = txn
    return txn


class TestContextManagerContract(unittest.TestCase):
    def test_closed_is_a_class_level_default_on_the_base(self):
        self.assertIs(BaseCursor._closed, False)

    def test_clean_exit_commits_then_closes(self):
        cr = _Cursor()
        with cr:
            pass
        self.assertEqual((cr.committed, cr.closed_count), (1, 1))

    def test_exception_closes_without_committing(self):
        cr = _Cursor()
        with self.assertRaises(ValueError), cr:
            raise ValueError("boom")
        self.assertEqual((cr.committed, cr.closed_count), (0, 1))

    def test_body_closing_the_cursor_skips_the_commit(self):
        cr = _Cursor()
        with cr:
            cr.close()
        self.assertEqual(cr.committed, 0)
        self.assertEqual(cr.closed_count, 2)


class TestFlushConvergence(unittest.TestCase):
    def test_no_transaction_and_no_hooks_is_a_noop(self):
        cr = _Cursor()
        cr.flush()

    def test_hooks_run_once_and_are_drained(self):
        cr = _Cursor()
        calls = []
        cr.precommit.add(lambda: calls.append(1))
        cr.flush()
        self.assertEqual(calls, [1])
        self.assertFalse(cr.precommit)

    def test_converging_chain_settles_without_raising(self):
        cr = _Cursor()
        txn = _attach(cr, rounds=3)
        cr.flush()
        self.assertEqual(txn.flush_calls, 4)

    def test_chain_settling_on_the_very_last_pass_does_not_raise(self):
        cr = _Cursor()
        txn = _attach(cr, rounds=BaseCursor._MAX_FLUSH_PASSES)
        cr.flush()
        self.assertEqual(txn.flush_calls, BaseCursor._MAX_FLUSH_PASSES + 1)

    def test_non_converging_chain_raises_instead_of_dropping_work(self):
        cr = _Cursor()
        _attach(cr, rounds=BaseCursor._MAX_FLUSH_PASSES + 1)
        with self.assertRaises(RuntimeError) as ctx:
            cr.flush()
        self.assertIn("did not converge", str(ctx.exception))
        self.assertTrue(cr.precommit, "pending hooks must survive the failure")

    def test_clear_drops_transaction_state_and_precommit(self):
        cr = _Cursor()
        txn = _attach(cr)
        cr.precommit.add(lambda: None)
        cr.clear()
        self.assertEqual(txn.cleared, 1)
        self.assertFalse(cr.precommit)


class TestSavepointSeam(unittest.TestCase):
    class _NonRestoring(_FlushingSavepoint):
        _restores_orm_state = False

    def test_flushing_savepoint_is_used_by_default(self):
        cr = _Cursor()
        cr._flushing_savepoint_cls = self._NonRestoring
        sp = cr.savepoint()
        self.assertIsInstance(sp, _FlushingSavepoint)
        self.assertEqual(cr.statements, ['SAVEPOINT "%s"' % sp.name])
        self.assertEqual(cr._savepoint_depth, 1)

    def test_flush_false_uses_the_plain_savepoint(self):
        cr = _Cursor()
        sp = cr.savepoint(flush=False)
        self.assertIsInstance(sp, Savepoint)
        self.assertNotIsInstance(sp, _FlushingSavepoint)

    def test_db_layer_flushing_savepoint_does_not_restore_orm_state(self):
        self.assertFalse(_FlushingSavepoint._restores_orm_state)

    def test_transaction_bearing_cursor_refuses_a_non_restoring_savepoint(self):
        cr = _Cursor()
        cr._flushing_savepoint_cls = self._NonRestoring
        _attach(cr)
        with self.assertRaises(RuntimeError) as ctx:
            cr.savepoint()
        self.assertIn("does not restore ORM state", str(ctx.exception))
        self.assertEqual(cr._savepoint_depth, 0, "no savepoint may have opened")

    def test_rollback_to_savepoint_hook_is_a_noop_on_the_base(self):
        cr = _Cursor()
        cr._on_rollback_to_savepoint()

    def test_discard_cached_plans_is_a_noop_on_the_base(self):
        _Cursor().invalidate_cached_plans()


class TestDictFetchHelpers(unittest.TestCase):
    class _Rows(_Cursor):
        def __init__(self, rows):
            super().__init__()
            self._rows = list(rows)

        def dictfetchone(self):
            return self._rows.pop(0) if self._rows else None

        def fetchone(self):
            return self._rows.pop(0) if self._rows else None

    def test_dictfetchall_drains(self):
        cr = self._Rows([{"a": 1}, {"a": 2}])
        self.assertEqual(cr.dictfetchall(), [{"a": 1}, {"a": 2}])
        self.assertEqual(cr.dictfetchall(), [])

    def test_dictfetchmany_respects_size_and_exhaustion(self):
        cr = self._Rows([{"a": 1}, {"a": 2}, {"a": 3}])
        self.assertEqual(cr.dictfetchmany(2), [{"a": 1}, {"a": 2}])
        self.assertEqual(cr.dictfetchmany(5), [{"a": 3}])

    def test_dictfetchmany_non_positive_size_yields_nothing(self):
        cr = self._Rows([{"a": 1}])
        for size in (0, -1):
            with self.subTest(size=size):
                self.assertEqual(cr.dictfetchmany(size), [])

    def test_fetchscalar_returns_none_on_no_rows(self):
        self.assertIsNone(self._Rows([]).fetchscalar())
        self.assertEqual(self._Rows([(7, "x")]).fetchscalar(), 7)


class _MetricsCursor(metrics._MetricsMixin):
    def __init__(self):
        import threading

        self._thread = threading.current_thread()
        self.sql_from_log = {}
        self.sql_into_log = {}
        self.sql_log_count = 0
        self.sql_statement_count = 0


class TestMetricsMixin(unittest.TestCase):
    def setUp(self):
        self._saved = metrics.sql_counter
        self.addCleanup(setattr, metrics, "sql_counter", self._saved)
        self.cur = _MetricsCursor()

    def test_record_metrics_bumps_both_counters(self):
        metrics.sql_counter = 0
        self.cur._record_metrics(0.01)
        self.cur._record_metrics(0.01, count=5)
        self.assertEqual(self.cur.sql_log_count, 6)  # noqa: E8516  asserts the row counter itself
        self.assertEqual(metrics.sql_counter, 6)

    def test_statements_are_counted_apart_from_the_rows_they_moved(self):
        self.cur._record_metrics(0.01)
        self.cur._record_metrics(0.01, count=40)
        self.assertEqual(self.cur.sql_log_count, 41)  # noqa: E8516  asserts the row counter itself
        self.assertEqual(
            self.cur.sql_statement_count,
            2,
            "a bulk statement moving 40 rows is one round trip, and that is the "
            "number assertQueryCount has to read",
        )

    def test_record_metrics_runs_query_hooks_with_the_call_context(self):
        seen = []
        self.cur._record_metrics(
            0.5, query="Q", params=(1,), start=2.0, hooks=[lambda *a: seen.append(a)]
        )
        self.assertEqual(seen, [(self.cur, "Q", (1,), 2.0, 0.5)])

    def test_record_metrics_tolerates_a_thread_without_metric_attrs(self):
        self.cur._record_metrics(0.01)

    def test_record_sql_log_buckets_reads_and_writes(self):
        self.cur._record_sql_log("from", "res_users", 0.001)
        self.cur._record_sql_log("from", "res_users", 0.002)
        self.cur._record_sql_log("into", "res_partner", 0.004)
        self.cur._record_sql_log("other", None, 9.0)
        self.assertEqual(self.cur.sql_from_log["res_users"][0], 2)
        self.assertEqual(self.cur.sql_into_log["res_partner"][0], 1)
        self.assertNotIn(None, self.cur.sql_from_log)

    def test_format_interpolates_positional_and_named_params(self):
        self.assertEqual(self.cur._format_statement("SELECT 1"), "SELECT 1")
        self.assertEqual(self.cur._format_statement("a=%s", (1,)), "a=1")
        self.assertEqual(self.cur._format_statement("a=%(k)s", {"k": 2}), "a=2")

    def test_format_unwraps_sql_objects(self):
        self.assertEqual(self.cur._format_statement(SQL("a=%s", 3)), "a=3")

    def test_format_falls_back_instead_of_raising(self):
        out = self.cur._format_statement("a=%s b=%s", (1,))
        self.assertIn("a=%s b=%s", out)
        self.assertIn("(1,)", out)


class TestBeforeStatementSeam(unittest.TestCase):
    def test_base_cursor_hook_is_a_noop(self):
        cursor = _Cursor()
        before = dict(cursor.__dict__)
        cursor._before_statement()
        self.assertEqual(cursor.__dict__, before)

    def test_every_statement_entry_point_calls_it(self):
        missing = [name for name in _STATEMENT_APIS if name not in _marks_statements()]
        self.assertEqual(
            missing,
            [],
            "a statement entry point that skips the hook lets a wrapper cursor's "
            "per-statement bookkeeping be bypassed silently",
        )

    def test_the_hook_marks_exactly_the_known_entry_points(self):
        self.assertEqual(
            _marks_statements(),
            set(_STATEMENT_APIS),
            "update _STATEMENT_APIS (and TestCursor) when the set changes",
        )


_STATEMENT_APIS = ("execute", "executemany", "execute_values", "copy_from", "copy")


def _marks_statements() -> set:
    import inspect

    from odoo.db.cursor import Cursor

    return {
        name
        for name in dir(Cursor)
        if callable(getattr(Cursor, name, None))
        and getattr(inspect.unwrap(getattr(Cursor, name)), "__code__", None) is not None
        and "_before_statement"
        in inspect.unwrap(getattr(Cursor, name)).__code__.co_names
    }


class TestWhatTheFlushPassLimitDoesNotCover(unittest.TestCase):
    def test_a_rearming_hook_is_drained_in_one_pass(self):
        cr = _Cursor()
        txn = _attach(cr)
        runs = {"n": 0}
        limit = BaseCursor._MAX_FLUSH_PASSES * 10

        def rearm():
            runs["n"] += 1
            if runs["n"] < limit:
                cr.precommit.add(rearm)

        cr.precommit.add(rearm)
        cr.flush()

        self.assertEqual(
            runs["n"],
            limit,
            "Callbacks.run drains re-armed work in the same call, so the "
            "hook runs to its own bound rather than to the pass limit",
        )
        self.assertEqual(
            txn.flush_calls,
            2,
            "one flush before the hooks and one after they converged -- the "
            "pass counter never advanced, which is exactly why it cannot "
            "bound this shape",
        )

    def test_the_limit_still_catches_the_shape_it_names(self):
        cr = _Cursor()
        _attach(cr, rounds=BaseCursor._MAX_FLUSH_PASSES + 1)
        with self.assertRaises(RuntimeError) as ctx:
            cr.flush()
        self.assertIn("did not converge", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()


class TestTheDiscardPathTellsAnOutageFromAFault(unittest.TestCase):
    def _close_with(self, rollback_error, *, clean):
        import logging
        from unittest.mock import MagicMock, patch

        from odoo.db import cursor as cursor_mod

        cur = cursor_mod.Cursor.__new__(cursor_mod.Cursor)
        cur._closed = False
        cur._obj = MagicMock()
        cur._cnx = MagicMock()
        cur.cache = MagicMock()
        cur._Cursor__pool = MagicMock()  # type: ignore[attr-defined]
        records = []

        class _Grab(logging.Handler):
            def emit(self, record):
                records.append(record)

        handler = _Grab()
        cursor_mod._logger.addHandler(handler)
        try:
            with (
                patch.object(
                    type(cur), "_rollback", side_effect=rollback_error, create=True
                ),
                patch.object(type(cur), "log_sql_stats", MagicMock(), create=True),
                patch.object(
                    type(cur), "_is_connection_clean", return_value=clean, create=True
                ),
                patch.object(cur, "_Cursor__pool", MagicMock(), create=True),
            ):
                cur._close()
        finally:
            cursor_mod._logger.removeHandler(handler)
        return records

    def test_a_lost_connection_is_a_warning_without_a_traceback(self):
        import psycopg

        exc = psycopg.OperationalError("the connection is lost")
        self.assertIsNone(getattr(exc, "sqlstate", None), "premise: no SQLSTATE")
        records = self._close_with(exc, clean=False)
        loud = [r for r in records if r.levelno >= 40]
        self.assertEqual(loud, [], "an outage was reported as a fault")
        said = [r for r in records if "backend is gone" in r.getMessage()]
        self.assertTrue(said, f"nothing said the connection was discarded: {records}")
        self.assertIsNone(said[0].exc_info, "a traceback adds nothing here")

    def test_a_server_side_failure_is_still_an_exception(self):
        import psycopg

        exc = psycopg.errors.InsufficientPrivilege("nope")
        self.assertIsNotNone(getattr(exc, "sqlstate", None), "premise: has a SQLSTATE")
        records = self._close_with(exc, clean=False)
        loud = [r for r in records if r.levelno >= 40]
        self.assertTrue(loud, "a genuine rollback fault stopped being reported")
        self.assertIsNotNone(loud[0].exc_info, "and it kept its traceback")


class TestPipelineAccountsForTheSyncCost(unittest.TestCase):
    # Per process: two Tier-2 runs at once (peer sessions, the pre-push hook)
    # would otherwise race on one name, and a killed run's leftover would
    # skip every later one.
    DBNAME = f"test_cursor_pipeline_sync_cost_{os.getpid()}"

    @classmethod
    def setUpClass(cls):
        try:
            subprocess.run(
                ["createdb", cls.DBNAME], check=True, capture_output=True, timeout=30
            )
        except (OSError, subprocess.CalledProcessError) as e:
            raise unittest.SkipTest(f"no local createdb available: {e}") from e

    @classmethod
    def tearDownClass(cls):
        from odoo.db import close_db

        close_db(cls.DBNAME)
        dropped = subprocess.run(
            ["dropdb", "--if-exists", cls.DBNAME],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert dropped.returncode == 0, (
            f"{cls.DBNAME} outlived the test, so the next run skips instead of "
            f"measuring: {dropped.stderr.strip()}"
        )

    def _timed_cursor(self):
        import odoo.tools.config  # noqa: F401  installs the pool settings source
        from odoo.db import db_connect

        thread = threading.current_thread()
        # The cursor accumulates onto the running thread, which declares neither
        # attribute -- that is the contract `_record_metrics` relies on.
        thread.query_count = 0  # type: ignore[attr-defined]
        thread.query_time = 0.0  # type: ignore[attr-defined]
        return thread, db_connect(self.DBNAME).cursor()

    def test_pipelined_execute_values_accounts_for_server_wait(self):
        import time

        thread, cr = self._timed_cursor()
        with cr:
            cr.execute("CREATE TABLE t_pipeline_sync(a int)")
            before_time = thread.query_time  # type: ignore[attr-defined]
            t0 = time.monotonic()
            # Two batches each wait on the server. Unlike a wall-time ratio for
            # cheap inserts, this lower bound excludes Python and logging costs.
            cr.execute_values(
                "INSERT INTO t_pipeline_sync "
                "SELECT column1 FROM (VALUES %s) AS batch "
                "CROSS JOIN (SELECT pg_sleep(0.05)) AS delay",
                [(1,), (2,), (3,), (4,)],
                page_size=2,
            )
            wall = time.monotonic() - t0
            recorded = thread.query_time - before_time  # type: ignore[attr-defined]
            logging.getLogger(__name__).debug(
                "pipeline server waits: recorded=%fs wall=%fs", recorded, wall
            )
            cr.execute("SELECT count(*) FROM t_pipeline_sync")
            self.assertEqual(cr.fetchone(), (4,))

        self.assertGreaterEqual(
            recorded,
            0.09,
            f"only {recorded:.4f}s was accounted for two 50ms server waits "
            "-- the pipeline sync/flush cost is going untimed again",
        )

    def test_python_time_inside_the_block_is_not_query_time(self):
        import time

        thread, cr = self._timed_cursor()
        with cr:
            before_time = thread.query_time  # type: ignore[attr-defined]
            t0 = time.monotonic()
            with cr.pipeline():
                cr.execute("SELECT 1")
                cr.execute("SELECT 2")
                time.sleep(0.05)
                cr.execute("SELECT 3")
            wall = time.monotonic() - t0
            recorded = thread.query_time - before_time  # type: ignore[attr-defined]
            cr.rollback()

        self.assertGreater(recorded, 0.0)
        self.assertLess(
            recorded / wall,
            0.2,
            f"{recorded:.4f}s of {wall:.4f}s was booked as query time, but the "
            f"block was 50 ms of sleep: wall-minus-statements is not a sync cost",
        )

    def test_a_fetch_inside_the_block_is_the_wait_it_is(self):
        import time

        thread, cr = self._timed_cursor()
        with cr:
            before_time = thread.query_time  # type: ignore[attr-defined]
            t0 = time.monotonic()
            with cr.pipeline():
                cr.execute("SELECT pg_sleep(0.02)")
                cr.execute("SELECT pg_sleep(0.02)")
                cr.execute("SELECT 3")
                rows = cr.fetchall()
            wall = time.monotonic() - t0
            recorded = thread.query_time - before_time  # type: ignore[attr-defined]
            cr.rollback()

        self.assertEqual(rows, [(3,)])
        self.assertGreater(
            recorded / wall,
            0.9,
            f"only {recorded:.4f}s of {wall:.4f}s: psycopg syncs on the first "
            f"fetch, so that fetch is where the server wait lands",
        )

    def test_rowcount_inside_the_block_is_the_statements_own(self):
        _, cr = self._timed_cursor()
        with cr:
            cr.execute("CREATE TABLE t_pipeline_rowcount(id int)")
            cr.execute("INSERT INTO t_pipeline_rowcount SELECT generate_series(1, 7)")
            with cr.pipeline():
                cr.execute("UPDATE t_pipeline_rowcount SET id = id WHERE id <= 3")
                self.assertEqual(cr.rowcount, 3)
                cr.execute("UPDATE t_pipeline_rowcount SET id = id WHERE id <= 5")
                self.assertTrue(cr.in_pipeline)
                self.assertEqual(cr.rowcount, 5)
                cr.execute("DELETE FROM t_pipeline_rowcount WHERE id > 100")
                self.assertEqual(cr.rowcount, 0)
                cr.execute("SELECT id FROM t_pipeline_rowcount ORDER BY id")
                self.assertEqual([c.name for c in cr.description], ["id"])
                self.assertEqual(cr.fetchone(), (1,))
                # executemany keeps no pgresult at all after its sync, so the
                # cursor tracks "queued since the last sync" itself.
                cr.executemany(
                    "INSERT INTO t_pipeline_rowcount VALUES (%s)", [(8,), (9,)]
                )
                self.assertEqual(cr.rowcount, 2)
                self.assertEqual(cr.rowcount, 2)
                cr.executemany(
                    "INSERT INTO t_pipeline_rowcount VALUES (%s) RETURNING id",
                    [(10,), (11,)],
                    returning=True,
                )
                self.assertEqual(cr.fetchone(), (10,))
                self.assertTrue(cr.nextset(), "nextset syncs like a fetch does")
                self.assertEqual(cr.fetchone(), (11,))
            cr.rollback()


class TestEnableLogging(unittest.TestCase):
    """`_enable_logging` is the aid a failed `assertQueryCount` reaches for.

    It went missing in the odoo/db split -- `addons/test_discuss_full`'s performance
    test still called it, so the warm branch of that test raised AttributeError
    instead of showing the queries it had just counted. Restored with this test, so
    the next split notices.
    """

    class _Metered(metrics._MetricsMixin):
        pass

    def _cursor(self):
        cursor = self._Metered()
        cursor._init_metrics_state()
        return cursor

    def test_the_block_logs_at_debug_and_the_level_comes_back(self):
        logger = logging.getLogger(CURSOR_LOGGER_NAME)
        logger.setLevel(logging.WARNING)
        try:
            with self._cursor()._enable_logging():
                self.assertTrue(logger.isEnabledFor(logging.DEBUG))
            self.assertEqual(logger.level, logging.WARNING)
        finally:
            logger.setLevel(logging.NOTSET)

    def test_the_level_comes_back_even_when_the_block_raises(self):
        logger = logging.getLogger(CURSOR_LOGGER_NAME)
        logger.setLevel(logging.WARNING)
        try:
            with self.assertRaises(ValueError), self._cursor()._enable_logging():
                raise ValueError("the block failed")
            self.assertEqual(logger.level, logging.WARNING)
        finally:
            logger.setLevel(logging.NOTSET)


class TestConnectionRecord(unittest.TestCase):
    class _Pool:
        readonly = False

        def __init__(self):
            self.borrowed: list = []

        def borrow(self, dsn, key=None, **kw):
            self.borrowed.append((dsn, key))
            raise RuntimeError("stop before a real connection")

    def test_dsn_strips_the_password_and_expands_a_uri(self):
        from odoo.db.cursor import Connection

        conn = Connection(
            typing.cast("Any", self._Pool()),
            "dbz",
            {"dsn": "postgresql://u:s3cret@h/dbz"},
        )
        self.assertEqual(conn.dbname, "dbz")
        self.assertEqual(conn.dsn, {"user": "u", "host": "h", "dbname": "dbz"})

    def test_cursor_borrows_with_the_key_computed_once(self):
        from odoo.db.cursor import Connection
        from odoo.db.dsn import _get_dsn_key

        pool = self._Pool()
        info = {"dbname": "x", "host": "h", "password": "hunter2"}
        conn = Connection(typing.cast("Any", pool), "x", info)
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, "stop before"):
                conn.cursor()
        self.assertEqual(pool.borrowed, [(info, _get_dsn_key(info))] * 2)
        self.assertNotIn("hunter2", str(sorted(pool.borrowed[0][1])))
