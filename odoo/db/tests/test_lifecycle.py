import unittest
from time import monotonic
from unittest.mock import patch

import psycopg
from psycopg.pq import ExecStatus

from odoo.db import settings as pool_settings
from odoo.db.lifecycle import (
    _IDLE_SINCE_ATTR,
    _ISOLATION_LEVEL,
    _PREPARE_THRESHOLD,
    _PREPARED_MAX,
    _RESET_SESSION_STATE_SQL,
    _check_connection,
    _configure_connection,
    _reset_connection,
)
from odoo.db.settings import PoolSettings


class _FakePrepared:
    def __init__(self):
        self.cleared = 0

    def clear(self):
        self.cleared += 1


class _FakeResult:
    def __init__(self, status):
        self.status = status

    def get_error_message(self):
        return "server said no"


class _FakePgconn:
    def __init__(self, conn, status=ExecStatus.COMMAND_OK):
        self.conn = conn
        self.status = status

    def exec_(self, command: bytes):
        self.conn.executed.append(command.decode())
        # libpq reports the status as a bare int, never the enum member: an
        # identity comparison against ExecStatus.COMMAND_OK failed every reset
        # live while a fake returning the member passed.
        return _FakeResult(int(self.status))


class _FakeConn:
    def __init__(self):
        self.executed: list[str] = []
        self.autocommit = False
        self.isolation_level = None
        self.read_only = None
        self.flag_sets = 0
        self.prepare_threshold = None
        self.prepared_max = None
        self.adapters = self
        self.registered: list[str] = []
        self._prepared = _FakePrepared()
        self.pgconn = _FakePgconn(self)

    def __setattr__(self, name, value):
        if name in ("isolation_level", "read_only") and "flag_sets" in self.__dict__:
            self.__dict__["flag_sets"] += 1
        object.__setattr__(self, name, value)

    def register_loader(self, name, loader):
        self.registered.append(name)

    def execute(self, sql, *, prepare=None):
        raise AssertionError("the reset must not go through psycopg's execute()")


class TestConfigureConnection(unittest.TestCase):
    def test_registers_adapters_and_prepare_tuning(self):
        conn = _FakeConn()
        _configure_connection(conn)
        self.assertIn("numeric", conn.registered)
        self.assertEqual(conn.prepare_threshold, _PREPARE_THRESHOLD)
        self.assertEqual(conn.prepared_max, _PREPARED_MAX)

    def test_seeds_the_liveness_stamp(self):
        conn = _FakeConn()
        _configure_connection(conn)
        self.assertIsNotNone(getattr(conn, _IDLE_SINCE_ATTR, None))

    def test_runs_no_statement(self):
        conn = _FakeConn()
        _configure_connection(conn)
        self.assertEqual(conn.executed, [])

    def test_sets_the_transaction_flags_once_for_the_pool_it_serves(self):
        for readonly in (False, True):
            with self.subTest(readonly=readonly):
                conn = _FakeConn()
                _configure_connection(conn, readonly=readonly)
                self.assertIs(conn.isolation_level, _ISOLATION_LEVEL)
                self.assertIs(conn.read_only, readonly)
                self.assertEqual(conn.flag_sets, 2)


class TestResetSessionStateSql(unittest.TestCase):
    def test_closes_every_documented_leak(self):
        for clause in (
            "RESET ALL",
            "RESET SESSION AUTHORIZATION",
            "CLOSE ALL",
            "UNLISTEN *",
            "pg_advisory_unlock_all()",
            "DISCARD TEMP",
            "DISCARD SEQUENCES",
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, _RESET_SESSION_STATE_SQL)

    def test_spares_the_caches_it_means_to_spare(self):
        self.assertNotIn("DEALLOCATE", _RESET_SESSION_STATE_SQL)
        self.assertNotIn("DISCARD PLANS", _RESET_SESSION_STATE_SQL)
        self.assertNotIn("DISCARD ALL", _RESET_SESSION_STATE_SQL)

    def test_is_a_single_round_trip(self):
        self.assertEqual(_RESET_SESSION_STATE_SQL.count(";"), 6)


class TestResetConnection(unittest.TestCase):
    def _reset(self, discard):
        conn = _FakeConn()
        _reset_connection(conn, discard=discard)
        return conn

    def test_the_default_is_the_installed_pool_policy(self):
        for discard in (False, True):
            with self.subTest(discard=discard):
                conn = _FakeConn()
                with pool_settings.installed(PoolSettings(discard_on_return=discard)):
                    _reset_connection(conn)
                expected = "DISCARD ALL" if discard else _RESET_SESSION_STATE_SQL
                self.assertEqual(conn.executed, [expected])

    def test_default_uses_the_cheap_reset(self):
        conn = self._reset(False)
        self.assertEqual(conn.executed, [_RESET_SESSION_STATE_SQL])

    def test_discard_on_return_uses_discard_all(self):
        conn = self._reset(True)
        self.assertEqual(conn.executed, ["DISCARD ALL"])

    def test_a_reset_the_server_refuses_raises_so_the_pool_discards(self):
        conn = _FakeConn()
        conn.pgconn = _FakePgconn(conn, status=ExecStatus.FATAL_ERROR)
        with self.assertRaisesRegex(psycopg.OperationalError, "server said no"):
            _reset_connection(conn, discard=False)

    def test_never_toggles_autocommit(self):
        conn = self._reset(False)
        self.assertFalse(conn.autocommit)

    def test_discard_all_also_drops_the_client_side_prepare_cache(self):
        conn = self._reset(True)
        self.assertEqual(conn._prepared.cleared, 1)

    def test_cheap_reset_keeps_the_client_side_prepare_cache(self):
        conn = self._reset(False)
        self.assertEqual(conn._prepared.cleared, 0)

    def test_goes_through_libpq_directly(self):
        for discard in (False, True):
            with self.subTest(discard=discard):
                conn = self._reset(discard)
                self.assertEqual(
                    len(conn.executed),
                    1,
                    "one simple-query round trip through pgconn.exec_: no BEGIN "
                    "folded in, no autocommit toggle, none of execute()'s "
                    "per-statement machinery (14 us against 24)",
                )

    def test_restores_the_pools_flags_and_prepare_tuning(self):
        conn = self._reset(False)
        self.assertFalse(conn.autocommit, "must leave autocommit off for the next tx")
        self.assertIs(conn.isolation_level, _ISOLATION_LEVEL)
        self.assertIs(conn.read_only, False)
        self.assertEqual(conn.prepare_threshold, _PREPARE_THRESHOLD)
        self.assertEqual(conn.prepared_max, _PREPARED_MAX)

    def test_flags_a_cursor_left_alone_are_not_re_set(self):
        conn = _FakeConn()
        _configure_connection(conn, readonly=True)
        conn.flag_sets = 0
        _reset_connection(conn, discard=False, readonly=True)
        self.assertEqual(
            conn.flag_sets,
            0,
            "re-issuing the two setters on every return cost 2.5 us per cursor "
            "cycle for values that had not changed",
        )

    def test_a_flag_a_cursor_changed_is_set_back(self):
        conn = _FakeConn()
        _configure_connection(conn, readonly=False)
        conn.read_only = True  # what Cursor.enforce_readonly does
        conn.flag_sets = 0
        _reset_connection(conn, discard=False, readonly=False)
        self.assertIs(conn.read_only, False)
        self.assertEqual(conn.flag_sets, 1)

    def test_restamps_liveness_last(self):
        conn = self._reset(False)
        self.assertIsNotNone(getattr(conn, _IDLE_SINCE_ATTR, None))


class TestProbeLiveness(unittest.TestCase):
    def test_an_empty_query_answered_as_such_is_alive(self):
        from odoo.db.lifecycle import _probe_liveness

        conn = _FakeConn()
        conn.pgconn = _FakePgconn(conn, status=ExecStatus.EMPTY_QUERY)
        _probe_liveness(conn)
        self.assertEqual(conn.executed, [""])

    def test_anything_else_raises_so_the_pool_discards(self):
        from odoo.db.lifecycle import _probe_liveness

        conn = _FakeConn()
        conn.pgconn = _FakePgconn(conn, status=ExecStatus.FATAL_ERROR)
        with self.assertRaisesRegex(psycopg.OperationalError, "server said no"):
            _probe_liveness(conn)


class TestCheckConnection(unittest.TestCase):
    GRACE = 1.0

    def setUp(self):
        self.probed: list[object] = []

        def _record(conn):
            self.probed.append(conn)

        patcher = patch("odoo.db.lifecycle._probe_liveness", _record)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _check(self, conn, grace=GRACE):
        _check_connection(conn, grace=grace)

    def test_the_default_is_the_installed_pool_policy(self):
        conn = _FakeConn()
        setattr(conn, _IDLE_SINCE_ATTR, monotonic() - 5)
        with pool_settings.installed(PoolSettings(healthcheck_grace=60.0)):
            _check_connection(conn)
        self.assertEqual(self.probed, [], "a 60s grace spares a 5s-idle connection")
        with pool_settings.installed(PoolSettings(healthcheck_grace=1.0)):
            _check_connection(conn)
        self.assertEqual(self.probed, [conn])

    def test_recently_released_connection_skips_the_probe(self):
        conn = _FakeConn()
        setattr(conn, _IDLE_SINCE_ATTR, monotonic())
        self._check(conn)
        self.assertEqual(self.probed, [], "a just-released connection was alive")

    def test_connection_idle_past_the_window_is_probed(self):
        conn = _FakeConn()
        setattr(conn, _IDLE_SINCE_ATTR, monotonic() - (self.GRACE + 1))
        self._check(conn)
        self.assertEqual(self.probed, [conn])

    def test_unstamped_connection_fails_safe_to_the_probe(self):
        conn = _FakeConn()
        self._check(conn)
        self.assertEqual(self.probed, [conn], "unknown liveness must be verified")

    def test_zero_grace_probes_every_borrow(self):
        conn = _FakeConn()
        setattr(conn, _IDLE_SINCE_ATTR, monotonic())
        self._check(conn, grace=0)
        self.assertEqual(self.probed, [conn], "grace 0 must disable the window")

    def test_a_wider_grace_spares_a_longer_idle_connection(self):
        conn = _FakeConn()
        setattr(conn, _IDLE_SINCE_ATTR, monotonic() - 30)
        self._check(conn, grace=60)
        self.assertEqual(self.probed, [])


if __name__ == "__main__":
    unittest.main()
