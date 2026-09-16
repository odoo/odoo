import typing
import unittest

import psycopg

from odoo.db import replica as replica_module
from odoo.db import settings as pool_settings
from odoo.db.lag import ReplicaLagGate
from odoo.db.pool import PoolError
from odoo.db.replica import (
    REPLICA_BORROW_TIMEOUT,
    REPLICA_RETRY_TIME,
    ReplicaRouter,
    WritePins,
)
from odoo.db.settings import PoolSettings
from odoo.libs.breaker import CircuitBreaker
from odoo.tools.config import configmanager


class _Conn:
    def __init__(self, label, fails=False, lag=0.0):
        self.label = label
        self.dbname = label
        self.fails = fails
        self.lag = lag
        self.attempts = 0
        self.queries = 0
        self.opened = []

    def cursor(self, **borrow):
        self.attempts += 1
        self.borrow_options = borrow
        if self.fails:
            raise psycopg.OperationalError(f"{self.label} is down")
        cr = _Cursor(self)
        self.opened.append(cr)
        return cr


def _as_conn(conn: _Conn | None) -> typing.Any:
    return conn


class _Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.closed = False
        self.write_observer = None

    def on_commit_if_written(self, observer):
        self.write_observer = observer

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


class TestTheReplicaBorrowNeverWaitsOutTheBudget(unittest.TestCase):
    def test_the_replica_is_asked_with_a_short_deadline_and_fail_fast(self):
        primary, replica = _Conn("primary"), _Conn("replica")
        router = ReplicaRouter(_as_conn(primary), _as_conn(replica))
        _cr, mode = router.cursor(readonly=True)
        self.assertEqual(mode, "ro")
        self.assertEqual(
            replica.borrow_options,
            {"borrow_timeout": REPLICA_BORROW_TIMEOUT, "fail_fast": True},
            "a dead replica cost the first read-only request the whole "
            "db_borrow_timeout (30 s measured against a refused port), once "
            "per breaker half-open attempt; the primary is the fallback, so "
            "the replica borrow probes and gives up",
        )
        self.assertLess(REPLICA_BORROW_TIMEOUT, 30.0)

    def test_the_primary_keeps_the_full_budget(self):
        primary, replica = _Conn("primary"), _Conn("replica")
        router = ReplicaRouter(_as_conn(primary), _as_conn(replica))
        router.cursor(readonly=False)
        self.assertEqual(primary.borrow_options, {})


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

        def no_connection(**borrow):
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

        def cursor_with_broken_execute(**borrow):
            cr = original(**borrow)
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


class TestWritePins(unittest.TestCase):
    def test_a_pinned_key_expires_after_the_window(self):
        now = [100.0]
        pins = WritePins(2.0, clock=lambda: now[0])
        pins.pin("sid")
        self.assertTrue(pins.is_pinned("sid"))
        self.assertFalse(pins.is_pinned("other"))
        now[0] = 101.9
        self.assertTrue(pins.is_pinned("sid"))
        now[0] = 102.0
        self.assertFalse(pins.is_pinned("sid"))
        self.assertEqual(len(pins), 0, "an expired pin is dropped when it is read")

    def test_the_count_is_of_live_pins_not_of_table_entries(self):
        now = [100.0]
        pins = WritePins(2.0, clock=lambda: now[0])
        pins.pin("a")
        pins.pin("b")
        now[0] = 101.0
        pins.pin("c")
        now[0] = 102.5
        self.assertEqual(len(pins), 1, "a and b expired unread; c is live")
        self.assertEqual(len(pins._deadlines), 3, "expiry is lazy, the count is not")

    def test_a_zero_window_pins_nothing(self):
        pins = WritePins(0.0)
        pins.pin("sid")
        self.assertFalse(pins.is_pinned("sid"))

    def test_the_table_is_pruned_past_its_ceiling(self):
        pins = WritePins(60.0)
        pins._deadlines = dict.fromkeys(range(WritePins._PRUNE_ABOVE), 0.0)
        pins.pin("fresh")
        self.assertEqual(
            len(pins), 1, "expired pins go when the table grows past the ceiling"
        )

    def test_the_debug_channel_never_carries_the_key(self):
        pins = WritePins(60.0)
        with self.assertLogs(replica_module._debug.logic.logger, level="DEBUG") as cm:
            pins.pin("a-session-id-is-a-secret")
        self.assertEqual(len(cm.output), 1)
        self.assertNotIn("a-session-id", cm.output[0])
        self.assertIn("replica.pinned", cm.output[0])


class TestTheRouterReadsItsPolicyFromTheSettingsSlot(unittest.TestCase):
    def test_max_lag_and_write_pin_come_from_the_slot_unless_given(self):
        primary, replica = _Conn("primary"), _Conn("replica")
        with pool_settings.override(replica_max_lag=7.0, replica_write_pin=0.5):
            router = ReplicaRouter(_as_conn(primary), _as_conn(replica))
            explicit = ReplicaRouter(
                _as_conn(primary), _as_conn(replica), max_lag=1.0, write_pin=0.0
            )
        self.assertEqual((router.lag.max_lag, router.pins.window), (7.0, 0.5))
        self.assertEqual((explicit.lag.max_lag, explicit.pins.window), (1.0, 0.0))


class TestLiveRoutersAreVisibleToTheHealthSurface(unittest.TestCase):
    def test_a_router_with_a_replica_reports_under_its_database_name(self):
        before = set(replica_module.get_replica_health())
        primary, replica = _Conn("prod"), _Conn("replica")
        router = ReplicaRouter(_as_conn(primary), _as_conn(replica))
        health = replica_module.get_replica_health()
        self.assertIn("prod", health)
        self.assertEqual(
            set(health["prod"]), {"lag", "breaker", "write_pins"}, health["prod"]
        )
        self.assertTrue(health["prod"]["breaker"]["closed"])
        del router
        self.assertEqual(
            set(replica_module.get_replica_health()),
            before,
            "a collected router leaves the table; the reference is weak",
        )

    def test_a_router_without_a_replica_has_nothing_to_report(self):
        primary = _Conn("solo")
        router = ReplicaRouter(_as_conn(primary))
        self.assertNotIn("solo", replica_module.get_replica_health())
        del router


class TestReadYourWrites(unittest.TestCase):
    def _router(self, window=2.0):
        primary, replica = _Conn("primary"), _Conn("replica")
        return (
            ReplicaRouter(_as_conn(primary), _as_conn(replica), write_pin=window),
            primary,
            replica,
        )

    def test_a_rw_cursor_with_a_key_pins_it_when_the_transaction_wrote(self):
        router, _primary, replica = self._router()
        cursor, mode = router.cursor(readonly=False, pin_key="sid")
        cr = typing.cast("_Cursor", cursor)
        self.assertEqual(mode, "rw")
        observer = cr.write_observer
        self.assertIsNotNone(observer, "the cursor asks at commit")
        assert observer is not None
        self.assertFalse(router.pins.is_pinned("sid"), "nothing written yet")
        observer()
        self.assertTrue(router.pins.is_pinned("sid"))
        _cr, mode = router.cursor(readonly=True, pin_key="sid")
        self.assertEqual(
            mode, "ro->rw", "its next read-only request stays on the primary"
        )
        self.assertEqual(replica.attempts, 0)
        _cr, mode = router.cursor(readonly=True, pin_key="someone_else")
        self.assertEqual(mode, "ro", "another session still reads from the replica")

    def test_a_pinned_session_refreshes_its_pin_when_the_reused_cursor_writes(self):
        router, _primary, replica = self._router()
        clock = [0.0]
        router.pins = replica_module.WritePins(2.0, clock=lambda: clock[0])
        router.pins.pin("sid")
        clock[0] = 1.5
        cursor, mode = router.cursor(readonly=True, pin_key="sid")
        cr = typing.cast("_Cursor", cursor)
        self.assertEqual(mode, "ro->rw")
        observer = cr.write_observer
        self.assertIsNotNone(
            observer,
            "the primary cursor handed to a pinned session asks at commit too; "
            "http reuses it for the write route",
        )
        assert observer is not None
        observer()
        clock[0] = 3.0
        _cr, mode = router.cursor(readonly=True, pin_key="sid")
        self.assertEqual(mode, "ro->rw", "the write moved the deadline forward")
        self.assertEqual(replica.attempts, 0)

    def test_a_demoted_read_only_request_that_writes_pins_too(self):
        primary = _Conn("primary")
        replica = _Conn("replica", fails=True)
        router = ReplicaRouter(_as_conn(primary), _as_conn(replica), write_pin=2.0)
        cursor, mode = router.cursor(readonly=True, pin_key="sid")
        self.assertEqual(mode, "ro->rw")
        self.assertFalse(router.breaker.closed)
        observer = typing.cast("_Cursor", cursor).write_observer
        self.assertIsNotNone(
            observer, "the breaker-open fallback is a primary cursor like any other"
        )
        assert observer is not None
        observer()
        self.assertTrue(router.pins.is_pinned("sid"))

    def test_no_key_means_no_observer_and_no_pin(self):
        router, _primary, _replica = self._router()
        cr = typing.cast("_Cursor", router.cursor(readonly=False)[0])
        self.assertIsNone(cr.write_observer)

    def test_a_zero_window_registers_no_observer(self):
        router, _primary, _replica = self._router(window=0.0)
        cr = typing.cast("_Cursor", router.cursor(readonly=False, pin_key="sid")[0])
        self.assertIsNone(cr.write_observer, "no pin window, no round trip at commit")

    def test_without_a_replica_the_key_is_irrelevant(self):
        router = ReplicaRouter(_as_conn(_Conn("primary")), None, write_pin=2.0)
        cursor, mode = router.cursor(readonly=False, pin_key="sid")
        self.assertEqual(mode, "rw")
        self.assertIsNone(typing.cast("_Cursor", cursor).write_observer)
