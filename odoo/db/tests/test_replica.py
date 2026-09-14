import typing
import unittest

import psycopg

from odoo.db import replica as replica_module
from odoo.db import settings as pool_settings
from odoo.db.lag import ReplicaLagGate
from odoo.db.pool import PoolError
from odoo.db.replica import REPLICA_RETRY_TIME, ReplicaRouter
from odoo.db.settings import PoolSettings
from odoo.libs.breaker import CircuitBreaker
from odoo.tools.config import configmanager


class _Conn:
    def __init__(self, label, fails=False, lag=0.0):
        self.label = label
        self.fails = fails
        self.lag = lag
        self.attempts = 0
        self.queries = 0
        self.opened = []

    def cursor(self):
        self.attempts += 1
        if self.fails:
            raise psycopg.OperationalError(f"{self.label} is down")
        cr = _Cursor(self)
        self.opened.append(cr)
        return cr


class _Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.closed = False

    def execute(self, *args, **kwargs):
        self.conn.queries += 1

    def fetchone(self):
        return (self.conn.lag,)

    def close(self):
        self.closed = True


def _router(*, replica_fails=False, with_replica=True, lag=0.0, max_lag=0.0):
    primary = _Conn("primary")
    readonly = _Conn("replica", fails=replica_fails, lag=lag) if with_replica else None
    return ReplicaRouter(
        typing.cast("typing.Any", primary),
        typing.cast("typing.Any", readonly),
        max_lag=max_lag,
    )


class TestRouting(unittest.TestCase):
    def test_a_usable_replica_serves_readonly_cursors_in_ro_mode(self):
        router = _router()
        cr, mode = router.cursor(readonly=True)
        self.assertIs(cr.conn, router.readonly)
        self.assertEqual(mode, "ro")
        self.assertTrue(router.breaker.closed)

    def test_no_readonly_connection_serves_the_primary_in_rw_mode(self):
        router = _router(with_replica=False)
        cr, mode = router.cursor(readonly=True)
        self.assertIs(cr.conn, router.primary)
        self.assertEqual(mode, "rw")

    def test_a_readwrite_request_never_touches_the_replica(self):
        router = _router()
        cr, mode = router.cursor(readonly=False)
        self.assertIs(cr.conn, router.primary)
        self.assertEqual(mode, "rw")
        self.assertEqual(router.readonly.attempts, 0)

    def test_a_failing_replica_demotes_and_opens_the_breaker(self):
        router = _router(replica_fails=True)
        cr, mode = router.cursor(readonly=True)
        self.assertIs(cr.conn, router.primary)
        self.assertEqual(mode, "ro->rw")
        self.assertFalse(router.breaker.closed)
        self.assertEqual(router.breaker.failures, 1)

    def test_an_open_breaker_demotes_without_re_attempting_the_replica(self):
        router = _router(replica_fails=True)
        for _ in range(20):
            _cr, mode = router.cursor(readonly=True)
            self.assertEqual(mode, "ro->rw")
        self.assertEqual(router.readonly.attempts, 1)

    def test_a_pool_error_counts_as_a_replica_failure(self):
        router = _router()

        def no_connection():
            raise PoolError("no connection")

        router.readonly.cursor = no_connection
        _cr, mode = router.cursor(readonly=True)
        self.assertEqual(mode, "ro->rw")
        self.assertFalse(router.breaker.closed)

    def test_it_recovers_without_waiting_out_the_ceiling(self):
        router = _router(replica_fails=True)
        router.cursor(readonly=True)
        router.readonly.fails = False
        router.breaker._opened_at -= router.breaker.initial_cooldown + 1

        _cr, mode = router.cursor(readonly=True)
        self.assertEqual(mode, "ro")
        self.assertTrue(router.breaker.closed)
        self.assertEqual(router.breaker.failures, 0)

    def test_repeated_failures_do_not_exceed_the_ceiling(self):
        router = _router(replica_fails=True)
        for _ in range(40):
            router.breaker._opened_at -= router.breaker.max_cooldown + 1
            router.cursor(readonly=True)
        self.assertLessEqual(router.breaker.cooldown_remaining, REPLICA_RETRY_TIME)

    def test_the_default_breaker_and_gate_can_be_injected(self):
        breaker = CircuitBreaker(max_cooldown=5)
        lag = ReplicaLagGate(30.0)
        router = ReplicaRouter(
            typing.cast("typing.Any", _Conn("primary")), breaker=breaker, lag=lag
        )
        self.assertIs(router.breaker, breaker)
        self.assertIs(router.lag, lag)
        self.assertEqual(
            ReplicaRouter(typing.cast("typing.Any", _Conn("p"))).breaker.max_cooldown,
            REPLICA_RETRY_TIME,
        )

    def test_get_health_surfaces_lag_and_breaker_snapshots(self):
        router = _router(lag=2.0, max_lag=30.0)
        router.cursor(readonly=True)
        router.breaker.record_failure()
        health = router.get_health()
        self.assertEqual(health["lag"], router.lag.get_snapshot())
        self.assertEqual(health["breaker"], router.breaker.get_snapshot())
        self.assertEqual(health["lag"]["last_lag_seconds"], 2.0)
        self.assertEqual(health["breaker"]["failures"], 1)


class TestLagGating(unittest.TestCase):
    def test_a_current_replica_serves_reads(self):
        router = _router(lag=1.0, max_lag=30.0)
        _cr, mode = router.cursor(readonly=True)
        self.assertEqual(mode, "ro")
        self.assertTrue(router.lag.is_replica_usable())

    def test_lag_over_the_ceiling_demotes_to_the_primary(self):
        router = _router(lag=120.0, max_lag=30.0)
        cr, mode = router.cursor(readonly=True)
        self.assertIs(cr.conn, router.primary)
        self.assertEqual(mode, "ro->rw")
        self.assertFalse(router.lag.is_replica_usable())

    def test_the_rejected_replica_cursor_is_closed_not_leaked(self):
        router = _router(lag=120.0, max_lag=30.0)
        router.cursor(readonly=True)
        opened = router.readonly.opened
        self.assertTrue(opened)
        self.assertTrue(all(cr.closed for cr in opened))

    def test_a_disabled_ceiling_never_queries_for_lag(self):
        router = _router(lag=9999.0, max_lag=0.0)
        router.cursor(readonly=True)
        self.assertEqual(router.readonly.queries, 0)

    def test_a_due_sample_records_the_measured_lag(self):
        router = _router(lag=7.5, max_lag=120.0)
        router.cursor(readonly=True)
        self.assertEqual(router.readonly.queries, 1)
        self.assertEqual(router.lag.last_lag, 7.5)

    def test_the_verdict_is_cached_between_samples(self):
        router = _router(lag=1.0, max_lag=120.0)
        for _ in range(10):
            router.cursor(readonly=True)
        self.assertEqual(router.readonly.queries, 1)

    def test_a_demoted_gate_recovers_when_the_replica_catches_up(self):
        router = _router(lag=120.0, max_lag=30.0)
        router.lag.sample_interval = 0.0
        self.assertEqual(router.cursor(readonly=True)[1], "ro->rw")
        router.readonly.lag = 2.0
        self.assertEqual(router.cursor(readonly=True)[1], "ro")
        self.assertTrue(router.lag.is_replica_usable())

    def test_an_unreadable_measurement_does_not_demote(self):
        router = _router(max_lag=30.0)

        def boom(*args, **kwargs):
            raise RuntimeError("boom")

        original = router.readonly.cursor

        def cursor_with_broken_execute():
            cr = original()
            cr.execute = boom
            return cr

        router.readonly.cursor = cursor_with_broken_execute
        self.assertEqual(router.cursor(readonly=True)[1], "ro")
        self.assertTrue(router.lag.is_replica_usable())

    def test_a_lag_demotion_does_not_consume_the_breakers_probe(self):
        router = _router(lag=120.0, max_lag=30.0)
        breaker = router.breaker
        breaker.record_failure()
        breaker._opened_at -= breaker.initial_cooldown + 1

        lag = router.lag
        lag.record(120.0)
        lag.acquire_sample_interval()
        lag.sample_interval = 1e9
        self.assertFalse(lag.is_replica_usable())
        self.assertFalse(lag.acquire_sample_interval())

        self.assertEqual(router.cursor(readonly=True)[1], "ro->rw")
        self.assertEqual(breaker._probing_since, 0.0)
        self.assertTrue(breaker.acquire_attempt())


class TestReadonlyCursorEnabled(unittest.TestCase):
    def test_a_plain_deployment_opens_no_second_connection(self):
        self.assertIs(replica_module.is_readonly_cursor_enabled(PoolSettings()), False)

    def test_the_switch_is_the_snapshot_not_the_option_dict(self):
        with pool_settings.installed(PoolSettings(readonly_cursors=True)):
            self.assertIs(replica_module.is_readonly_cursor_enabled(), True)
        with pool_settings.installed(PoolSettings(readonly_cursors=False)):
            self.assertIs(replica_module.is_readonly_cursor_enabled(), False)

    def test_each_of_the_three_switches_enables_it(self):
        for key, value in (
            ("db_replica_host", "replica.example"),
            ("test_enable", True),
            ("dev_mode", ["replica"]),
        ):
            with self.subTest(key=key):
                options = configmanager()
                options[key] = value
                self.assertIs(PoolSettings.from_config(options).readonly_cursors, True)
        self.assertIs(PoolSettings.from_config(configmanager()).readonly_cursors, False)


if __name__ == "__main__":
    unittest.main()
