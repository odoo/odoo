import logging
import os
import threading
import unittest
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

import psycopg
from psycopg_pool import PoolTimeout

from odoo.db import settings as pool_settings
from odoo.db.dsn import _get_dsn_key
from odoo.db.pool import (
    _DIRECT_CONNECTION,
    ConnectionBudget,
    ConnectionPool,
    PoolError,
    _get_base_connection_options,
    _get_seconds_remaining,
    _prepare_connection_options,
    _SuppressKnownPoolWarnings,
)
from odoo.db.probe import PROBE_CONNECT_TIMEOUT, get_libpq_connect_timeout
from odoo.db.reaper import _LAST_BORROW_ATTR, mark_active
from odoo.db.settings import PoolSettings

# As in test_probe: ConnectionPool() reads the settings slot, which nothing
# provides when this module runs alone.
_settings = pool_settings.installed(PoolSettings())


def setUpModule():
    _settings.__enter__()


def tearDownModule():
    _settings.__exit__(None, None, None)


def _fake_pool_factory(*_a, **_k):
    return _FakePool()


class TestBorrowBudgetHelpers(unittest.TestCase):
    def test_remaining_is_unbounded_without_a_deadline(self):
        self.assertEqual(_get_seconds_remaining(None), float("inf"))

    def test_remaining_counts_down_and_goes_negative(self):
        self.assertGreater(_get_seconds_remaining(monotonic() + 5), 4)
        self.assertLess(_get_seconds_remaining(monotonic() - 1), 0)

    def test_no_deadline_keeps_the_cap(self):
        self.assertEqual(get_libpq_connect_timeout(None, PROBE_CONNECT_TIMEOUT), 5)

    def test_ample_budget_keeps_the_cap(self):
        self.assertEqual(get_libpq_connect_timeout(monotonic() + 60, 5), 5)

    def test_tight_budget_shrinks_below_the_cap(self):
        self.assertEqual(get_libpq_connect_timeout(monotonic() + 3.9, 5), 3)

    def test_exhausted_budget_returns_zero_not_a_libpq_forever(self):
        for deadline in (monotonic() + 0.9, monotonic(), monotonic() - 10):
            with self.subTest(deadline=deadline):
                self.assertEqual(get_libpq_connect_timeout(deadline, 5), 0)


class TestBaseConnOptions(unittest.TestCase):
    def test_explicit_kwarg_wins(self):
        with patch.dict(os.environ, {"PGOPTIONS": "-c from_env=1"}):
            self.assertEqual(
                _get_base_connection_options(
                    "postgresql://h/db?options=-c%20from_uri%3D1",
                    {"options": "-c from_kwarg=1"},
                ),
                "-c from_kwarg=1",
            )

    def test_uri_options_beat_the_environment(self):
        with patch.dict(os.environ, {"PGOPTIONS": "-c from_env=1"}):
            self.assertEqual(
                _get_base_connection_options(
                    "postgresql://h/db?options=-c%20from_uri%3D1", {}
                ),
                "-c from_uri=1",
            )

    def test_environment_is_the_last_resort(self):
        with patch.dict(os.environ, {"PGOPTIONS": "-c from_env=1"}):
            self.assertEqual(_get_base_connection_options("", {}), "-c from_env=1")

    def test_nothing_configured_is_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(_get_base_connection_options("", {}), "")


class TestSuppressKnownPoolWarnings(unittest.TestCase):
    def _record(self, msg):
        return logging.LogRecord(
            "psycopg.pool", logging.WARNING, __file__, 1, msg, (), None
        )

    def test_expected_noise_is_dropped(self):
        f = _SuppressKnownPoolWarnings()
        self.assertFalse(f.filter(self._record("discarding closed connection: x")))
        self.assertFalse(f.filter(self._record('database "gone" does not exist')))

    def test_real_errors_survive(self):
        f = _SuppressKnownPoolWarnings()
        self.assertTrue(f.filter(self._record('role "nobody" does not exist')))
        self.assertTrue(f.filter(self._record("connection refused")))


class _FakePool:
    def __init__(self, size=1, available=1, closed=False, getconn_raises=None):
        self._stats = {"pool_size": size, "pool_available": available}
        self.closed = closed
        self.close_calls = 0
        self.drain_calls = 0
        self._getconn_raises = getconn_raises

    def get_stats(self):
        return dict(self._stats)

    def getconn(self, timeout=None):
        if self._getconn_raises is not None:
            raise self._getconn_raises
        raise NotImplementedError("this test needs _FakePool(getconn_raises=...)")

    def close(self):
        self.close_calls += 1
        self.closed = True

    def drain(self):
        self.drain_calls += 1


def _key(**kw):
    return frozenset(kw.items())


class TestConstructorValidation(unittest.TestCase):
    def test_rejects_non_positive_maxconn(self):
        for bad in (0, -1):
            with self.subTest(maxconn=bad), self.assertRaises(ValueError):
                ConnectionPool(maxconn=bad)

    def test_rejects_negative_minconn(self):
        with self.assertRaises(ValueError):
            ConnectionPool(maxconn=4, minconn=-1)

    def test_rejects_minconn_above_maxconn(self):
        with self.assertRaises(ValueError):
            ConnectionPool(maxconn=2, minconn=3)


class TestSemaphoreAccounting(unittest.TestCase):
    def test_give_back_of_an_untracked_connection_never_over_releases(self):
        pool = ConnectionPool(maxconn=3)

        class Conn:
            closed = False
            info = SimpleNamespace(dsn="dbname=x")

            def close(self):
                type(self).closed = True

        conn = Conn()
        pool.give_back(conn)
        self.assertEqual(pool._budget.available, 3)
        self.assertTrue(Conn.closed, "an unowned live connection must be closed")

    def test_direct_connection_release_is_claimed_exactly_once(self):
        pool = ConnectionPool(maxconn=3)
        pool._budget.acquire(1.0)
        with pool._lock:
            pool._direct_out += 1

        class Conn:
            closed = False
            info = SimpleNamespace(dsn="dbname=x")

            def __init__(self):
                self._odoo_pool = _DIRECT_CONNECTION

            def close(self):
                self.closed = True

        conn = Conn()
        pool.give_back(conn)
        self.assertEqual(pool._budget.available, 3)
        self.assertEqual(pool._direct_out, 0)
        self.assertTrue(conn.closed, "a maintenance-db connection is never pooled")

        pool.give_back(conn)
        self.assertEqual(pool._budget.available, 3)
        self.assertEqual(pool._direct_out, 0)

    def test_repr_counts_direct_connections(self):
        pool = ConnectionPool(maxconn=8)
        pool._pools = {_key(dbname="db"): _FakePool(size=3, available=1)}
        pool._direct_out = 2
        text = repr(pool)
        self.assertIn("used=2/total=3/limit=8", text)
        self.assertIn("direct=2", text)


class TestIdlePoolReaping(unittest.TestCase):
    def _pool(self, ttl=300.0):
        return ConnectionPool(maxconn=8, reap_idle_ttl=ttl)

    def test_disabled_when_ttl_is_not_positive(self):
        pool = self._pool(ttl=0)
        pool._pools = {_key(dbname="db"): _FakePool()}
        setattr(next(iter(pool._pools.values())), _LAST_BORROW_ATTR, monotonic() - 1e6)
        self.assertEqual(pool._reaper.get_keys_reapable(pool._pools), [])

    def test_reaps_only_pools_idle_past_the_ttl(self):
        pool = self._pool(ttl=10)
        fresh, stale = _FakePool(), _FakePool()
        setattr(fresh, _LAST_BORROW_ATTR, monotonic())
        setattr(stale, _LAST_BORROW_ATTR, monotonic() - 60)
        pool._pools = {_key(dbname="fresh"): fresh, _key(dbname="stale"): stale}
        self.assertEqual(
            [dict(k)["dbname"] for k in pool._reaper.get_keys_reapable(pool._pools)],
            ["stale"],
        )

    def test_never_reaps_a_pool_with_a_checked_out_connection(self):
        pool = self._pool(ttl=10)
        held = _FakePool(size=2, available=1)
        setattr(held, _LAST_BORROW_ATTR, monotonic() - 60)
        pool._pools = {_key(dbname="held"): held}
        self.assertEqual(pool._reaper.get_keys_reapable(pool._pools), [])

    def test_excluded_key_is_never_reaped(self):
        pool = self._pool(ttl=10)
        k = _key(dbname="mine")
        p = _FakePool()
        setattr(p, _LAST_BORROW_ATTR, monotonic() - 60)
        pool._pools = {k: p}
        self.assertEqual(pool._reaper.get_keys_reapable(pool._pools, exclude_key=k), [])

    def test_note_pool_activity_protects_a_returned_pool(self):
        pool = self._pool(ttl=10)
        p = _FakePool()
        setattr(p, _LAST_BORROW_ATTR, monotonic() - 60)
        pool._pools = {_key(dbname="db"): p}
        mark_active(p)
        self.assertEqual(pool._reaper.get_keys_reapable(pool._pools), [])

    def test_reap_check_interval_is_derived_and_floored(self):
        self.assertEqual(
            ConnectionPool(maxconn=4, reap_idle_ttl=400)._reaper.check_interval, 100
        )
        self.assertEqual(
            ConnectionPool(maxconn=4, reap_idle_ttl=0.4)._reaper.check_interval, 1.0
        )
        self.assertEqual(
            ConnectionPool(maxconn=4, reap_idle_ttl=0)._reaper.check_interval, 0.0
        )


class TestCloseAndDrainMatching(unittest.TestCase):
    def _pool_with(self):
        return ConnectionPool(maxconn=8)

    def test_close_database_matches_every_dsn_form(self):
        a, b, other = _FakePool(), _FakePool(), _FakePool()
        cp = self._pool_with()
        cp._pools = {
            _key(dbname="db", host="h1"): a,
            _key(dbname="db", host="h2", password_fp="ab"): b,
            _key(dbname="elsewhere"): other,
        }
        cp.close_database("db")
        self.assertEqual((a.close_calls, b.close_calls, other.close_calls), (1, 1, 0))
        self.assertEqual(list(cp._pools.values()), [other])

    def test_close_all_empties_the_registry(self):
        a, b = _FakePool(), _FakePool()
        cp = self._pool_with()
        cp._pools = {_key(dbname="a"): a, _key(dbname="b"): b}
        cp.close_all()
        self.assertEqual(cp._pools, {})
        self.assertTrue(a.close_calls and b.close_calls)

    def test_drain_database_skips_already_closed_pools(self):
        live, dead = _FakePool(), _FakePool(closed=True)
        cp = self._pool_with()
        cp._pools = {
            _key(dbname="db", host="a"): live,
            _key(dbname="db", host="b"): dead,
        }
        cp.drain_database("db")
        self.assertEqual((live.drain_calls, dead.drain_calls), (1, 0))

    def test_get_stats_is_keyed_by_database_name(self):
        cp = self._pool_with()
        cp._pools = {_key(dbname="db"): _FakePool(size=4, available=2)}
        self.assertEqual(cp.get_stats(), {"db": {"pool_size": 4, "pool_available": 2}})

    def test_health_reports_backends_summed_across_databases(self):
        cp = ConnectionPool(maxconn=2)
        cp._pools = {
            _key(dbname="a"): _FakePool(size=3, available=3),
            _key(dbname="b"): _FakePool(size=2, available=2),
        }
        health = cp.get_health()
        self.assertEqual(health["databases"], 2)
        self.assertEqual(health["backends"], 5)
        self.assertGreater(
            health["backends"],
            health["pool"]["budget_maxconn"],
            "the whole point: backends is not bounded by the budget",
        )

    def test_health_backends_includes_direct_connections(self):
        cp = ConnectionPool(maxconn=4)
        cp._pools = {_key(dbname="a"): _FakePool(size=1, available=1)}
        cp._direct_out = 2
        self.assertEqual(cp.get_health()["backends"], 3)

    def test_safe_close_and_drain_swallow_one_pools_failure(self):

        class Boom(_FakePool):
            def close(self):
                raise RuntimeError("boom")

            def drain(self):
                raise RuntimeError("boom")

        ConnectionPool._close_pool_safely(Boom())
        ConnectionPool._drain_pool_safely(Boom())


class TestPoolErrorIsRaisedForCapacity(unittest.TestCase):
    def test_exhausted_semaphore_reports_the_limit_and_direct_count(self):
        pool = ConnectionPool(maxconn=1, borrow_timeout=0.05)
        pool._budget.acquire(1.0)
        pool._direct_out = 2
        with patch.object(pool, "_get_or_create_pool", return_value=_FakePool()):
            with self.assertRaises(PoolError) as ctx:
                pool.borrow({"dbname": "somedb"})
        msg = str(ctx.exception)
        self.assertIn("connection budget (1)", msg)
        self.assertIn("2 direct maintenance connection(s)", msg)

    def test_borrow_budget_is_taken_before_pool_creation(self):
        pool = ConnectionPool(maxconn=1, borrow_timeout=2.0)
        pool._budget.acquire(1.0)
        seen = {}

        def fake_get_or_create(key, connection_info, deadline=None, **kw):
            seen["deadline"] = deadline
            return _FakePool()

        with patch.object(pool, "_get_or_create_pool", fake_get_or_create):
            start = monotonic()
            with self.assertRaises(PoolError):
                pool.borrow({"dbname": "somedb"})
            elapsed = monotonic() - start
        self.assertIsNotNone(
            seen["deadline"], "pool creation must receive the deadline"
        )
        self.assertLessEqual(elapsed, 3.0, "the semaphore wait must use what is left")


class TestConnectionBudgetSharing(unittest.TestCase):
    def test_a_shared_budget_is_consumed_by_both_pools(self):
        budget = ConnectionBudget(2)
        rw = ConnectionPool(maxconn=2, budget=budget)
        ro = ConnectionPool(maxconn=2, readonly=True, budget=budget)
        self.assertIs(rw._budget, ro._budget)
        self.assertFalse(rw.readonly)
        self.assertTrue(ro.readonly)
        self.assertTrue(rw._budget.acquire(0.01))
        self.assertTrue(rw._budget.acquire(0.01))
        self.assertFalse(
            ro._budget.acquire(0.01),
            "a shared budget must not hand out more than maxconn in total",
        )
        rw._budget.release()
        self.assertTrue(ro._budget.acquire(0.01), "a release frees it for either pool")
        ro._budget.release()
        rw._budget.release()

    def test_a_directly_constructed_pool_owns_its_budget(self):
        a, b = ConnectionPool(maxconn=2), ConnectionPool(maxconn=2)
        self.assertIsNot(a._budget, b._budget)
        self.assertTrue(a._budget.acquire(0.01))
        self.assertTrue(a._budget.acquire(0.01))
        self.assertTrue(b._budget.acquire(0.01))
        b._budget.release()
        a._budget.release()
        a._budget.release()

    def test_budget_rejects_a_non_positive_ceiling(self):
        for bad in (0, -1):
            with self.subTest(maxconn=bad), self.assertRaises(ValueError):
                ConnectionBudget(bad)

    def test_saturation_is_bounded_not_a_hang(self):
        budget = ConnectionBudget(1)
        ro = ConnectionPool(
            maxconn=1, readonly=True, budget=budget, borrow_timeout=0.05
        )
        budget.acquire(0.01)
        started = monotonic()
        with patch.object(ro, "_get_or_create_pool", return_value=_FakePool()):
            with self.assertRaises(PoolError):
                ro.borrow({"dbname": "somedb"})
        self.assertLess(
            monotonic() - started, 2.0, "must fail on the borrow timeout, not hang"
        )
        budget.release()

    def test_double_release_is_loud(self):
        budget = ConnectionBudget(1)
        budget.acquire(0.01)
        budget.release()
        with self.assertRaises(ValueError):
            budget.release()

    def test_note_pool_activity_needs_no_lock(self):
        p = _FakePool()
        errors = []

        def spin():
            try:
                for _ in range(2000):
                    mark_active(p)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=spin) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertIsInstance(getattr(p, _LAST_BORROW_ATTR), float)


if __name__ == "__main__":
    unittest.main()


class TestABugIsNotLaunderedIntoAPoolError(unittest.TestCase):
    def _borrow_against(self, exc):
        class Broken(_FakePool):
            def getconn(self, timeout=None):
                raise exc

        pool = ConnectionPool(maxconn=4, borrow_timeout=1.0)
        pool._probe.probe_connectable = lambda *a, **k: True  # type: ignore[method-assign]
        info = {"dbname": "bugdb", "host": "h"}
        with patch("odoo.db.pool._PsycopgPool", lambda *a, **k: Broken()):
            with self.assertRaises(type(exc)) as caught:
                pool.borrow(info)
        return pool, caught.exception

    def test_a_bug_keeps_its_type(self):
        bug = AttributeError("'NoneType' object has no attribute 'x'")
        _pool, raised = self._borrow_against(bug)
        self.assertIs(raised, bug)
        self.assertNotIsInstance(
            raised,
            PoolError,
            "as a PoolError it is swallowed by every caller that treats one "
            "as an unavailable database",
        )

    def test_the_permit_is_still_released(self):
        pool, _raised = self._borrow_against(KeyError("boom"))
        self.assertEqual(
            pool._budget.in_use,
            0,
            "the guard releases on BaseException; letting the type through "
            "must not change that",
        )

    def test_an_operational_failure_is_unaffected(self):
        pool = ConnectionPool(maxconn=4, borrow_timeout=1.0)
        pool._probe.probe_connectable = lambda *a, **k: True  # type: ignore[method-assign]

        class Timing(_FakePool):
            def getconn(self, timeout=None):
                raise PoolTimeout("couldn't get a connection")

        with patch("odoo.db.pool._PsycopgPool", lambda *a, **k: Timing()):
            with self.assertRaises(PoolError):
                pool.borrow({"dbname": "slowdb", "host": "h"})
        self.assertEqual(pool._budget.in_use, 0)


class TestCancelQueriesOf(unittest.TestCase):
    class _Conn:
        def __init__(self, fails=False):
            self.fails = fails
            self.cancelled = 0

        def cancel_safe(self, *, timeout=30.0):
            if self.fails:
                raise psycopg.OperationalError("connection gone")
            self.cancelled += 1

    def test_cancels_each_connection_the_thread_holds_and_counts_them(self):
        pool = ConnectionPool(maxconn=4)
        mine, also_mine, theirs, gone = (
            self._Conn(),
            self._Conn(),
            self._Conn(),
            self._Conn(fails=True),
        )
        for conn in (mine, also_mine, gone):
            pool._checkouts.track(conn)
        pool._checkouts.track(theirs)
        pool._checkouts._out[theirs] = pool._checkouts._out[theirs]._replace(
            thread="other-thread"
        )
        me = threading.current_thread().name
        self.assertEqual(pool.cancel_queries_of(me), 2)
        self.assertEqual(
            (mine.cancelled, also_mine.cancelled, theirs.cancelled), (1, 1, 0)
        )
        self.assertEqual(pool.cancel_queries_of("nobody"), 0)

    def test_a_connection_rehomed_while_the_list_aged_is_not_cancelled(self):
        pool = ConnectionPool(maxconn=4)
        slow, rehomed = self._Conn(), self._Conn()
        pool._checkouts.track(slow)
        pool._checkouts.track(rehomed)
        me = threading.current_thread().name

        def cancel_and_rehome(*, timeout):
            slow.cancelled += 1
            pool._checkouts.release(rehomed)
            pool._checkouts.track(rehomed)
            pool._checkouts._out[rehomed] = pool._checkouts._out[rehomed]._replace(
                thread="another-request"
            )

        slow.cancel_safe = cancel_and_rehome  # type: ignore[assignment, method-assign]
        self.assertEqual(pool.cancel_queries_of(me), 1)
        self.assertEqual(
            (slow.cancelled, rehomed.cancelled),
            (1, 0),
            "the cancel would have reached another request's statement",
        )

    def test_the_registry_fans_out_over_every_pool(self):
        from odoo.db.endpoints import EndpointRegistry

        reg = EndpointRegistry()
        with pool_settings.installed(PoolSettings()):
            rw = reg.get_pool_at_endpoint(("h", 5432), False)
            ro = reg.get_pool_at_endpoint(("h", 5432), True)
        a, b = self._Conn(), self._Conn()
        rw._checkouts.track(a)
        ro._checkouts.track(b)
        self.assertEqual(reg.cancel_queries_of(threading.current_thread().name), 2)


class TestIdleInTransactionTimeoutAtConnect(unittest.TestCase):
    def test_a_configured_timeout_is_a_startup_guc_in_milliseconds(self):
        options = _prepare_connection_options(
            "", {}, 5, session_gucs=None, idle_in_transaction_ms=90000
        )
        self.assertIn("-c idle_in_transaction_session_timeout=90000", options)

    def test_zero_leaves_the_server_setting_alone(self):
        options = _prepare_connection_options(
            "", {}, 5, session_gucs=None, idle_in_transaction_ms=0
        )
        self.assertNotIn("idle_in_transaction", options)

    def test_the_pool_reads_it_from_its_settings(self):
        with pool_settings.installed(PoolSettings(idle_in_transaction_timeout=90.0)):
            pool = ConnectionPool(maxconn=2)
        _conninfo, kwargs = pool._prepare_connect_args(
            _get_dsn_key({"dbname": "d"}), {"dbname": "d"}
        )
        self.assertIn("-c idle_in_transaction_session_timeout=90000", kwargs["options"])


class TestCancelDoesNotWaitOutAnUnreachableServer(unittest.TestCase):
    def test_cancel_safe_is_given_a_short_timeout(self):
        seen = {}

        class _Conn:
            def cancel_safe(self, *, timeout):
                seen["timeout"] = timeout

        pool = ConnectionPool(maxconn=2)
        pool._checkouts.track(_Conn())
        pool.cancel_queries_of(threading.current_thread().name)
        self.assertEqual(seen["timeout"], ConnectionPool._CANCEL_TIMEOUT)
        self.assertLess(
            ConnectionPool._CANCEL_TIMEOUT,
            30.0,
            "psycopg's default is 30 s per connection, in the thread that "
            "exists to enforce budgets",
        )
