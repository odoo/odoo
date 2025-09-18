import json
import logging
from datetime import datetime
from functools import partial
from unittest.mock import MagicMock, patch

import psycopg
from psycopg import IsolationLevel
from psycopg_pool import PoolTimeout

from odoo import api
from odoo.db import db_connect
from odoo.db.cursor import _id_sequence_cache
from odoo.db.pool import (
    ConnectionPool,
    PoolError,
    _normalize_dsn_key,
    _SuppressKnownPoolWarnings,
)
from odoo.db.utils import categorize_query, connection_info_for
from odoo.modules.registry import Registry
from odoo.tests import common
from odoo.tests.common import BaseCase, HttpCase
from odoo.tests.test_cursor import TestCursor

ADMIN_USER_ID = common.ADMIN_USER_ID


def registry():
    return Registry(common.get_db_name())


class TestRealCursor(BaseCase):
    def test_execute_bad_params(self):
        """
        Try to use iterable but non-list or int params in query parameters.
        """
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
        # even without db_replica, we expect the connection to be readonly for consistency
        registry_ = registry()
        with registry_.cursor(readonly=False) as cr:
            cr.execute("SHOW transaction_read_only")
            self.assertEqual(cr.fetchone(), ("off",))
            self.assertFalse(cr.readonly)

        with registry_.cursor(readonly=True) as cr:
            cr.execute("SHOW transaction_read_only")
            self.assertEqual(cr.fetchone(), ("on",))
            self.assertTrue(cr.readonly)


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

        # a generic patcher to check if the method was called with a readonly cursor or not.
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
        # make the registry in test mode
        self.registry_enter_test_mode()
        # now we make a test cursor for self.cr
        self.cr = self.registry.cursor()
        self.addCleanup(self.cr.close)
        self.env = api.Environment(self.cr, api.SUPERUSER_ID, {})
        self.record = self.env["res.partner"].create({"name": "Foo"})

    def write(self, record, value):
        record.ref = value

    def flush(self, record):
        record.flush_model(["ref"])

    def check(self, record, value):
        # make sure to fetch the field from the database
        record.invalidate_recordset()
        self.assertEqual(record.read(["ref"])[0]["ref"], value)

    def test_single_cursor(self):
        """Check the behavior of a single test cursor."""
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, "A")
        self.cr.commit()

        self.write(self.record, "B")
        self.cr.rollback()
        self.check(self.record, "A")

        self.write(self.record, "C")
        self.cr.rollback()
        self.check(self.record, "A")

    def test_sub_commit(self):
        """Check the behavior of a subcursor that commits."""
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, "A")
        self.cr.commit()

        self.write(self.record, "B")
        self.flush(self.record)

        # check behavior of a "sub-cursor" that commits
        with self.registry.cursor() as cr:
            self.assertIsInstance(cr, TestCursor)
            record = self.record.with_env(self.env(cr=cr))
            self.check(record, "B")
            self.write(record, "C")

        self.check(self.record, "C")

        self.cr.rollback()
        self.check(self.record, "A")

    def test_sub_rollback(self):
        """Check the behavior of a subcursor that rollbacks."""
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, "A")
        self.cr.commit()

        self.write(self.record, "B")
        self.flush(self.record)

        # check behavior of a "sub-cursor" that rollbacks
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

    def test_interleaving(self):
        """If test cursors are retrieved independently it becomes possible for
        the savepoint operations to be interleaved (especially as some are lazy
        e.g. the request cursor, so cursors might be semantically nested but
        technically interleaved), and for them to commit one another:

        .. code-block:: sql

            SAVEPOINT A
            SAVEPOINT B
            RELEASE SAVEPOINT A
            RELEASE SAVEPOINT B -- "savepoint b does not exist"
        """
        a = self.registry.cursor()
        b = self.registry.cursor()
        # This forces the savepoint to be created
        a._check_savepoint()
        b._check_savepoint()
        # `a` should warn that it found un-closed cursor `b` when trying to close itself
        with self.assertLogs("odoo.db.cursor", level=logging.WARNING) as cm:
            a.close()
        [msg] = cm.output
        self.assertIn("WARNING:odoo.db.cursor:Found different un-closed cursor", msg)
        # avoid a warning on teardown (when self.cr finds a still on the stack)
        # as well as ensure the stack matches our expectations
        with self.assertRaises(psycopg.errors.InvalidSavepointSpecification):
            with self.assertLogs("odoo.db.cursor", level=logging.WARNING) as cm:
                b.close()

    def test_borrow_connection(self):
        """Tests the behavior of the postgresql connection pool recycling/borrowing.

        With psycopg_pool, connections are managed per-database. Each
        ``getconn()`` returns a raw psycopg.Connection wrapped in a new
        ``psycopg.Connection``, so we compare backend PIDs (the PostgreSQL
        process ID) rather than Python object identity.
        """
        cursors = []
        try:
            connection = db_connect(self.cr.dbname)

            # Case #1: 2 cursors, both opened/used, do not recycle/borrow.
            # The 2nd cursor must not use the connection of the 1st cursor as it's used (not closed).
            cursors.extend((connection.cursor(), connection.cursor()))
            # Check that both cursors got different underlying connections.
            pid0 = cursors[0]._cnx.info.backend_pid
            pid1 = cursors[1]._cnx.info.backend_pid
            self.assertNotEqual(pid0, pid1)

            # Case #2: Close 1st cursor, open 3rd cursor, must recycle/borrow.
            # The 3rd must recycle/borrow the connection of the 1st one.
            cursors[0].close()
            cursors.append(connection.cursor())
            # Check the 3rd cursor reuses the backend connection from the 1st.
            pid2 = cursors[2]._cnx.info.backend_pid
            self.assertEqual(pid0, pid2)

        finally:
            for cursor in cursors:
                if not cursor.closed:
                    cursor.close()


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

        # check hook on commit()
        self.prepare_hooks(cr)
        cr.commit()
        self.assertEqual(self.log, ["preC", "postC"])

        # check hook on flush(), then on rollback()
        self.prepare_hooks(cr)
        cr.flush()
        self.assertEqual(self.log, ["preC"])
        cr.rollback()
        self.assertEqual(self.log, ["preC", "preR", "postR"])

        # check hook on close()
        self.prepare_hooks(cr)
        cr.close()
        self.assertEqual(self.log, ["preR", "postR"])

    def test_hooks_on_testcursor(self):
        self.registry_enter_test_mode()

        cr = self.registry.cursor()

        # check hook on commit(); post-commit hooks are ignored
        self.prepare_hooks(cr)
        cr.commit()
        self.assertEqual(self.log, ["preC"])

        # check hook on flush(), then on rollback()
        self.prepare_hooks(cr)
        cr.flush()
        self.assertEqual(self.log, ["preC"])
        cr.rollback()
        self.assertEqual(self.log, ["preC", "preR", "postR"])

        # check hook on close()
        self.prepare_hooks(cr)
        cr.close()
        self.assertEqual(self.log, ["preR", "postR"])


class TestCursorHooksTransactionCaseCleanup(common.TransactionCase):
    """Check savepoint cases handle commit hooks properly."""

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
    """Test that PostgreSQL numeric values are loaded as Python floats."""

    def test_numeric_column_returns_float(self):
        """Ensure the _NumericToFloatLoader adapter is active."""
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
    """Test fetchscalar, dictfetchone, dictfetchmany, dictfetchall."""

    def test_fetchscalar_value(self):
        with registry().cursor() as cr:
            cr.execute("SELECT 42")
            self.assertEqual(cr.fetchscalar(), 42)

    def test_fetchscalar_null(self):
        """fetchscalar returns None for NULL values (not the row tuple)."""
        with registry().cursor() as cr:
            cr.execute("SELECT NULL::int")
            self.assertIsNone(cr.fetchscalar())

    def test_fetchscalar_empty(self):
        """fetchscalar returns None when no rows match."""
        with registry().cursor() as cr:
            cr.execute("SELECT 1 WHERE FALSE")
            self.assertIsNone(cr.fetchscalar())

    def test_fetchscalar_multi_column(self):
        """fetchscalar returns the first column value only."""
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
        """Requesting more rows than available returns only what's there."""
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
    """Test now() caching and reset behavior."""

    def test_now_returns_datetime(self):
        with registry().cursor() as cr:
            result = cr.now()
            self.assertIsInstance(result, datetime)

    def test_now_cached_within_transaction(self):
        """Repeated calls return the exact same object (cached)."""
        with registry().cursor() as cr:
            t1 = cr.now()
            t2 = cr.now()
            self.assertIs(t1, t2)

    def test_now_reset_after_commit(self):
        """commit() resets the cached timestamp."""
        with registry().cursor() as cr:
            cr.now()
            self.assertIsNotNone(cr._now)
            cr.commit()
            self.assertIsNone(cr._now)

    def test_now_reset_after_rollback(self):
        """rollback() resets the cached timestamp."""
        with registry().cursor() as cr:
            cr.now()
            self.assertIsNotNone(cr._now)
            cr.rollback()
            self.assertIsNone(cr._now)


class TestCursorBulkMethods(BaseCase):
    """Test execute_values, executemany, and pipeline."""

    def test_execute_values_basic(self):
        """execute_values builds multi-row VALUES queries."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_ev (a int, b text)")
            cr.execute_values(
                "INSERT INTO _test_ev (a, b) VALUES %s",
                [(1, "x"), (2, "y"), (3, "z")],
            )
            cr.execute("SELECT a, b FROM _test_ev ORDER BY a")
            self.assertEqual(cr.fetchall(), [(1, "x"), (2, "y"), (3, "z")])

    def test_execute_values_with_fetch(self):
        """execute_values with fetch=True returns RETURNING results."""
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
        """execute_values with empty argslist is a no-op."""
        with registry().cursor() as cr:
            result = cr.execute_values("INSERT INTO nonexistent VALUES %s", [])
            self.assertIsNone(result)
            result = cr.execute_values(
                "INSERT INTO nonexistent VALUES %s", [], fetch=True
            )
            self.assertEqual(result, [])

    def test_execute_values_custom_template(self):
        """execute_values accepts a custom row template."""
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
        """execute_values respects page_size for batching large inserts."""
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

    def test_executemany_basic(self):
        """executemany inserts multiple rows via pipeline."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_em (a int, b text)")
            cr.executemany(
                "INSERT INTO _test_em (a, b) VALUES (%s, %s)",
                [(1, "x"), (2, "y"), (3, "z")],
            )
            cr.execute("SELECT a, b FROM _test_em ORDER BY a")
            self.assertEqual(cr.fetchall(), [(1, "x"), (2, "y"), (3, "z")])

    def test_executemany_returning(self):
        """executemany with returning=True collects RETURNING result sets."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_emr (id serial, val int)")
            cr.executemany(
                "INSERT INTO _test_emr (val) VALUES (%s) RETURNING id",
                [(10,), (20,), (30,)],
                returning=True,
            )
            # Results span multiple result sets — collect via nextset() loop
            ids = list(cr.fetchall())
            while cr._obj.nextset():
                ids.extend(cr.fetchall())
            self.assertEqual(len(ids), 3)

    def test_executemany_empty(self):
        """executemany with empty params_seq is a no-op."""
        with registry().cursor() as cr:
            cr.executemany("INSERT INTO nonexistent VALUES (%s)", [])

    def test_pipeline_mode(self):
        """pipeline batches multiple queries in a single round-trip."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_pipe (val int)")
            with cr.pipeline():
                for i in range(5):
                    cr.execute("INSERT INTO _test_pipe (val) VALUES (%s)", [i])
            cr.execute("SELECT count(*) FROM _test_pipe")
            self.assertEqual(cr.fetchone()[0], 5)

    def test_pipeline_nesting(self):
        """Nested pipeline contexts reuse the active pipeline (no-op)."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_nest (val int)")
            with cr.pipeline():
                cr.execute("INSERT INTO _test_nest (val) VALUES (%s)", [1])
                with cr.pipeline():
                    cr.execute("INSERT INTO _test_nest (val) VALUES (%s)", [2])
                    cr.execute("INSERT INTO _test_nest (val) VALUES (%s)", [3])
                # Still in outer pipeline after inner exits
                cr.execute("INSERT INTO _test_nest (val) VALUES (%s)", [4])
            cr.execute("SELECT count(*) FROM _test_nest")
            self.assertEqual(cr.fetchone()[0], 4)

    def test_pipeline_fire_and_forget_updates(self):
        """Pipeline batches fire-and-forget UPDATEs without fetching results."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_upd (id int, val int)")
            cr.execute("INSERT INTO _test_upd VALUES (1, 10), (2, 20), (3, 30)")
            with cr.pipeline():
                cr.execute("UPDATE _test_upd SET val = val + 100 WHERE id = %s", [1])
                cr.execute("UPDATE _test_upd SET val = val + 200 WHERE id = %s", [2])
                cr.execute("UPDATE _test_upd SET val = val + 300 WHERE id = %s", [3])
            cr.execute("SELECT val FROM _test_upd ORDER BY id")
            self.assertEqual(cr.fetchall(), [(110,), (220,), (330,)])


class TestMerge(BaseCase):
    """Test MERGE (atomic upsert) protocol path."""

    def test_merge_insert(self):
        """merge() inserts new rows when no match exists."""
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_ins (id serial PRIMARY KEY, key text UNIQUE, val text)"
            )
            result = cr.merge(
                "_test_mg_ins",
                ["key", "val"],
                [("a", "v1"), ("b", "v2")],
                on_columns=["key"],
            )
            self.assertEqual(len(result), 2)
            cr.execute("SELECT key, val FROM _test_mg_ins ORDER BY key")
            self.assertEqual(cr.fetchall(), [("a", "v1"), ("b", "v2")])

    def test_merge_update(self):
        """merge() updates existing rows when match exists."""
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_upd (id serial PRIMARY KEY, key text UNIQUE, val text)"
            )
            cr.execute("INSERT INTO _test_mg_upd (key, val) VALUES ('a', 'old')")
            cr.merge(
                "_test_mg_upd",
                ["key", "val"],
                [("a", "new")],
                on_columns=["key"],
            )
            cr.execute("SELECT val FROM _test_mg_upd WHERE key = 'a'")
            self.assertEqual(cr.fetchone()[0], "new")

    def test_merge_mixed(self):
        """merge() handles a mix of inserts and updates."""
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_mix (id serial PRIMARY KEY, key text UNIQUE, val int)"
            )
            cr.execute("INSERT INTO _test_mg_mix (key, val) VALUES ('existing', 10)")
            result = cr.merge(
                "_test_mg_mix",
                ["key", "val"],
                [("existing", 20), ("new_key", 30)],
                on_columns=["key"],
            )
            self.assertEqual(len(result), 2)
            cr.execute("SELECT key, val FROM _test_mg_mix ORDER BY key")
            self.assertEqual(cr.fetchall(), [("existing", 20), ("new_key", 30)])

    def test_merge_returning(self):
        """merge() respects custom RETURNING clause."""
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_ret (id serial PRIMARY KEY, key text UNIQUE, val text)"
            )
            cr.execute("INSERT INTO _test_mg_ret (key, val) VALUES ('a', 'old')")
            result = cr.merge(
                "_test_mg_ret",
                ["key", "val"],
                [("a", "new"), ("b", "fresh")],
                on_columns=["key"],
                returning="merge_action(), OLD.val, NEW.val",
            )
            # First row: UPDATE with old/new values
            self.assertEqual(result[0][0], "UPDATE")
            self.assertEqual(result[0][1], "old")
            self.assertEqual(result[0][2], "new")
            # Second row: INSERT with NULL old value
            self.assertEqual(result[1][0], "INSERT")
            self.assertIsNone(result[1][1])
            self.assertEqual(result[1][2], "fresh")

    def test_merge_empty_rows(self):
        """merge() returns empty list for empty input."""
        with registry().cursor() as cr:
            cr.execute(
                "CREATE TEMP TABLE _test_mg_empty (id serial PRIMARY KEY, key text UNIQUE, val text)"
            )
            result = cr.merge("_test_mg_empty", ["key", "val"], [], on_columns=["key"])
            self.assertEqual(result, [])


class TestCopyFrom(BaseCase):
    """Test COPY protocol path (copy_from)."""

    def test_copy_from_basic(self):
        """copy_from inserts rows via PostgreSQL COPY protocol."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cp (a int, b text)")
            result = cr.copy_from("_test_cp", ["a", "b"], [(1, "x"), (2, "y")])
            self.assertIsNone(result)
            cr.execute("SELECT a, b FROM _test_cp ORDER BY a")
            self.assertEqual(cr.fetchall(), [(1, "x"), (2, "y")])

    def test_copy_from_returning_ids(self):
        """copy_from with returning_ids pre-generates IDs from the sequence."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpid (id serial PRIMARY KEY, val text)")
            try:
                ids = cr.copy_from(
                    "_test_cpid",
                    ["val"],
                    [("a",), ("b",), ("c",)],
                    returning_ids=True,
                )
                self.assertEqual(len(ids), 3)
                # Verify the IDs match what was actually inserted
                cr.execute("SELECT id, val FROM _test_cpid ORDER BY id")
                rows = cr.fetchall()
                self.assertEqual(len(rows), 3)
                for expected_id, (row_id, _) in zip(ids, rows, strict=False):
                    self.assertEqual(expected_id, row_id)
            finally:
                # Clean up sequence cache to avoid cross-test contamination
                _id_sequence_cache.pop("_test_cpid", None)

    def test_copy_from_empty_returning(self):
        """copy_from with empty rows and returning_ids returns empty list."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpe (id serial PRIMARY KEY, val text)")
            ids = cr.copy_from("_test_cpe", ["val"], [], returning_ids=True)
            self.assertEqual(ids, [])

    def test_copy_from_null_values(self):
        """copy_from handles None → NULL conversion."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpn (a int, b text)")
            cr.copy_from("_test_cpn", ["a", "b"], [(1, None), (None, "y")])
            cr.execute("SELECT a, b FROM _test_cpn ORDER BY COALESCE(a, 0)")
            rows = cr.fetchall()
            self.assertEqual(rows[0], (None, "y"))
            self.assertEqual(rows[1], (1, None))

    def test_copy_from_large_batch(self):
        """COPY handles batches larger than typical INSERT thresholds."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cplg (val int)")
            rows = [(i,) for i in range(500)]
            cr.copy_from("_test_cplg", ["val"], rows)
            cr.execute("SELECT count(*) FROM _test_cplg")
            self.assertEqual(cr.fetchone()[0], 500)

    def test_copy_from_json_values(self):
        """COPY adapts JSON (dict/list) types via psycopg3's Transformer."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_cpj (data jsonb)")
            cr.copy_from(
                "_test_cpj",
                ["data"],
                [(psycopg.types.json.Json({"key": "value"}),)],
            )
            cr.execute("SELECT data->>'key' FROM _test_cpj")
            self.assertEqual(cr.fetchone()[0], "value")


class TestDDLFormatting(BaseCase):
    """Test that DDL statements use client-side formatting automatically."""

    def test_ddl_client_side_formatting(self):
        """DDL statements use client-side formatting automatically.

        PostgreSQL's extended query protocol rejects $N parameters in DDL
        structural positions, so execute() detects DDL and inlines params
        client-side via psycopg.sql.quote().
        """
        with registry().cursor() as cr:
            # Without client-side formatting, psycopg3 would send $1 which
            # PostgreSQL rejects for DEFAULT expressions.
            cr.execute("CREATE TEMP TABLE _test_ddl (val int DEFAULT %s)", (0,))
            cr.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = '_test_ddl' AND column_name = 'val'"
            )
            default = cr.fetchone()[0]
            self.assertEqual(default, "0")

    def test_ddl_comment(self):
        """COMMENT ON is DDL and uses client-side formatting."""
        with registry().cursor() as cr:
            cr.execute("CREATE TEMP TABLE _test_ddl2 (val int)")
            cr.execute("COMMENT ON TABLE _test_ddl2 IS %s", ("test comment",))
            cr.execute(
                "SELECT obj_description(c.oid) FROM pg_class c WHERE c.relname = '_test_ddl2'"
            )
            self.assertEqual(cr.fetchone()[0], "test comment")


class TestCategorizeQuery(BaseCase):
    """Test query categorization utility (from/into/other)."""

    def test_select_from(self):
        qtype, table = categorize_query("SELECT * FROM res_users")
        self.assertEqual(qtype, "from")
        self.assertEqual(table, "res_users")

    def test_insert_into(self):
        qtype, table = categorize_query("INSERT INTO res_users (name) VALUES ('x')")
        self.assertEqual(qtype, "into")
        self.assertEqual(table, "res_users")

    def test_insert_select_prioritizes_into(self):
        """INSERT INTO ... SELECT FROM ... prioritizes 'into' over 'from'."""
        qtype, table = categorize_query("INSERT INTO t1 SELECT * FROM t2")
        self.assertEqual(qtype, "into")
        self.assertEqual(table, "t1")

    def test_update_without_from(self):
        qtype, table = categorize_query("UPDATE res_users SET name='x'")
        self.assertEqual(qtype, "other")
        self.assertIsNone(table)

    def test_other(self):
        qtype, table = categorize_query("COMMIT")
        self.assertEqual(qtype, "other")
        self.assertIsNone(table)

    def test_quoted_table_name(self):
        qtype, table = categorize_query('SELECT * FROM "my_table" WHERE id = 1')
        self.assertEqual(qtype, "from")
        self.assertEqual(table, "my_table")

    def test_case_insensitive(self):
        qtype, table = categorize_query("select * from RES_USERS")
        self.assertEqual(qtype, "from")
        self.assertEqual(table, "RES_USERS")

    def test_multiline_query(self):
        qtype, table = categorize_query("SELECT id\n  FROM res_partner\n WHERE active")
        self.assertEqual(qtype, "from")
        self.assertEqual(table, "res_partner")


class TestConnectionInfoFor(BaseCase):
    """Test connection_info_for URI/name parsing."""

    def test_postgresql_uri(self):
        db, info = connection_info_for("postgresql://user:pass@localhost:5432/mydb")
        self.assertEqual(db, "mydb")
        self.assertIn("dsn", info)
        self.assertEqual(info["dsn"], "postgresql://user:pass@localhost:5432/mydb")
        # Health params are always included
        self.assertIn("connect_timeout", info)
        self.assertIn("keepalives", info)

    def test_postgres_uri_scheme(self):
        """Both 'postgresql://' and 'postgres://' schemes are accepted."""
        db, info = connection_info_for("postgres://localhost/testdb")
        self.assertEqual(db, "testdb")
        self.assertIn("dsn", info)

    def test_uri_no_path_uses_username(self):
        """When URI path is just '/', fall back to username as db name."""
        db, _ = connection_info_for("postgresql://admin@localhost/")
        self.assertEqual(db, "admin")

    def test_uri_no_path_no_user_uses_hostname(self):
        """When URI has no path and no username, use hostname."""
        db, _ = connection_info_for("postgresql://localhost/")
        self.assertEqual(db, "localhost")

    def test_plain_dbname(self):
        db, info = connection_info_for("mydb")
        self.assertEqual(db, "mydb")
        self.assertEqual(info["dbname"], "mydb")
        self.assertNotIn("dsn", info)
        # Health params are always included
        self.assertIn("connect_timeout", info)

    def test_application_name_included(self):
        _, info = connection_info_for("mydb")
        self.assertIn("application_name", info)


class TestNormalizeDsnKey(BaseCase):
    """Test DSN normalization for pool lookup keys."""

    def test_dbname_aliased_to_database(self):
        key_dict = dict(_normalize_dsn_key({"dbname": "test", "host": "localhost"}))
        self.assertEqual(key_dict["database"], "test")
        self.assertNotIn("dbname", key_dict)

    def test_password_excluded(self):
        """Passwords are excluded from pool keys (security + correctness)."""
        key_dict = dict(_normalize_dsn_key({"dbname": "test", "password": "secret"}))
        self.assertNotIn("password", key_dict)

    def test_none_values_excluded(self):
        key_dict = dict(_normalize_dsn_key({"dbname": "test", "host": None}))
        self.assertNotIn("host", key_dict)

    def test_string_dsn(self):
        """String DSNs are parsed via conninfo_to_dict."""
        key_dict = dict(_normalize_dsn_key("dbname=test host=localhost"))
        self.assertEqual(key_dict["database"], "test")
        self.assertEqual(key_dict["host"], "localhost")

    def test_same_dsn_same_key(self):
        """Different dict representations of the same DSN produce equal keys."""
        key1 = _normalize_dsn_key({"dbname": "test", "host": "localhost"})
        key2 = _normalize_dsn_key({"database": "test", "host": "localhost"})
        self.assertEqual(key1, key2)


class TestPoolBasics(BaseCase):
    """Test pool representation, properties, and statistics."""

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

    def test_pool_maxconn_clamp(self):
        """Pool maxconn is clamped to at least 1."""
        pool = ConnectionPool(maxconn=0)
        self.assertEqual(pool._maxconn, 1)
        pool.close_all()


class TestSuppressKnownPoolWarnings(BaseCase):
    """Test the logging filter for known psycopg_pool warnings."""

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


class TestPoolTimeoutCleanup(BaseCase):
    """Test that dead pools are cleaned up on PoolTimeout."""

    def test_pool_removed_on_timeout(self):
        """When getconn() raises PoolTimeout, the pool must be removed from
        _pools so subsequent borrows create a fresh pool instead of hitting
        the same dead one (e.g. after a database drop).
        """
        pool = ConnectionPool(maxconn=4)
        info = connection_info_for("nonexistent_db_test")[1]
        key = _normalize_dsn_key(info)

        # Pre-create a mock psycopg_pool that raises PoolTimeout
        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.getconn.side_effect = PoolTimeout("connection timeout")
        pool._pools[key] = mock_pool

        with self.assertRaises(PoolError):
            pool.borrow(info)

        # The dead pool must have been removed from _pools
        self.assertNotIn(key, pool._pools)
        # And close() must have been called on it
        mock_pool.close.assert_called_once()

    def test_pool_not_removed_on_other_errors(self):
        """Non-timeout psycopg errors should NOT remove the pool —
        the error might be transient (e.g. brief network hiccup).
        """
        pool = ConnectionPool(maxconn=4)
        info = connection_info_for("nonexistent_db_test")[1]
        key = _normalize_dsn_key(info)

        mock_pool = MagicMock()
        mock_pool.closed = False
        mock_pool.getconn.side_effect = psycopg.OperationalError("connection refused")
        pool._pools[key] = mock_pool

        with self.assertRaises(psycopg.OperationalError):
            pool.borrow(info)

        # Pool should still be in _pools for non-timeout errors
        self.assertIn(key, pool._pools)
        mock_pool.close.assert_not_called()


class TestDroppedDBRecovery(BaseCase):
    """Test that check_signaling() cleans up stale registries when the
    database is unreachable (e.g. dropped by another worker).

    Uses a mock cursor to avoid the 30s psycopg_pool retry timeout —
    the pool-level behavior is separately tested by TestPoolTimeoutCleanup.
    """

    DB_NAME = "odoo_test_pool_recovery"

    def test_check_signaling_cleans_up_after_db_drop(self):
        """check_signaling() must delete the stale registry when cursor
        creation fails with OperationalError, and re-raise the error.

        Without this fix, the stale registry stays in the LRU and every
        subsequent request creates a new pool that blocks for 30s on
        PoolTimeout — repeated hangs until the process is restarted.
        """
        # Build a minimal registry shell and inject it into the LRU.
        # No real DB needed — we mock the cursor to simulate failure.
        reg = object.__new__(Registry)
        reg.db_name = self.DB_NAME
        reg._db_readonly = None
        Registry.registries[self.DB_NAME] = reg
        self.addCleanup(Registry.delete, self.DB_NAME)

        # Simulate dropped DB: cursor() raises OperationalError
        with patch.object(
            type(reg),
            "cursor",
            side_effect=psycopg.OperationalError(
                f'database "{self.DB_NAME}" does not exist'
            ),
        ):
            with self.assertRaises(psycopg.OperationalError):
                reg.check_signaling()

        # The stale registry must have been removed from the LRU
        self.assertNotIn(self.DB_NAME, Registry.registries)

    def test_check_signaling_cleans_up_after_pool_error(self):
        """check_signaling() must also handle PoolError (raised by borrow()
        when the pool times out, e.g. after a database drop).
        """
        reg = object.__new__(Registry)
        reg.db_name = self.DB_NAME
        reg._db_readonly = None
        Registry.registries[self.DB_NAME] = reg
        self.addCleanup(Registry.delete, self.DB_NAME)

        with patch.object(
            type(reg),
            "cursor",
            side_effect=PoolError("couldn't get a connection after 30.00 sec"),
        ):
            with self.assertRaises(PoolError):
                reg.check_signaling()

        self.assertNotIn(self.DB_NAME, Registry.registries)

    def test_check_signaling_keeps_registry_when_caller_provides_cursor(self):
        """When the caller provides a cursor (cr is not None) and it fails
        mid-query, the registry should NOT be deleted — the failure has a
        different cause (e.g. dead connection mid-query, not a dropped DB).
        """
        reg = object.__new__(Registry)
        reg.db_name = self.DB_NAME
        reg._db_readonly = None
        reg.registry_sequence = -1
        Registry.registries[self.DB_NAME] = reg
        self.addCleanup(Registry.delete, self.DB_NAME)

        # Simulate a cursor that fails during get_sequences()
        mock_cr = MagicMock()
        mock_cr.__enter__ = MagicMock(return_value=mock_cr)
        mock_cr.__exit__ = MagicMock(return_value=False)
        mock_cr.execute.side_effect = psycopg.OperationalError("connection closed")

        with self.assertRaises(psycopg.OperationalError):
            reg.check_signaling(cr=mock_cr)

        # Registry should still be in the LRU — caller-provided cursor
        # failure is not necessarily a dropped DB.
        self.assertIn(self.DB_NAME, Registry.registries)
