import contextlib
import copy
import inspect
import json
import logging
import os
import socket
import threading
import time
import warnings
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import partial
from itertools import starmap
from unittest.mock import MagicMock, patch

import psycopg
from psycopg import IsolationLevel
from psycopg.postgres import types as _pg_types
from psycopg.pq import TransactionStatus as _TxStatus
from psycopg_pool import PoolTimeout

import odoo
from odoo import api, tools
from odoo.db import Connection, db_connect, get_or_create_row
from odoo.db import pool as pool_module
from odoo.db import schema as sql_schema
from odoo.db import settings as pool_settings
from odoo.db import utils as _db_utils
from odoo.db.cursor import (
    Cursor,
    _FlushingSavepoint,
)
from odoo.db.errors import is_stale_cached_plan
from odoo.db.lifecycle import (
    _IDLE_SINCE_ATTR,
    _RESET_SESSION_STATE_SQL,
)
from odoo.db.pool import (
    ConnectionPool,
    PoolError,
    _check_connection,
    _configure_connection,
    _get_dsn_key,
    _reset_connection,
    _SuppressKnownPoolWarnings,
)
from odoo.db.reaper import get_checked_out_count as reaper_checked_out
from odoo.db.utils import get_connection_info_for_database
from odoo.exceptions import ConcurrencyError
from odoo.modules.registry import Registry
from odoo.orm.runtime.backend import COPY_THRESHOLD
from odoo.service.db import exp_drop
from odoo.service.transaction import retrying
from odoo.tests import common
from odoo.tests.common import BaseCase, HttpCase
from odoo.tests.cursor import TestCursor
from odoo.tools import SQL
from odoo.tools.misc import mute_logger

_TX_IDLE = _TxStatus.IDLE

ADMIN_USER_ID = common.ADMIN_USER_ID


INT4_OID = _pg_types["int4"].oid
TEXT_OID = _pg_types["text"].oid


def _boom(*_args, **_kwargs):
    raise RuntimeError("hook exploded")


class _ProbeAbort(Exception):
    pass


def _callees(func):
    return set(func.__code__.co_names)


def _calls(func):
    import ast
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def _own_methods(model_cls):
    methods = {}
    for name in dir(model_cls):
        if not name.startswith("_") and name != "method_direct_trigger":
            continue
        attr = inspect.getattr_static(model_cls, name, None)
        func = getattr(attr, "__func__", attr)
        if inspect.isfunction(func):
            methods[name] = _callees(func)
    return methods


def _reachable(start, methods):
    seen, todo = set(), [start]
    while todo:
        name = todo.pop()
        for called in methods.get(name, ()):
            if called in methods and called not in seen:
                seen.add(called)
                todo.append(called)
    return seen


def registry():
    return Registry(common.get_db_name())


class TestRealCursor(BaseCase):
    def test_execute_bad_params(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE login=%s", "admin")
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", 1)
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", "1")

    def test_using_closed_cursor(self):
        with registry().cursor() as cr:
            cr.close()
            with self.assertRaises(psycopg.InterfaceError):
                cr.execute("SELECT 1", log_exceptions=False)

    def test_commit_rollback_on_closed_cursor_raise(self):
        cr = registry().cursor()
        cr.close()
        with self.assertRaises(psycopg.InterfaceError):
            cr.commit()
        with self.assertRaises(psycopg.InterfaceError):
            cr.rollback()

    def test_multiple_close_call_cursor(self):
        cr = registry().cursor()
        cr.close()
        cr.close()

    def test_transaction_isolation_cursor(self):
        with registry().cursor() as cr:
            self.assertEqual(
                cr.connection.isolation_level, IsolationLevel.REPEATABLE_READ
            )

    def test_connection_readonly(self):
        registry_ = registry()
        with registry_.cursor(readonly=False) as cr:
            cr.execute("SHOW transaction_read_only")
            self.assertEqual(cr.fetchone(), ("off",))
            self.assertFalse(cr.readonly)

        with registry_.cursor(readonly=True) as cr:
            cr.execute("SHOW transaction_read_only")
            self.assertEqual(cr.fetchone(), ("on",))
            self.assertTrue(cr.readonly)


class TestSeedPlannerStats(BaseCase):
    def test_seeds_floors_for_zero_stat_tables(self):
        from odoo.db.utils import update_planner_stats

        cr = registry().cursor()
        try:
            cr.execute(
                'CREATE TABLE "_test_seed_planner_stats" '
                "(id serial PRIMARY KEY, val integer)"
            )
            seeded = update_planner_stats(cr)
            self.assertGreaterEqual(seeded, 1)

            cr.execute(
                "SELECT reltuples::int, relpages FROM pg_class "
                "WHERE relname = '_test_seed_planner_stats'"
            )
            reltuples, relpages = cr.fetchone()
            self.assertGreater(reltuples, 0)
            self.assertGreater(relpages, 0)

            self.assertEqual(update_planner_stats(cr), 0)
        finally:
            cr.rollback()
            cr.close()


class TestSeedPlannerStatsInClassTransaction(common.TransactionCase):
    def test_no_zero_stat_tables_visible(self):
        self.env.cr.execute(
            """
            SELECT c.relname
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE c.relkind = 'r'
               AND n.nspname = 'public'
               AND c.reltuples <= 0
               AND c.relowner = quote_ident(current_user)::regrole
            """
        )
        self.assertEqual([row[0] for row in self.env.cr.fetchall()], [])


class TestHTTPCursor(HttpCase):
    def test_cursor_keeps_readwriteness(self):
        with self.env.registry.cursor(readonly=False) as cr:
            self.assertFalse(cr.readonly)
            cr.execute("SELECT 1")
            cr.rollback()
            self.assertFalse(cr.readonly)
            cr.execute("SELECT 1")
            cr.commit()
            self.assertFalse(cr.readonly)

        with self.env.registry.cursor(readonly=True) as cr:
            self.assertTrue(cr.readonly)
            cr.execute("SELECT 1")
            cr.rollback()
            self.assertTrue(cr.readonly)
            cr.execute("SELECT 1")
            cr.commit()
            self.assertTrue(cr.readonly)

    def test_call_kw_readonly(self):
        self.authenticate("admin", "admin")
        _ = self.env.user.partner_id.id

        def return_readonly(self, *args, **kwargs):
            return ["ok", self.env.cr.readonly]

        with patch.object(type(self.env["res.partner"]), "read", return_readonly):
            result_read = self.url_open(
                "/web/dataset/call_kw",
                data=json.dumps(
                    {
                        "params": {
                            "model": "res.partner",
                            "method": "read",
                            "args": [self.env.user.partner_id.id, ["name"]],
                            "kwargs": {},
                        },
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(result_read.status_code, 200)
            ok, readonly = result_read.json()["result"]
            self.assertEqual(ok, "ok")
            self.assertEqual(readonly, True, "Call to read are expecte to be read only")

        with patch.object(type(self.env["res.partner"]), "write", return_readonly):
            result_write = self.url_open(
                "/web/dataset/call_kw",
                data=json.dumps(
                    {
                        "params": {
                            "model": "res.partner",
                            "method": "write",
                            "args": [
                                self.env.user.partner_id.id,
                                {"name": "Urgo"},
                            ],
                            "kwargs": {},
                        },
                    }
                ),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(result_write.status_code, 200)
            ok, readonly = result_write.json()["result"]
            self.assertEqual(ok, "ok")
            self.assertEqual(
                readonly, False, "Call to write are expecte to be read write"
            )


class TestTestCursor(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.registry_enter_test_mode()
        self.cr = self.registry.cursor()
        self.addCleanup(self.cr.close)
        self.env = api.Environment(self.cr, api.SUPERUSER_ID, {})
        self.record = self.env["res.partner"].create({"name": "Foo"})

    def write(self, record, value):
        record.ref = value

    def flush(self, record):
        record.flush_model(["ref"])

    def check(self, record, value):
        record.invalidate_recordset()
        self.assertEqual(record.read(["ref"])[0]["ref"], value)

    def test_single_cursor(self):
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, "A")
        self.cr.commit()

        self.write(self.record, "B")
        self.cr.rollback()
        self.check(self.record, "A")

        self.write(self.record, "C")
        self.cr.rollback()
        self.check(self.record, "A")

    def test_now_is_utc_and_resets(self):
        self.assertIsInstance(self.cr, TestCursor)
        self.cr.commit()
        self.assertIsNone(self.cr._now)

        t = self.cr.now()
        self.assertIsNone(t.tzinfo, "now() must be naive")
        utc_naive = datetime.now(UTC).replace(tzinfo=None)
        self.assertLess(
            abs((utc_naive - t).total_seconds()),
            600,
            "TestCursor.now() is not UTC — local-time regression",
        )
        self.assertIs(self.cr.now(), t, "now() must be cached within a transaction")

        self.cr.commit()
        self.assertIsNone(self.cr._now, "commit() must reset now()")
        self.cr.now()
        self.cr.rollback()
        self.assertIsNone(self.cr._now, "rollback() must reset now()")

    def test_fetch_helpers_forward_to_real_cursor(self):
        self.assertIsInstance(self.cr, TestCursor)

        self.cr.execute("SELECT 42")
        self.assertEqual(self.cr.fetchscalar(), 42)

        self.cr.execute("SELECT 1 WHERE FALSE")
        self.assertIsNone(self.cr.fetchscalar())

        self.cr.execute("SELECT 7 AS v")
        self.assertEqual(self.cr.fetchone(), (7,))
        self.cr.execute("SELECT 7 AS v")
        self.assertEqual(self.cr.dictfetchone(), {"v": 7})

    def test_sub_commit(self):
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, "A")
        self.cr.commit()

        self.write(self.record, "B")
        self.flush(self.record)

        with self.registry.cursor() as cr:
            self.assertIsInstance(cr, TestCursor)
            record = self.record.with_env(self.env(cr=cr))
            self.check(record, "B")
            self.write(record, "C")

        self.check(self.record, "C")

        self.cr.rollback()
        self.check(self.record, "A")

    def test_sub_rollback(self):
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, "A")
        self.cr.commit()

        self.write(self.record, "B")
        self.flush(self.record)

        with self.assertRaises(ValueError):
            with self.registry.cursor() as cr:
                self.assertIsInstance(cr, TestCursor)
                record = self.record.with_env(self.env(cr=cr))
                self.check(record, "B")
                self.write(record, "C")
                raise ValueError(42)

        self.check(self.record, "B")

        self.cr.rollback()
        self.check(self.record, "A")

    def test_an_outer_cursor_first_used_inside_a_nested_one_keeps_its_savepoint(self):
        outer = self.registry.cursor()
        inner = self.registry.cursor()
        inner.execute("SELECT 1")
        outer.execute("SELECT 1")
        inner.close()
        outer.commit()
        outer.close()
        self.assertNotIn(outer, TestCursor._cursors_stack)

    def test_interleaving(self):
        a = self.registry.cursor()
        b = self.registry.cursor()
        a._check_savepoint()
        b._check_savepoint()
        with self.assertLogs("odoo.tests.cursor", level=logging.WARNING) as cm:
            a.close()
        [msg] = cm.output
        self.assertIn("WARNING:odoo.tests.cursor:Out-of-order close", msg)
        self.assertIn(b, TestCursor._cursors_stack)
        with self.assertNoLogs("odoo.tests.cursor", level=logging.WARNING):
            with self.assertRaises(psycopg.errors.InvalidSavepointSpecification):
                b.close()
        self.assertNotIn(b, TestCursor._cursors_stack)

    def test_borrow_connection(self):
        cursors = []
        pool = ConnectionPool(maxconn=4)
        self.addCleanup(pool.close_all)
        db, info = get_connection_info_for_database(self.cr.dbname)
        try:
            connection = Connection(pool, db, info)

            cursors.extend((connection.cursor(), connection.cursor()))
            pid0 = cursors[0].connection.info.backend_pid
            pid1 = cursors[1].connection.info.backend_pid
            self.assertNotEqual(pid0, pid1)

            cursors[0].close()
            cursors.append(connection.cursor())
            pid2 = cursors[2].connection.info.backend_pid
            self.assertEqual(pid0, pid2)

        finally:
            for cursor in cursors:
                if not cursor.closed:
                    cursor.close()


class TestStatementBudgetOnATestCursor(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.registry_enter_test_mode()

    def _sleeps(self, cr, seconds=0.4):
        try:
            cr.execute("SELECT pg_sleep(%s)", (seconds,))
        except psycopg.errors.QueryCanceled:
            cr.rollback()
            return False
        return True

    def test_the_budget_outlives_a_rollback_and_ends_with_the_test_cursor(self):
        cr = self.registry.cursor()
        try:
            cr.set_statement_timeout(0.1)
            self.assertFalse(self._sleeps(cr), "bounded on the first statement")
            self.assertFalse(self._sleeps(cr), "still bounded after its rollback")
            cr.execute("SHOW statement_timeout")
            self.assertEqual(cr.fetchone(), ("100ms",))
        finally:
            cr.close()
        cr = self.registry.cursor()
        try:
            cr.execute("SHOW statement_timeout")
            self.assertEqual(
                cr.fetchone(),
                ("0",),
                "the real cursor outlives every test cursor: the budget must not",
            )
            self.assertTrue(self._sleeps(cr, 0.05))
        finally:
            cr.close()


class TestCursorHooks(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.log = []

    def prepare_hooks(self, cr):
        self.log.clear()
        cr.precommit.add(partial(self.log.append, "preC"))
        cr.postcommit.add(partial(self.log.append, "postC"))
        cr.prerollback.add(partial(self.log.append, "preR"))
        cr.postrollback.add(partial(self.log.append, "postR"))
        self.assertEqual(self.log, [])

    def test_hooks_on_cursor(self):
        cr = self.registry.cursor()

        self.prepare_hooks(cr)
        cr.commit()
        self.assertEqual(self.log, ["preC", "postC"])

        self.prepare_hooks(cr)
        cr.flush()
        self.assertEqual(self.log, ["preC"])
        cr.rollback()
        self.assertEqual(self.log, ["preC", "preR", "postR"])

        self.prepare_hooks(cr)
        cr.close()
        self.assertEqual(self.log, ["preR", "postR"])

    def test_hooks_on_testcursor(self):
        self.registry_enter_test_mode()

        cr = self.registry.cursor()

        self.prepare_hooks(cr)
        cr.commit()
        self.assertEqual(self.log, ["preC"])

        self.prepare_hooks(cr)
        cr.flush()
        self.assertEqual(self.log, ["preC"])
        cr.rollback()
        self.assertEqual(self.log, ["preC", "preR", "postR"])

        self.prepare_hooks(cr)
        cr.close()
        self.assertEqual(self.log, ["preR", "postR"])


class TestCursorHooksTransactionCaseCleanup(common.TransactionCase):
    @staticmethod
    def initial_callback():
        pass

    @staticmethod
    def other_callback():
        pass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cr = cls.env.cr
        cls.callback_names = [
            "precommit",
            "postcommit",
            "prerollback",
            "postrollback",
        ]
        cls.callbacks = [
            cr.precommit,
            cr.postcommit,
            cr.prerollback,
            cr.postrollback,
        ]

        for callback, name in zip(cls.callbacks, cls.callback_names, strict=False):
            callback.data[f"test_cursor_hooks_{name}"] = ["keep"]
            callback.add(cls.initial_callback)

    def assertHookData(self):
        for callback, name in zip(self.callbacks, self.callback_names, strict=False):
            self.assertEqual(
                callback.data[f"test_cursor_hooks_{name}"],
                ["keep"],
                f"{name} failed to clean up between transaction tests",
            )
            self.assertIn(self.initial_callback, callback._funcs)
            self.assertNotIn(self.other_callback, callback._funcs)

    def test_1_isolation(self):
        self.assertHookData()
        for callback, name in zip(self.callbacks, self.callback_names, strict=False):
            callback.data[f"test_cursor_hooks_{name}"].append("don't keep")
            callback.add(self.other_callback)

    def test_2_isolation(self):
        self.assertHookData()
        for callback in self.callbacks:
            callback.run()

    def test_3_isolation(self):
        self.assertHookData()
        for callback in self.callbacks:
            callback.clear()

    def test_4_isolation(self):
        self.assertHookData()
        self.env.cr.clear()

    def test_5_isolation(self):
        self.assertHookData()


class TestNumericToFloat(common.TransactionCase):
    def test_numeric_column_returns_float(self):
        self.env.cr.execute("SELECT 1.5::numeric")
        val = self.env.cr.fetchone()[0]
        self.assertIsInstance(val, float)
        self.assertEqual(val, 1.5)

    def test_numeric_null_returns_none(self):
        self.env.cr.execute("SELECT NULL::numeric")
        val = self.env.cr.fetchone()[0]
        self.assertIsNone(val)

    def test_numeric_precision(self):
        self.env.cr.execute("SELECT 123456789.123456789::numeric")
        val = self.env.cr.fetchone()[0]
        self.assertIsInstance(val, float)
        self.assertAlmostEqual(val, 123456789.123456789)


class TestCursorFetchMethods(BaseCase):
    def test_fetchscalar_value(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 42")
            self.assertEqual(cr.fetchscalar(), 42)

    def test_fetchscalar_null(self):
        with registry().cursor() as cr:
            cr.execute("SELECT NULL::int")
            self.assertIsNone(cr.fetchscalar())

    def test_fetchscalar_empty(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 1 WHERE FALSE")
            self.assertIsNone(cr.fetchscalar())

    def test_fetchscalar_multi_column(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 1, 2, 3")
            self.assertEqual(cr.fetchscalar(), 1)

    def test_dictfetchone(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 1 AS a, 'hello' AS b")
            self.assertEqual(cr.dictfetchone(), {"a": 1, "b": "hello"})

    def test_dictfetchone_empty(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 1 AS a WHERE FALSE")
            self.assertIsNone(cr.dictfetchone())

    def test_dictfetchmany(self):
        with registry().cursor() as cr:
            cr.execute("SELECT generate_series(1, 5) AS v")
            rows = cr.dictfetchmany(3)
            self.assertEqual(len(rows), 3)
            self.assertEqual([r["v"] for r in rows], [1, 2, 3])

    def test_dictfetchmany_exceeds_available(self):
        with registry().cursor() as cr:
            cr.execute("SELECT generate_series(1, 2) AS v")
            rows = cr.dictfetchmany(10)
            self.assertEqual(len(rows), 2)

    def test_dictfetchall(self):
        with registry().cursor() as cr:
            cr.execute("SELECT generate_series(1, 3) AS v")
            rows = cr.dictfetchall()
            self.assertEqual(len(rows), 3)
            self.assertEqual([r["v"] for r in rows], [1, 2, 3])

    def test_dictfetchall_empty(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 1 AS v WHERE FALSE")
            self.assertEqual(cr.dictfetchall(), [])


class TestCursorNow(BaseCase):
    def test_now_returns_datetime(self):
        with registry().cursor() as cr:
            result = cr.now()
            self.assertIsInstance(result, datetime)

    def test_now_cached_within_transaction(self):
        with registry().cursor() as cr:
            t1 = cr.now()
            t2 = cr.now()
            self.assertIs(t1, t2)

    def test_now_reset_after_commit(self):
        with registry().cursor() as cr:
            cr.now()
            self.assertIsNotNone(cr._now)
            cr.commit()
            self.assertIsNone(cr._now)

    def test_now_reset_after_rollback(self):
        with registry().cursor() as cr:
            cr.now()
            self.assertIsNotNone(cr._now)
            cr.rollback()
            self.assertIsNone(cr._now)

    def test_now_survives_savepoint(self):
        with registry().cursor() as cr:
            t1 = cr.now()
            with cr.savepoint():
                cr.execute("SELECT 1")
            self.assertIs(cr.now(), t1)
            with cr.savepoint() as sp:
                cr.execute("SELECT 1")
                sp.rollback()
            self.assertIs(cr.now(), t1)

    def test_now_equals_transaction_timestamp(self):
        with registry().cursor() as cr:
            t = cr.now()
            cr.execute("SELECT transaction_timestamp() AT TIME ZONE 'UTC'")
            self.assertEqual(t, cr.fetchone()[0])


class TestCursorBulkMethods(BaseCase):
    def test_execute_values_basic(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_ev (a int, b text)")
            cr.execute_values(
                "INSERT INTO _test_ev (a, b) VALUES %s",
                [(1, "x"), (2, "y"), (3, "z")],
            )
            cr.execute("SELECT a, b FROM _test_ev ORDER BY a")
            self.assertEqual(cr.fetchall(), [(1, "x"), (2, "y"), (3, "z")])

    def test_execute_values_with_fetch(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_evf (id serial, val int)")
            results = cr.execute_values(
                "INSERT INTO _test_evf (val) VALUES %s RETURNING id, val",
                [(10,), (20,)],
                fetch=True,
            )
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0][1], 10)
            self.assertEqual(results[1][1], 20)

    def test_execute_values_empty(self):
        with registry().cursor() as cr:
            result = cr.execute_values("INSERT INTO nonexistent VALUES %s", [])
            self.assertIsNone(result)
            result = cr.execute_values(
                "INSERT INTO nonexistent VALUES %s", [], fetch=True
            )
            self.assertEqual(result, [])

    def test_execute_values_custom_template(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_evt (a int, b int)")
            cr.execute_values(
                "INSERT INTO _test_evt (a, b) VALUES %s",
                [(1, 10), (2, 20)],
                template="(%s, %s)",
            )
            cr.execute("SELECT a, b FROM _test_evt ORDER BY a")
            self.assertEqual(cr.fetchall(), [(1, 10), (2, 20)])

    def test_execute_values_paging(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_evp (val int)")
            data = [(i,) for i in range(10)]
            cr.execute_values(
                "INSERT INTO _test_evp (val) VALUES %s",
                data,
                page_size=3,
            )
            cr.execute("SELECT count(*) FROM _test_evp")
            self.assertEqual(cr.fetchone()[0], 10)

    def test_execute_values_pipeline_error_is_logged(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_evpl (n int)")
            cr.commit()
            rows = [(i,) for i in range(150)]
            rows[75] = ("not-an-int",)
            with (
                self.assertLogs("odoo.db.cursor", level="WARNING") as cm,
                self.assertRaises(psycopg.Error),
            ):
                cr.execute_values("INSERT INTO _test_evpl (n) VALUES %s", rows)
            cr.rollback()
        self.assertTrue(
            any("_test_evpl" in line for line in cm.output),
            f"pipelined execute_values error was not logged: {cm.output}",
        )

    def test_executemany_basic(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_em (a int, b text)")
            cr.executemany(
                "INSERT INTO _test_em (a, b) VALUES (%s, %s)",
                [(1, "x"), (2, "y"), (3, "z")],
            )
            cr.execute("SELECT a, b FROM _test_em ORDER BY a")
            self.assertEqual(cr.fetchall(), [(1, "x"), (2, "y"), (3, "z")])

    def test_executemany_returning(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_emr (id serial, val int)")
            cr.executemany(
                "INSERT INTO _test_emr (val) VALUES (%s) RETURNING id",
                [(10,), (20,), (30,)],
                returning=True,
            )
            ids = list(cr.fetchall())
            while cr.nextset():
                ids.extend(cr.fetchall())
            self.assertEqual(len(ids), 3)

    def test_executemany_empty(self):
        with registry().cursor() as cr:
            cr.executemany("INSERT INTO nonexistent VALUES (%s)", [])

    def test_pipeline_mode(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_pipe (val int)")
            with cr.pipeline():
                for i in range(5):
                    cr.execute("INSERT INTO _test_pipe (val) VALUES (%s)", [i])
            cr.execute("SELECT count(*) FROM _test_pipe")
            self.assertEqual(cr.fetchone()[0], 5)

    def test_pipeline_nesting(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_nest (val int)")
            with cr.pipeline():
                cr.execute("INSERT INTO _test_nest (val) VALUES (%s)", [1])
                with cr.pipeline():
                    cr.execute("INSERT INTO _test_nest (val) VALUES (%s)", [2])
                    cr.execute("INSERT INTO _test_nest (val) VALUES (%s)", [3])
                cr.execute("INSERT INTO _test_nest (val) VALUES (%s)", [4])
            cr.execute("SELECT count(*) FROM _test_nest")
            self.assertEqual(cr.fetchone()[0], 4)

    def test_pipeline_of_one_statement_never_enters_pipeline_mode(self):
        with registry().cursor() as cr:
            with cr.pipeline():
                cr.execute("SELECT 1 AS a")
                self.assertFalse(
                    cr.in_pipeline,
                    "a lone statement in a pipeline block should have run "
                    "outside pipeline mode",
                )
                self.assertEqual(cr.fetchall(), [(1,)])

    def test_pipeline_enters_on_the_second_statement(self):
        with registry().cursor() as cr:
            with cr.pipeline():
                cr.execute("SELECT 1 AS a")
                cr.execute("SELECT 2 AS b")
                self.assertTrue(
                    cr.in_pipeline,
                    "the second statement should have run in pipeline mode",
                )
                # The queued statement has no result yet; the cursor syncs the
                # pipeline to answer rather than reporting the stale None.
                self.assertEqual([c.name for c in cr.description], ["b"])
                self.assertEqual(cr.fetchall(), [(2,)])

    def test_executemany_counts_toward_arming_the_pipeline(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_em_pipe (val int)")
            with cr.pipeline():
                cr.executemany(
                    "INSERT INTO _test_em_pipe (val) VALUES (%s)", [(1,), (2,)]
                )
                self.assertFalse(
                    cr.in_pipeline, "one statement is still a batch that never forms"
                )
                cr.executemany(
                    "INSERT INTO _test_em_pipe (val) VALUES (%s)", [(3,), (4,)]
                )
                self.assertTrue(
                    cr.in_pipeline,
                    "executemany is a statement and the block arms on the "
                    "second one; counting only execute() meant a block made of "
                    "executemany calls never entered the mode its caller asked "
                    "for, paying one sync per call instead of one per block",
                )
            cr.execute("SELECT count(*) FROM _test_em_pipe")
            self.assertEqual(cr.fetchone()[0], 4)

    def test_an_empty_executemany_does_not_arm_the_pipeline(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_em_empty (val int)")
            with cr.pipeline():
                cr.executemany("INSERT INTO _test_em_empty (val) VALUES (%s)", [])
                cr.executemany("INSERT INTO _test_em_empty (val) VALUES (%s)", [])
                self.assertFalse(
                    cr.in_pipeline,
                    "a call that issues no statement must not count toward the "
                    "second one, or an empty batch arms a mode with nothing in it",
                )

    def test_pipeline_nesting_does_not_re_enter_the_mode(self):
        with registry().cursor() as cr:
            with cr.pipeline():
                cr.execute("SELECT 1 AS a")
                with cr.pipeline():
                    cr.execute("SELECT 2 AS b")
                    self.assertTrue(cr.in_pipeline)
                    self.assertEqual(cr.fetchall(), [(2,)])
                self.assertTrue(
                    cr.in_pipeline, "the inner exit must not leave the mode"
                )
                cr.execute("SELECT 3 AS c")
                self.assertEqual(cr.fetchall(), [(3,)])

    def test_copy_from_inside_a_pipeline_says_what_is_wrong(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _cp_err (id int)")
            with cr.pipeline():
                cr.execute("SELECT 1")
                cr.execute("SELECT 2")
                with self.assertRaises(Exception) as caught:
                    cr.copy_from("_cp_err", ["id"], [(1,)])
            self.assertIn("cannot run inside pipeline mode", str(caught.exception))
            self.assertIn("execute_values", str(caught.exception))

    def test_pipeline_fire_and_forget_updates(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_upd (id int, val int)")
            cr.execute("INSERT INTO _test_upd VALUES (1, 10), (2, 20), (3, 30)")
            with cr.pipeline():
                cr.execute("UPDATE _test_upd SET val = val + 100 WHERE id = %s", [1])
                cr.execute("UPDATE _test_upd SET val = val + 200 WHERE id = %s", [2])
                cr.execute("UPDATE _test_upd SET val = val + 300 WHERE id = %s", [3])
            cr.execute("SELECT val FROM _test_upd ORDER BY id")
            self.assertEqual(cr.fetchall(), [(110,), (220,), (330,)])


def _merge(cr, table, columns, rows, on_columns, *, returning="NEW.id"):
    if not rows:
        return []

    comma = SQL(", ").join
    col_ids = [SQL.identifier(c) for c in columns]
    s_cols = [SQL("s.%s", SQL.identifier(c)) for c in columns]
    on_pred = SQL(" AND ").join(
        SQL("t.%s = s.%s", SQL.identifier(c), SQL.identifier(c)) for c in on_columns
    )
    update_cols = [c for c in columns if c not in on_columns]
    assignments = comma(
        SQL("%s = s.%s", SQL.identifier(c), SQL.identifier(c)) for c in update_cols
    )

    query = SQL(
        """
        MERGE INTO %(table)s t
        USING (VALUES %(values)s) AS s(%(cols)s)
        ON %(on_pred)s
        WHEN MATCHED THEN
            UPDATE SET %(assignments)s
        WHEN NOT MATCHED THEN
            INSERT (%(cols)s) VALUES (%(s_cols)s)
        RETURNING %(returning)s
        """,
        table=SQL.identifier(table),
        values=comma(rows),
        cols=comma(col_ids),
        on_pred=on_pred,
        assignments=assignments,
        s_cols=comma(s_cols),
        returning=SQL(returning),
    )
    cr.execute(query)
    return cr.fetchall()


class TestPipelineModeRoutesFailuresThroughTheSeam(BaseCase):
    def _warm_a_prepared_plan(self, cr, table):
        query = f"SELECT id, a FROM {table} WHERE a = %s"
        for _ in range(3):
            cr.execute(query, (1,))
            cr.fetchall()
        cr.commit()
        return query

    def test_a_stale_cached_plan_is_marked_inside_a_pipeline(self):
        table = "_stale_plan_pipeline"
        with registry().cursor() as writer, registry().cursor() as cr:
            writer.execute(f"DROP TABLE IF EXISTS {table}")
            writer.execute(f"CREATE TABLE {table} (id serial PRIMARY KEY, a int)")
            writer.commit()
            try:
                query = self._warm_a_prepared_plan(cr, table)
                writer.execute(f"ALTER TABLE {table} ALTER COLUMN a TYPE bigint")
                writer.commit()

                with self.assertRaises(psycopg.Error) as caught, cr.pipeline():
                    cr.execute("SELECT 1")
                    cr.execute("SELECT 1")
                    cr.execute(query, (1,), log_exceptions=False)
                cr.rollback()
            finally:
                writer.execute(f"DROP TABLE IF EXISTS {table}")
                writer.commit()

        self.assertTrue(
            is_stale_cached_plan(caught.exception),
            "unmarked, service.transaction.retrying does not replay it: the "
            "same statement outside a pipeline recovers and this one does not",
        )

    def test_retrying_replays_a_pipelined_stale_plan(self):
        table = "_retrying_pipelined_plan"
        with registry().cursor() as writer:
            writer.execute(f"DROP TABLE IF EXISTS {table}")
            writer.execute(f"CREATE TABLE {table} (id serial PRIMARY KEY, a int)")
            writer.execute(f"INSERT INTO {table} (a) VALUES (1)")
            writer.commit()
            try:
                with registry().cursor() as cr:
                    env = api.Environment(cr, ADMIN_USER_ID, {})
                    query = f"SELECT id, a FROM {table} WHERE a = %s"
                    for _ in range(3):
                        cr.execute(query, (1,))
                        cr.fetchall()
                    cr.commit()

                    writer.execute(f"ALTER TABLE {table} ALTER COLUMN a TYPE bigint")
                    writer.commit()

                    attempts = []

                    def request():
                        attempts.append(1)
                        with cr.pipeline():
                            cr.execute("SELECT 1")
                            cr.execute("SELECT 1")
                            cr.execute(query, (1,), log_exceptions=False)
                            return cr.fetchall()

                    rows = retrying(request, env)
                    self.assertEqual(rows, [(1, 1)])
                    self.assertEqual(
                        len(attempts),
                        2,
                        "the first attempt must fail and the second succeed; "
                        "one attempt means the plan never went stale and the "
                        "test proves nothing",
                    )
            finally:
                writer.execute(f"DROP TABLE IF EXISTS {table}")
                writer.commit()

    def test_a_constraint_violation_inside_a_pipeline_is_tiered_and_logged_once(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _pipe_chk (n int CHECK (n < 10))")
            with (
                self.assertLogs("odoo.db.cursor", level="WARNING") as cm,
                self.assertRaises(psycopg.errors.CheckViolation),
                cr.pipeline(),
            ):
                cr.execute("INSERT INTO _pipe_chk VALUES (1)")
                cr.execute("INSERT INTO _pipe_chk VALUES (2)")
                cr.execute("INSERT INTO _pipe_chk VALUES (99)")
            cr.rollback()

        violations = [r for r in cm.records if "constraint violation" in r.getMessage()]
        self.assertEqual(
            len(violations),
            1,
            f"the seam is reached from the entry point and from the pipeline "
            f"sync; exactly one of them may log: {cm.output}",
        )

    def test_a_caller_error_inside_a_pipeline_is_not_reported_as_sql(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError), cr.pipeline():
                cr.execute("SELECT 1")
                cr.execute("SELECT 1")
                raise ValueError("caller bug")
            cr.rollback()


class TestCursorConstructionNeverLeaksAPermit(BaseCase):
    def test_a_baseexception_during_construction_returns_the_connection(self):
        registry_ = registry()
        pool = registry_._replica.primary._Connection__pool
        with registry_.cursor() as probe:
            connection_class = type(probe._cnx)
        before = pool.stats.get_snapshot(budget=pool._budget, checkouts=pool._checkouts)

        real = connection_class.cursor
        seen = []

        def interrupted(conn, *args, **kwargs):
            caller = inspect.currentframe().f_back.f_code
            if not seen and caller is Cursor.__init__.__code__:
                seen.append(True)
                raise KeyboardInterrupt("watchdog")
            return real(conn, *args, **kwargs)

        with patch.object(connection_class, "cursor", interrupted):
            with self.assertRaises(KeyboardInterrupt):
                registry_.cursor()

        after = pool.stats.get_snapshot(budget=pool._budget, checkouts=pool._checkouts)
        self.assertEqual(after["budget_in_use"], before["budget_in_use"])
        self.assertEqual(after["checked_out"], before["checked_out"])

        with registry_.cursor() as cr:
            cr.execute("SELECT 1")
            self.assertEqual(cr.fetchone(), (1,))


class TestASavepointIsNeverOpenedInsideAPipeline(BaseCase):
    def test_it_is_refused_with_a_reason(self):
        with registry().cursor() as cr:
            with cr.pipeline():
                cr.execute("SELECT 1")
                cr.execute("SELECT 1")
                with self.assertRaises(RuntimeError) as caught:
                    cr.savepoint(flush=False)
            self.assertIn("cr.pipeline()", str(caught.exception))
            self.assertIn("ROLLBACK TO SAVEPOINT", str(caught.exception))

    def test_the_transaction_is_still_usable_after_the_refusal(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _pipe_sp (k int UNIQUE)")
            cr.execute("INSERT INTO _pipe_sp VALUES (1)")
            with contextlib.suppress(RuntimeError), cr.pipeline():
                cr.execute("SELECT 1")
                cr.execute("SELECT 1")
                with cr.savepoint(flush=False):
                    cr.execute("INSERT INTO _pipe_sp VALUES (1)")
            cr.execute("SELECT count(*) FROM _pipe_sp")
            self.assertEqual(cr.fetchone(), (1,))
            cr.rollback()

    def test_a_savepoint_around_the_pipeline_still_recovers(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _pipe_sp2 (k int UNIQUE)")
            cr.execute("INSERT INTO _pipe_sp2 VALUES (1)")
            with (
                self.assertRaises(psycopg.errors.UniqueViolation),
                cr.savepoint(flush=False),
                cr.pipeline(),
            ):
                cr.execute("SELECT 1")
                cr.execute("SELECT 1")
                cr.execute("INSERT INTO _pipe_sp2 VALUES (1)")
            cr.execute("SELECT count(*) FROM _pipe_sp2")
            self.assertEqual(
                cr.fetchone(),
                (1,),
                "the supported shape -- savepoint outside, pipeline inside -- "
                "must keep working; the pipeline syncs before the ROLLBACK TO",
            )
            cr.rollback()


class TestCreateInsidePipeline(common.TransactionCase):
    def test_create_above_the_copy_threshold_inside_a_pipeline(self):
        Partner = self.env["res.partner"]
        names = [f"pipe_{i}" for i in range(COPY_THRESHOLD + 5)]
        with self.cr.pipeline():
            self.cr.execute("SELECT 1")
            self.cr.execute("SELECT 2")
            partners = Partner.create([{"name": name} for name in names])
            self.env.flush_all()
        self.assertEqual(len(partners), len(names))
        self.assertEqual(sorted(partners.mapped("name")), sorted(names))


class TestMerge(BaseCase):
    def test_merge_insert(self):
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_ins (id serial PRIMARY KEY, key text UNIQUE, val text)"
            )
            result = _merge(
                cr,
                "_test_mg_ins",
                ["key", "val"],
                [("a", "v1"), ("b", "v2")],
                on_columns=["key"],
            )
            self.assertEqual(len(result), 2)
            cr.execute("SELECT key, val FROM _test_mg_ins ORDER BY key")
            self.assertEqual(cr.fetchall(), [("a", "v1"), ("b", "v2")])

    def test_merge_update(self):
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_upd (id serial PRIMARY KEY, key text UNIQUE, val text)"
            )
            cr.execute("INSERT INTO _test_mg_upd (key, val) VALUES ('a', 'old')")
            _merge(
                cr,
                "_test_mg_upd",
                ["key", "val"],
                [("a", "new")],
                on_columns=["key"],
            )
            cr.execute("SELECT val FROM _test_mg_upd WHERE key = 'a'")
            self.assertEqual(cr.fetchone()[0], "new")

    def test_merge_mixed(self):
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_mix (id serial PRIMARY KEY, key text UNIQUE, val int)"
            )
            cr.execute("INSERT INTO _test_mg_mix (key, val) VALUES ('existing', 10)")
            result = _merge(
                cr,
                "_test_mg_mix",
                ["key", "val"],
                [("existing", 20), ("new_key", 30)],
                on_columns=["key"],
            )
            self.assertEqual(len(result), 2)
            cr.execute("SELECT key, val FROM _test_mg_mix ORDER BY key")
            self.assertEqual(cr.fetchall(), [("existing", 20), ("new_key", 30)])

    def test_merge_returning(self):
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_ret (id serial PRIMARY KEY, key text UNIQUE, val text)"
            )
            cr.execute("INSERT INTO _test_mg_ret (key, val) VALUES ('a', 'old')")
            result = _merge(
                cr,
                "_test_mg_ret",
                ["key", "val"],
                [("a", "new"), ("b", "fresh")],
                on_columns=["key"],
                returning="merge_action(), OLD.val, NEW.val",
            )
            self.assertEqual(result[0][0], "UPDATE")
            self.assertEqual(result[0][1], "old")
            self.assertEqual(result[0][2], "new")
            self.assertEqual(result[1][0], "INSERT")
            self.assertIsNone(result[1][1])
            self.assertEqual(result[1][2], "fresh")

    def test_merge_empty_rows(self):
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_empty (id serial PRIMARY KEY, key text UNIQUE, val text)"
            )
            result = _merge(
                cr, "_test_mg_empty", ["key", "val"], [], on_columns=["key"]
            )
            self.assertEqual(result, [])


class TestCopyFrom(BaseCase):
    def test_copy_from_basic(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cp (a int, b text)")
            result = cr.copy_from("_test_cp", ["a", "b"], [(1, "x"), (2, "y")])
            self.assertIsNone(result)
            cr.execute("SELECT a, b FROM _test_cp ORDER BY a")
            self.assertEqual(cr.fetchall(), [(1, "x"), (2, "y")])

    def test_copy_from_returning_ids(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpid (id serial PRIMARY KEY, val text)")
            ids = cr.copy_from(
                "_test_cpid",
                ["val"],
                [("a",), ("b",), ("c",)],
                returning_ids=True,
            )
            self.assertEqual(len(ids), 3)
            cr.execute("SELECT id, val FROM _test_cpid ORDER BY id")
            rows = cr.fetchall()
            self.assertEqual(len(rows), 3)
            for expected_id, (row_id, _) in zip(ids, rows, strict=False):
                self.assertEqual(expected_id, row_id)

    def test_resolve_id_sequence_shared_fallback_is_schema_aware(self):
        cr = registry().cursor()
        try:
            for s, seq in (("_cpseq_s1", "seq_a"), ("_cpseq_s2", "seq_b")):
                cr.execute(f"CREATE SCHEMA {s}")
                cr.execute(f"CREATE SEQUENCE {s}.{seq}")
                cr.execute(
                    f"CREATE TABLE {s}.foo "
                    f"(id int DEFAULT nextval('{s}.{seq}'), val text)"
                )
            cr.execute("SET LOCAL search_path = _cpseq_s2, public")
            cr.execute("SELECT pg_get_serial_sequence('foo', 'id')")
            self.assertIsNone(cr.fetchone()[0])
            seq_name = cr._get_id_sequence("foo")
            self.assertEqual(seq_name, "seq_b")
        finally:
            cr.rollback()
            cr.close()

    def test_copy_from_empty_returning(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpe (id serial PRIMARY KEY, val text)")
            ids = cr.copy_from("_test_cpe", ["val"], [], returning_ids=True)
            self.assertEqual(ids, [])

    def test_copy_from_returning_ids_generator_input(self):
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_cpgen (id serial PRIMARY KEY, val text)"
            )
            rows = ((f"v{i}",) for i in range(5))
            ids = cr.copy_from("_test_cpgen", ["val"], rows, returning_ids=True)
            self.assertEqual(len(ids), 5)
            cr.execute("SELECT id, val FROM _test_cpgen ORDER BY id")
            inserted = cr.fetchall()
            self.assertEqual([r[0] for r in inserted], ids)
            self.assertEqual([r[1] for r in inserted], [f"v{i}" for i in range(5)])

    def test_copy_from_empty_nonreturning_short_circuits(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpens (a int, b text)")
            before = cr.sql_log_count  # noqa: E8516  asserts the row counter itself
            self.assertIsNone(cr.copy_from("_test_cpens", ["a", "b"], []))
            self.assertEqual(
                cr.sql_log_count,  # noqa: E8516  asserts the row counter itself
                before,
                "empty copy_from must not hit the server",
            )
            self.assertIsNone(cr.copy_from("_test_cpens", ["a", "b"], (x for x in ())))
            with self.assertRaises(ValueError):
                cr.copy_from("_test_cpens", [], [])

    def test_copy_from_empty_columns_raises(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpec (a int)")
            with self.assertRaises(ValueError):
                cr.copy_from("_test_cpec", [], [(1,)])

    def test_copy_from_null_values(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpn (a int, b text)")
            cr.copy_from("_test_cpn", ["a", "b"], [(1, None), (None, "y")])
            cr.execute("SELECT a, b FROM _test_cpn ORDER BY COALESCE(a, 0)")
            rows = cr.fetchall()
            self.assertEqual(rows[0], (None, "y"))
            self.assertEqual(rows[1], (1, None))

    def test_copy_from_large_batch(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cplg (val int)")
            rows = [(i,) for i in range(500)]
            cr.copy_from("_test_cplg", ["val"], rows)
            cr.execute("SELECT count(*) FROM _test_cplg")
            self.assertEqual(cr.fetchone()[0], 500)

    def test_copy_from_json_values(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpj (data jsonb)")
            cr.copy_from(
                "_test_cpj",
                ["data"],
                [(psycopg.types.json.Json({"key": "value"}),)],
            )
            cr.execute("SELECT data->>'key' FROM _test_cpj")
            self.assertEqual(cr.fetchone()[0], "value")


class TestInsertOrExistingUnderARealRace(BaseCase):
    TABLE = "_ioe_race"

    @property
    def threads(self):
        budget = int(tools.config["db_maxconn"] or 8)
        return max(2, min(6, budget - 2))

    def test_one_creator_one_row_and_the_rest_are_retryable(self):
        threads_wanted = self.threads
        db_name = common.get_db_name()
        setup = db_connect(db_name).cursor()
        setup.execute(f"DROP TABLE IF EXISTS {self.TABLE}")
        setup.execute(
            f"CREATE TABLE {self.TABLE} (id serial PRIMARY KEY, k text UNIQUE, v int)"
        )
        setup.commit()
        setup.close()

        barrier = threading.Barrier(threads_wanted)
        outcomes: list = []
        lock = threading.Lock()

        def worker(i):
            cr = db_connect(db_name).cursor()
            try:

                def insert():
                    cr.execute(
                        f"INSERT INTO {self.TABLE} (k, v) VALUES ('same', %s) "
                        f"RETURNING id",
                        (i,),
                    )
                    return cr.fetchone()[0]

                def find():
                    cr.execute(f"SELECT id FROM {self.TABLE} WHERE k = 'same'")
                    row = cr.fetchone()
                    return row[0] if row else None

                barrier.wait(timeout=30)
                _row, created = get_or_create_row(cr, insert, find, conflict="ioe key")
                cr.commit()
                outcome = "created" if created else "found"
            except ConcurrencyError:
                outcome = "concurrency"
            except Exception as exc:
                outcome = f"unexpected:{type(exc).__name__}"
            finally:
                with contextlib.suppress(Exception):
                    cr.close()
            with lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=worker, args=(i,)) for i in range(threads_wanted)
        ]
        try:
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=60)

            check = db_connect(db_name).cursor()
            check.execute(f"SELECT count(*) FROM {self.TABLE}")
            rows = check.fetchone()[0]
            check.close()

            self.assertEqual(rows, 1, "the unique key must admit exactly one row")
            self.assertEqual(
                outcomes.count("created"), 1, f"exactly one creator: {outcomes}"
            )
            self.assertFalse(
                [o for o in outcomes if o.startswith("unexpected")],
                f"every loser must be retryable, not an arbitrary error: {outcomes}",
            )
            self.assertEqual(
                len(outcomes), threads_wanted, f"every thread reported: {outcomes}"
            )
        finally:
            cleanup = db_connect(db_name).cursor()
            cleanup.execute(f"DROP TABLE IF EXISTS {self.TABLE}")
            cleanup.commit()
            cleanup.close()


class TestBinaryCopyIsSafeAgainstColumnsNotValues(BaseCase):
    def test_text_accepts_a_string_where_binary_does_not(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _bin_vs_text (a int)")
            cr.copy_from("_bin_vs_text", ["a"], [("42",)], binary=False)
            cr.execute("SELECT a FROM _bin_vs_text")
            self.assertEqual(cr.fetchall(), [(42,)])

            with self.assertRaises(TypeError):
                cr.copy_from(
                    "_bin_vs_text", ["a"], [("42",)], binary=True, log_exceptions=False
                )
            cr.rollback()

    def test_the_failure_says_which_mode_rejected_it(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _bin_note (a int)")
            with self.assertRaises(TypeError) as caught:
                cr.copy_from(
                    "_bin_note", ["a"], [("42",)], binary=True, log_exceptions=False
                )
            notes = " ".join(getattr(caught.exception, "__notes__", []))
            self.assertIn("binary=True", notes)
            self.assertIn("_bin_note", notes)
            self.assertIn("['a']", notes, "the note must name the columns")
            cr.rollback()

    def test_a_server_side_failure_gets_no_such_note(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _bin_chk (a int CHECK (a < 10))")
            with self.assertRaises(psycopg.errors.CheckViolation) as caught:
                cr.copy_from(
                    "_bin_chk", ["a"], [(99,)], binary=True, log_exceptions=False
                )
            self.assertEqual(
                getattr(caught.exception, "__notes__", []),
                [],
                "has_reached_server is what separates the two; a violation the "
                "server reported is not a value the client could not encode",
            )
            cr.rollback()

    def test_a_typed_value_still_goes_binary(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _bin_ok (a int, b text)")
            cr.copy_from("_bin_ok", ["a", "b"], [(42, "x")], binary=True)
            cr.execute("SELECT a, b FROM _bin_ok")
            self.assertEqual(cr.fetchall(), [(42, "x")])
            cr.rollback()


class TestCopyFromBinaryTypeResolution(BaseCase):
    @contextlib.contextmanager
    def _rolled_back_cursor(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            yield cr
        finally:
            cr.rollback()
            cr.close()

    def test_binary_copy_array_column(self):
        with self._rolled_back_cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_bt_arr (tags int4[])")
            cr.copy_from("_test_bt_arr", ["tags"], [([1, 2, 3],)], binary=True)
            cr.execute("SELECT tags FROM _test_bt_arr")
            self.assertEqual(cr.fetchscalar(), [1, 2, 3])

    def test_binary_copy_enum_column(self):
        with self._rolled_back_cursor() as cr:
            cr.execute("CREATE TYPE _test_bt_mood AS ENUM ('up', 'down')")
            cr.execute("CREATE TEMP TABLE _test_bt_en (m _test_bt_mood)")
            cr.copy_from("_test_bt_en", ["m"], [("up",)], binary=True)
            self.assertEqual(
                cr._schema_cache.get_column_types("_test_bt_en", ["m"]),
                [TEXT_OID],
                "an enum column must resolve to the text OID",
            )
            cr.execute("SELECT m::text FROM _test_bt_en")
            self.assertEqual(cr.fetchscalar(), "up")

    def test_binary_copy_domain_column(self):
        with self._rolled_back_cursor() as cr:
            cr.execute("CREATE DOMAIN _test_bt_pos AS int4 CHECK (VALUE > 0)")
            cr.execute("CREATE DOMAIN _test_bt_pos2 AS _test_bt_pos")
            cr.execute("CREATE TEMP TABLE _test_bt_dom (p _test_bt_pos2)")
            cr.copy_from("_test_bt_dom", ["p"], [(5,)], binary=True)
            self.assertEqual(
                cr._schema_cache.get_column_types("_test_bt_dom", ["p"]),
                [INT4_OID],
                "a domain over a domain must resolve to the ultimate base type",
            )
            cr.execute("SELECT p FROM _test_bt_dom")
            self.assertEqual(cr.fetchscalar(), 5)

    def test_binary_copy_undumpable_type_falls_back_to_text(self):
        with self._rolled_back_cursor() as cr:
            cr.execute("CREATE TYPE _test_bt_pair AS (a int, b int)")
            cr.execute("CREATE TEMP TABLE _test_bt_comp (n int, c _test_bt_pair)")
            oids = cr._get_column_type_oids("_test_bt_comp", ["n", "c"])
            self.assertFalse(
                cr._can_dump_binary(oids),
                "a composite type has no binary dumper",
            )
            cr.copy_from("_test_bt_comp", ["n", "c"], [(1, "(2,3)")], binary=True)
            cr.execute("SELECT n, (c).a, (c).b FROM _test_bt_comp")
            self.assertEqual(cr.fetchall(), [(1, 2, 3)])

    def test_can_dump_binary_accepts_builtin_scalars(self):
        with self._rolled_back_cursor() as cr:
            self.assertTrue(cr._can_dump_binary([INT4_OID, TEXT_OID]))

    def test_can_dump_binary_agrees_with_set_types_on_every_type(self):
        with self._rolled_back_cursor() as cr:
            cr.execute("""
                SELECT t.oid, t.typname
                  FROM pg_type t
                  JOIN pg_namespace n ON n.oid = t.typnamespace
                  JOIN pg_type e ON e.oid = t.typelem
                 WHERE t.typisdefined AND t.typtype = 'b'
                   AND n.nspname = 'pg_catalog'
                   AND t.typelem <> 0     -- arrays: the class that broke
                   -- element must itself be a plain base type: arrays OF the
                   -- catalog composites (``_pg_attribute`` &c) cannot be a
                   -- column at all (they carry pseudo-type members).
                   AND e.typtype = 'b'
                 ORDER BY t.oid
            """)
            array_types = cr.fetchall()
            self.assertGreater(len(array_types), 30, "expected many array types")

            mismatches = []
            for oid, typname in array_types:
                verdict = cr._can_dump_binary([oid])
                with cr.savepoint(flush=False) as sp:
                    cr.execute(
                        f'CREATE TEMP TABLE _test_bt_probe (c "{typname}") '
                        f"ON COMMIT DROP"
                    )
                    try:
                        with cr._obj.copy(
                            "COPY _test_bt_probe (c) FROM STDIN (FORMAT BINARY)"
                        ) as cp:
                            cp.set_types([oid])
                            raise _ProbeAbort
                    except _ProbeAbort:
                        truth = True
                    except Exception:
                        truth = False
                    sp.close(rollback=True)
                if verdict != truth:
                    mismatches.append((typname, oid, verdict, truth))

            self.assertEqual(
                mismatches,
                [],
                "probe disagrees with set_types() for: "
                + ", ".join(f"{n} (probe={v}, real={t})" for n, _, v, t in mismatches),
            )


class TestDDLFormatting(BaseCase):
    def test_ddl_client_side_formatting(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_ddl (val int DEFAULT %s)", (0,))
            cr.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = '_test_ddl' AND column_name = 'val'"
            )
            default = cr.fetchone()[0]
            self.assertEqual(default, "0")

    def test_ddl_comment(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_ddl2 (val int)")
            cr.execute("COMMENT ON TABLE _test_ddl2 IS %s", ("test comment",))
            cr.execute(
                "SELECT obj_description(c.oid) FROM pg_class c WHERE c.relname = '_test_ddl2'"
            )
            self.assertEqual(cr.fetchone()[0], "test comment")


class TestBytesQuery(BaseCase):
    def test_bytes_ddl_executes(self):
        with registry().cursor() as cr:
            cr.execute(b"CREATE TEMP TABLE _test_bytes_ddl (val int)")
            cr.execute(b"INSERT INTO _test_bytes_ddl VALUES (42)")
            cr.execute(b"SELECT val FROM _test_bytes_ddl")
            self.assertEqual(cr.fetchone()[0], 42)

    def test_bytes_ddl_invalidates_the_caches(self):
        with registry().cursor() as cr:
            with patch.object(type(cr), "_invalidate_caches_after_ddl") as invalidate:
                cr.execute(b"CREATE TEMP TABLE _test_bytes_ddl2 (val int)")
            self.assertTrue(
                invalidate.called,
                "a bytes CREATE was not recognised as schema-changing DDL",
            )

    def test_bytes_multi_statement_ddl_invalidates_the_caches(self):
        with registry().cursor() as cr:
            cr.execute(b"CREATE TEMP TABLE _test_bytes_ddl3 (val int)")
            with patch.object(type(cr), "_invalidate_caches_after_ddl") as invalidate:
                cr.execute(
                    b"SET LOCAL statement_timeout = 0;"
                    b" ALTER TABLE _test_bytes_ddl3 ADD COLUMN extra int"
                )
            self.assertTrue(
                invalidate.called,
                "DDL hidden behind a leading SET was missed for a bytes query",
            )

    def test_bytes_non_ddl_does_not_invalidate(self):
        with registry().cursor() as cr:
            with patch.object(type(cr), "_invalidate_caches_after_ddl") as invalidate:
                cr.execute(b"SELECT 1")
            self.assertFalse(invalidate.called)

    def test_undecodable_bytes_do_not_crash_the_analysis(self):
        with registry().cursor() as cr, self.assertRaises(psycopg.Error):
            with contextlib.suppress(UnicodeDecodeError):
                cr.execute(b"SELECT '\xff\xfe'::int", log_exceptions=False)
                raise psycopg.ProgrammingError("expected the server to reject it")


class TestComposableQueries(BaseCase):
    def test_composed_ddl_create_view(self):
        with registry().cursor() as cr:
            cr.execute(
                psycopg.sql.SQL("CREATE TEMP VIEW {} as ({})").format(
                    psycopg.sql.Identifier("_test_composed_view"),
                    psycopg.sql.SQL("SELECT 42 AS answer"),
                )
            )
            cr.execute("SELECT answer FROM _test_composed_view")
            self.assertEqual(cr.fetchone()[0], 42)
            cr.execute(
                psycopg.sql.SQL("DROP VIEW {}").format(
                    psycopg.sql.Identifier("_test_composed_view")
                )
            )

    def test_composed_ddl_with_params(self):
        with registry().cursor() as cr:
            cr.execute(
                psycopg.sql.SQL("CREATE TEMP TABLE {} (val int DEFAULT %s)").format(
                    psycopg.sql.Identifier("_test_composed_ddl")
                ),
                (7,),
            )
            cr.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = '_test_composed_ddl' AND column_name = 'val'"
            )
            self.assertEqual(cr.fetchone()[0], "7")

    def test_composed_non_ddl(self):
        with registry().cursor() as cr:
            cr.execute(
                psycopg.sql.SQL("SELECT {} FROM res_users WHERE id = %s").format(
                    psycopg.sql.Identifier("login")
                ),
                (1,),
            )
            self.assertTrue(cr.fetchone())

    def test_composed_executemany(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_composed_many (val int)")
            cr.executemany(
                psycopg.sql.SQL("INSERT INTO {} (val) VALUES (%s)").format(
                    psycopg.sql.Identifier("_test_composed_many")
                ),
                [(1,), (2,), (3,)],
            )
            cr.execute("SELECT sum(val) FROM _test_composed_many")
            self.assertEqual(cr.fetchone()[0], 6)


class TestConnectionInfoFor(BaseCase):
    def test_postgresql_uri(self):
        db, info = get_connection_info_for_database(
            "postgresql://user:pass@localhost:5432/mydb"
        )
        self.assertEqual(db, "mydb")
        self.assertIn("dsn", info)
        self.assertEqual(info["dsn"], "postgresql://user:pass@localhost:5432/mydb")
        self.assertIn("connect_timeout", info)
        self.assertIn("keepalives", info)

    def test_postgres_uri_scheme(self):
        db, info = get_connection_info_for_database("postgres://localhost/testdb")
        self.assertEqual(db, "testdb")
        self.assertIn("dsn", info)

    def test_uri_no_path_uses_username(self):
        db, _ = get_connection_info_for_database("postgresql://admin@localhost/")
        self.assertEqual(db, "admin")

    def test_uri_no_path_no_user_uses_hostname(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            db, _ = get_connection_info_for_database("postgresql://localhost/")
        self.assertEqual(db, "localhost")

    def test_plain_dbname(self):
        db, info = get_connection_info_for_database("mydb")
        self.assertEqual(db, "mydb")
        self.assertEqual(info["dbname"], "mydb")
        self.assertNotIn("dsn", info)
        self.assertIn("connect_timeout", info)

    def test_application_name_included(self):
        _, info = get_connection_info_for_database("mydb")
        self.assertIn("application_name", info)


class TestConnectionDsnRedaction(BaseCase):
    CANARY = "s3cr3tPW"

    def _dsn_for(self, target):
        pool = ConnectionPool(maxconn=1)
        dbname, info = get_connection_info_for_database(target)
        return Connection(pool, dbname, info).dsn

    def test_uri_password_not_leaked(self):
        dsn = self._dsn_for(f"postgresql://u:{self.CANARY}@dbhost:5432/mydb")
        self.assertNotIn(self.CANARY, repr(dsn))
        self.assertNotIn("dsn", dsn)
        self.assertEqual(dsn.get("host"), "dbhost")
        self.assertEqual(dsn.get("user"), "u")
        self.assertEqual(dsn.get("dbname"), "mydb")

    def test_keyword_password_not_leaked(self):
        pool = ConnectionPool(maxconn=1)
        _, info = get_connection_info_for_database("mydb")
        info["password"] = self.CANARY
        dsn = Connection(pool, "mydb", info).dsn
        self.assertNotIn(self.CANARY, repr(dsn))
        self.assertEqual(dsn.get("dbname"), "mydb")

    def test_uri_without_password_does_not_crash(self):
        dsn = self._dsn_for("postgresql://u@dbhost/mydb")
        self.assertNotIn("dsn", dsn)
        self.assertEqual(dsn.get("host"), "dbhost")


class TestPoolBasics(BaseCase):
    def test_readwrite_pool_repr(self):
        pool = ConnectionPool(maxconn=4)
        r = repr(pool)
        self.assertIn("read/write", r)
        self.assertIn("limit=4", r)
        pool.close_all()

    def test_readonly_pool_repr(self):
        pool = ConnectionPool(maxconn=4, readonly=True)
        self.assertIn("read-only", repr(pool))
        self.assertTrue(pool.readonly)
        pool.close_all()

    def test_pool_stats_empty(self):
        pool = ConnectionPool(maxconn=4)
        stats = pool.get_stats()
        self.assertEqual(stats, {})
        pool.close_all()

    def test_tuning_params_stored_and_derived(self):
        pool = ConnectionPool(
            maxconn=4,
            borrow_timeout=12.5,
            max_lifetime=1234,
            max_idle=77,
            reap_idle_ttl=88.0,
        )
        self.assertEqual(pool._borrow_timeout, 12.5)
        self.assertEqual(pool._max_lifetime, 1234)
        self.assertEqual(pool._max_idle, 77)
        self.assertEqual(pool._reaper.ttl, 88.0)
        self.assertEqual(pool._reaper.check_interval, 22.0)
        pool.close_all()

    def test_tuning_defaults_come_from_the_settings_snapshot(self):
        settings = pool_settings.current()
        pool = ConnectionPool(maxconn=1)
        self.assertEqual(pool._borrow_timeout, settings.borrow_timeout)
        self.assertEqual(pool._max_lifetime, settings.conn_max_lifetime)
        self.assertEqual(pool._max_idle, settings.conn_max_idle)
        self.assertEqual(pool._reaper.ttl, settings.pool_reap_idle)
        self.assertEqual(pool._pool_workers, settings.pool_workers)
        pool.close_all()
        with pool_settings.override(borrow_timeout=12.5, pool_reap_idle=88.0):
            pool = ConnectionPool(maxconn=1)
        self.assertEqual(pool._borrow_timeout, 12.5)
        self.assertEqual(pool._reaper.ttl, 88.0)
        pool.close_all()

    def test_reap_check_interval_disabled_when_ttl_zero(self):
        pool = ConnectionPool(maxconn=1, reap_idle_ttl=0.0)
        self.assertEqual(pool._reaper.check_interval, 0.0)
        pool.close_all()

    def test_checked_out_formula(self):

        class _StubPool:
            def __init__(self, stats):
                self._stats = stats

            def get_stats(self):
                return self._stats

        self.assertEqual(
            reaper_checked_out(_StubPool({"pool_size": 5, "pool_available": 2})),
            3,
        )
        self.assertEqual(
            reaper_checked_out(_StubPool({"pool_size": 4, "pool_available": 4})),
            0,
        )
        self.assertEqual(reaper_checked_out(_StubPool({})), 0)

    def test_repr_does_not_deadlock_under_lock(self):
        pool = ConnectionPool(maxconn=2)
        out = []
        with pool._lock:
            t = threading.Thread(target=lambda: out.append(repr(pool)))
            t.start()
            t.join(timeout=5)
            alive = t.is_alive()
        self.assertFalse(alive, "repr(pool) deadlocked while _lock was held")
        self.assertTrue(out and out[0].startswith("ConnectionPool("))
        pool.close_all()

    def test_repr_survives_concurrent_pool_churn(self):

        class _FakePool:
            closed = False

            def get_stats(self):
                return {"pool_size": 1, "pool_available": 1}

            def close(self):
                pass

        pool = ConnectionPool(maxconn=4)
        stop = threading.Event()
        errors = []

        def churn():
            i = 0
            while not stop.is_set():
                pool._pools[frozenset([("dbname", f"d{i & 7}"), ("n", str(i))])] = (
                    _FakePool()
                )
                keys = list(pool._pools)
                if len(keys) > 6:
                    pool._pools.pop(keys[0], None)
                i += 1

        def render():
            while not stop.is_set():
                try:
                    repr(pool)
                except RuntimeError as e:
                    errors.append(str(e))
                    return

        ts = [threading.Thread(target=churn), threading.Thread(target=render)]
        for t in ts:
            t.start()
        time.sleep(1.0)
        stop.set()
        for t in ts:
            t.join()
        pool._pools.clear()
        pool.close_all()
        self.assertEqual(errors, [], "repr(pool) raced with pool churn")

    def test_pool_maxconn_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            ConnectionPool(maxconn=0)
        with self.assertRaises(ValueError):
            ConnectionPool(maxconn=-1)


class TestSuppressKnownPoolWarnings(BaseCase):
    def test_suppresses_discard_message(self):
        f = _SuppressKnownPoolWarnings()
        record = logging.LogRecord(
            "test",
            logging.WARNING,
            "",
            0,
            "discarding closed connection in pool",
            (),
            None,
        )
        self.assertFalse(f.filter(record))

    def test_suppresses_database_does_not_exist(self):
        f = _SuppressKnownPoolWarnings()
        record = logging.LogRecord(
            "test",
            logging.WARNING,
            "",
            0,
            'error connecting: FATAL: database "test" does not exist',
            (),
            None,
        )
        self.assertFalse(f.filter(record))

    def test_passes_other_messages(self):
        f = _SuppressKnownPoolWarnings()
        record = logging.LogRecord(
            "test",
            logging.WARNING,
            "",
            0,
            "connection timeout error",
            (),
            None,
        )
        self.assertTrue(f.filter(record))


class TestPoolSemaphoreAccounting(BaseCase):
    def _info(self):
        return get_connection_info_for_database(common.get_db_name())[1]

    def test_borrow_tags_and_give_back_releases(self):
        pool = ConnectionPool(maxconn=2)
        self.addCleanup(pool.close_all)
        conn = pool.borrow(self._info())
        self.assertEqual(pool._budget.available, 1)
        self.assertIsNotNone(getattr(conn, "_odoo_pool", None))
        self.assertIn(conn._odoo_pool, pool._pools.values())
        pool.give_back(conn)
        self.assertEqual(pool._budget.available, 2)
        self.assertNotIn("_odoo_pool", conn.__dict__)

    def test_double_give_back_does_not_over_release(self):
        pool = ConnectionPool(maxconn=2)
        self.addCleanup(pool.close_all)
        conn = pool.borrow(self._info())
        pool.give_back(conn)
        pool.give_back(conn)
        self.assertEqual(pool._budget.available, 2)

    def test_non_borrowed_connection_does_not_release(self):
        pool = ConnectionPool(maxconn=2)
        self.addCleanup(pool.close_all)
        before = pool._budget.available
        raw = psycopg.connect(**{k: v for k, v in self._info().items() if k != "dsn"})
        try:
            pool.give_back(raw)
            self.assertEqual(pool._budget.available, before)
            self.assertTrue(raw.closed)
        finally:
            if not raw.closed:
                raw.close()

    def test_dead_connection_still_releases_slot(self):
        pool = ConnectionPool(maxconn=2)
        self.addCleanup(pool.close_all)
        conn = pool.borrow(self._info())
        conn.close()
        self.assertIsNotNone(getattr(conn, "_odoo_pool", None))
        pool.give_back(conn)
        self.assertEqual(pool._budget.available, 2)


class TestConnectionStateReset(BaseCase):
    def _raw_conn(self):
        info = get_connection_info_for_database(common.get_db_name())[1]
        conn = psycopg.connect(
            **{k: v for k, v in info.items() if k != "dsn"}, autocommit=True
        )
        self.addCleanup(conn.close)
        return conn

    @staticmethod
    def _dirty(conn):
        conn.execute("DROP SEQUENCE IF EXISTS _leak_seq")
        conn.execute("CREATE SEQUENCE _leak_seq")
        conn.execute("SELECT nextval('_leak_seq')")
        was_autocommit = conn.autocommit
        conn.autocommit = False
        conn.execute("DECLARE _leak_cursor CURSOR WITH HOLD FOR SELECT 1")
        conn.commit()
        conn.autocommit = was_autocommit

        conn.execute("SET application_name = 'tenant_leak_probe'")
        conn.execute("SET search_path = 'leak_schema, public'")
        conn.execute("CREATE TEMP TABLE _leak_probe (x int)")
        conn.execute("LISTEN leak_channel")
        conn.execute("SELECT pg_advisory_lock(987654321)")

    def _assert_clean(self, conn):
        def get(q):
            return conn.execute(q).fetchone()[0]

        self.assertNotEqual(get("SHOW application_name"), "tenant_leak_probe")
        self.assertNotIn("leak_schema", get("SHOW search_path"))
        self.assertFalse(get("SELECT to_regclass('pg_temp._leak_probe') IS NOT NULL"))
        self.assertEqual(get("SELECT count(*) FROM pg_listening_channels()"), 0)
        self.assertEqual(
            get(
                "SELECT count(*) FROM pg_locks "
                "WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
            ),
            0,
        )
        self.assertEqual(
            get("SELECT count(*) FROM pg_cursors WHERE name = '_leak_cursor'"),
            0,
            "CLOSE ALL did not close the held cursor",
        )
        with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
            conn.execute("SELECT currval('_leak_seq')")
        conn.execute("DROP SEQUENCE IF EXISTS public._leak_seq")

    def test_reset_sql_resets_role(self):
        self.assertIn("RESET SESSION AUTHORIZATION", _RESET_SESSION_STATE_SQL)

    @staticmethod
    def _override_discard(value):
        from odoo.tools import config

        return patch.object(
            config, "options", config.options.new_child({"db_discard_on_return": value})
        )

    def test_default_mode_closes_leaks(self):
        conn = self._raw_conn()
        self._dirty(conn)
        with self._override_discard(False):
            _reset_connection(conn)
        conn.autocommit = True
        self._assert_clean(conn)

    def test_discard_mode_closes_leaks(self):
        conn = self._raw_conn()
        self._dirty(conn)
        with self._override_discard(True):
            _reset_connection(conn)
        conn.autocommit = True
        self._assert_clean(conn)

    def test_no_prepared_statement_crash_across_returns(self):
        for discard in (False, True):
            conn = self._raw_conn()
            conn.prepare_threshold = 2
            with self._override_discard(discard):
                for _ in range(6):
                    conn.execute("SELECT 1 WHERE %s::int = 1", (1,))
                    self._dirty(conn)
                    _reset_connection(conn)
                    conn.autocommit = True
            self._assert_clean(conn)


class TestIdlePoolReaper(BaseCase):
    def _info(self, app):
        return {
            **get_connection_info_for_database(common.get_db_name())[1],
            "application_name": app,
        }

    @staticmethod
    def _dbset(pool):
        return {dict(k).get("application_name") for k in pool._pools}

    def _force_idle(self, pool, app):
        for k, psy in pool._pools.items():
            if dict(k).get("application_name") != app:
                psy._odoo_last_borrow = 0.0

    def test_idle_pool_reaped_on_new_pool_creation(self):
        pool = ConnectionPool(maxconn=4, reap_idle_ttl=300.0)
        self.addCleanup(pool.close_all)
        for app in ("reap_a", "reap_b", "reap_c"):
            pool.give_back(pool.borrow(self._info(app)))
        self.assertEqual(len(pool._pools), 3)
        self._force_idle(pool, app="none")
        pool.give_back(pool.borrow(self._info("reap_d")))
        self.assertEqual(
            self._dbset(pool),
            {"reap_d"},
            "only the freshly created pool should survive",
        )

    def test_checked_out_connection_is_not_reaped(self):
        pool = ConnectionPool(maxconn=4, reap_idle_ttl=300.0)
        self.addCleanup(pool.close_all)
        held = pool.borrow(self._info("held"))
        self.addCleanup(lambda: pool.give_back(held))
        pool.give_back(pool.borrow(self._info("idle")))
        self._force_idle(pool, app="none")
        pool.give_back(pool.borrow(self._info("trigger")))
        survivors = self._dbset(pool)
        self.assertIn("held", survivors, "pool with a held connection must stay")
        self.assertNotIn("idle", survivors, "idle pool with nothing held is reaped")

    def test_give_back_refreshes_activity_stamp(self):
        pool = ConnectionPool(maxconn=4, reap_idle_ttl=300.0)
        self.addCleanup(pool.close_all)
        conn = pool.borrow(self._info("returned"))
        (key,) = list(pool._pools)
        pool._pools[key]._odoo_last_borrow = 0.0
        pool.give_back(conn)
        self.assertGreater(
            pool._pools[key]._odoo_last_borrow,
            0.0,
            "give_back must refresh the pool's activity stamp",
        )

    def test_long_held_then_returned_pool_survives_sweep(self):
        pool = ConnectionPool(maxconn=4, reap_idle_ttl=300.0)
        self.addCleanup(pool.close_all)
        conn = pool.borrow(self._info("returned"))
        (key,) = list(pool._pools)
        pool._pools[key]._odoo_last_borrow = 0.0
        pool.give_back(conn)
        pool.give_back(pool.borrow(self._info("trigger")))
        self.assertIn(
            "returned",
            self._dbset(pool),
            "a pool that just returned a connection is active, not idle",
        )

    def test_reaper_disabled_keeps_all_pools(self):
        pool = ConnectionPool(maxconn=4, reap_idle_ttl=0.0)
        self.addCleanup(pool.close_all)
        for app in ("a", "b", "c"):
            pool.give_back(pool.borrow(self._info(app)))
        self._force_idle(pool, app="none")
        pool.give_back(pool.borrow(self._info("d")))
        self.assertEqual(len(pool._pools), 4, "reaper disabled -> nothing reaped")

    def test_borrow_rebuilds_when_pool_closed_underneath_it(self):
        pool = ConnectionPool(maxconn=4, reap_idle_ttl=0.0)
        self.addCleanup(pool.close_all)
        pool.give_back(pool.borrow(self._info("rebuild")))
        (key,) = list(pool._pools)
        victim = pool._pools[key]
        victim.close()
        conn = pool.borrow(self._info("rebuild"))
        try:
            self.assertFalse(conn.closed)
            self.assertIsNot(
                pool._pools[key], victim, "a fresh pool replaced the closed one"
            )
            self.assertEqual(pool._budget.available, 3, "exactly one permit held")
        finally:
            pool.give_back(conn)
        self.assertEqual(pool._budget.available, 4, "permit released, no leak")


class TestCursorDelReclaimsConnection(BaseCase):
    def _info(self):
        return get_connection_info_for_database(common.get_db_name())[1]

    def test_del_warns_and_reclaims_permit(self):
        import gc

        pool = ConnectionPool(maxconn=2)
        self.addCleanup(pool.close_all)
        dbname = common.get_db_name()
        info = self._info()

        def leak():
            cr = Cursor(pool, dbname, info)
            cr.execute("SELECT 1")
            self.assertEqual(cr.fetchscalar(), 1)
            self.assertEqual(pool._budget.available, 1, "permit not consumed on open")

        with self.assertLogs("odoo.db.cursor", level="WARNING") as cm:
            leak()
            gc.collect()

        self.assertTrue(
            any("not closed explicitly" in m for m in cm.output),
            "Cursor.__del__ did not warn about the unclosed cursor",
        )
        self.assertEqual(
            pool._budget.available,
            2,
            "Cursor.__del__ leaked the pool semaphore permit",
        )

    def test_del_reclaims_the_permit_of_a_dead_connection_too(self):
        import gc

        pool = ConnectionPool(maxconn=2)
        self.addCleanup(pool.close_all)
        dbname = common.get_db_name()
        info = self._info()

        def leak():
            cr = Cursor(pool, dbname, info)
            cr.execute("SELECT pg_backend_pid()")
            pid = cr.fetchscalar()
            with contextlib.closing(db_connect(dbname).cursor()) as admin:
                admin.execute("SELECT pg_terminate_backend(%s)", (pid,))
                admin.commit()
            with self.assertRaises(psycopg.OperationalError):
                cr.execute("SELECT 1")
            self.assertTrue(cr._cnx.closed, "psycopg marks a killed backend closed")
            self.assertEqual(pool._budget.available, 1)
            self.assertEqual(len(pool._checkouts), 1)

        with self.assertLogs("odoo.db.cursor", level="WARNING") as cm:
            leak()
            gc.collect()

        self.assertTrue(any("not closed explicitly" in m for m in cm.output))
        self.assertEqual(
            pool._budget.available,
            2,
            "__del__ used to skip _close() on a dead connection, and _close() "
            "is the only path that gives the permit back: a request whose "
            "backend died and whose cursor was never closed lost one permit "
            "for the life of the process",
        )
        self.assertEqual(len(pool._checkouts), 0)


class TestPoolTimeoutCleanup(BaseCase):
    def test_pool_removed_on_timeout(self):
        pool = ConnectionPool(maxconn=4)
        info = get_connection_info_for_database("nonexistent_db_test")[1]
        key = _get_dsn_key(info)

        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.getconn.side_effect = PoolTimeout("connection timeout")
        mock_pool.get_stats.return_value = {"pool_size": 0}
        pool._pools[key] = mock_pool

        with self.assertRaises(PoolError):
            pool.borrow(info)

        self.assertNotIn(key, pool._pools)
        mock_pool.close.assert_called_once()

    def test_pool_kept_on_timeout_with_live_connections(self):
        pool = ConnectionPool(maxconn=4)
        info = get_connection_info_for_database("nonexistent_db_test")[1]
        key = _get_dsn_key(info)

        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.getconn.side_effect = PoolTimeout("connection timeout")
        mock_pool.get_stats.return_value = {"pool_size": 3}
        pool._pools[key] = mock_pool

        with self.assertRaises(PoolError):
            pool.borrow(info)

        self.assertIn(key, pool._pools)
        mock_pool.close.assert_not_called()

    def test_pool_not_removed_on_other_errors(self):
        pool = ConnectionPool(maxconn=4)
        info = get_connection_info_for_database("nonexistent_db_test")[1]
        key = _get_dsn_key(info)

        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.getconn.side_effect = psycopg.OperationalError("connection refused")
        pool._pools[key] = mock_pool

        with self.assertRaises(psycopg.OperationalError):
            pool.borrow(info)

        self.assertIn(key, pool._pools)
        mock_pool.close.assert_not_called()


class TestDroppedDBRecovery(BaseCase):
    DB_NAME = "odoo_test_pool_recovery"

    def test_check_signaling_cleans_up_after_db_drop(self):
        reg = object.__new__(Registry)
        reg.db_name = self.DB_NAME
        Registry.registries[self.DB_NAME] = reg
        self.addCleanup(Registry.remove, self.DB_NAME)

        with patch.object(
            type(reg),
            "cursor",
            side_effect=psycopg.OperationalError(
                f'database "{self.DB_NAME}" does not exist'
            ),
        ):
            with self.assertRaises(psycopg.OperationalError):
                reg.check_signaling()

        self.assertNotIn(self.DB_NAME, Registry.registries)

    def test_check_signaling_keeps_registry_on_pool_error(self):
        reg = object.__new__(Registry)
        reg.db_name = self.DB_NAME
        Registry.registries[self.DB_NAME] = reg
        self.addCleanup(Registry.remove, self.DB_NAME)

        with patch.object(
            type(reg),
            "cursor",
            side_effect=PoolError("couldn't get a connection after 30.00 sec"),
        ):
            with self.assertRaises(PoolError):
                reg.check_signaling()

        self.assertIn(self.DB_NAME, Registry.registries)

    def test_check_signaling_keeps_registry_when_caller_provides_cursor(self):
        reg = object.__new__(Registry)
        reg.db_name = self.DB_NAME
        reg.registry_sequence = -1
        Registry.registries[self.DB_NAME] = reg
        self.addCleanup(Registry.remove, self.DB_NAME)

        mock_cr = MagicMock()
        mock_cr.__enter__ = MagicMock(return_value=mock_cr)
        mock_cr.__exit__ = MagicMock(return_value=False)
        mock_cr.execute.side_effect = psycopg.OperationalError("connection closed")

        with self.assertRaises(psycopg.OperationalError):
            reg.check_signaling(cr=mock_cr)

        self.assertIn(self.DB_NAME, Registry.registries)


class TestPoolDrainConcurrency(BaseCase):
    def test_drain_does_not_race_churn(self):
        pool = ConnectionPool(maxconn=4)
        for i in range(500):
            pool._pools[f"fake-{i}"] = MagicMock(closed=False)

        errors = []
        stop = threading.Event()

        def drain_loop():
            while not stop.is_set():
                try:
                    pool.drain_all()
                except RuntimeError as e:
                    errors.append(str(e))
                    return

        def churn_loop():
            while not stop.is_set():
                with pool._lock:
                    snapshot = list(pool._pools.values())
                    pool._pools.clear()
                    for i, v in enumerate(snapshot):
                        pool._pools[f"fake-{i}"] = v

        threads = [
            threading.Thread(target=drain_loop),
            threading.Thread(target=churn_loop),
        ]
        for t in threads:
            t.start()
        time.sleep(1.0)
        stop.set()
        for t in threads:
            t.join()

        pool.close_all()
        self.assertEqual(
            errors, [], "drain() raced the pools dict — fix in pool.py regressed"
        )


class TestExecuteValuesTripwire(BaseCase):
    def test_rejects_zero_markers(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute_values("INSERT INTO t DEFAULT VALUES", [(1,)])

    def test_rejects_multiple_markers(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute_values(
                    "UPDATE t SET col=%s FROM (VALUES %s) s WHERE id=s.x",
                    [(1, 2), (3, 4)],
                )

    def test_accepts_single_marker(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_evt_tw (v int)")
            cr.execute_values(
                "INSERT INTO _test_evt_tw (v) VALUES %s",
                [(1,), (2,)],
            )
            cr.execute("SELECT count(*) FROM _test_evt_tw")
            self.assertEqual(cr.fetchone()[0], 2)


class TestExecutemanyTripwire(BaseCase):
    def test_rejects_sql_with_embedded_params(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.executemany(
                    SQL("INSERT INTO t(a,b) VALUES (%s, %s)", 1, 2),
                    [(3, 4)],
                )

    def test_plain_str_query_still_works(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_em_tw (a int, b int)")
            cr.executemany(
                "INSERT INTO _test_em_tw(a, b) VALUES (%s, %s)",
                [(1, 2), (3, 4)],
            )
            cr.execute("SELECT count(*) FROM _test_em_tw")
            self.assertEqual(cr.fetchone()[0], 2)


class TestFlushingSavepointDepthOnFailure(BaseCase):
    def test_savepoint_depth_unchanged_on_sql_failure(self):
        cr = MagicMock()
        cr._savepoint_depth = 0
        cr.transaction = None
        cr.flush = MagicMock()
        cr.execute = MagicMock(
            side_effect=psycopg.OperationalError("simulated broken connection")
        )

        with self.assertRaises(psycopg.OperationalError):
            _FlushingSavepoint(cr)

        self.assertEqual(
            cr._savepoint_depth, 0, "savepoint_depth leaked after SAVEPOINT SQL failure"
        )

    def test_savepoint_depth_balanced_when_release_fails(self):

        def execute(sql, *args, **kwargs):
            if "RELEASE" in str(sql):
                raise psycopg.OperationalError("simulated RELEASE failure")

        cr = MagicMock()
        cr._savepoint_depth = 0
        cr.transaction = None
        cr.flush = MagicMock()
        cr.execute = MagicMock(side_effect=execute)

        sp = _FlushingSavepoint(cr)
        self.assertEqual(cr._savepoint_depth, 1)
        with self.assertRaises(psycopg.OperationalError):
            sp.close(rollback=False)
        self.assertEqual(
            cr._savepoint_depth, 0, "savepoint_depth leaked after RELEASE failure"
        )


class TestURIMalformedWarning(BaseCase):
    def test_hostname_fallback_emits_warning(self):
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            db, _info = get_connection_info_for_database("postgresql://localhost/")
        self.assertEqual(db, "localhost")
        matched = [w for w in captured if issubclass(w.category, RuntimeWarning)]
        self.assertTrue(
            matched, "Expected a RuntimeWarning for URI without path/username"
        )

    def test_well_formed_uri_no_warning(self):
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            db, _info = get_connection_info_for_database("postgresql://localhost/mydb")
        self.assertEqual(db, "mydb")
        matched = [w for w in captured if issubclass(w.category, RuntimeWarning)]
        self.assertFalse(
            matched, "Well-formed URI should not trigger the hostname-fallback warning"
        )


class TestClosedCursorAttributeAccess(BaseCase):
    def test_unknown_attr_on_closed_cursor_raises_cleanly(self):
        cr = registry().cursor()
        cr.close()
        with self.assertRaises(psycopg.InterfaceError):
            cr.some_nonexistent_attr

    def test_closure_is_reported_before_the_unknown_name(self):
        cr = registry().cursor()
        cr.close()
        with self.assertRaises(psycopg.InterfaceError) as ctx:
            _ = cr.row_factory
        self.assertIn("closed", str(ctx.exception).lower())


class TestCloseKeepsHealthyConnections(BaseCase):
    def _closed_after_hook(self, hook_name):
        cr = db_connect(common.get_db_name()).cursor()
        cr.execute("SELECT 1")
        cnx = cr._cnx
        getattr(cr, hook_name).add(_boom)
        cr.close()
        return bool(cnx.closed)

    def test_control_a_clean_close_keeps_the_connection(self):
        cr = db_connect(common.get_db_name()).cursor()
        cr.execute("SELECT 1")
        cnx = cr._cnx
        cr.close()
        self.assertFalse(cnx.closed, "premise: a clean close pools the connection")

    def test_raising_postrollback_hook_keeps_the_connection(self):
        self.assertFalse(
            self._closed_after_hook("postrollback"),
            "a hook bug must not also cost a warm pooled connection",
        )

    def test_raising_prerollback_hook_keeps_the_connection(self):
        self.assertFalse(self._closed_after_hook("prerollback"))

    def test_a_connection_left_in_a_transaction_is_still_discarded(self):
        cr = db_connect(common.get_db_name()).cursor()
        cr.execute("SELECT 1")
        cnx = cr._cnx
        with patch.object(type(cnx), "rollback", _boom):
            cr.close()
        self.assertTrue(cnx.closed, "an un-rolled-back connection must be discarded")

    def test_connection_is_clean_reports_false_on_a_dead_connection(self):
        cr = db_connect(common.get_db_name()).cursor()
        cr.execute("SELECT 1")
        cr._cnx.close()
        self.assertFalse(cr._is_connection_clean())
        cr.close()


class TestCursorCloseWithDeadConnection(BaseCase):
    def test_close_releases_slot_when_cnx_dies_externally(self):
        cr = registry().cursor()
        pool = cr._Cursor__pool
        sem_before = pool._budget.available
        cr.connection.close()
        self.assertTrue(cr.closed, "closed property should reflect dead _cnx")
        self.assertFalse(cr._closed, "internal _closed flag must not be set yet")
        cr.close()
        self.assertGreater(
            pool._budget.available,
            sem_before,
            "close() must release the semaphore slot even when _cnx is dead",
        )
        self.assertNotIn(
            "_obj",
            cr.__dict__,
            "close() must delete _obj even when _cnx is dead",
        )


class TestCopyFromIncompatibleOptions(BaseCase):
    def test_binary_with_on_error_raises(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.copy_from("t", ["c"], [(1,)], binary=True, on_error="ignore")

    def test_returning_ids_with_ignore_raises(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.copy_from("t", ["c"], [(1,)], returning_ids=True, on_error="ignore")


class TestDictFetchoneNoAssert(BaseCase):
    def test_uses_explicit_raise_not_assert(self):
        src = inspect.getsource(Cursor.dictfetchone)
        self.assertNotIn(
            "assert desc",
            src,
            "dictfetchone must not use `assert` (stripped by python -O)",
        )


class TestReadonlyPropertyCached(BaseCase):
    def test_readonly_stable_across_close(self):
        for ro in (False, True):
            with self.subTest(readonly=ro):
                cr = registry().cursor(readonly=ro)
                before = cr.readonly
                cr.close()
                after = cr.readonly
                self.assertEqual(
                    before, after, "readonly must not change after close()"
                )
                self.assertEqual(bool(ro), before)


class TestGetStatsLocked(BaseCase):
    def test_get_stats_safe_under_churn(self):
        src = inspect.getsource(ConnectionPool.get_stats)
        self.assertIn(
            "with self._lock",
            src,
            "get_stats must snapshot _pools under the lock",
        )


class TestSuppressKnownPoolWarningsNarrow(BaseCase):
    def test_does_not_swallow_role_does_not_exist(self):
        f = _SuppressKnownPoolWarnings()
        rec = logging.LogRecord(
            "test",
            logging.WARNING,
            "",
            0,
            'FATAL: role "nobody" does not exist',
            (),
            None,
        )
        self.assertTrue(
            f.filter(rec),
            "role-does-not-exist must NOT be suppressed (misconfiguration signal)",
        )


class TestPGAppNameWarningOnce(BaseCase):
    def test_deprecation_warning_is_one_shot(self):
        os.environ["ODOO_PGAPPNAME"] = "test"
        saved = _db_utils._ODOO_PGAPPNAME_WARNED
        _db_utils._ODOO_PGAPPNAME_WARNED = False
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                for _ in range(5):
                    get_connection_info_for_database("mydb")
            pg = [w for w in captured if "ODOO_PGAPPNAME" in str(w.message)]
            self.assertEqual(
                len(pg),
                1,
                f"expected exactly one warning across 5 calls, got {len(pg)}",
            )
        finally:
            del os.environ["ODOO_PGAPPNAME"]
            _db_utils._ODOO_PGAPPNAME_WARNED = saved


class TestExecuteValuesPageSize(BaseCase):
    def test_zero_page_size_raises(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute_values("INSERT INTO t VALUES %s", [(1,)], page_size=0)

    def test_negative_page_size_raises(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute_values("INSERT INTO t VALUES %s", [(1,)], page_size=-1)

    def test_marker_count_validated_even_when_empty(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute_values("INSERT INTO t VALUES %s, %s", [])
            with self.assertRaises(ValueError):
                cr.execute_values("INSERT INTO t DEFAULT VALUES", [])
            self.assertIsNone(cr.execute_values("INSERT INTO t VALUES %s", []))
            self.assertEqual(
                cr.execute_values("INSERT INTO t VALUES %s", [], fetch=True), []
            )

    def test_a_page_wider_than_the_bind_ceiling_is_clamped(self):
        # PostgreSQL counts bind parameters in a uint16; a page_size that would
        # put 65 536 of them in one statement is split rather than refused.
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _ev_ceiling (a int, b int)")
            rows = [(i, -i) for i in range(40000)]
            cr.execute_values(
                "INSERT INTO _ev_ceiling VALUES %s", rows, page_size=100000
            )
            cr.execute("SELECT count(*), sum(a + b) FROM _ev_ceiling")
            self.assertEqual(cr.fetchone(), (40000, 0))
            cr.execute("SELECT count(*) FROM _ev_ceiling WHERE a = 39999")
            self.assertEqual(cr.fetchone(), (1,))


class TestFaketimeSearchPathIsAStartupOption(BaseCase):
    def test_a_configured_database_sees_the_path_on_every_cursor(self):
        db_name = common.get_db_name()
        with (
            patch.dict(os.environ, {"ODOO_FAKETIME_TEST_MODE": "1"}),
            pool_settings.override(db_names=(db_name,)) as settings,
        ):
            pool = ConnectionPool(maxconn=1, settings=settings)
            try:
                _, info = get_connection_info_for_database(db_name)
                connection = Connection(pool, db_name, info)
                for attempt in ("fresh", "after a return"):
                    with self.subTest(attempt=attempt):
                        cr = connection.cursor()
                        try:
                            # public resolves before pg_catalog, so a public.now()
                            # shadows the builtin: that is what faketime needs
                            cr.execute("SELECT current_schemas(true)")
                            self.assertEqual(cr.fetchone(), (["public", "pg_catalog"],))
                            self.assertEqual(
                                cr.sql_statement_count,
                                1,
                                "the pin costs no statement of its own",
                            )
                        finally:
                            cr.close()
                    time.sleep(0.2)
            finally:
                pool.close_all()

    def test_an_unconfigured_database_keeps_the_default_path(self):
        db_name = common.get_db_name()
        with (
            patch.dict(os.environ, {"ODOO_FAKETIME_TEST_MODE": "1"}),
            pool_settings.override(db_names=("some_other_db",)) as settings,
        ):
            pool = ConnectionPool(maxconn=1, settings=settings)
            try:
                _, info = get_connection_info_for_database(db_name)
                with Connection(pool, db_name, info).cursor() as cr:
                    cr.execute("SELECT current_schemas(true)")
                    self.assertEqual(cr.fetchone(), (["pg_catalog", "public"],))
            finally:
                pool.close_all()


class TestResetConnectionRestoresPrepare(BaseCase):
    def test_reset_restores_prepare_threshold(self):
        with registry().cursor() as cr:
            cr.connection.prepare_threshold = None
            cr.connection.prepared_max = 1
            _reset_connection(cr.connection)
            self.assertEqual(cr.connection.prepare_threshold, 2)
            self.assertEqual(cr.connection.prepared_max, 500)


class TestHealthCheckGracePeriod(BaseCase):
    class _Bare:
        pass

    def test_fresh_connection_skips_probe(self):
        conn = self._Bare()
        setattr(conn, _IDLE_SINCE_ATTR, time.monotonic())
        with patch("odoo.db.lifecycle._probe_liveness") as probe:
            _check_connection(conn)
        probe.assert_not_called()

    def test_idle_connection_is_probed(self):
        from odoo.tools import config

        conn = self._Bare()
        setattr(
            conn,
            _IDLE_SINCE_ATTR,
            time.monotonic() - config["db_healthcheck_grace"] - 1,
        )
        with patch("odoo.db.lifecycle._probe_liveness") as probe:
            _check_connection(conn)
        probe.assert_called_once_with(conn)

    def test_unstamped_connection_fails_safe_to_probe(self):
        conn = self._Bare()
        with patch("odoo.db.lifecycle._probe_liveness") as probe:
            _check_connection(conn)
        probe.assert_called_once_with(conn)

    def test_a_terminated_backend_fails_the_probe_and_the_pool_reconnects(self):
        from odoo.db.lifecycle import _probe_liveness

        dbname = common.get_db_name()
        _, info = get_connection_info_for_database(dbname)
        pool = ConnectionPool(maxconn=1, settings=pool_settings.current())
        self.addCleanup(pool.close_all)
        with contextlib.closing(Cursor(pool, dbname, info)) as cr:
            cr.execute("SELECT pg_backend_pid()")
            first = cr.fetchscalar()
            _probe_liveness(cr._cnx)
        with contextlib.closing(db_connect(dbname).cursor()) as admin:
            admin.execute("SELECT pg_terminate_backend(%s)", (first,))
            admin.commit()
        time.sleep(0.2)
        [psycopg_pool] = pool._pools.values()
        idle = psycopg_pool._pool[0]
        with self.assertRaises(psycopg.OperationalError):
            _probe_liveness(idle)
        setattr(idle, _IDLE_SINCE_ATTR, 0.0)
        with contextlib.closing(Cursor(pool, dbname, info)) as cr:
            cr.execute("SELECT pg_backend_pid()")
            self.assertNotEqual(
                cr.fetchscalar(),
                first,
                "the check callback must refuse the dead backend so the pool "
                "hands out a fresh one",
            )

    def test_configure_and_reset_stamp_freshness(self):
        conn = MagicMock()
        conn.pgconn.exec_.return_value.status = 1
        _configure_connection(conn)
        first = getattr(conn, _IDLE_SINCE_ATTR)
        self.assertIsInstance(first, float)
        time.sleep(0.002)
        _reset_connection(conn)
        self.assertGreater(
            getattr(conn, _IDLE_SINCE_ATTR),
            first,
            "reset() must re-stamp the freshness timestamp on return",
        )


class TestDiscardOnReturn(BaseCase):
    def _set_discard(self, value):
        from odoo.tools import config

        old = config["db_discard_on_return"]
        config["db_discard_on_return"] = value
        self.addCleanup(config.__setitem__, "db_discard_on_return", old)

    def _conn(self):
        conn = MagicMock()
        conn.autocommit = False
        conn.pgconn.exec_.return_value.status = 1
        return conn

    def test_default_runs_cheap_session_reset(self):
        conn = self._conn()
        self._set_discard(False)
        _reset_connection(conn)
        self.assertEqual(
            [c.args for c in conn.pgconn.exec_.call_args_list],
            [(_RESET_SESSION_STATE_SQL.encode(),)],
            "default return path must run the cheap session reset "
            "(and never DISCARD ALL)",
        )
        conn.execute.assert_not_called()
        self.assertEqual(conn.prepare_threshold, 2)
        self.assertEqual(conn.prepared_max, 500)
        self.assertFalse(conn.autocommit)

    def test_opt_in_runs_discard_all_without_touching_autocommit(self):
        conn = self._conn()
        self._set_discard(True)
        _reset_connection(conn)
        self.assertEqual(
            [c.args for c in conn.pgconn.exec_.call_args_list], [(b"DISCARD ALL",)]
        )
        conn._prepared.clear.assert_called_once_with()
        self.assertFalse(
            conn.autocommit,
            "the simple-query call folds no BEGIN in, so the autocommit toggle "
            "that used to bracket the reset is gone with its 1 us",
        )
        self.assertEqual(conn.prepare_threshold, 2)
        self.assertEqual(conn.prepared_max, 500)


class TestURIHealthParamsMerge(BaseCase):
    def test_uri_connect_timeout_preserved(self):
        uri = "postgresql://u:p@h:5432/db?connect_timeout=60&keepalives_idle=300"
        _, info = get_connection_info_for_database(uri)
        self.assertNotIn("connect_timeout", info)
        self.assertNotIn("keepalives_idle", info)
        self.assertEqual(info.get("keepalives"), "1")


class TestExpDropClosesPoolTwice(BaseCase):
    def test_close_db_called_before_and_after_drop(self):
        events: list[tuple[str, str]] = []
        fake_db = "_t_exp_drop_fake"

        def fake_close_db(name: str) -> None:
            events.append(("close_db", name))

        fake_cursor = MagicMock()

        def cursor_execute(query, *_args, **_kwargs):
            if "DROP DATABASE" in str(query):
                events.append(("drop_database", fake_db))

        fake_cursor.execute.side_effect = cursor_execute

        fake_conn = MagicMock()
        fake_conn.cursor.return_value = fake_cursor

        with (
            patch("odoo.service.db.listing.list_dbs", return_value=[fake_db]),
            patch("odoo.modules.registry.Registry.remove"),
            patch("odoo.service.db.lifecycle._terminate_backends"),
            patch("odoo.db.close_db", side_effect=fake_close_db),
            patch("odoo.db.db_connect", return_value=fake_conn),
            patch(
                "odoo.service.db.lifecycle.get_database_identifier",
                return_value=SQL(f'"{fake_db}"'),
            ),
        ):
            result = exp_drop(fake_db)

        self.assertTrue(result, f"exp_drop should return True; events={events}")

        close_indices = [i for i, (k, _) in enumerate(events) if k == "close_db"]
        drop_indices = [i for i, (k, _) in enumerate(events) if k == "drop_database"]

        self.assertEqual(
            len(close_indices),
            2,
            f"close_db must be called exactly twice; events={events}",
        )
        self.assertEqual(
            len(drop_indices),
            1,
            f"DROP DATABASE must be executed exactly once; events={events}",
        )
        self.assertLess(
            close_indices[0],
            drop_indices[0],
            "first close_db must precede DROP DATABASE",
        )
        self.assertGreater(
            close_indices[1],
            drop_indices[0],
            "second close_db must follow DROP DATABASE",
        )


class TestBulkCatalogFactScope(BaseCase):
    def test_facts_are_reused_within_one_transaction(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TABLE _test_scope (id serial PRIMARY KEY, v int)")
            for _ in range(5):
                cr.copy_from(
                    "_test_scope", ["v"], [(1,)], returning_ids=True, binary=True
                )
            cache = cr._schema_cache
            self.assertEqual(len(cache._column_types), 1)
            self.assertEqual(len(cache._id_sequences), 1)
            self.assertIn("_test_scope", cache.locked_tables)
            cr.execute("SELECT count(*) FROM _test_scope")
            self.assertEqual(cr.fetchone()[0], 5)
            cr.rollback()

    def test_commit_and_rollback_drop_the_facts(self):
        for finish in ("commit", "rollback"):
            with self.subTest(finish=finish):
                cr = registry().cursor()
                try:
                    cr.execute(
                        "CREATE TABLE _test_scope2 (id serial PRIMARY KEY, v int)"
                    )
                    cr.copy_from(
                        "_test_scope2", ["v"], [(1,)], returning_ids=True, binary=True
                    )
                    self.assertTrue(cr._schema_cache._column_types)
                    getattr(cr, finish)()
                    self.assertFalse(cr._schema_cache._column_types)
                    self.assertFalse(cr._schema_cache._id_sequences)
                    self.assertFalse(cr._schema_cache.locked_tables)
                finally:
                    if finish == "commit":
                        cr.execute("DROP TABLE IF EXISTS _test_scope2")
                        cr.commit()
                    cr.close()

    def test_facts_are_not_shared_between_cursors(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TABLE _test_scope3 (id serial PRIMARY KEY, v int)")
            cr.commit()
            try:
                cr.copy_from("_test_scope3", ["v"], [(1,)], binary=True)
                self.assertTrue(cr._schema_cache._column_types)
                with registry().cursor() as cr2:
                    self.assertFalse(cr2._schema_cache._column_types)
            finally:
                cr.rollback()
                cr.execute("DROP TABLE IF EXISTS _test_scope3")
                cr.commit()

    def test_temp_relation_facts_are_cacheable(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_tmp_nc (id serial PRIMARY KEY, v int)")
            cr.copy_from("_test_tmp_nc", ["v"], [(1,)], returning_ids=True)
            cr.copy_from("_test_tmp_nc", ["v"], [(2,)], binary=True)
            seq = cr._schema_cache.get_id_sequence("_test_tmp_nc")
            self.assertIsNotNone(seq)
            self.assertIn("pg_temp", seq)
            self.assertEqual(
                cr._schema_cache.get_column_types("_test_tmp_nc", ["v"]), [INT4_OID]
            )
            cr.execute("SELECT v FROM _test_tmp_nc ORDER BY v")
            self.assertEqual(cr.fetchall(), [(1,), (2,)])

    def test_get_column_type_oids_missing_column(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr._get_column_type_oids("ir_model_data", ["id", "no_such_column"])

    def test_ddl_invalidates_column_type_cache(self):
        tbl = "_test_ddl_inval"
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute(f"CREATE TABLE {tbl} (x int)")
            cr.copy_from(tbl, ["x"], [(1,)], binary=True)
            self.assertEqual(
                cr._schema_cache.get_column_types(tbl, ["x"]),
                [INT4_OID],
                "binary copy_from should have cached the column type",
            )
            cr.execute(f"ALTER TABLE {tbl} ALTER COLUMN x TYPE text")
            self.assertIsNone(
                cr._schema_cache.get_column_types(tbl, ["x"]),
                "ALTER must invalidate the cached column type",
            )
            cr.copy_from(tbl, ["x"], [("hello",)], binary=True)
            cr.execute(f"SELECT x FROM {tbl} ORDER BY x")
            self.assertEqual(cr.fetchall(), [("1",), ("hello",)])
        finally:
            cr.rollback()
            cr.close()

    def test_rolled_back_ddl_does_not_poison_later_inserts(self):
        tbl = "_test_ddl_rb"
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute(f"CREATE TABLE {tbl} (x date)")
            cr.commit()
            for undo in ("rollback", "savepoint"):
                with self.subTest(undo=undo):
                    sp = cr.savepoint(flush=False) if undo == "savepoint" else None
                    cr.execute(f"ALTER TABLE {tbl} ALTER COLUMN x TYPE int4 USING 0")
                    cr.copy_from(tbl, ["x"], [(1,)], binary=True)
                    self.assertEqual(
                        cr._schema_cache.get_column_types(tbl, ["x"]), [INT4_OID]
                    )
                    if sp is not None:
                        sp.close(rollback=True)
                    else:
                        cr.rollback()
                    self.assertIsNone(
                        cr._schema_cache.get_column_types(tbl, ["x"]),
                        "undoing the DDL must drop the facts it produced",
                    )
                    cr.copy_from(tbl, ["x"], [(date(2024, 9, 4),)], binary=True)
                    cr.execute(f"SELECT x FROM {tbl}")
                    self.assertEqual(cr.fetchall(), [(date(2024, 9, 4),)])
                    cr.rollback()
        finally:
            cr.rollback()
            cr.execute(f"DROP TABLE IF EXISTS {tbl}")
            cr.commit()
            cr.close()


class TestConcurrentDdlDuringBinaryCopy(BaseCase):
    @mute_logger("odoo.db.cursor")
    def test_concurrent_alter_does_not_corrupt_binary_copy(self):
        tbl = "_test_race_copy"
        db_name = common.get_db_name()
        setup = db_connect(db_name).cursor()
        setup.execute(f"DROP TABLE IF EXISTS {tbl}")
        setup.execute(f"CREATE TABLE {tbl} (id serial PRIMARY KEY, x int)")
        setup.commit()
        setup.close()

        alter_locked = threading.Event()
        outcome = {}

        def alterer():
            cr = db_connect(db_name).cursor()
            try:
                cr.execute(f"ALTER TABLE {tbl} ALTER COLUMN x TYPE date USING NULL")
                alter_locked.set()
                time.sleep(0.8)
                cr.commit()
            except Exception as exc:
                outcome["alter"] = repr(exc)
                cr.rollback()
            finally:
                cr.close()

        thread = threading.Thread(target=alterer)
        thread.start()
        try:
            self.assertTrue(alter_locked.wait(timeout=10))
            time.sleep(0.05)
            cr = db_connect(db_name).cursor()
            try:
                with contextlib.suppress(Exception):
                    cr.copy_from(tbl, ["x"], [(1234567,)], binary=True)
                    cr.commit()
            finally:
                with contextlib.suppress(Exception):
                    cr.rollback()
                cr.close()
        finally:
            thread.join(timeout=20)

        check = db_connect(db_name).cursor()
        try:
            self.assertEqual(outcome, {}, "the concurrent ALTER thread failed")
            check.execute(
                f"SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                f"WHERE attrelid = '{tbl}'::regclass AND attname = 'x'"
            )
            self.assertEqual(
                check.fetchone()[0], "date", "the concurrent ALTER did not commit"
            )
            check.execute(f"SELECT x::text FROM {tbl}")
            rows = check.fetchall()
            self.assertNotIn(
                ("5380-02-17",),
                rows,
                "binary COPY encoded with pre-ALTER types — the lock taken by "
                "_lock_table_for_bulk regressed",
            )
        finally:
            check.rollback()
            check.execute(f"DROP TABLE IF EXISTS {tbl}")
            check.commit()
            check.close()


class TestBorrowHonoursItsTimeout(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            cls.refused_port = probe.getsockname()[1]

        tarpit = socket.socket()
        tarpit.bind(("127.0.0.1", 0))
        tarpit.listen(1)
        cls.addClassCleanup(tarpit.close)
        cls.tarpit_port = tarpit.getsockname()[1]

    def _info(self, port, **overrides):
        return {
            "dbname": "nonexistent",
            "host": "127.0.0.1",
            "port": str(port),
            "connect_timeout": "10",
            "application_name": "odoo-borrow-budget-test",
            **overrides,
        }

    def _refused(self, **overrides):
        with socket.socket() as probe:
            probe.settimeout(0.5)
            if probe.connect_ex(("127.0.0.1", self.refused_port)) == 0:
                self.skipTest(f"port {self.refused_port} was taken since setUpClass")
        return self._info(self.refused_port, **overrides)

    def test_cold_pool_to_an_unreachable_host_stays_inside_the_budget(self):
        budget = 3.0
        info = self._refused()
        pool = ConnectionPool(maxconn=4, borrow_timeout=budget)
        try:
            start = time.monotonic()
            with self.assertRaises((PoolError, psycopg.Error)):
                pool.borrow(info)
            elapsed = time.monotonic() - start
            self.assertLess(
                elapsed,
                budget + 1.5,
                f"borrow took {elapsed:.2f}s against a {budget}s budget",
            )
            self.assertEqual(
                pool._budget.available, 4, "a failed borrow must not leak a permit"
            )
        finally:
            pool.close_all()

    def test_maintenance_db_path_stays_inside_the_budget(self):
        budget = 3.0
        info = self._info(self.tarpit_port, dbname="postgres")
        pool = ConnectionPool(maxconn=4, borrow_timeout=budget)
        try:
            start = time.monotonic()
            with self.assertRaises((PoolError, psycopg.Error)):
                pool.borrow(info)
            elapsed = time.monotonic() - start
            self.assertGreater(
                elapsed,
                0.5,
                "the connect returned at once, so the budget was never reached "
                "and this test asserts nothing",
            )
            self.assertLess(
                elapsed,
                budget + 1.5,
                f"direct borrow took {elapsed:.2f}s against a {budget}s budget",
            )
            self.assertEqual(pool._budget.available, 4)
            self.assertEqual(pool._direct_out, 0)
        finally:
            pool.close_all()

    def test_missing_database_on_a_reachable_host_still_fails_fast(self):
        pool = ConnectionPool(maxconn=4, borrow_timeout=30.0)
        _, info = get_connection_info_for_database("_test_no_such_db_borrow_budget")
        try:
            start = time.monotonic()
            with self.assertRaises(psycopg.errors.InvalidCatalogName):
                pool.borrow(info)
            self.assertLess(time.monotonic() - start, 5.0)
            self.assertEqual(pool._budget.available, 4)
        finally:
            pool.close_all()


class TestCheckSignalingDrains(BaseCase):
    def test_the_reload_branch_still_drains_the_database(self):
        self.assertIn(
            "_reload_after_signaling",
            inspect.getsource(Registry.check_signaling),
            "check_signaling must reach the reload branch to reach the drain",
        )
        self.assertIn(
            "drain_db",
            inspect.getsource(Registry._reload_after_signaling),
            "the reload branch must drain_db(self.db_name)",
        )

    def test_the_drain_is_skipped_when_another_registry_is_already_current(self):
        src = inspect.getsource(Registry._reload_after_signaling)
        self.assertLess(
            src.index("published.registry_sequence"),
            src.index("drain_db"),
            "an already-published registry returns before the drain, which is "
            "the whole reason the branch was extracted",
        )


class TestCopyFromOnErrorWhitelist(BaseCase):
    def test_rejects_arbitrary_on_error(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.copy_from("t", ["c"], [(1,)], on_error="ignore, FREEZE")

    def test_accepts_stop(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_oe (v int)")
            cr.copy_from("_test_oe", ["v"], [(1,)], on_error="stop")
            cr.execute("SELECT count(*) FROM _test_oe")
            self.assertEqual(cr.fetchone()[0], 1)


class TestExecuteValuesEscapedPercent(BaseCase):
    def test_literal_double_percent_accepted(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_evpesc (v text)")
            cr.execute_values(
                "INSERT INTO _test_evpesc (v) SELECT x FROM (VALUES %s) s(x) "
                "WHERE 'abc' NOT LIKE 'a%%s'",
                [("r1",), ("r2",)],
            )
            cr.execute("SELECT count(*) FROM _test_evpesc")
            self.assertEqual(cr.fetchone()[0], 2)

    def test_literal_only_rejected(self):
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute_values("SELECT 'a%%s'", [(1,)])


class TestSavepointGuardsSurviveOptimize(BaseCase):
    def test_commit_inside_savepoint_raises(self):
        with registry().cursor() as cr:
            self.assertIsNone(cr.transaction)
            with self.assertRaises(RuntimeError):
                with cr.savepoint(flush=False):
                    cr.commit()
            self.assertEqual(cr._savepoint_depth, 0)

    def test_rollback_inside_savepoint_raises(self):
        with registry().cursor() as cr:
            self.assertIsNone(cr.transaction)
            with self.assertRaises(RuntimeError):
                with cr.savepoint(flush=False):
                    cr.rollback()
            self.assertEqual(cr._savepoint_depth, 0)


class TestFlushingSavepointLayering(BaseCase):
    def test_orm_subclass_is_registered(self):
        from odoo.db.cursor import BaseCursor
        from odoo.db.savepoint import _FlushingSavepoint
        from odoo.orm.runtime.savepoint import _OrmFlushingSavepoint

        self.assertIs(BaseCursor._flushing_savepoint_cls, _OrmFlushingSavepoint)
        self.assertTrue(issubclass(_OrmFlushingSavepoint, _FlushingSavepoint))

    def test_db_layer_does_not_import_orm_helpers(self):
        from odoo.db import savepoint as db_savepoint
        from odoo.db.savepoint import _FlushingSavepoint
        from odoo.orm.runtime.savepoint import _OrmFlushingSavepoint

        self.assertFalse(hasattr(db_savepoint, "reset_cached_properties"))
        self.assertIsNot(
            _OrmFlushingSavepoint._restore_orm_state,
            _FlushingSavepoint._restore_orm_state,
        )
        self.assertEqual(
            _OrmFlushingSavepoint.__slots__,
            ("_generation_before",),
            "the ORM savepoint snapshots the cache-invalidation generations and "
            "nothing else: default_env is set by the transaction's opener, not by "
            "whoever constructs an Environment first",
        )

    def test_savepoint_restores_orm_state_on_rollback(self):
        from odoo.orm.runtime.savepoint import _OrmFlushingSavepoint

        class _StubTransaction:
            def __init__(self, reg):
                self.default_env = "ENV_OPENER"
                self.registry = reg
                self.envs = []
                self.cleared = 0
                self.was_reset = 0

            def flush(self):
                pass

            def clear(self):
                self.cleared += 1

            def reset(self):
                self.was_reset += 1

        reg = registry()
        with reg.cursor() as cr:
            cr.transaction = _StubTransaction(reg)
            try:
                sp = cr.savepoint()
                self.assertIsInstance(sp, _OrmFlushingSavepoint)
                self.assertEqual(cr._savepoint_depth, 1)
                cr.transaction.default_env = "ENV_DURING"
                sp.rollback()
                self.assertEqual(
                    cr.transaction.default_env,
                    "ENV_DURING",
                    "a savepoint rollback restores caches, not the opener's "
                    "default_env; the code that changes it restores it",
                )
                self.assertEqual(cr.transaction.cleared, 1)
                self.assertEqual(cr.transaction.was_reset, 0)
                sp.close(rollback=True)
                self.assertEqual(cr._savepoint_depth, 0)
            finally:
                cr.transaction = None


class TestFlushNonConvergence(BaseCase):
    def test_flush_nonconvergence_raises(self):
        class _EndlessTransaction:
            def __init__(self, cr):
                self._cr = cr

            def flush(self):
                self._cr.precommit.add(lambda: None)

            def clear(self):
                pass

        with registry().cursor() as cr:
            orig = cr.transaction
            cr.transaction = _EndlessTransaction(cr)
            try:
                with self.assertRaises(RuntimeError):
                    cr.flush()
            finally:
                cr.transaction = orig
                cr.precommit.clear()
                cr.rollback()

    def test_flush_self_requeue_drains_in_single_run(self):
        from odoo.db.cursor import BaseCursor

        with registry().cursor() as cr:
            orig = cr.transaction
            cr.transaction = None
            try:
                remaining = [BaseCursor._MAX_FLUSH_PASSES * 5]

                def hook():
                    remaining[0] -= 1
                    if remaining[0] > 0:
                        cr.precommit.add(hook)

                cr.precommit.add(hook)
                cr.flush()
                self.assertEqual(remaining[0], 0)
                self.assertFalse(cr.precommit)
            finally:
                cr.transaction = orig
                cr.precommit.clear()
                cr.rollback()

    def test_flush_converges_at_budget(self):
        from odoo.db.cursor import BaseCursor

        class _BoundedTransaction:
            def __init__(self, cr, limit):
                self._cr = cr
                self.limit = limit
                self.calls = 0

            def flush(self):
                if self.calls < self.limit:
                    self.calls += 1
                    self._cr.precommit.add(lambda: None)

            def clear(self):
                pass

        budget = BaseCursor._MAX_FLUSH_PASSES
        with registry().cursor() as cr:
            orig = cr.transaction
            try:
                cr.transaction = _BoundedTransaction(cr, budget)
                cr.flush()
                self.assertFalse(cr.precommit)
                cr.transaction = _BoundedTransaction(cr, budget + 1)
                with self.assertRaises(RuntimeError):
                    cr.flush()
            finally:
                cr.transaction = orig
                cr.precommit.clear()
                cr.rollback()


class TestUninitializedCursorClosed(BaseCase):
    def test_uninitialized_cursor_raises_interface_error(self):
        cur = object.__new__(Cursor)
        with self.assertRaises(psycopg.InterfaceError):
            cur.some_attribute


class TestTheModuleLevelFanOut(BaseCase):
    def test_is_pooled_follows_a_real_connection(self):
        name = common.get_db_name()
        cr = db_connect(name).cursor()
        try:
            cr.execute("SELECT 1")
            self.assertTrue(
                odoo.db.is_pooled(name),
                "a database with a live pool must report as pooled",
            )
        finally:
            cr.rollback()
            cr.close()
        self.assertFalse(
            odoo.db.is_pooled("_no_such_database_xyz"),
            "and one that was never connected to must not",
        )

    def _fake_registry(self):
        pools = {}
        made = []
        for endpoint in ((None, 5432), ("elsewhere.example", 5433)):
            for readonly in (False, True):
                m = MagicMock()
                m.has_database.side_effect = lambda n: n == "dbz"
                pools[endpoint, readonly] = m
                made.append(m)
        return pools, made

    def test_close_db_reaches_every_endpoint_and_both_modes(self):
        pools, made = self._fake_registry()
        with patch.dict(odoo.db.registry._pools, pools, clear=True):
            odoo.db.close_db("dbz")
        for m in made:
            m.close_database.assert_called_once_with("dbz")

    def test_drain_db_reaches_every_endpoint_and_both_modes(self):
        pools, made = self._fake_registry()
        with patch.dict(odoo.db.registry._pools, pools, clear=True):
            odoo.db.drain_db("dbz")
        for m in made:
            m.drain_database.assert_called_once_with("dbz")

    def test_drain_all_drains_every_pool(self):
        pools, made = self._fake_registry()
        with patch.dict(odoo.db.registry._pools, pools, clear=True):
            odoo.db.drain_all()
        for m in made:
            m.drain_all.assert_called_once_with()

    def test_is_pooled_asks_every_pool_before_answering_no(self):
        pools, made = self._fake_registry()
        for m in made:
            m.has_database.side_effect = lambda n: False
        with patch.dict(odoo.db.registry._pools, pools, clear=True):
            self.assertFalse(odoo.db.is_pooled("dbz"))
        self.assertTrue(
            all(m.has_database.called for m in made),
            "a 'no' has to have asked every endpoint; short-circuiting on the "
            "configured one is how the URI pools used to be missed",
        )


class TestCloseDatabaseByName(BaseCase):
    def test_close_database_matches_uri_pools(self):
        pool = ConnectionPool(maxconn=2)
        uri_key = _get_dsn_key({"dsn": "postgresql://localhost/dbz?connect_timeout=10"})
        uri_pool = MagicMock()
        uri_pool.closed = False
        other_key = _get_dsn_key({"dbname": "other"})
        other_pool = MagicMock()
        other_pool.closed = False
        pool._pools[uri_key] = uri_pool
        pool._pools[other_key] = other_pool

        pool.close_database("dbz")

        self.assertNotIn(uri_key, pool._pools)
        uri_pool.close.assert_called_once()
        self.assertIn(other_key, pool._pools)
        other_pool.close.assert_not_called()


class TestVersionGateInBorrow(BaseCase):
    def test_configure_does_not_raise_version_error(self):
        from odoo.db.pool import _configure_connection

        src = inspect.getsource(_configure_connection)
        self.assertNotIn("raise PoolError", src)

    def test_borrow_checks_server_version(self):
        gate_src = inspect.getsource(ConnectionPool._check_min_server_version)
        self.assertIn("server_version", gate_src)
        self.assertIn("MIN_PG_VERSION", gate_src)
        self.assertIn(
            "_check_min_server_version",
            inspect.getsource(ConnectionPool._check_borrowed_connection),
        )
        self.assertIn(
            "_check_min_server_version",
            inspect.getsource(ConnectionPool._borrow_directly),
        )
        borrow_src = inspect.getsource(ConnectionPool.borrow)
        self.assertIn("_check_borrowed_connection", borrow_src)


class TestPsycopgPoolPrivateApi(BaseCase):
    def test_conn_pool_attribute_set_by_getconn(self):
        with registry().cursor() as cr:
            self.assertIsNotNone(getattr(cr._cnx, "_pool", None))

    def test_connection_prepared_attribute_exists(self):
        with registry().cursor() as cr:
            self.assertTrue(hasattr(cr._cnx, "_prepared"))


class TestPoolFailsFastOnMissingDatabase(BaseCase):
    def test_borrow_missing_db_raises_invalid_catalog_name_fast(self):
        pool = ConnectionPool(maxconn=4)
        self.addCleanup(pool.close_all)
        info = get_connection_info_for_database("zzz_missing_db_for_probe_test")[1]
        start = time.monotonic()
        with self.assertRaises(psycopg.errors.InvalidCatalogName):
            pool.borrow(info)
        elapsed = time.monotonic() - start
        self.assertLess(
            elapsed,
            10,
            msg=f"missing-db connect took {elapsed:.1f}s — fast-fail probe regressed",
        )

    def test_probe_is_wired_into_pool_creation(self):
        src = inspect.getsource(ConnectionPool._get_or_create_pool)
        self.assertIn("_check_connectable_or_fail_fast", src)
        src = inspect.getsource(ConnectionPool._check_connectable_or_fail_fast)
        self.assertIn(
            "self._probe.check_connectable",
            src,
            "the pre-flight probe moved to db/probe.py; pool creation must "
            "still go through it or a missing database costs a PoolTimeout",
        )


class TestBorrowReturnsConnectionOnPostGetconnFailure(BaseCase):
    def test_info_failure_returns_connection_and_releases_semaphore(self):
        pool = ConnectionPool(maxconn=4)
        info = get_connection_info_for_database("nonexistent_db_test")[1]
        key = _get_dsn_key(info)

        class _Info:
            @property
            def server_version(self):
                raise psycopg.OperationalError("simulated degraded backend")

            backend_pid = 1

        conn = MagicMock()
        conn.info = _Info()
        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.getconn.return_value = conn
        pool._pools[key] = mock_pool

        sem_before = pool._budget.available
        with self.assertRaises(psycopg.OperationalError):
            pool.borrow(info)

        mock_pool.putconn.assert_called_once_with(conn)
        self.assertEqual(
            pool._budget.available,
            sem_before,
            "semaphore not released — borrow() leak fix regressed",
        )

    def test_min_version_path_also_returns_connection(self):
        pool = ConnectionPool(maxconn=4)
        info = get_connection_info_for_database("nonexistent_db_test")[1]
        key = _get_dsn_key(info)

        conn = MagicMock()
        conn.info.server_version = 150000
        conn.info.backend_pid = 1
        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.getconn.return_value = conn
        pool._pools[key] = mock_pool

        sem_before = pool._budget.available
        with self.assertRaises(PoolError):
            pool.borrow(info)
        mock_pool.putconn.assert_called_once_with(conn)
        self.assertEqual(pool._budget.available, sem_before)


class TestExecutemanyGeneratorParams(BaseCase):
    def test_loaded_generator_executes_and_counts_all_rows(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_em_gen (v int)")
            before = cr.sql_log_count  # noqa: E8516  asserts the row counter itself
            cr.executemany(
                "INSERT INTO _test_em_gen(v) VALUES (%s)",
                ((i,) for i in range(3)),
            )
            counted = cr.sql_log_count - before  # noqa: E8516  asserts the row counter itself
            cr.execute("SELECT count(*) FROM _test_em_gen")
            self.assertEqual(cr.fetchone()[0], 3)
            self.assertEqual(
                counted, 3, "metric undercount for generator — fix regressed"
            )

    def test_empty_generator_short_circuits(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_em_empty (v int)")
            before = cr.sql_log_count  # noqa: E8516  asserts the row counter itself
            cr.executemany("INSERT INTO _test_em_empty(v) VALUES (%s)", (x for x in ()))
            self.assertEqual(
                cr.sql_log_count,  # noqa: E8516  asserts the row counter itself
                before,
                "empty generator must short-circuit",
            )
            cr.execute("SELECT count(*) FROM _test_em_empty")
            self.assertEqual(cr.fetchone()[0], 0)

    def test_copy_from_empty_generator_short_circuits(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_copy_empty_gen (v int)")
            rows_before = cr.sql_log_count  # noqa: E8516  asserts the row counter itself
            statements_before = cr.sql_statement_count
            cr.copy_from("_test_copy_empty_gen", ["v"], (x for x in ()))
            self.assertEqual(
                cr.sql_statement_count,
                statements_before,
                "an empty generator must not pay a COPY round trip; a length "
                "test cannot see one, so the first row is peeled instead",
            )
            self.assertEqual(cr.sql_log_count, rows_before)  # noqa: E8516  asserts the row counter itself

    def test_copy_from_a_generator_still_copies(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_copy_gen (v int)")
            cr.copy_from("_test_copy_gen", ["v"], ((i,) for i in range(3)))
            cr.execute("SELECT count(*) FROM _test_copy_gen")
            self.assertEqual(
                cr.fetchone()[0],
                3,
                "peeling the first row must put it back, not drop it",
            )


class TestRecoverableErrorLogLevel(BaseCase):
    def test_readonly_write_logged_as_warning_not_error(self):
        with self.assertLogs("odoo.db.cursor", level="WARNING") as cm:
            with self.assertRaises(psycopg.errors.ReadOnlySqlTransaction):
                with registry().cursor(readonly=True) as cr:
                    cr.execute(
                        "UPDATE res_users SET login = login WHERE id = %s",
                        (ADMIN_USER_ID,),
                    )
        levels = {r.levelname for r in cm.records}
        self.assertIn("WARNING", levels)
        self.assertNotIn(
            "ERROR", levels, "recoverable error logged at ERROR — fix regressed"
        )

    def test_lock_not_available_logged_as_warning_not_error(self):
        # An advisory lock, not a row of res_users: under ``-u`` the loading
        # transaction holds the admin row until it commits, so a plain
        # ``FOR UPDATE`` on it waits forever. ``lock_timeout`` raises the same
        # 55P03 ``LockNotAvailable`` that ``NOWAIT`` does.
        with registry().cursor() as cr_lock:
            cr_lock.execute("SELECT pg_advisory_xact_lock(%s)", (0x0D00,))
            with self.assertLogs("odoo.db.cursor", level="WARNING") as cm:
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    with registry().cursor() as cr_nowait:
                        cr_nowait.execute("SET LOCAL lock_timeout = '50ms'")
                        cr_nowait.execute("SELECT pg_advisory_xact_lock(%s)", (0x0D00,))
        levels = {r.levelname for r in cm.records}
        self.assertIn("WARNING", levels)
        self.assertNotIn(
            "ERROR", levels, "LockNotAvailable logged at ERROR — fix regressed"
        )


class TestDDLDetectionLeadingWhitespace(BaseCase):
    def test_leading_whitespace_ddl_still_inlines_params(self):
        with registry().cursor() as cr:
            cr.execute(
                "\n            CREATE TEMP TABLE _test_ddl_ws (val int DEFAULT %s)",
                (7,),
            )
            cr.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = '_test_ddl_ws' AND column_name = 'val'"
            )
            self.assertEqual(cr.fetchone()[0], "7")

    def test_deeply_indented_ddl_inlines_params(self):
        with registry().cursor() as cr:
            cr.execute(
                " " * 70 + "CREATE TEMP TABLE _test_ddl_deep (val int DEFAULT %s)",
                (7,),
            )
            cr.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = '_test_ddl_deep' AND column_name = 'val'"
            )
            self.assertEqual(cr.fetchone()[0], "7")

    def test_deeply_indented_ddl_invalidates_prepared_cache(self):
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_ddl_plan (a int)")
            cr.execute("INSERT INTO _test_ddl_plan VALUES (1)")
            for _ in range(3):
                cr.execute("SELECT * FROM _test_ddl_plan")
                cr.fetchall()
            cr.execute(" " * 70 + "ALTER TABLE _test_ddl_plan ADD COLUMN b int")
            cr.execute("SELECT * FROM _test_ddl_plan")
            self.assertEqual(cr.fetchall(), [(1, None)])


class TestResetConnectionClosesSessionGucLeak(BaseCase):
    def test_session_set_cleared_by_return_hook(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            conn = cr.connection
            cr.execute("SET search_path = pg_catalog")
            cr.commit()
            cr.rollback()
            cr.execute("SHOW search_path")
            self.assertEqual(cr.fetchscalar(), "pg_catalog")
            cr.rollback()
            _reset_connection(conn)
            cr.execute("SHOW search_path")
            self.assertNotEqual(
                cr.fetchscalar(),
                "pg_catalog",
                "_reset_connection must clear session GUCs (RESET ALL) so they "
                "cannot leak to the next borrower",
            )
        finally:
            cr.execute("RESET search_path")
            cr.commit()
            cr.close()


class TestProbeDoesNotBlockOtherDatabases(BaseCase):
    def test_slow_probe_for_one_db_does_not_block_another(self):
        pool = ConnectionPool(maxconn=8)
        probe_sleep = 1.0

        class _StubPool:
            closed = False

            def __init__(self, *a, **k):
                pass

            def get_stats(self):
                return {}

            def close(self):
                pass

            @staticmethod
            def check_connection(conn):
                return None

        probe_started = threading.Event()

        def slow_probe(conninfo, kwargs, deadline=None):
            probe_started.set()
            time.sleep(probe_sleep)

        errors = []
        elapsed = {}

        def create(label, info):
            try:
                t0 = time.monotonic()
                pool._get_or_create_pool(frozenset(info.items()), dict(info))
                elapsed[label] = time.monotonic() - t0
            except Exception as e:
                errors.append(f"{label}: {type(e).__name__}: {e}")

        with (
            patch("odoo.db.pool._PsycopgPool", _StubPool),
            patch.object(pool._probe, "probe_connectable", side_effect=slow_probe),
        ):
            t_a = threading.Thread(target=create, args=("a", {"database": "a"}))
            t_b = threading.Thread(target=create, args=("b", {"database": "b"}))
            start = time.monotonic()
            t_a.start()
            self.assertTrue(probe_started.wait(5.0), "probe for A never started")
            t_b.start()
            t_a.join()
            t_b.join()
            wall = time.monotonic() - start

        pool.close_all()
        self.assertEqual(errors, [], f"pool creation raised: {errors}")
        self.assertLess(
            wall,
            probe_sleep * 1.6,
            f"pool creation for two different databases serialized "
            f"(wall={wall:.2f}s, probe={probe_sleep}s) — the probe is holding "
            f"the shared _pools lock across its network round-trip",
        )

    def test_probe_uses_short_connect_timeout(self):
        from odoo.db.probe import PROBE_CONNECT_TIMEOUT

        pool = ConnectionPool(maxconn=2)
        captured = {}

        def fake_connect(conninfo, **kw):
            captured.update(kw)
            raise psycopg.OperationalError("connection refused")

        with patch("psycopg.connect", side_effect=fake_connect):
            pool._probe.probe_connectable(
                "", {"dbname": "x", "connect_timeout": "10", "options": "-c jit=off"}
            )
        self.assertEqual(captured.get("connect_timeout"), PROBE_CONNECT_TIMEOUT)


class TestAdapterIsolationPerConnection(BaseCase):
    def test_pooled_cursor_decodes_numeric_as_float(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 1.5::numeric")
            self.assertIsInstance(cr.fetchone()[0], float)

    def test_raw_connection_decodes_numeric_as_decimal(self):
        _, info = get_connection_info_for_database(common.get_db_name())
        conn = psycopg.connect(**info)
        try:
            self.assertIsInstance(
                conn.execute("SELECT 1.5::numeric").fetchone()[0], Decimal
            )
        finally:
            conn.close()


class TestPoolMinconn(BaseCase):
    def test_default_minconn_is_zero(self):
        pool = ConnectionPool(maxconn=4)
        try:
            self.assertEqual(pool._minconn, 0)
        finally:
            pool.close_all()

    def test_minconn_stored(self):
        pool = ConnectionPool(maxconn=4, minconn=2)
        try:
            self.assertEqual(pool._minconn, 2)
        finally:
            pool.close_all()

    def test_minconn_exceeding_maxconn_raises(self):
        with self.assertRaises(ValueError):
            ConnectionPool(maxconn=4, minconn=5)

    def test_negative_minconn_raises(self):
        with self.assertRaises(ValueError):
            ConnectionPool(maxconn=4, minconn=-1)

    def test_maintenance_databases_are_never_pooled(self):
        pool = ConnectionPool(maxconn=4, minconn=2)
        _, info = get_connection_info_for_database("postgres")
        try:
            conn = pool.borrow(info)
            self.assertEqual(
                pool._pools, {}, "no per-DSN pool may exist for 'postgres'"
            )
            self.assertFalse(conn.closed)
            self.assertEqual(pool._direct_out, 1)
            self.assertEqual(
                conn.execute("SHOW idle_session_timeout").fetchone()[0], "15min"
            )
            conn.rollback()
            pool.give_back(conn)
            self.assertTrue(
                conn.closed, "maintenance-db connection must close on give_back"
            )
            self.assertEqual(pool._direct_out, 0)
            conns = [pool.borrow(info) for _ in range(4)]
            for c in conns:
                pool.give_back(c)
        finally:
            pool.close_all()

    def test_maintenance_db_double_give_back_is_noop(self):
        pool = ConnectionPool(maxconn=2)
        _, info = get_connection_info_for_database("postgres")
        try:
            conn = pool.borrow(info)
            pool.give_back(conn)
            pool.give_back(conn)
            a = pool.borrow(info)
            b = pool.borrow(info)
            pool._borrow_timeout = 0.2
            with self.assertRaises(PoolError):
                pool.borrow(info)
            pool.give_back(a)
            pool.give_back(b)
        finally:
            pool.close_all()


class TestPoolSessionGucOptions(BaseCase):
    def _created_pool_args(self, connection_info, **pool_kw):
        pool = ConnectionPool(maxconn=2, **pool_kw)
        created = {}

        class _FakePool:
            closed = False

            def __init__(self, conninfo, **kw):
                created["conninfo"] = conninfo
                created.update(kw)

            def close(self):
                pass

            def get_stats(self):
                return {}

        key = _get_dsn_key(connection_info)
        with (
            patch.object(pool_module, "_PsycopgPool", _FakePool),
            patch.object(pool._probe, "probe_connectable"),
        ):
            try:
                pool._get_or_create_pool(key, dict(connection_info))
            finally:
                pool.close_all()
        return created

    def test_uri_options_preserved_alongside_session_gucs(self):
        created = self._created_pool_args(
            {"dsn": "postgresql://u@h/db?options=-csearch_path%3Dfoo"}
        )
        opts = created["kwargs"]["options"]
        self.assertIn("search_path=foo", opts, "URI ?options= GUC was dropped")
        self.assertIn("jit=off", opts)
        self.assertIn("work_mem=16MB", opts)

    def test_keyword_options_preserved(self):
        created = self._created_pool_args(
            {"dbname": "db", "options": "-c statement_timeout=5000"}
        )
        opts = created["kwargs"]["options"]
        self.assertIn("statement_timeout=5000", opts)
        self.assertIn("jit=off", opts)

    def test_pgoptions_env_used_as_fallback(self):
        with patch.dict(os.environ, {"PGOPTIONS": "-c search_path=envpath"}):
            created = self._created_pool_args({"dbname": "db"})
        opts = created["kwargs"]["options"]
        self.assertIn("search_path=envpath", opts)
        self.assertIn("jit=off", opts)

    def test_pgoptions_env_loses_to_explicit_options(self):
        with patch.dict(os.environ, {"PGOPTIONS": "-c search_path=envpath"}):
            created = self._created_pool_args(
                {"dbname": "db", "options": "-c statement_timeout=5000"}
            )
        opts = created["kwargs"]["options"]
        self.assertIn("statement_timeout=5000", opts)
        self.assertNotIn("envpath", opts)

    def test_idle_session_timeout_default_unchanged(self):
        created = self._created_pool_args({"dbname": "db"})
        self.assertIn("idle_session_timeout=900000", created["kwargs"]["options"])

    def test_idle_session_timeout_scales_with_max_idle(self):
        created = self._created_pool_args({"dbname": "db"}, max_idle=1200)
        self.assertIn("idle_session_timeout=1800000", created["kwargs"]["options"])


class TestCopyFromMetricsQueryLazy(BaseCase):
    def test_no_hook_passes_none(self):
        captured = {}
        orig = Cursor._record_metrics

        def spy(
            self, delay, count=1, *, query=None, params=None, start=0.0, hooks=None
        ):
            captured["query"] = query
            return orig(
                self, delay, count, query=query, params=params, start=start, hooks=hooks
            )

        with patch.object(Cursor, "_record_metrics", spy):
            with registry().cursor() as cr:
                cr.execute("CREATE TEMP TABLE _t_metrics_nh (a int)")
                cr.copy_from("_t_metrics_nh", ["a"], [(1,), (2,)])
        self.assertIsNone(captured["query"])

    def test_hook_receives_rendered_copy_statement(self):
        seen = []
        t = threading.current_thread()
        t.query_hooks = [lambda cr, q, p, s, d: seen.append(q)]
        try:
            with registry().cursor() as cr:
                cr.execute("CREATE TEMP TABLE _t_metrics_h (a int)")
                cr.copy_from("_t_metrics_h", ["a"], [(1,)])
        finally:
            del t.query_hooks
        self.assertTrue(seen)
        self.assertIsInstance(seen[-1], str)
        self.assertTrue(seen[-1].startswith("COPY"))


class TestCopyFromBinaryNumeric(BaseCase):
    def test_binary_copy_float_into_numeric_roundtrips(self):
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _t_bin_num (a int, n numeric(12,2), m numeric)"
            )
            cr.copy_from(
                "_t_bin_num",
                ["a", "n", "m"],
                [(1, 1234.56, 0.1), (2, -7.0, 99999.999)],
                binary=True,
            )
            cr.execute("SELECT a, n, m FROM _t_bin_num ORDER BY a")
            rows = cr.fetchall()
        self.assertEqual(rows[0][0], 1)
        self.assertAlmostEqual(rows[0][1], 1234.56, places=2)
        self.assertAlmostEqual(rows[0][2], 0.1, places=6)
        self.assertAlmostEqual(rows[1][1], -7.0, places=2)


class TestCursorForwardingContract(BaseCase):
    FORWARDED = (
        "fetchone",
        "fetchall",
        "fetchmany",
        "description",
        "rowcount",
        "nextset",
        "connection",
        "readonly",
    )

    def test_forwarded_names_resolve(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 1")
            for name in self.FORWARDED:
                with self.subTest(name=name):
                    getattr(cr, name)

    def test_non_forwarded_attr_raises(self):
        with registry().cursor() as cr:
            with self.assertRaises(AttributeError) as ctx:
                _ = cr.row_factory
            message = str(ctx.exception)
            self.assertIn("row_factory", message)
            self.assertIn("cr._obj.row_factory", message, "point at the escape hatch")

    def test_it_no_longer_silently_forwards_to_psycopg(self):
        with registry().cursor() as cr:
            with self.assertRaises(AttributeError):
                _ = cr.scroll
            self.assertTrue(
                callable(cr._obj.scroll), "the deliberate route still works"
            )

    UNDEFINED_DUNDERS = ("__len__", "__iter__", "__next__", "__fspath__")

    def test_dunder_probes_report_absent_without_warning(self):
        with registry().cursor() as cr:
            for name in self.UNDEFINED_DUNDERS:
                with self.subTest(name=name):
                    with warnings.catch_warnings(record=True) as w:
                        warnings.simplefilter("always")
                        present = hasattr(cr, name)
                    self.assertFalse(present, f"{name} must not be forwarded")
                    self.assertEqual(
                        [
                            str(x.message)
                            for x in w
                            if issubclass(x.category, DeprecationWarning)
                        ],
                        [],
                        f"{name} probe emitted a deprecation warning",
                    )

    def test_copy_protocol_probes_do_not_warn_either(self):
        with registry().cursor() as cr:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                for name in ("__copy__", "__deepcopy__", "__getstate__"):
                    self.assertTrue(hasattr(cr, name))
            self.assertEqual(
                [
                    str(x.message)
                    for x in w
                    if issubclass(x.category, DeprecationWarning)
                ],
                [],
            )

    def test_cursor_refuses_to_be_copied(self):
        with registry().cursor() as cr:
            for label, call in (
                ("copy", lambda: copy.copy(cr)),
                ("deepcopy", lambda: copy.deepcopy(cr)),
            ):
                with self.subTest(op=label), self.assertRaises(TypeError) as ctx:
                    call()
                self.assertIn("cannot be copied", str(ctx.exception))
            cr.execute("SELECT 1")
            self.assertEqual(cr.fetchone(), (1,))

    def test_dunder_probes_are_quiet_on_a_closed_cursor_too(self):
        cr = registry().cursor()
        cr.close()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertFalse(hasattr(cr, "__len__"))
        self.assertEqual([str(x.message) for x in w], [])
        with self.assertRaises(psycopg.InterfaceError):
            _ = cr.row_factory


class TestPreparedCacheSurvivesReleaseNotRollback(BaseCase):
    QUERY = "SELECT id FROM res_partner WHERE active = %s"

    def _warm(self, cr):
        for _ in range(4):
            cr.execute(self.QUERY, (True,))
            cr.fetchall()
        prepared = len(cr._cnx._prepared._names)
        self.assertGreater(prepared, 0, "nothing got prepared; tuning changed?")
        return prepared

    def test_release_savepoint_keeps_the_cache(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute("SAVEPOINT sp_keep")
            before = self._warm(cr)
            cr.execute("RELEASE SAVEPOINT sp_keep")
            self.assertEqual(
                len(cr._cnx._prepared._names),
                before,
                "RELEASE must not wipe the prepared-statement cache",
            )
        finally:
            cr.rollback()
            cr.close()

    def test_rollback_to_savepoint_wipes_the_cache(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute("SAVEPOINT sp_undo")
            self._warm(cr)
            cr.execute("ROLLBACK TO SAVEPOINT sp_undo")
            self.assertEqual(
                len(cr._cnx._prepared._names),
                0,
                "ROLLBACK TO SAVEPOINT is expected to wipe the cache (psycopg "
                "guards against rolled-back DDL resurrecting stale plans)",
            )
        finally:
            cr.rollback()
            cr.close()

    def test_commit_keeps_the_cache(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            before = self._warm(cr)
            cr.commit()
            self.assertEqual(len(cr._cnx._prepared._names), before)
        finally:
            cr.rollback()
            cr.close()


class TestBorrowValidationFailureNoLeak(BaseCase):
    def test_version_gate_failure_releases_semaphore_and_putconn(self):
        pool = ConnectionPool(maxconn=4)
        info = get_connection_info_for_database("nonexistent_db_test")[1]
        key = _get_dsn_key(info)

        conn = MagicMock()
        conn.info.server_version = 170000
        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.getconn.return_value = conn
        pool._pools[key] = mock_pool

        sem_before = pool._budget.available
        with self.assertRaises(PoolError):
            pool.borrow(info)
        mock_pool.putconn.assert_called_once_with(conn)
        self.assertEqual(
            pool._budget.available,
            sem_before,
            "semaphore leaked when borrow() rejected a connection in validation",
        )


class TestCursorInitCursorFailureReturnsConnection(BaseCase):
    def test_cursor_failure_propagates_real_error_and_returns_connection(self):
        sentinel = psycopg.OperationalError("simulated cursor() failure")
        conn = MagicMock()
        conn.closed = False
        conn.cursor.side_effect = sentinel
        pool = MagicMock()
        pool.readonly = False
        pool.borrow.return_value = conn

        with self.assertRaises(psycopg.OperationalError) as cm:
            Cursor(pool, "somedb", {"dbname": "somedb"})

        self.assertIs(
            cm.exception,
            sentinel,
            "Cursor.__init__ masked the real cursor() failure with a different "
            "exception (the __getattr__-via-getattr regression)",
        )
        pool.give_back.assert_called_once()
        (returned,), kwargs = pool.give_back.call_args
        self.assertIs(returned, conn)
        self.assertIn(
            "keep_in_pool",
            kwargs,
            "the construction guard decides poolability the way _close does: "
            "a constructor that raised after a statement leaves a failed "
            "transaction behind",
        )

    def test_a_clean_connection_is_still_pooled(self):
        conn = MagicMock()
        conn.closed = False
        conn.info.transaction_status = _TX_IDLE
        conn.cursor.side_effect = psycopg.OperationalError("simulated")
        pool = MagicMock()
        pool.readonly = False
        pool.borrow.return_value = conn

        with self.assertRaises(psycopg.OperationalError):
            Cursor(pool, "somedb", {"dbname": "somedb"})

        self.assertTrue(
            pool.give_back.call_args.kwargs["keep_in_pool"],
            "nothing ran on this connection, so discarding it would throw away "
            "a warm backend for an error that never touched it",
        )

    def test_a_damaged_connection_is_discarded(self):
        conn = MagicMock()
        conn.closed = False
        conn.info.transaction_status = _TxStatus.INERROR
        conn.cursor.side_effect = psycopg.OperationalError("simulated")
        pool = MagicMock()
        pool.readonly = False
        pool.borrow.return_value = conn

        with self.assertRaises(psycopg.OperationalError):
            Cursor(pool, "somedb", {"dbname": "somedb"})

        self.assertFalse(pool.give_back.call_args.kwargs["keep_in_pool"])


class TestPasswordRotationEvictsStalePool(BaseCase):
    @staticmethod
    def _pool_factory():
        def factory(*args, **kwargs):
            m = MagicMock()
            m.closed = False
            return m

        return factory

    def test_rotation_evicts_and_closes_old_pool(self):
        pool = ConnectionPool(maxconn=4)
        pool._probe.probe_connectable = lambda *a, **k: None
        base = {"dbname": "rotdb", "host": "h", "user": "u"}
        info_old = {**base, "password": "old"}
        info_new = {**base, "password": "new"}
        k_old = _get_dsn_key(info_old)
        k_new = _get_dsn_key(info_new)
        with patch("odoo.db.pool._PsycopgPool") as PP:
            PP.side_effect = self._pool_factory()
            old_pool = pool._get_or_create_pool(k_old, info_old)
            pool._get_or_create_pool(k_new, info_new)

        self.assertNotIn(k_old, pool._pools, "old-password pool was not evicted")
        self.assertIn(k_new, pool._pools)
        old_pool.close.assert_called_once()

    def test_different_user_pool_is_preserved(self):
        pool = ConnectionPool(maxconn=4)
        pool._probe.probe_connectable = lambda *a, **k: None
        base = {"dbname": "rotdb", "host": "h", "password": "p"}
        info_u1 = {**base, "user": "u1"}
        info_u2 = {**base, "user": "u2"}
        k1 = _get_dsn_key(info_u1)
        k2 = _get_dsn_key(info_u2)
        with patch("odoo.db.pool._PsycopgPool") as PP:
            PP.side_effect = self._pool_factory()
            pool._get_or_create_pool(k1, info_u1)
            pool._get_or_create_pool(k2, info_u2)

        self.assertIn(k1, pool._pools, "different-user pool must NOT be evicted")
        self.assertIn(k2, pool._pools)


class TestCopyFromRecoverableErrorLogLevel(BaseCase):
    def setUp(self):
        super().setUp()
        with registry().cursor() as cr:
            cr.execute("DROP TABLE IF EXISTS _cf_lock")
            cr.execute("CREATE TABLE _cf_lock (v int)")
            cr.commit()
        self.addCleanup(self._drop)

    def _drop(self):
        with registry().cursor() as cr:
            cr.execute("DROP TABLE IF EXISTS _cf_lock")
            cr.commit()

    def test_copy_from_lock_timeout_logged_as_warning_not_error(self):
        with registry().cursor() as cr_lock:
            cr_lock.execute("LOCK TABLE _cf_lock IN ACCESS EXCLUSIVE MODE")
            with self.assertLogs("odoo.db.cursor", level="WARNING") as cm:
                with self.assertRaises(psycopg.errors.LockNotAvailable):
                    with registry().cursor() as cr_copy:
                        cr_copy.execute("SET lock_timeout = '250ms'")
                        cr_copy.copy_from("_cf_lock", ["v"], [(1,), (2,)])
        levels = {r.levelname for r in cm.records}
        self.assertIn("WARNING", levels)
        self.assertNotIn(
            "ERROR",
            levels,
            "recoverable COPY error logged at ERROR — copy_from regressed to "
            "its old hand-rolled _logger.error path",
        )
        self.assertTrue(
            any("recoverable SQL error" in r.getMessage() for r in cm.records)
        )


class TestConcurrencyErrorTaxonomy(BaseCase):
    def test_sqlstates_match_exception_classes(self):
        from odoo.db.errors import PG_RETRY_EXCEPTIONS, PG_RETRY_SQLSTATES

        self.assertEqual(
            tuple(exc.sqlstate for exc in PG_RETRY_EXCEPTIONS),
            PG_RETRY_SQLSTATES,
        )

    def test_recoverable_is_retryable_plus_read_only(self):
        from odoo.db.errors import PG_RECOVERABLE_EXCEPTIONS, PG_RETRY_EXCEPTIONS

        extra = set(PG_RECOVERABLE_EXCEPTIONS) - set(PG_RETRY_EXCEPTIONS)
        self.assertEqual(extra, {psycopg.errors.ReadOnlySqlTransaction})

    def test_public_aliases_are_the_canonical_objects(self):
        from odoo.db import errors as db_errors
        from odoo.service import transaction as svc

        self.assertIs(
            svc.PG_CONCURRENCY_EXCEPTIONS_TO_RETRY, db_errors.PG_RETRY_EXCEPTIONS
        )
        self.assertIs(svc.PG_CONCURRENCY_ERRORS_TO_RETRY, db_errors.PG_RETRY_SQLSTATES)


class TestExecutemanyLogExceptions(BaseCase):
    def test_log_exceptions_false_suppresses_error_log(self):
        with self.assertNoLogs("odoo.db.cursor", level="ERROR"):
            with self.assertRaises(psycopg.Error):
                with registry().cursor() as cr:
                    cr.executemany(
                        "INSERT INTO _no_such_table_xyz (v) VALUES (%s)",
                        [(1,)],
                        log_exceptions=False,
                    )

    def test_default_still_logs_error(self):
        with self.assertLogs("odoo.db.cursor", level="ERROR") as cm:
            with self.assertRaises(psycopg.Error):
                with registry().cursor() as cr:
                    cr.executemany(
                        "INSERT INTO _no_such_table_xyz (v) VALUES (%s)",
                        [(1,)],
                    )
        self.assertTrue(any("bad query" in r.getMessage() for r in cm.records))


class TestDictFetchManyNegativeSize(BaseCase):
    def test_negative_size_returns_empty_and_preserves_rows(self):
        with registry().cursor() as cr:
            cr.execute("SELECT generate_series(1, 3) AS v")
            self.assertEqual(cr.dictfetchmany(-1), [])
            self.assertEqual(len(cr.dictfetchmany(3)), 3)

    def test_zero_and_oversize_unchanged(self):
        with registry().cursor() as cr:
            cr.execute("SELECT generate_series(1, 3) AS v")
            self.assertEqual(cr.dictfetchmany(0), [])
            self.assertEqual(len(cr.dictfetchmany(10)), 3)


class TestPoolCleanupIsolatesFailures(BaseCase):
    class _FakePool:
        def __init__(self, name, raises=False):
            self.name = name
            self.raises = raises
            self.close_called = False
            self.drain_called = False
            self.closed = False

        def close(self):
            self.close_called = True
            if self.raises:
                raise RuntimeError(f"{self.name}: simulated close failure")

        def drain(self):
            self.drain_called = True
            if self.raises:
                raise RuntimeError(f"{self.name}: simulated drain failure")

        def get_stats(self):
            return {}

    def _make_pool_with(self, *fakes):
        cp = ConnectionPool(maxconn=8)
        cp._pools = {frozenset([("dbname", fp.name)]): fp for fp in fakes}
        return cp

    def test_close_all_closes_survivors_despite_failure(self):
        a = self._FakePool("A", raises=True)
        b = self._FakePool("B")
        c = self._FakePool("C")
        cp = self._make_pool_with(a, b, c)
        cp.close_all()
        self.assertTrue(a.close_called and b.close_called and c.close_called)
        self.assertEqual(cp._pools, {})

    def test_close_database_closes_survivors_despite_failure(self):
        a = self._FakePool("db", raises=True)
        b = self._FakePool("db")
        cp = ConnectionPool(maxconn=8)
        cp._pools = {
            frozenset([("dbname", "db"), ("host", "h1")]): a,
            frozenset([("dbname", "db"), ("host", "h2")]): b,
        }
        cp.close_database("db")
        self.assertTrue(a.close_called and b.close_called)
        self.assertEqual(cp._pools, {})

    def test_drain_drains_survivors_despite_failure(self):
        a = self._FakePool("A", raises=True)
        b = self._FakePool("B")
        cp = self._make_pool_with(a, b)
        cp.drain_all()
        self.assertTrue(a.drain_called and b.drain_called)

    def test_drain_database_drains_survivors_despite_failure(self):
        a = self._FakePool("db", raises=True)
        b = self._FakePool("db")
        cp = ConnectionPool(maxconn=8)
        cp._pools = {
            frozenset([("dbname", "db"), ("host", "h1")]): a,
            frozenset([("dbname", "db"), ("host", "h2")]): b,
        }
        cp.drain_database("db")
        self.assertTrue(a.drain_called and b.drain_called)


class TestDdlCacheInvalidationNarrowed(BaseCase):
    def test_comment_grant_keep_cache_alter_clears_it(self):
        tbl = "_test_ddl_narrow"
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute(f"CREATE TABLE {tbl} (x int)")
            cr.copy_from(tbl, ["x"], [(1,)], binary=True)
            self.assertEqual(
                cr._schema_cache.get_column_types(tbl, ["x"]),
                [INT4_OID],
                "binary copy_from should have cached the column type",
            )
            cr.execute(f"COMMENT ON TABLE {tbl} IS %s", ("narrowing test",))
            self.assertEqual(
                cr._schema_cache.get_column_types(tbl, ["x"]),
                [INT4_OID],
                "COMMENT (non-schema-changing DDL) must not clear the cache",
            )
            cr.execute(f"REVOKE ALL ON TABLE {tbl} FROM PUBLIC")
            self.assertEqual(
                cr._schema_cache.get_column_types(tbl, ["x"]),
                [INT4_OID],
                "REVOKE (non-schema-changing DDL) must not clear the cache",
            )
            cr.execute(f"ALTER TABLE {tbl} ALTER COLUMN x TYPE bigint")
            self.assertIsNone(
                cr._schema_cache.get_column_types(tbl, ["x"]),
                "ALTER (schema-changing DDL) must clear the cache",
            )
        finally:
            cr.rollback()
            cr.close()


class TestDdlParamInliningInjectionLive(BaseCase):
    def test_injection_values_roundtrip_exact_and_do_not_execute(self):
        tbl = "_test_ddl_injection"
        payloads = [
            "'; DROP TABLE " + tbl + "; --",
            "x' OR '1'='1",
            "a\\'; DELETE FROM pg_class; --",
            "%s and %(x)s literal markers",
            "tab\tand\nnewline",
            "back\\slash and 100% percent",
            "unicode ☃ snowman",
        ]
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute(f"CREATE TABLE {tbl} (x int)")
            for payload in payloads:
                cr.execute(f"COMMENT ON TABLE {tbl} IS %s", (payload,))
                cr.execute("SELECT obj_description(%s::regclass, 'pg_class')", (tbl,))
                self.assertEqual(
                    cr.fetchone()[0],
                    payload,
                    "positional DDL param must round-trip byte-exact, not inject",
                )
                cr.execute(f"COMMENT ON TABLE {tbl} IS %(c)s", {"c": payload})
                cr.execute("SELECT obj_description(%s::regclass, 'pg_class')", (tbl,))
                self.assertEqual(
                    cr.fetchone()[0],
                    payload,
                    "named DDL param must round-trip byte-exact, not inject",
                )
            cr.execute("SELECT to_regclass(%s) IS NOT NULL", (tbl,))
            self.assertTrue(
                cr.fetchone()[0],
                "an injection payload executed as SQL — client-side quoting failed",
            )
        finally:
            cr.rollback()
            cr.close()


class TestDdlInvalidatesPreparedPlan(BaseCase):
    def test_alter_after_prepared_select_star_does_not_raise(self):
        tbl = "_test_prepared_plan"
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute(f"DROP TABLE IF EXISTS {tbl}")
            cr.execute(f"CREATE TABLE {tbl} (a int)")
            cr.execute(f"INSERT INTO {tbl} VALUES (1)")
            for _ in range(5):
                cr.execute(f"SELECT * FROM {tbl}")
                cr.fetchall()
            cr.execute(f"ALTER TABLE {tbl} ADD COLUMN b int")
            try:
                cr.execute(f"SELECT * FROM {tbl}")
                rows = cr.fetchall()
            except psycopg.errors.FeatureNotSupported as e:
                self.fail(
                    "prepared-statement cache not invalidated after schema-"
                    f"changing DDL: {e}"
                )
            self.assertEqual(rows, [(1, None)])
        finally:
            cr.rollback()
            cr.close()

    def test_alter_hidden_behind_a_leading_non_ddl_statement(self):
        tbl = "_test_hidden_ddl"
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute(f"DROP TABLE IF EXISTS {tbl}")
            cr.execute(f"CREATE TABLE {tbl} (a int)")
            cr.execute(f"INSERT INTO {tbl} VALUES (1)")
            cr.commit()
            for _ in range(5):
                cr.execute(f"SELECT * FROM {tbl}")
                cr.fetchall()
            cr.execute(f"BEGIN; ALTER TABLE {tbl} ADD COLUMN b int; COMMIT")
            try:
                cr.execute(f"SELECT * FROM {tbl}")
                rows = cr.fetchall()
            except psycopg.errors.FeatureNotSupported as e:
                self.fail(f"cache not invalidated for non-leading DDL: {e}")
            self.assertEqual(rows, [(1, None)])
        finally:
            with contextlib.suppress(Exception):
                cr.rollback()
                cr.execute(f"DROP TABLE IF EXISTS {tbl}")
                cr.commit()
            cr.close()


class TestEvaluatedCodeKeepsItsDatabaseErrorClass(common.TransactionCase):
    def _duplicate_xmlid_action(self):
        model = self.env["ir.model"].search([("model", "=", "res.partner")], limit=1)
        return self.env["ir.actions.server"].create(
            {
                "name": "duplicate xmlid",
                "model_id": model.id,
                "state": "code",
                "code": (
                    "env['ir.model.data'].create({'module':'_t','name':'dup',"
                    "'model':'res.partner','res_id':1})\n"
                    "env.cr.flush()\n"
                    "env['ir.model.data'].create({'module':'_t','name':'dup',"
                    "'model':'res.partner','res_id':1})\n"
                    "env.cr.flush()\n"
                ),
            }
        )

    def test_a_constraint_violated_by_a_server_action_keeps_its_class(self):
        action = self._duplicate_xmlid_action()
        with (
            self.assertRaises(psycopg.IntegrityError) as caught,
            mute_logger("odoo.db.cursor", "odoo.db.cursor"),
            self.env.cr.savepoint(flush=False),
        ):
            action.run()
        self.assertNotIsInstance(
            caught.exception,
            ValueError,
            "a wrapped IntegrityError never reaches retrying()'s "
            "IntegrityError -> ValidationError translation, so the user sees "
            "the raw psycopg repr instead of a message. Measured end to end "
            "before this fix: ValueError: UniqueViolation(...) while "
            "evaluating; after: ValidationError: The operation cannot be "
            "completed: duplicate key value violates unique constraint ...",
        )

    def test_safe_eval_consults_the_taxonomy(self):
        from odoo.db import errors as db_errors
        from odoo.tools.safe_eval import _is_classified_db_error

        for cls in (
            *db_errors.PG_RECOVERABLE_EXCEPTIONS,
            *db_errors.PG_STALE_PLAN_EXCEPTIONS,
            *db_errors.PG_USER_FAULT_EXCEPTIONS,
        ):
            with self.subTest(cls=cls.__name__):
                self.assertTrue(_is_classified_db_error(cls("boom")))

    def test_an_unclassified_database_error_is_still_wrapped(self):
        from odoo.tools.safe_eval import _is_classified_db_error

        self.assertFalse(
            _is_classified_db_error(psycopg.errors.UndefinedTable("x")),
            "an UndefinedTable in a server action is a bug in the action, not a "
            "condition the framework recovers from",
        )


class TestCronsRecoverLikeRequests(BaseCase):
    ACTION = "_run_server_action"

    def test_the_callback_goes_through_retrying(self):
        cls = registry()["ir.cron"]
        self.assertIn(
            "retrying",
            _calls(cls._run_server_action_with_retry),
            "without it a deadlock, a serialization failure or a stale cached "
            "plan counts against the cron's deactivation budget",
        )

    def test_the_run_loop_reaches_the_wrapped_runner(self):
        methods = _own_methods(registry()["ir.cron"])
        self.assertIn(
            "_run_server_action_with_retry",
            _reachable("_run_job", methods),
            "the run loop must reach the wrapped runner",
        )
        self.assertIn(
            "_run_job_within_budget",
            _reachable("_run_job", methods),
            "the run loop must go through the budgeted runner",
        )

    def test_nothing_reaches_the_action_except_the_wrapped_runner(self):
        methods = _own_methods(registry()["ir.cron"])
        callers = {name for name, calls in methods.items() if self.ACTION in calls} - {
            self.ACTION
        }
        self.assertEqual(
            callers,
            {"_run_server_action_with_retry"},
            f"{self.ACTION} must be invoked only from the runner wrapped in "
            f"retrying(); these call it too",
        )

    def _drive_callback(self, callback):
        from odoo.addons.base.tests.test_ir_cron import make_job

        reg = registry()
        with contextlib.closing(reg.cursor()) as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            cron = env["ir.cron"].search([], limit=1)
            self.assertTrue(cron, "base installs crons; one is needed to drive")
            cls = type(cron)
            with patch.object(cls, self.ACTION, callback):
                cls._run_server_action_with_retry(
                    cron,
                    make_job(cron, cron_name="probe", ir_actions_server_id=0),
                    env,
                )

    def test_a_recoverable_failure_is_replayed_not_charged(self):
        calls = {"n": 0}

        def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] <= 2:
                raise psycopg.errors.SerializationFailure("injected")

        self._drive_callback(flaky)
        self.assertEqual(
            calls["n"],
            3,
            "two recoverable failures must be replayed, not charged to the job",
        )

    def test_a_permanent_failure_still_escapes(self):
        def broken(*args, **kwargs):
            raise ValueError("permanently broken")

        with self.assertRaises(ValueError):
            self._drive_callback(broken)

    def test_a_recoverable_error_is_in_the_retry_taxonomy(self):
        from odoo.db.errors import PG_RETRY_EXCEPTIONS, PG_STALE_PLAN_EXCEPTIONS

        self.assertTrue(PG_RETRY_EXCEPTIONS)
        self.assertTrue(PG_STALE_PLAN_EXCEPTIONS)

    def test_deactivation_is_still_reachable_for_a_genuinely_broken_cron(self):
        from odoo.addons.base.models.ir_cron import (
            MIN_FAILURE_COUNT_BEFORE_DEACTIVATION,
        )

        self.assertGreater(
            MIN_FAILURE_COUNT_BEFORE_DEACTIVATION,
            0,
            "retrying recoverable errors must not remove the ability to "
            "deactivate a cron that is actually broken",
        )


class TestCopyEncodingsAgree(BaseCase):
    COLUMNS = (
        ("i", "int4"),
        ("f", "float8"),
        ("n", "numeric"),
        ("t", "text"),
        ("d", "date"),
        ("j", "jsonb"),
        ("ar", "int4[]"),
    )

    def _rows(self):
        import datetime
        import decimal

        return [
            [
                1,
                0.5,
                decimal.Decimal("1.25"),
                "x",
                datetime.date(2026, 1, 1),
                '{"en_US": "a"}',
                [1, 2],
            ],
            [-1, -0.0, decimal.Decimal(0), "", datetime.date(1, 1, 1), "{}", []],
            [None, None, None, None, None, None, None],
            [
                2,
                1e300,
                decimal.Decimal("-9.87"),
                "\u00fcn\u00efc\u00f8d\u00e9",
                datetime.date(9999, 12, 31),
                '"scalar"',
                [0],
            ],
        ]

    def _load(self, cr, table, binary):
        ddl = ", ".join(f'"{c}" {t}' for c, t in self.COLUMNS)
        cr.execute(f"DROP TABLE IF EXISTS {table}")
        cr.execute(f"CREATE TABLE {table} (id serial primary key, {ddl})")
        cr.copy_from(table, [c for c, _ in self.COLUMNS], self._rows(), binary=binary)

    def test_binary_and_text_write_identical_rows(self):
        cr = db_connect(common.get_db_name()).cursor()
        names = ", ".join(f'"{c}"' for c, _ in self.COLUMNS)
        try:
            self._load(cr, "_t_copy_bin", True)
            self._load(cr, "_t_copy_txt", False)
            for a, b in (
                ("_t_copy_bin", "_t_copy_txt"),
                ("_t_copy_txt", "_t_copy_bin"),
            ):
                cr.execute(
                    f"SELECT count(*) FROM ("
                    f"  SELECT {names} FROM {a} EXCEPT SELECT {names} FROM {b}) d"
                )
                self.assertEqual(
                    cr.fetchone()[0],
                    0,
                    f"rows in {a} that are not in {b}: binary=True is documented "
                    f"as a hint, so the two encodings must agree",
                )
        finally:
            cr.rollback()
            cr.close()

    def test_a_json_string_is_stored_as_a_document_under_both(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            for binary in (True, False):
                with self.subTest(binary=binary):
                    cr.execute("DROP TABLE IF EXISTS _t_json")
                    cr.execute("CREATE TABLE _t_json (id serial primary key, j jsonb)")
                    cr.copy_from("_t_json", ["j"], [['{"a": 1}']], binary=binary)
                    cr.execute("SELECT jsonb_typeof(j), j->>'a' FROM _t_json")
                    kind, a = cr.fetchone()
                    self.assertEqual(
                        (kind, a),
                        ("object", "1"),
                        "a JSON document passed as text must be parsed, not "
                        "re-encoded as a JSON string value",
                    )
        finally:
            cr.rollback()
            cr.close()

    def test_a_caller_wrapped_value_is_untouched(self):
        from psycopg.types.json import Json, Jsonb

        cr = db_connect(common.get_db_name()).cursor()
        try:
            for binary in (True, False):
                for wrapper in (Json, Jsonb):
                    with self.subTest(binary=binary, wrapper=wrapper.__name__):
                        cr.execute("DROP TABLE IF EXISTS _t_json2")
                        cr.execute(
                            "CREATE TABLE _t_json2 (id serial primary key, j jsonb)"
                        )
                        cr.copy_from(
                            "_t_json2",
                            ["j"],
                            [[wrapper({"en_US": "hi"})]],
                            binary=binary,
                        )
                        cr.execute("SELECT j->>'en_US' FROM _t_json2")
                        self.assertEqual(cr.fetchone()[0], "hi")
        finally:
            cr.rollback()
            cr.close()

    def test_the_json_oids_are_the_real_ones(self):
        from odoo.db.bulk import _JSON_OIDS

        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute("SELECT oid FROM pg_type WHERE typname IN ('json', 'jsonb')")
            self.assertEqual({r[0] for r in cr.fetchall()}, set(_JSON_OIDS))
        finally:
            cr.close()

    def test_binary_is_still_chosen_for_a_json_column(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute("DROP TABLE IF EXISTS _t_json3")
            cr.execute("CREATE TABLE _t_json3 (id serial primary key, a int, j jsonb)")
            oids = cr._get_column_type_oids("_t_json3", ["a", "j"])
            self.assertTrue(
                cr._is_binary_copy_worthwhile(oids),
                "a JSON column must not disqualify binary COPY on its own",
            )
        finally:
            cr.rollback()
            cr.close()


class TestFailedStatementsAreCounted(BaseCase):
    def _cr(self):
        cr = db_connect(common.get_db_name()).cursor()
        cr.execute("DROP TABLE IF EXISTS _test_count CASCADE")
        cr.execute("CREATE TABLE _test_count (a int UNIQUE)")
        cr.execute("INSERT INTO _test_count VALUES (1)")
        cr.commit()
        return cr

    def _delta(self, cr, fn):
        before, before_global = cr.sql_log_count, odoo.db.sql_counter  # noqa: E8516  asserts the row counter itself
        with contextlib.suppress(Exception):
            fn()
        delta = (cr.sql_log_count - before, odoo.db.sql_counter - before_global)  # noqa: E8516  asserts the row counter itself
        with contextlib.suppress(Exception):
            cr.rollback()
        return delta

    def test_a_successful_statement_counts_one(self):
        cr = self._cr()
        try:
            self.assertEqual(self._delta(cr, lambda: cr.execute("SELECT 1")), (1, 1))
        finally:
            cr.rollback()
            cr.close()

    def test_server_side_failures_count(self):
        cr = self._cr()
        try:
            for label, stmt in (
                ("syntax error", "SELEKT 1"),
                ("undefined table", "SELECT * FROM _no_such_table_xyz"),
                ("unique violation", "INSERT INTO _test_count VALUES (1)"),
            ):
                with self.subTest(case=label):
                    self.assertEqual(
                        self._delta(
                            cr, lambda s=stmt: cr.execute(s, log_exceptions=False)
                        ),
                        (1, 1),
                        f"a {label} reached the server and cost a round trip",
                    )
        finally:
            cr.rollback()
            cr.close()

    def test_a_failing_executemany_counts_its_rows(self):
        cr = self._cr()
        try:
            self.assertEqual(
                self._delta(
                    cr,
                    lambda: cr.executemany(
                        "INSERT INTO _test_count VALUES (%s)",
                        [(1,), (1,)],
                        log_exceptions=False,
                    ),
                ),
                (2, 2),
            )
        finally:
            cr.rollback()
            cr.close()

    def test_client_side_rejections_still_count_zero(self):
        cr = self._cr()
        try:
            self.assertEqual(
                self._delta(
                    cr,
                    lambda: cr.execute("SELECT %s, %s", (1,), log_exceptions=False),
                ),
                (0, 0),
                "psycopg raises before anything reaches the wire; counting it "
                "would inflate every query budget",
            )
        finally:
            cr.rollback()
            cr.close()

    def test_a_failing_copy_from_counts_like_a_failing_execute(self):
        cr = self._cr()
        try:
            self.assertEqual(
                self._delta(
                    cr,
                    lambda: cr.copy_from(
                        "_test_count", ["a"], [(1,)], log_exceptions=False
                    ),
                ),
                (1, 1),
                "copy_from carried its own copy of the metrics envelope and "
                "that copy recorded nothing when the COPY failed, so a bulk "
                "insert that violated a constraint cost a round trip nobody "
                "was charged for",
            )
        finally:
            cr.rollback()
            cr.close()

    def test_a_failing_copy_is_logged_like_every_other_statement(self):
        cr = self._cr()
        try:
            with (
                self.assertLogs("odoo.db.cursor", level="ERROR") as cm,
                self.assertRaises(Exception),
                cr.copy("COPY _test_count (a) FROM STDIN") as cp,
            ):
                cp.write("not-an-integer\n")
            self.assertTrue(
                any("bad COPY" in r.getMessage() for r in cm.records),
                "cr.copy() had no except clause at all, so a failed COPY was "
                "the one statement failure this layer never reported",
            )
        finally:
            cr.rollback()
            cr.close()

    def test_copy_times_the_transfer_and_not_the_context_manager(self):
        cr = self._cr()
        try:
            cr.execute("CREATE TEMP TABLE _t_copy_timing (a int)")
            seen = []
            thread = threading.current_thread()
            thread.query_hooks = [lambda _c, _q, _p, _s, delay: seen.append(delay)]
            try:
                t0 = time.monotonic()
                with cr.copy("COPY _t_copy_timing (a) FROM STDIN") as cp:
                    for i in range(20000):
                        cp.write(f"{i}\n")
                wall = time.monotonic() - t0
            finally:
                del thread.query_hooks
            self.assertEqual(len(seen), 1)
            self.assertGreater(
                seen[0],
                wall / 2,
                "psycopg's Cursor.copy is a @contextmanager, so timing the "
                "call that builds it measured nothing: 200k rows took 120 ms "
                "and were reported as 0.008 ms",
            )
        finally:
            cr.rollback()
            cr.close()

    def test_copy_is_counted_like_every_other_statement_entry_point(self):
        cr = self._cr()
        try:
            before = cr.sql_log_count  # noqa: E8516  asserts the row counter itself
            with cr.copy("COPY _test_count (a) FROM STDIN") as cp:
                cp.write("7\n8\n")
            self.assertEqual(
                cr.sql_log_count - before,  # noqa: E8516  asserts the row counter itself
                1,
                "cr.copy() was the one marked statement entry point invisible "
                "to query counting",
            )
        finally:
            cr.rollback()
            cr.close()


class TestStaleCachedPlanIsRecoverable(BaseCase):
    def _stale_plan(self, cr_a, cr_b, tbl):
        cr_a.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cr_a.execute(f"CREATE TABLE {tbl} (id serial primary key, a int)")
        cr_a.execute(f"INSERT INTO {tbl} (a) VALUES (1)")
        cr_a.commit()
        for _ in range(6):
            cr_b.execute(f"SELECT id, a FROM {tbl}")
            cr_b.fetchall()
        cr_b.commit()
        cr_a.execute(f"ALTER TABLE {tbl} ALTER COLUMN a TYPE bigint")
        cr_a.commit()

    def test_the_cursor_marks_it_and_a_replay_then_succeeds(self):
        from odoo.db.errors import is_stale_cached_plan

        db_name = common.get_db_name()
        a, b = db_connect(db_name).cursor(), db_connect(db_name).cursor()
        tbl = "_test_stale_plan"
        try:
            self.assertIsNot(a._cnx, b._cnx)
            self._stale_plan(a, b, tbl)
            for _attempt in range(8):
                try:
                    b.execute(f"SELECT id, a FROM {tbl}", log_exceptions=False)
                    b.fetchall()
                except psycopg.errors.FeatureNotSupported as exc:
                    self.assertTrue(
                        is_stale_cached_plan(exc),
                        "the cursor must name this as a stale plan; nothing "
                        "downstream can tell it from a permanent 0A000",
                    )
                    b.rollback()
                    b.execute(f"SELECT id, a FROM {tbl}")
                    self.assertEqual(b.fetchall(), [(1, 1)], "the replay must work")
                    break
                b.commit()
            else:
                self.skipTest("no borrow drew the poisoned backend in 8 attempts")
        finally:
            with contextlib.suppress(Exception):
                b.rollback()
                b.close()
            with contextlib.suppress(Exception):
                a.execute(f"DROP TABLE IF EXISTS {tbl}")
                a.commit()
                a.close()

    def test_a_permanent_0A000_is_not_marked(self):
        from odoo.db.errors import is_stale_cached_plan

        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute("DROP TABLE IF EXISTS _test_perm CASCADE")
            cr.execute("CREATE TABLE _test_perm (a int)")
            cr.execute("CREATE VIEW _test_perm_v AS SELECT a FROM _test_perm")
            for _ in range(3):
                cr.execute("SELECT a FROM _test_perm")
                cr.fetchall()
            self.assertTrue(
                cr._cnx._prepared._names,
                "the cache must be warm or this test asserts nothing",
            )
            with self.assertRaises(psycopg.errors.FeatureNotSupported) as caught:
                cr.execute(
                    "ALTER TABLE _test_perm ALTER COLUMN a TYPE bigint",
                    log_exceptions=False,
                )
            self.assertFalse(
                is_stale_cached_plan(caught.exception),
                "a column-used-by-a-view failure is permanent; marking it "
                "would spend the whole retry budget on a request that can "
                "never succeed",
            )
            self.assertTrue(
                cr._cnx._prepared._names,
                "and it must not discard the connection's prepared statements "
                "either: nothing about this failure invalidates them",
            )
        finally:
            cr.rollback()
            cr.close()

    def test_retrying_catches_the_family_and_retries_on_the_marker(self):
        from odoo.db.errors import PG_STALE_PLAN_EXCEPTIONS, mark_stale_cached_plan
        from odoo.service.transaction import (
            _RECOVERY_EXCEPTIONS,
            _resolve_retry_error_name,
        )

        for cls in PG_STALE_PLAN_EXCEPTIONS:
            self.assertTrue(
                issubclass(cls, _RECOVERY_EXCEPTIONS),
                f"{cls.__name__} is not an OperationalError; the except clause "
                "must name the family or the retry loop never sees it",
            )
            exc = cls("cached plan must not change result type")
            self.assertIsNone(_resolve_retry_error_name(exc))
            mark_stale_cached_plan(exc)
            self.assertEqual(_resolve_retry_error_name(exc), "StaleCachedPlan")

    def test_a_marked_exception_is_not_blanket_retryable_by_sqlstate(self):
        from odoo.db.errors import PG_RETRY_SQLSTATES, PG_STALE_PLAN_EXCEPTIONS

        for cls in PG_STALE_PLAN_EXCEPTIONS:
            self.assertNotIn(cls.sqlstate, PG_RETRY_SQLSTATES)


class TestDropDependingViewsQuoting(BaseCase):
    def test_it_drops_a_normally_named_dependent_view(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute("DROP TABLE IF EXISTS _test_dv CASCADE")
            cr.execute("CREATE TABLE _test_dv (id serial primary key, a int)")
            cr.execute("CREATE VIEW _test_dv_view AS SELECT a FROM _test_dv")
            self.assertEqual(
                [
                    v
                    for v, _ in sql_schema.get_views_depending_on_table(
                        cr, "_test_dv", "a"
                    )
                ],
                ["_test_dv_view"],
            )
            sql_schema.drop_views_depending_on_table(cr, "_test_dv", "a")
            self.assertEqual(
                sql_schema.get_views_depending_on_table(cr, "_test_dv", "a"), []
            )
        finally:
            cr.rollback()
            cr.close()

    def test_it_uses_the_house_identifier_helper(self):
        src = inspect.getsource(sql_schema.drop_views_depending_on_table)
        self.assertIn("SQL.identifier", src)
        self.assertNotIn(
            "replace(",
            src,
            "hand-rolled identifier quoting is back; it bypasses "
            "SQL.identifier's validation and feeds raw text to the "
            "parameter layer",
        )

    def test_a_view_name_that_is_not_an_identifier_is_named_in_the_error(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute("DROP TABLE IF EXISTS _test_dv2 CASCADE")
            cr.execute("CREATE TABLE _test_dv2 (id serial primary key, a int)")
            cr.execute('CREATE VIEW "v%s_dep" AS SELECT a FROM _test_dv2')
            with self.assertRaises(ValueError) as caught:
                sql_schema.drop_views_depending_on_table(cr, "_test_dv2", "a")
            self.assertIn("v%s_dep", str(caught.exception))
        finally:
            cr.rollback()
            cr.close()


class TestCreateModelTableAndConstraintColumns(BaseCase):
    def setUp(self):
        super().setUp()
        self.cr = db_connect(common.get_db_name()).cursor()
        self.addCleanup(self.cr.close)
        self.addCleanup(self.cr.rollback)
        self.cr.execute("DROP TABLE IF EXISTS _test_mt CASCADE")

    def test_create_model_table_makes_the_shape_auto_init_expects(self):
        sql_schema.create_model_table(
            self.cr,
            "_test_mt",
            comment="A model",
            columns=[("name", "varchar", "The name"), ("qty", "int4", "How many")],
        )
        self.assertEqual(
            sorted(sql_schema.get_table_columns(self.cr, "_test_mt")),
            ["id", "name", "qty"],
        )
        self.cr.execute(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = '_test_mt' AND column_name = 'id'"
        )
        self.assertIn(
            "nextval",
            self.cr.fetchscalar() or "",
            "id must be SERIAL: copy_from's returning_ids pre-allocates from "
            "that sequence",
        )
        self.cr.execute(
            "SELECT a.attname FROM pg_constraint c "
            "JOIN pg_attribute a ON a.attrelid = c.conrelid "
            "AND a.attnum = ANY(c.conkey) "
            "WHERE c.conrelid = '_test_mt'::regclass AND c.contype = 'p'"
        )
        self.assertEqual(self.cr.fetchscalar(), "id")
        self.cr.execute("SELECT obj_description('_test_mt'::regclass)")
        self.assertEqual(self.cr.fetchscalar(), "A model")

    def test_constraint_columns_needs_the_catalog_for_a_composite_key(self):
        sql_schema.create_model_table(
            self.cr, "_test_mt", columns=[("name", "varchar", ""), ("qty", "int4", "")]
        )
        self.cr.execute(
            "ALTER TABLE _test_mt ADD CONSTRAINT _test_mt_uq UNIQUE (name, qty)"
        )
        self.cr.execute("INSERT INTO _test_mt (name, qty) VALUES ('a', 1)")
        with (
            self.assertRaises(psycopg.errors.UniqueViolation) as caught,
            self.cr.savepoint(flush=False),
        ):
            self.cr.execute(
                "INSERT INTO _test_mt (name, qty) VALUES ('a', 1)",
                log_exceptions=False,
            )
        diag = caught.exception.diag
        self.assertIsNone(
            diag.column_name,
            "PostgreSQL names no single column for a composite constraint, "
            "which is the whole reason check_catalog exists",
        )
        self.assertEqual(sql_schema.get_column_names_in_constraint(self.cr, diag), [])
        self.assertEqual(
            sql_schema.get_column_names_in_constraint(
                self.cr, diag, check_catalog=True
            ),
            ["name", "qty"],
            "only the catalog lookup can tell the user which fields clashed",
        )


class TestSchemaCapabilityProbesAndDropIndex(BaseCase):
    def setUp(self):
        super().setUp()
        self.cr = db_connect(common.get_db_name()).cursor()
        self.addCleanup(self.cr.close)
        self.addCleanup(self.cr.rollback)

    def _catalog_has(self, proname):
        self.cr.execute(
            "SELECT count(*) FROM pg_proc WHERE proname = %s "
            "AND pronamespace = current_schema::regnamespace",
            (proname,),
        )
        return bool(self.cr.fetchscalar())

    def test_has_trigram_agrees_with_the_catalog(self):
        self.assertEqual(
            sql_schema.has_trigram(self.cr),
            self._catalog_has("word_similarity"),
            "has_trigram gates every trigram index _auto_init would create",
        )

    def test_has_unaccent_reports_indexability_not_just_presence(self):
        status = sql_schema.get_unaccent_status(self.cr)
        self.assertIsInstance(status, sql_schema.FunctionStatus)
        if not self._catalog_has("unaccent"):
            self.assertIs(status, sql_schema.FunctionStatus.MISSING)
        else:
            self.cr.execute(
                "SELECT p.provolatile FROM pg_proc p WHERE p.proname = 'unaccent' "
                "AND p.pronamespace = current_schema::regnamespace AND p.pronargs = 1"
            )
            immutable = self.cr.fetchscalar() == "i"
            self.assertIs(
                status,
                sql_schema.FunctionStatus.INDEXABLE
                if immutable
                else sql_schema.FunctionStatus.PRESENT,
                "only an IMMUTABLE unaccent can go in an index expression, "
                "which is why this is three states and not a bool",
            )

    def test_drop_index_removes_one_and_tolerates_a_missing_one(self):
        self.cr.execute("DROP TABLE IF EXISTS _test_di CASCADE")
        self.cr.execute("CREATE TABLE _test_di (id serial primary key, a int)")
        self.cr.execute("CREATE INDEX _test_di_idx ON _test_di (a)")
        self.assertTrue(sql_schema.index_exists(self.cr, "_test_di_idx"))
        sql_schema.drop_index(self.cr, "_test_di_idx", "_test_di")
        self.assertFalse(sql_schema.index_exists(self.cr, "_test_di_idx"))
        sql_schema.drop_index(self.cr, "_test_di_idx", "_test_di")
        self.assertFalse(
            sql_schema.index_exists(self.cr, "_test_di_idx"),
            "the second drop must be a no-op: convert_column_translatable "
            "drops an index that may never have existed",
        )


class TestSchemaForeignKeys(BaseCase):
    def setUp(self):
        super().setUp()
        self.cr = db_connect(common.get_db_name()).cursor()
        self.addCleanup(self.cr.close)
        self.addCleanup(self.cr.rollback)
        self.cr.execute("DROP TABLE IF EXISTS _test_fk_child CASCADE")
        self.cr.execute("DROP TABLE IF EXISTS _test_fk_parent CASCADE")
        self.cr.execute("CREATE TABLE _test_fk_parent (id serial primary key)")
        self.cr.execute(
            "CREATE TABLE _test_fk_child (id serial primary key, parent_id int)"
        )

    def _add(self, ondelete):
        sql_schema.add_foreign_key(
            self.cr, "_test_fk_child", "parent_id", "_test_fk_parent", "id", ondelete
        )

    def _find(self, ondelete):
        return sql_schema.get_fk_constraint_names(
            self.cr, "_test_fk_child", "parent_id", "_test_fk_parent", "id", ondelete
        )

    def test_every_ondelete_policy_round_trips(self):
        for policy in sql_schema._CONFDELTYPES:
            with self.subTest(ondelete=policy):
                self.cr.execute(
                    "ALTER TABLE _test_fk_child "
                    "DROP CONSTRAINT IF EXISTS _test_fk_child_parent_id_fkey"
                )
                self._add(policy)
                self.assertTrue(self._find(policy), f"{policy} was not found back")

    def test_a_key_is_not_found_under_a_different_policy(self):
        self._add("RESTRICT")
        self.assertTrue(self._find("RESTRICT"))
        self.assertEqual(
            self._find("CASCADE"),
            [],
            "check_foreign_keys drops and re-adds on this answer; matching "
            "regardless of ondelete would leave a changed policy unapplied",
        )

    def test_an_invalid_policy_is_refused_before_any_ddl(self):
        with self.assertRaises(ValueError):
            self._add("EXPLODE")
        self.assertEqual(
            sql_schema.get_fk_constraints_batch(self.cr, ["_test_fk_child"]), []
        )

    def test_the_policy_is_case_insensitive(self):
        self._add("cascade")
        self.assertTrue(self._find("CASCADE"))

    def test_the_batch_query_reports_the_whole_row(self):
        self._add("SET NULL")
        rows = sql_schema.get_fk_constraints_batch(self.cr, ["_test_fk_child"])
        self.assertEqual(len(rows), 1)
        name, t1, c1, t2, c2, deltype = rows[0]
        self.assertEqual(
            (t1, c1, t2, c2, deltype),
            ("_test_fk_child", "parent_id", "_test_fk_parent", "id", "n"),
            "check_foreign_keys keys its `existing` map on exactly this shape",
        )
        sql_schema.drop_constraint(self.cr, "_test_fk_child", name)
        self.assertEqual(
            sql_schema.get_fk_constraints_batch(self.cr, ["_test_fk_child"]), []
        )


class TestSchemaColumnLifecycle(BaseCase):
    def setUp(self):
        super().setUp()
        self.cr = db_connect(common.get_db_name()).cursor()
        self.addCleanup(self.cr.close)
        self.addCleanup(self.cr.rollback)
        self.cr.execute("DROP TABLE IF EXISTS _test_collife CASCADE")
        self.cr.execute("CREATE TABLE _test_collife (id serial primary key)")

    def _col(self, name):
        return sql_schema.get_table_columns(self.cr, "_test_collife")[name]

    def test_create_column_reports_through_table_columns(self):
        sql_schema.create_column(self.cr, "_test_collife", "note", "varchar")
        self.assertEqual(self._col("note")["udt_name"], "varchar")
        self.assertEqual(self._col("note")["is_nullable"], "YES")

    def test_a_boolean_column_is_created_with_a_default(self):
        sql_schema.create_column(self.cr, "_test_collife", "flag", "boolean")
        self.cr.execute(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = '_test_collife' AND column_name = 'flag'"
        )
        self.assertEqual(
            self.cr.fetchscalar(),
            "false",
            "a boolean added to existing rows must land false, not NULL",
        )

    def test_a_column_comment_survives_ddl_param_inlining(self):
        for comment in ("Discount %", "Rate %s of total", "Uses %(name)s"):
            with self.subTest(comment=comment):
                self.cr.execute("ALTER TABLE _test_collife DROP COLUMN IF EXISTS c")
                sql_schema.create_column(
                    self.cr, "_test_collife", "c", "varchar", comment=comment
                )
                self.cr.execute(
                    "SELECT col_description('_test_collife'::regclass, attnum) "
                    "FROM pg_attribute WHERE attrelid = '_test_collife'::regclass "
                    "AND attname = 'c'"
                )
                self.assertEqual(self.cr.fetchscalar(), comment)

    def test_not_null_goes_on_and_comes_off(self):
        sql_schema.create_column(self.cr, "_test_collife", "note", "varchar")
        self.cr.execute("INSERT INTO _test_collife (note) VALUES ('x')")
        sql_schema.set_not_null(self.cr, "_test_collife", "note")
        self.assertEqual(self._col("note")["is_nullable"], "NO")
        sql_schema.drop_not_null(self.cr, "_test_collife", "note")
        self.assertEqual(self._col("note")["is_nullable"], "YES")

    def test_translatable_conversion_round_trips_the_value(self):
        sql_schema.create_column(self.cr, "_test_collife", "note", "varchar")
        self.cr.execute("INSERT INTO _test_collife (note) VALUES ('hello')")
        sql_schema.convert_column_translatable(
            self.cr, "_test_collife", "note", "jsonb"
        )
        self.cr.execute("SELECT note FROM _test_collife")
        self.assertEqual(
            self.cr.fetchscalar(),
            {"en_US": "hello"},
            "the varchar becomes the en_US term of a jsonb translation",
        )
        self.assertEqual(self._col("note")["udt_name"], "jsonb")
        sql_schema.convert_column_translatable(
            self.cr, "_test_collife", "note", "varchar"
        )
        self.cr.execute("SELECT note FROM _test_collife")
        self.assertEqual(self.cr.fetchscalar(), "hello", "and back again")

    def test_a_null_value_stays_null_across_the_translatable_conversion(self):
        sql_schema.create_column(self.cr, "_test_collife", "note", "varchar")
        self.cr.execute("INSERT INTO _test_collife (note) VALUES (NULL)")
        sql_schema.convert_column_translatable(
            self.cr, "_test_collife", "note", "jsonb"
        )
        self.cr.execute("SELECT note FROM _test_collife")
        self.assertIsNone(
            self.cr.fetchscalar(),
            "the USING clause guards NULL explicitly; without it every "
            "untranslated row would gain a {'en_US': null} object",
        )

    def test_convert_column_falls_back_by_dropping_a_dependent_view(self):
        sql_schema.create_column(self.cr, "_test_collife", "note", "varchar")
        self.cr.execute("CREATE VIEW _test_collife_v AS SELECT note FROM _test_collife")
        self.addCleanup(self.cr.execute, "DROP VIEW IF EXISTS _test_collife_v CASCADE")
        sql_schema.convert_column(self.cr, "_test_collife", "note", "text")
        self.assertEqual(
            self._col("note")["udt_name"],
            "text",
            "PostgreSQL refuses ALTER TYPE under a view; the savepoint "
            "fallback drops the view and retries",
        )


class TestPartitionedTablesAreVisible(BaseCase):
    def _partition(self, cr, tbl):
        cr.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cr.execute(f"DROP TABLE IF EXISTS {tbl}_p0 CASCADE")
        cr.execute(
            f"CREATE TABLE {tbl} (id int NOT NULL, a int) PARTITION BY RANGE (id)"
        )
        cr.execute(
            f"CREATE TABLE {tbl}_p0 PARTITION OF {tbl} FOR VALUES FROM (0) TO (1000)"
        )

    def test_a_partitioned_table_exists(self):
        tbl = "_test_partitioned"
        cr = db_connect(common.get_db_name()).cursor()
        try:
            self._partition(cr, tbl)
            self.assertTrue(
                sql_schema.table_exists(cr, tbl),
                "a partitioned table exists; reporting otherwise makes "
                "_auto_init CREATE TABLE over it and the registry fails to load",
            )
            self.assertEqual(sql_schema.get_tables_existing(cr, [tbl]), [tbl])
        finally:
            cr.rollback()
            cr.close()

    def test_table_exists_and_table_kind_agree(self):
        tbl = "_test_partitioned_kind"
        cr = db_connect(common.get_db_name()).cursor()
        try:
            self._partition(cr, tbl)
            self.assertEqual(
                sql_schema.get_table_kind(cr, tbl), sql_schema.TableKind.Partitioned
            )
            self.assertTrue(sql_schema.table_exists(cr, tbl))
        finally:
            cr.rollback()
            cr.close()

    def test_a_partitioned_table_is_not_Regular(self):
        tbl = "_test_partitioned_regular"
        cr = db_connect(common.get_db_name()).cursor()
        try:
            self._partition(cr, tbl)
            self.assertNotEqual(
                sql_schema.get_table_kind(cr, tbl),
                sql_schema.TableKind.Regular,
                "ir.model.fields.unlink gates DROP COLUMN on Regular; a "
                "partitioned table must stay outside that gate",
            )
        finally:
            cr.rollback()
            cr.close()

    def test_every_relkind_the_kind_enum_names_is_admitted_as_existing(self):
        named = {k.value for k in sql_schema.TableKind if k.value} - {"t"}
        for relkind in self.assertSweep(sorted(named)):
            self.assertIn(
                relkind,
                sql_schema._EXISTING_RELKINDS,
                f"TableKind names relkind {relkind!r} but get_tables_existing "
                f"does not admit it, so get_table_kind and table_exists "
                f"disagree about that relation",
            )


class TestDdlDrainsSiblingConnections(BaseCase):
    def _prepare_sibling(self, cr, tbl):
        for _ in range(5):
            cr.execute(f"SELECT id, a FROM {tbl}")
            cr.fetchall()
        cr.commit()

    def test_committed_ddl_heals_an_idle_sibling_connection(self):
        tbl = "_test_sibling_plan"
        db_name = common.get_db_name()
        writer = db_connect(db_name).cursor()
        reader = db_connect(db_name).cursor()
        try:
            self.assertIsNot(
                writer._cnx, reader._cnx, "the two cursors must hold distinct backends"
            )
            writer.execute(f"DROP TABLE IF EXISTS {tbl}")
            writer.execute(f"CREATE TABLE {tbl} (id serial primary key, a int)")
            writer.execute(f"INSERT INTO {tbl} (a) VALUES (1)")
            writer.commit()

            self._prepare_sibling(reader, tbl)
            reader.close()

            writer.execute(f"ALTER TABLE {tbl} ALTER COLUMN a TYPE bigint")
            writer.commit()

            for attempt in range(6):
                probe = db_connect(db_name).cursor()
                try:
                    probe.execute(f"SELECT id, a FROM {tbl}")
                    probe.fetchall()
                except psycopg.errors.FeatureNotSupported as e:
                    probe.rollback()
                    self.fail(
                        f"borrow #{attempt} drew a connection still holding a "
                        f"plan from before the committed schema change: {e}. "
                        f"Cursor.commit() must drain the sibling connections "
                        f"when the transaction changed the schema."
                    )
                finally:
                    probe.close()
        finally:
            with contextlib.suppress(Exception):
                reader.close()
            with contextlib.suppress(Exception):
                writer.execute(f"DROP TABLE IF EXISTS {tbl}")
                writer.commit()
            writer.close()

    def test_a_rolled_back_schema_change_does_not_drain(self):
        db_name = common.get_db_name()
        cr = db_connect(db_name).cursor()
        try:
            cr.execute("CREATE TABLE _test_rolled_back_ddl (a int)")
            self.assertTrue(
                cr._schema_changed, "schema-changing DDL must arm the drain flag"
            )
            with patch.object(type(cr), "_drain_sibling_connections") as drain:
                cr.rollback()
                drain.assert_not_called()
            self.assertFalse(
                cr._schema_changed,
                "a rolled-back schema change never became visible to another "
                "connection, so it must disarm the flag rather than drain on "
                "the next unrelated commit",
            )
        finally:
            cr.close()

    def test_a_plain_commit_does_not_drain(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            cr.execute("SELECT 1")
            cr.fetchall()
            with patch.object(type(cr), "_drain_sibling_connections") as drain:
                cr.commit()
                drain.assert_not_called()
        finally:
            cr.close()

    def test_many_ddl_statements_in_one_transaction_drain_once(self):
        cr = db_connect(common.get_db_name()).cursor()
        try:
            for i in range(5):
                cr.execute(f"DROP TABLE IF EXISTS _test_ddl_batch_{i}")
            cr.commit()
            with patch.object(type(cr), "_drain_sibling_connections") as drain:
                for i in range(5):
                    cr.execute(f"CREATE TABLE _test_ddl_batch_{i} (a int)")
                cr.commit()
                self.assertEqual(
                    drain.call_count,
                    1,
                    "the drain is per transaction, not per statement: a module "
                    "install issues ~1000 schema-changing statements and each "
                    "drain closes and reopens every idle connection",
                )
        finally:
            with contextlib.suppress(Exception):
                for i in range(5):
                    cr.execute(f"DROP TABLE IF EXISTS _test_ddl_batch_{i}")
                cr.commit()
            cr.close()


class TestMaintenanceConnectionOptions(BaseCase):
    def test_both_borrow_paths_share_one_options_assembler(self):
        self.assertIn(
            "_prepare_connect_args",
            inspect.getsource(ConnectionPool._get_or_create_pool),
        )
        for path in ("_prepare_connect_args", "_borrow_directly"):
            src = inspect.getsource(getattr(ConnectionPool, path))
            self.assertIn(
                "_prepare_connection_options",
                src,
                f"{path} assembles libpq options by hand again; one assembler, "
                f"or the exemption below goes back to being invisible.",
            )

    def test_the_maintenance_path_opts_out_in_the_open(self):
        self.assertIn(
            "session_gucs=None",
            inspect.getsource(ConnectionPool._borrow_directly),
            "the maintenance path must state its exemption at the call site",
        )
        self.assertIn(
            "session_gucs=self._settings.session_gucs",
            inspect.getsource(ConnectionPool._prepare_connect_args),
            "the pooled path applies the pool's configured session policy",
        )

    def test_session_gucs_reach_a_pooled_connection(self):
        from odoo.tools import config

        saved = config["db_session_gucs"]
        config["db_session_gucs"] = "work_mem=19MB"
        pool = ConnectionPool(maxconn=4)
        conn = None
        try:
            _, info = get_connection_info_for_database(common.get_db_name())
            conn = pool.borrow(info)
            self.assertEqual(conn.execute("SHOW work_mem").fetchone()[0], "19MB")
        finally:
            if conn is not None:
                conn.rollback()
                pool.give_back(conn)
            pool.close_all()
            config["db_session_gucs"] = saved

    def test_session_gucs_do_not_reach_a_maintenance_connection(self):
        from odoo.tools import config

        saved = config["db_session_gucs"]
        config["db_session_gucs"] = "work_mem=19MB"
        pool = ConnectionPool(maxconn=4)
        conn = None
        try:
            _, info = get_connection_info_for_database("postgres")
            conn = pool.borrow(info)
            self.assertNotEqual(
                conn.execute("SHOW work_mem").fetchone()[0],
                "19MB",
                "an application-tuned session policy must not follow "
                "administrative DDL onto the maintenance path — "
                "statement_timeout there kills CREATE DATABASE",
            )
        finally:
            if conn is not None:
                conn.rollback()
                pool.give_back(conn)
            pool.close_all()
            config["db_session_gucs"] = saved

    def test_a_hostile_guc_does_not_break_database_creation(self):
        from odoo.tools import config

        saved = config["db_session_gucs"]
        config["db_session_gucs"] = "statement_timeout=50ms"
        pool = ConnectionPool(maxconn=4)
        conn = None
        name = f"_test_guc_create_db_{os.getpid()}"
        try:
            _, info = get_connection_info_for_database("postgres")
            conn = pool.borrow(info)
            conn.autocommit = True
            conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
            conn.execute(f'CREATE DATABASE "{name}"')
            conn.execute(f'DROP DATABASE "{name}"')
        finally:
            if conn is not None:
                with contextlib.suppress(Exception):
                    conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
                conn.autocommit = False
                pool.give_back(conn)
            pool.close_all()
            config["db_session_gucs"] = saved

    def test_idle_session_timeout_still_applies_to_maintenance(self):
        pool = ConnectionPool(maxconn=4)
        conn = None
        try:
            _, info = get_connection_info_for_database("postgres")
            conn = pool.borrow(info)
            self.assertEqual(
                conn.execute("SHOW idle_session_timeout").fetchone()[0],
                "15min",
                "the exemption covers db_session_gucs only; the derived "
                "idle_session_timeout is still applied unconditionally",
            )
        finally:
            if conn is not None:
                conn.rollback()
                pool.give_back(conn)
            pool.close_all()


class TestReplicaConnectionInfo(BaseCase):
    def _saved(self, *keys):
        from odoo.tools import config

        saved = {k: config[k] for k in keys}
        self.addCleanup(lambda: list(starmap(config.__setitem__, saved.items())))
        return config

    def test_readonly_overrides_every_keyword_when_set(self):
        config = self._saved(
            "db_host",
            "db_port",
            "db_user",
            "db_password",
            "db_sslmode",
            "db_replica_host",
            "db_replica_port",
            "db_replica_user",
            "db_replica_password",
            "db_replica_sslmode",
        )
        config["db_host"] = "primary.example"
        config["db_port"] = 5432
        config["db_user"] = "primary_user"
        config["db_password"] = "primary_pw"
        config["db_sslmode"] = "require"
        config["db_replica_host"] = "replica.example"
        config["db_replica_port"] = 5433
        config["db_replica_user"] = "replica_user"
        config["db_replica_password"] = "replica_pw"
        config["db_replica_sslmode"] = "verify-full"

        _, ro = get_connection_info_for_database("mydb", readonly=True)
        self.assertEqual(ro["host"], "replica.example")
        self.assertEqual(ro["port"], 5433)
        self.assertEqual(ro["user"], "replica_user")
        self.assertEqual(ro["password"], "replica_pw")
        self.assertEqual(ro["sslmode"], "verify-full")

        _, rw = get_connection_info_for_database("mydb", readonly=False)
        self.assertEqual(rw["host"], "primary.example")
        self.assertEqual(rw["user"], "primary_user")
        self.assertEqual(rw["password"], "primary_pw")

    def test_an_unset_replica_keyword_inherits_the_primary(self):
        config = self._saved(
            "db_host",
            "db_port",
            "db_user",
            "db_password",
            "db_sslmode",
            "db_replica_host",
            "db_replica_port",
            "db_replica_user",
            "db_replica_password",
            "db_replica_sslmode",
        )
        config["db_host"] = "primary.example"
        config["db_port"] = 5432
        config["db_user"] = "shared_user"
        config["db_password"] = "shared_pw"
        config["db_sslmode"] = "require"
        config["db_replica_host"] = "replica.example"
        for key in (
            "db_replica_port",
            "db_replica_user",
            "db_replica_password",
            "db_replica_sslmode",
        ):
            config[key] = None

        _, ro = get_connection_info_for_database("mydb", readonly=True)
        self.assertEqual(ro["host"], "replica.example", "the one override applies")
        self.assertEqual(ro["port"], 5432)
        self.assertEqual(ro["user"], "shared_user")
        self.assertEqual(ro["password"], "shared_pw")
        self.assertEqual(ro["sslmode"], "require")


_WIRE_RECEIVERS = frozenset({"_obj", "_cnx"})
"""The attributes a statement can be issued on from inside the cursor layer.

`_obj` alone left a hole: `invalidate_cached_plans` reached the connection
directly, so its `DEALLOCATE ALL` was a wire call this gate could not see.
"""


class TestTestCursorContainsBulkWrites(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.cr.execute(
            'CREATE TABLE IF NOT EXISTS "_bulk_savepoint_probe" '
            "(id serial primary key, k int)"
        )
        self.env.cr.execute('TRUNCATE "_bulk_savepoint_probe"')
        self.env.flush_all()

    def _survivors(self):
        self.env.cr.execute('SELECT count(*) FROM "_bulk_savepoint_probe"')
        return self.env.cr.fetchone()[0]

    def _run_and_roll_back(self, write):
        with self.enter_registry_test_mode():
            cr = self.registry.cursor()
            self.assertIsInstance(cr, TestCursor, "registry test mode is not active")
            try:
                write(cr)
                self.assertIsNotNone(
                    cr._savepoint, "the write did not open the rollback savepoint"
                )
            finally:
                cr.close()
        return self._survivors()

    def test_execute_is_contained(self):
        self.assertEqual(
            self._run_and_roll_back(
                lambda cr: cr.execute(
                    'INSERT INTO "_bulk_savepoint_probe"(k) VALUES (1)'
                )
            ),
            0,
        )

    def test_executemany_is_contained(self):
        self.assertEqual(
            self._run_and_roll_back(
                lambda cr: cr.executemany(
                    'INSERT INTO "_bulk_savepoint_probe"(k) VALUES (%s)', [(1,), (2,)]
                )
            ),
            0,
        )

    def test_execute_values_is_contained(self):
        self.assertEqual(
            self._run_and_roll_back(
                lambda cr: cr.execute_values(
                    'INSERT INTO "_bulk_savepoint_probe"(k) VALUES %s', [(1,), (2,)]
                )
            ),
            0,
        )

    def test_copy_from_is_contained(self):
        self.assertEqual(
            self._run_and_roll_back(
                lambda cr: cr.copy_from("_bulk_savepoint_probe", ["k"], [(1,), (2,)])
            ),
            0,
        )

    def test_copy_is_contained(self):
        def write(cr):
            with cr.copy('COPY "_bulk_savepoint_probe" (k) FROM STDIN') as cp:
                cp.write("1\n2\n")

        self.assertEqual(
            self._run_and_roll_back(write),
            0,
            "rows written through cr.copy() outlived the test's rollback. "
            "TestCursor must forward `copy` explicitly; reached through "
            "__getattr__ instead it goes straight to the real cursor and the "
            "COPY lands outside the savepoint. The sibling structural test "
            "says the forwarder is missing, this one says what that costs -- "
            "and `copy` is a @contextmanager, so it is the one entry point "
            "where the forwarder has to return the manager unopened.",
        )

    def test_binary_copy_from_is_contained(self):
        self.assertEqual(
            self._run_and_roll_back(
                lambda cr: cr.copy_from(
                    "_bulk_savepoint_probe", ["k"], [(1,), (2,)], binary=True
                )
            ),
            0,
        )

    def test_every_wire_level_write_is_marked(self):
        import ast
        import textwrap

        from odoo.db import bulk

        wire = {"execute", "executemany", "copy"}
        unmarked = []
        for owner, label in ((Cursor, "Cursor"), (bulk._BulkAccessMixin, "bulk")):
            tree = ast.parse(textwrap.dedent(inspect.getsource(owner)))
            for fn in ast.walk(tree):
                if not isinstance(fn, ast.FunctionDef):
                    continue
                aliases = {
                    node.targets[0].id
                    for node in ast.walk(fn)
                    if isinstance(node, ast.Assign)
                    and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Attribute)
                    and node.value.attr in _WIRE_RECEIVERS
                }
                calls = [
                    n
                    for n in ast.walk(fn)
                    if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute)
                    and n.func.attr in wire
                    and (
                        (
                            isinstance(n.func.value, ast.Name)
                            and n.func.value.id in aliases
                        )
                        or (
                            isinstance(n.func.value, ast.Attribute)
                            and n.func.value.attr in _WIRE_RECEIVERS
                        )
                    )
                ]
                if not calls:
                    continue
                names = {
                    x.func.attr
                    for x in ast.walk(fn)
                    if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
                }
                if "_before_statement" not in names:
                    unmarked.append(f"{label}.{fn.name}")
        self.assertEqual(
            unmarked,
            [],
            "these put a statement on the wire without calling "
            "_before_statement(), so TestCursor never opens its savepoint for "
            "them and their writes survive the test's rollback",
        )

    def test_the_scan_covers_both_wire_receivers(self):
        self.assertEqual(
            _WIRE_RECEIVERS,
            frozenset({"_obj", "_cnx"}),
            "a statement issued on the connection rather than the cursor is "
            "still a statement, and was invisible to this gate",
        )

    def test_the_wire_scan_would_catch_an_unmarked_method(self):
        import ast
        import textwrap

        src = textwrap.dedent(
            "class X:\n"
            "    def sneaky(self, q):\n"
            "        obj = self._obj\n"
            "        obj.execute(q)\n"
        )
        fn = next(n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef))
        aliases = {
            node.targets[0].id
            for node in ast.walk(fn)
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "_obj"
        }
        self.assertEqual(aliases, {"obj"}, "the alias walk is what makes it work")
        names = {
            x.func.attr
            for x in ast.walk(fn)
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
        }
        self.assertNotIn("_before_statement", names)

    def test_every_marked_entry_point_is_forwarded_by_the_wrapper(self):
        marked = {
            name
            for name in dir(Cursor)
            if callable(getattr(Cursor, name, None))
            and getattr(inspect.unwrap(getattr(Cursor, name)), "__code__", None)
            is not None
            and "_before_statement"
            in inspect.unwrap(getattr(Cursor, name)).__code__.co_names
        }
        self.assertTrue(marked, "Cursor marks no statement entry points at all")
        not_forwarded = sorted(marked - set(vars(TestCursor)))
        self.assertEqual(
            not_forwarded,
            [],
            "these reach the real cursor via __getattr__, skipping the savepoint",
        )

    def test_each_cursor_takes_its_own_savepoint(self):
        with self.enter_registry_test_mode():
            outer = self.registry.cursor()
            self.addCleanup(outer.close)
            outer.execute("SELECT 1")
            inner = self.registry.cursor()
            self.addCleanup(inner.close)
            self.assertIsNone(inner._savepoint)
            outer.execute("SELECT 1")
            self.assertIsNone(
                inner._savepoint,
                "the outer cursor's statement opened the inner cursor's savepoint",
            )
            inner.execute("SELECT 1")
            self.assertIsNotNone(inner._savepoint)
            self.assertIsNot(inner._savepoint, outer._savepoint)


class TestCopyFromTableIdentity(BaseCase):
    def setUp(self):
        super().setUp()
        self.db = db_connect(common.get_db_name())

    def test_schema_qualified_table_round_trips(self):
        with self.db.cursor() as cr:
            cr.execute("DROP SCHEMA IF EXISTS _cf_s CASCADE")
            cr.execute("CREATE SCHEMA _cf_s")
            cr.execute("CREATE TABLE _cf_s.t (id serial primary key, v int)")
            for binary in (False, True):
                with self.subTest(binary=binary):
                    cr.execute("TRUNCATE _cf_s.t")
                    ids = cr.copy_from(
                        "_cf_s.t",
                        ["v"],
                        [(1,), (2,)],
                        returning_ids=True,
                        binary=binary,
                    )
                    self.assertEqual(len(ids), 2)
                    cr.execute("SELECT v FROM _cf_s.t ORDER BY v")
                    self.assertEqual(cr.fetchall(), [(1,), (2,)])
            cr.execute("DROP SCHEMA _cf_s CASCADE")
            cr.rollback()

    def test_mixed_case_table_is_not_confused_with_its_folded_twin(self):
        with self.db.cursor() as cr:
            cr.execute('DROP TABLE IF EXISTS "MyCaseTbl"')
            cr.execute("DROP TABLE IF EXISTS mycasetbl")
            cr.execute('CREATE TABLE "MyCaseTbl" (id serial primary key, v int4)')
            cr.execute("CREATE TABLE mycasetbl (id serial primary key, v date)")
            cr.copy_from("MyCaseTbl", ["v"], [(20000,)], binary=True)
            cr.execute('SELECT v FROM "MyCaseTbl"')
            self.assertEqual(
                cr.fetchall(), [(20000,)], "types were read from the wrong relation"
            )
            cr.execute("SELECT count(*) FROM mycasetbl")
            self.assertEqual(cr.fetchone()[0], 0)
            cr.execute('DROP TABLE "MyCaseTbl"')
            cr.execute("DROP TABLE mycasetbl")
            cr.rollback()


class TestCopyFromChoosesEncodingByCost(BaseCase):
    def setUp(self):
        super().setUp()
        self.db = db_connect(common.get_db_name())

    def test_numeric_heavy_table_degrades_to_text_with_identical_rows(self):
        with self.db.cursor() as cr:
            cr.execute("DROP TABLE IF EXISTS _cf_num")
            cr.execute(
                "CREATE TABLE _cf_num (id serial primary key, "
                "a numeric, b numeric, c numeric)"
            )
            rows = [(1.5, 2.25, 3.125), (0.1, 0.2, 0.3)]
            oids = cr._get_column_type_oids("_cf_num", ["a", "b", "c"])
            self.assertFalse(
                cr._is_binary_copy_worthwhile(oids),
                "an all-numeric row must prefer text",
            )
            cr.copy_from("_cf_num", ["a", "b", "c"], rows, binary=True)
            cr.execute("SELECT a, b, c FROM _cf_num ORDER BY a")
            self.assertEqual(
                cr.fetchall(),
                [(0.1, 0.2, 0.3), (1.5, 2.25, 3.125)],
                "the text fallback must insert exactly the same values",
            )
            cr.rollback()

    def test_a_few_numeric_columns_still_use_binary(self):
        with self.db.cursor() as cr:
            cr.execute("DROP TABLE IF EXISTS _cf_mixed")
            cols = ", ".join(f"c{i} int" for i in range(15))
            cr.execute(
                f"CREATE TABLE _cf_mixed (id serial primary key, {cols}, "
                "amount numeric, tax numeric)"
            )
            names = [f"c{i}" for i in range(15)] + ["amount", "tax"]
            oids = cr._get_column_type_oids("_cf_mixed", names)
            self.assertTrue(
                cr._is_binary_copy_worthwhile(oids),
                "2 numeric columns in 17 is well under the crossover",
            )
            cr.rollback()


class TestNoRedundantLockAfterDdl(BaseCase):
    def setUp(self):
        super().setUp()
        self.db = db_connect(common.get_db_name())

    def test_ddl_keeps_the_lock_ledger_but_drops_the_types(self):
        with self.db.cursor() as cr:
            cr.execute("DROP TABLE IF EXISTS _cf_lock")
            cr.execute("CREATE TABLE _cf_lock (id serial primary key, k int)")
            cr.copy_from("_cf_lock", ["k"], [(1,)], binary=True)
            self.assertIn("_cf_lock", cr._schema_cache.locked_tables)
            cr.execute("CREATE TABLE IF NOT EXISTS _cf_lock_other (x int)")
            self.assertIn(
                "_cf_lock",
                cr._schema_cache.locked_tables,
                "the ROW EXCLUSIVE lock is still held after unrelated DDL",
            )
            self.assertIsNone(
                cr._schema_cache.get_column_types("_cf_lock", ["k"]),
                "the catalog facts must not survive DDL",
            )
            cr.rollback()

    def test_rollback_to_savepoint_clears_the_lock_ledger(self):
        with self.db.cursor() as cr:
            cr.execute("DROP TABLE IF EXISTS _cf_sp")
            cr.execute("CREATE TABLE _cf_sp (id serial primary key, k int)")
            cr.commit()
            sp = cr.savepoint(flush=False)
            cr.copy_from("_cf_sp", ["k"], [(1,)], binary=True)
            self.assertIn("_cf_sp", cr._schema_cache.locked_tables)
            sp.rollback()
            self.assertNotIn(
                "_cf_sp",
                cr._schema_cache.locked_tables,
                "ROLLBACK TO SAVEPOINT releases locks taken inside it",
            )
            sp.close()
            cr.execute("DROP TABLE _cf_sp")
            cr.commit()


class TestPermitsSurviveKilledBackendsUnderLoad(BaseCase):
    # Cursors are taken from db_connect(), not registry(): every TestCursor
    # serialises on one lock, and this test exists to race.
    @mute_logger("odoo.db.cursor")
    def test_budget_and_checkouts_read_zero_after_the_storm(self):
        import gc
        import random

        dbname = common.get_db_name()
        _, info = get_connection_info_for_database(dbname)
        pool = ConnectionPool(maxconn=6, borrow_timeout=5)
        self.addCleanup(pool.close_all)
        stop = threading.Event()
        pids: set[int] = set()
        lock = threading.Lock()
        outcomes = {"ok": 0, "killed": 0, "pool_error": 0, "other": 0}

        def worker():
            rnd = random.Random()
            while not stop.is_set():
                try:
                    cr = Cursor(pool, dbname, info)
                except PoolError:
                    with lock:
                        outcomes["pool_error"] += 1
                    continue
                except Exception:
                    with lock:
                        outcomes["other"] += 1
                    continue
                try:
                    cr.execute("SELECT pg_backend_pid()")
                    with lock:
                        pids.add(cr.fetchscalar())
                    if rnd.random() < 0.5:
                        cr.commit()
                    if rnd.random() < 0.1:
                        del cr  # dropped without close: __del__ must release
                        continue
                    cr.close()
                    with lock:
                        outcomes["ok"] += 1
                except psycopg.OperationalError, psycopg.InterfaceError:
                    with lock:
                        outcomes["killed"] += 1
                    cr.close()

        def killer():
            with contextlib.closing(db_connect(dbname).cursor()) as admin:
                while not stop.is_set():
                    time.sleep(0.05)
                    with lock:
                        victims = list(pids)[:2]
                        pids.difference_update(victims)
                    for pid in victims:
                        admin.execute("SELECT pg_terminate_backend(%s)", (pid,))
                    admin.commit()

        threads = [threading.Thread(target=worker) for _ in range(8)]
        threads.append(threading.Thread(target=killer))
        for t in threads:
            t.start()
        time.sleep(2.0)
        stop.set()
        for t in threads:
            t.join(10)
        gc.collect()
        time.sleep(0.2)
        health = pool.get_health()["pool"]
        self.assertGreater(outcomes["killed"], 0, "the killer must have hit someone")
        self.assertEqual(outcomes["other"], 0, outcomes)
        self.assertEqual(
            (health["budget_in_use"], health["checked_out"]),
            (0, 0),
            f"a permit or a checkout outlived its borrow: {health} {outcomes}",
        )


class TestSaturatedPoolNamesItsHolders(BaseCase):
    def setUp(self):
        super().setUp()
        self.pool = ConnectionPool(maxconn=2, borrow_timeout=0.2)
        self.info = get_connection_info_for_database(common.get_db_name())[1]
        self.addCleanup(self.pool.close_all)

    def test_exhaustion_error_names_the_oldest_checkouts(self):
        held = [self.pool.borrow(self.info) for _ in range(2)]
        self.addCleanup(lambda: [self.pool.give_back(c) for c in held])
        with self.assertRaises(PoolError) as ctx:
            self.pool.borrow(self.info)
        message = str(ctx.exception)
        self.assertIn("budget (2) reached", message)
        self.assertIn("oldest checkouts:", message)
        self.assertIn(threading.current_thread().name, message)
        self.assertIn("test_db_cursor.py:", message, "the borrow site is captured")

    def test_the_tracker_empties_when_connections_come_back(self):
        conns = [self.pool.borrow(self.info) for _ in range(2)]
        self.assertEqual(len(self.pool._checkouts), 2)
        for conn in conns:
            self.pool.give_back(conn)
        self.assertEqual(len(self.pool._checkouts), 0)
        self.assertEqual(self.pool._budget.in_use, 0)

    def test_health_reports_the_live_checkout_gauges(self):
        conn = self.pool.borrow(self.info)
        self.addCleanup(self.pool.give_back, conn)
        stats = self.pool.get_health()["pool"]
        self.assertEqual(stats["checked_out"], 1)
        self.assertGreaterEqual(stats["checked_out_oldest_seconds"], 0.0)
        self.assertEqual(stats["budget_in_use"], 1)
        self.assertEqual(stats["budget_exhausted"], 0)

    def test_a_failed_borrow_leaves_no_phantom_checkout(self):
        held = [self.pool.borrow(self.info) for _ in range(2)]
        self.addCleanup(lambda: [self.pool.give_back(c) for c in held])
        with self.assertRaises(PoolError):
            self.pool.borrow(self.info)
        self.assertEqual(
            len(self.pool._checkouts), 2, "the failed borrow must not be tracked"
        )
        self.assertEqual(self.pool.stats.borrows_failed, 1)


class TestInsertOrExisting(BaseCase):
    TABLE = "_test_insert_or_existing"

    def setUp(self):
        super().setUp()
        self.registry = Registry(common.get_db_name())
        self.addCleanup(self._drop)
        with self.registry.cursor() as cr:
            cr.execute(
                f'CREATE TABLE "{self.TABLE}"'
                " (id serial PRIMARY KEY, k text UNIQUE, v text)"
            )

    def _drop(self):
        with self.registry.cursor() as cr:
            cr.execute(f'DROP TABLE IF EXISTS "{self.TABLE}"')

    def _insert(self, cr, key, value):
        def insert():
            cr.execute(
                f'INSERT INTO "{self.TABLE}" (k, v) VALUES (%s, %s) RETURNING id',
                (key, value),
            )
            return cr.fetchone()[0]

        def find():
            cr.execute(f'SELECT id FROM "{self.TABLE}" WHERE k = %s', (key,))
            row = cr.fetchone()
            return row[0] if row else None

        return get_or_create_row(cr, insert, find, conflict=f"key {key!r}")

    def test_clean_insert_reports_created(self):
        with self.registry.cursor() as cr:
            row_id, created = self._insert(cr, "fresh", "v1")
            self.assertTrue(created)
            self.assertTrue(row_id)

    @mute_logger("odoo.db.cursor")
    def test_conflict_with_a_visible_row_returns_it(self):
        with self.registry.cursor() as cr:
            first, created = self._insert(cr, "dup", "v1")
            self.assertTrue(created)
            second, created = self._insert(cr, "dup", "v2")
            self.assertFalse(created)
            self.assertEqual(second, first)

    @mute_logger("odoo.db.cursor")
    def test_conflict_with_a_concurrent_row_is_retryable(self):
        with self.registry.cursor() as cr_a, self.registry.cursor() as cr_b:
            cr_b.execute(f'SELECT count(*) FROM "{self.TABLE}"')
            self._insert(cr_a, "raced", "winner")
            cr_a.commit()

            with self.assertRaises(ConcurrencyError):
                self._insert(cr_b, "raced", "loser")

            cr_b.rollback()
            _row, created = self._insert(cr_b, "raced", "loser")
            self.assertFalse(created)


class TestCloseRunsHooksOnALiveCursor(BaseCase):
    def test_prerollback_hook_can_still_read_on_close(self):
        cr = registry().cursor()
        seen = []

        def hook():
            cr.execute("SELECT 1")
            seen.append(cr.fetchone())

        cr.prerollback.add(hook)
        cr.close()
        self.assertEqual(seen, [(1,)], "the hook ran against a dead cursor")

    def test_postrollback_hook_still_runs_on_close(self):
        cr = registry().cursor()
        seen = []
        cr.postrollback.add(partial(seen.append, "postR"))
        cr.execute("SELECT 1")
        cr.close()
        self.assertEqual(seen, ["postR"])

    def test_rollback_runs_even_if_logging_raises(self):
        cr = registry().cursor()
        seen = []
        cr.prerollback.add(partial(seen.append, "preR"))
        cr.log_sql_stats = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
        with self.assertRaises(RuntimeError):
            cr.close()
        self.assertEqual(seen, ["preR"], "a logging failure skipped the rollback")
        self.assertTrue(cr._closed)

    def test_a_failing_hook_does_not_escape_close(self):
        cr = registry().cursor()
        cr.prerollback.add(lambda: (_ for _ in ()).throw(RuntimeError("hook boom")))
        cr.close()
        self.assertTrue(cr._closed)


class TestSavepointRollbackDropsRefilledRegistryCaches(BaseCase):
    KEY = "base.test_savepoint_cache_reclear"

    def _icp(self, cr):
        return api.Environment(cr, api.SUPERUSER_ID, {})["ir.config_parameter"].sudo()

    def test_a_rolled_back_write_does_not_outlive_its_savepoint(self):
        reg = registry()
        cr = reg.cursor()
        self.addCleanup(cr.close)
        icp = self._icp(cr)

        icp.set_param(self.KEY, "committed")
        cr.flush()
        reg.clear_cache("stable")
        self.assertEqual(icp.get_param(self.KEY), "committed")

        try:
            with cr.savepoint(flush=True):
                icp.set_param(self.KEY, "discarded")
                cr.flush()
                self.assertEqual(icp.get_param(self.KEY), "discarded")
                raise _Abort
        except _Abort:
            pass

        cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", (self.KEY,))
        row = cr.fetchone()
        self.assertEqual(row[0], "committed", "sanity: the row rolled back")
        self.assertEqual(
            icp.get_param(self.KEY),
            "committed",
            "the registry cache kept a value the savepoint discarded",
        )

    def test_a_savepoint_that_wrote_nothing_cached_clears_nothing(self):
        reg = registry()
        cr = reg.cursor()
        self.addCleanup(cr.close)
        reg.clear_cache("stable")
        reg.cache_invalidated.clear()

        cleared = []
        original = reg.clear_cache

        self.patch(
            reg, "clear_cache", lambda *names: cleared.append(names) or original(*names)
        )

        try:
            with cr.savepoint(flush=True):
                cr.execute("SELECT 1")
                raise _Abort
        except _Abort:
            pass

        self.assertEqual(
            cleared, [], "a read-only savepoint must not drop the worker's caches"
        )


class _Abort(Exception):
    pass
