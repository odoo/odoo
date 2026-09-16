import unittest
from time import monotonic
from types import SimpleNamespace
from unittest.mock import patch

import psycopg

from odoo.db import settings as pool_settings
from odoo.db.dsn import _get_dsn_key
from odoo.db.pool import ConnectionPool, PoolError
from odoo.db.settings import PoolSettings

# ConnectionPool() reads the settings slot; run alone, nothing has provided
# one (in the full suite an earlier import of odoo.tools does). Install a
# default for this module so its tests do not depend on collection order.
_settings = pool_settings.installed(PoolSettings())


def setUpModule():
    _settings.__enter__()


def tearDownModule():
    _settings.__exit__(None, None, None)


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


def _fake_pool_factory(*_a, **_k):
    return _FakePool()


def _record(calls: list, args: tuple, answer: bool = True) -> bool:
    calls.append(args)
    return answer


class TestReachabilityProof(unittest.TestCase):
    def _pool_with_probe_counter(self, **kw):
        pool = ConnectionPool(maxconn=2, **kw)
        calls: list[tuple] = []
        pool._probe.probe_connectable = lambda *a, **k: _record(calls, a)  # type: ignore[method-assign]
        return pool, calls

    def test_first_cold_start_probes(self):
        pool, calls = self._pool_with_probe_counter()
        key = _get_dsn_key({"dbname": "d"})
        with patch("odoo.db.pool._PsycopgPool", _fake_pool_factory):
            pool._get_or_create_pool(key, {"dbname": "d"})
        self.assertEqual(len(calls), 1, "an unseen DSN must be probed")

    def test_rebuild_after_a_proven_connect_skips_the_probe(self):
        pool, calls = self._pool_with_probe_counter()
        key = _get_dsn_key({"dbname": "d"})
        pool._probe.mark_proven(key)
        pool._pools.clear()
        with patch("odoo.db.pool._PsycopgPool", _fake_pool_factory):
            pool._get_or_create_pool(key, {"dbname": "d"})
        self.assertEqual(calls, [], "a proven DSN must not be re-probed")

    def test_close_database_revokes_the_proof(self):
        pool, calls = self._pool_with_probe_counter()
        key = _get_dsn_key({"dbname": "d"})
        pool._probe.mark_proven(key)
        pool.close_database("d")
        self.assertFalse(pool._probe.is_proven(key))
        with patch("odoo.db.pool._PsycopgPool", _fake_pool_factory):
            pool._get_or_create_pool(key, {"dbname": "d"})
        self.assertEqual(len(calls), 1, "a closed database must be probed again")

    def test_close_database_revokes_proofs_with_no_live_pool(self):
        pool, _ = self._pool_with_probe_counter()
        key = _get_dsn_key({"dbname": "d", "host": "h"})
        pool._probe.mark_proven(key)
        self.assertEqual(pool._pools, {})
        pool.close_database("d")
        self.assertFalse(pool._probe.is_proven(key))

    def test_other_databases_keep_their_proof(self):
        pool, _ = self._pool_with_probe_counter()
        keep = _get_dsn_key({"dbname": "other"})
        pool._probe.mark_proven(keep)
        pool._probe.mark_proven(_get_dsn_key({"dbname": "d"}))
        pool.close_database("d")
        self.assertTrue(pool._probe.is_proven(keep))

    def test_a_connect_failure_revokes_the_proof(self):
        pool = ConnectionPool(maxconn=2, borrow_timeout=0.05)
        key = _get_dsn_key({"dbname": "d"})
        pool._probe.mark_proven(key)
        failing = _FakePool(getconn_raises=psycopg.errors.InvalidCatalogName("gone"))
        with self.assertRaises(psycopg.Error):
            pool._get_connection_with_retry(
                failing, key, {"dbname": "d"}, monotonic() + 0.05
            )
        self.assertFalse(pool._probe.is_proven(key))

    def test_rotated_credentials_revoke_the_old_proof(self):
        pool, _ = self._pool_with_probe_counter()
        old = _get_dsn_key({"dbname": "d", "password": "old"})
        new = _get_dsn_key({"dbname": "d", "password": "new"})
        pool._probe.mark_proven(old)
        pool._pools[old] = _FakePool()
        with patch("odoo.db.pool._PsycopgPool", _fake_pool_factory):
            pool._get_or_create_pool(new, {"dbname": "d", "password": "new"})
        self.assertFalse(pool._probe.is_proven(old))


class TestTheDedupedProbeDoesNotShareATraceback(unittest.TestCase):
    def _run(self, followers=8):
        import threading
        import time

        pool = ConnectionPool(maxconn=8)
        key = _get_dsn_key({"dbname": "unreachable"})
        go = threading.Event()
        caught: dict = {}

        def slow_failing_probe(*_a, **_k):
            go.wait(20)
            raise RuntimeError("unreachable host")

        pool._probe.probe_connectable = slow_failing_probe  # type: ignore[method-assign]

        def call(tag):
            try:
                pool._probe.check_connectable(key, "", {})
            except Exception as exc:
                caught[tag] = exc

        leader = threading.Thread(target=call, args=("leader",), daemon=True)
        leader.start()
        time.sleep(0.2)
        threads = [
            threading.Thread(target=call, args=(i,), daemon=True)
            for i in range(followers)
        ]
        for t in threads:
            t.start()
        time.sleep(0.2)
        go.set()
        leader.join(20)
        for t in threads:
            t.join(20)
        return caught

    @staticmethod
    def _frames(exc):
        n, tb = 0, exc.__traceback__
        while tb is not None:
            n += 1
            tb = tb.tb_next
        return n

    def test_every_follower_still_gets_the_leaders_failure(self):
        caught = self._run()
        self.assertEqual(len(caught), 9, "leader plus every follower must raise")
        self.assertTrue(all(isinstance(e, RuntimeError) for e in caught.values()))

    def test_the_shared_traceback_does_not_grow_with_the_followers(self):
        few = self._run(followers=2)
        many = self._run(followers=8)
        self.assertEqual(
            self._frames(few["leader"]),
            self._frames(many["leader"]),
            "the traceback grew with the number of waiters: each follower "
            "raises the same object and a raise appends to it, so a dead DSN "
            "under load produced a stack of repeated frames from unrelated "
            "threads, each keeping its thread's locals alive",
        )


class TestLeaderRemovalAndCompletionAreAtomic(unittest.TestCase):
    def test_a_second_caller_cannot_observe_the_slot_free_before_done_is_set(self):
        import threading
        import time

        from odoo.db import probe as probe_module

        pool = ConnectionPool(maxconn=8)
        key = _get_dsn_key({"dbname": "atomic-check"})
        entered_finally = threading.Event()
        release_leader = threading.Event()
        real_set = threading.Event.set
        real_probe_init = probe_module._InFlightProbe.__init__
        first_done_id: dict = {}

        def tagging_init(self_probe):
            real_probe_init(self_probe)
            first_done_id.setdefault("id", id(self_probe.done))

        def slow_set(event_self):
            if id(event_self) == first_done_id.get("id"):
                entered_finally.set()
                release_leader.wait(5)
            real_set(event_self)

        def instant_probe(*_a, **_k):
            return None

        pool._probe.probe_connectable = instant_probe  # type: ignore[method-assign]

        def leader():
            pool._probe.check_connectable(key, "", {})

        leader_thread = threading.Thread(target=leader, daemon=True)
        second_returned = []

        def second_caller():
            pool._probe.check_connectable(key, "", {})
            second_returned.append(True)

        with (
            patch.object(probe_module._InFlightProbe, "__init__", tagging_init),
            patch.object(threading.Event, "set", slow_set),
        ):
            leader_thread.start()
            self.assertTrue(
                entered_finally.wait(5), "leader never reached the finally block"
            )
            second_thread = threading.Thread(target=second_caller, daemon=True)
            second_thread.start()
            time.sleep(0.2)
            self.assertEqual(
                second_returned,
                [],
                "a second caller returned from check_connectable while the "
                "leader was still inside its own del+set critical section -- "
                "del and set() are not atomic with respect to each other",
            )
            release_leader.set()
            leader_thread.join(5)
            second_thread.join(5)

        self.assertEqual(second_returned, [True])


if __name__ == "__main__":
    unittest.main()


class TestFailFast(unittest.TestCase):
    def _pool(self, connected):
        pool = ConnectionPool(maxconn=2)
        pool._probe.probe_connectable = lambda *a, **k: connected  # type: ignore[method-assign, return-value]
        return pool

    def test_a_transient_probe_failure_ends_a_fail_fast_borrow_at_once(self):
        pool = self._pool(False)
        key = _get_dsn_key({"dbname": "d"})
        with (
            patch("odoo.db.pool._PsycopgPool", _fake_pool_factory),
            self.assertRaisesRegex(PoolError, "fail_fast"),
        ):
            pool._get_or_create_pool(key, {"dbname": "d"}, fail_fast=True)
        self.assertEqual(pool._pools, {}, "no pool is built for a refused connect")

    def test_without_fail_fast_the_same_failure_still_builds_the_pool(self):
        pool = self._pool(False)
        key = _get_dsn_key({"dbname": "d"})
        with patch("odoo.db.pool._PsycopgPool", _fake_pool_factory):
            pool._get_or_create_pool(key, {"dbname": "d"})
        self.assertIn(key, pool._pools, "the primary waits its budget out")

    def test_a_proven_key_never_fails_fast(self):
        pool = self._pool(False)
        key = _get_dsn_key({"dbname": "d"})
        pool._probe.mark_proven(key)
        with patch("odoo.db.pool._PsycopgPool", _fake_pool_factory):
            pool._get_or_create_pool(key, {"dbname": "d"}, fail_fast=True)
        self.assertIn(key, pool._pools)

    def test_a_connected_answer_is_handed_back_as_is(self):
        pool = self._pool(True)
        key = _get_dsn_key({"dbname": "d"})
        self.assertTrue(pool._probe.check_connectable(key, "", {"dbname": "d"}))

    def test_a_follower_learns_the_leaders_answer(self):
        import threading

        pool = ConnectionPool(maxconn=2)
        release = threading.Event()

        def slow_refused(*a, **k):
            release.wait(2.0)
            return False

        pool._probe.probe_connectable = slow_refused  # type: ignore[method-assign]
        key = _get_dsn_key({"dbname": "d"})
        answers = []
        threads = [
            threading.Thread(
                target=lambda: answers.append(
                    pool._probe.check_connectable(key, "", {"dbname": "d"})
                )
            )
            for _ in range(3)
        ]
        for t in threads:
            t.start()
        release.set()
        for t in threads:
            t.join(3.0)
        self.assertEqual(answers, [False, False, False])


class TestFailFastOnASurvivingPool(unittest.TestCase):
    def test_an_unproven_pool_with_nothing_idle_is_probed_again(self):
        pool = ConnectionPool(maxconn=2)
        pool._probe.probe_connectable = lambda *a, **k: False  # type: ignore[method-assign]
        key = _get_dsn_key({"dbname": "d"})
        pool._pools[key] = _FakePool(size=2, available=0)
        with self.assertRaisesRegex(PoolError, "fail_fast"):
            pool._get_or_create_pool(key, {"dbname": "d"}, fail_fast=True)

    def test_a_proven_pool_or_one_with_an_idle_connection_is_handed_out(self):
        for proven, available in ((True, 0), (False, 1)):
            with self.subTest(proven=proven, available=available):
                pool = ConnectionPool(maxconn=2)
                pool._probe.probe_connectable = lambda *a, **k: False  # type: ignore[method-assign]
                key = _get_dsn_key({"dbname": "d"})
                if proven:
                    pool._probe.mark_proven(key)
                fake = _FakePool(size=2, available=available)
                pool._pools[key] = fake
                self.assertIs(
                    pool._get_or_create_pool(key, {"dbname": "d"}, fail_fast=True),
                    fake,
                )

    def test_without_fail_fast_a_surviving_pool_is_never_probed(self):
        pool = ConnectionPool(maxconn=2)
        calls: list[tuple] = []
        pool._probe.probe_connectable = lambda *a, **k: _record(calls, a, False)  # type: ignore[method-assign]
        key = _get_dsn_key({"dbname": "d"})
        fake = _FakePool(size=2, available=0)
        pool._pools[key] = fake
        self.assertIs(pool._get_or_create_pool(key, {"dbname": "d"}), fake)
        self.assertEqual(calls, [])


class TestAuthenticationIsClassifiedWithoutTheMessage(unittest.TestCase):
    # lc_messages translates every word of a connect failure; libpq's
    # needs_password/used_password do not.
    def _error(self, *, needs=False, used=False, pgconn=True):
        conn = SimpleNamespace(needs_password=needs, used_password=used)
        return psycopg.OperationalError(
            "FATAL: <translated, unreadable>", pgconn=conn if pgconn else None
        )

    def _probe(self, maintenance):
        pool = ConnectionPool(maxconn=2)
        pool._probe.ask_maintenance_db = lambda *a, **k: maintenance  # type: ignore[method-assign]
        return pool._probe

    def _connect_raising(self, exc):
        return patch("odoo.db.probe.psycopg.connect", side_effect=exc)

    def test_a_server_that_wanted_a_password_we_lacked_is_permanent(self):
        probe = self._probe("unknown")
        with (
            self._connect_raising(self._error(needs=True)),
            self.assertRaises(psycopg.errors.InvalidAuthorizationSpecification),
        ):
            probe.probe_connectable("", {"dbname": "d"})

    def test_a_password_the_server_rejected_twice_is_permanent(self):
        probe = self._probe("auth_failed")
        with (
            self._connect_raising(self._error(used=True)),
            self.assertRaises(psycopg.errors.InvalidAuthorizationSpecification),
        ):
            probe.probe_connectable("", {"dbname": "d"})

    def test_a_missing_database_behind_a_good_password_stays_a_missing_database(self):
        probe = self._probe("absent")
        with (
            self._connect_raising(self._error(used=True)),
            self.assertRaises(psycopg.errors.InvalidCatalogName),
        ):
            probe.probe_connectable("", {"dbname": "d"})

    def test_a_refusal_before_the_password_stage_is_transient(self):
        probe = self._probe("unknown")
        with self._connect_raising(self._error()):
            self.assertFalse(probe.probe_connectable("", {"dbname": "d"}))

    def test_a_used_password_with_a_reachable_present_database_is_transient(self):
        probe = self._probe("present")
        with self._connect_raising(self._error(used=True)):
            self.assertFalse(probe.probe_connectable("", {"dbname": "d"}))

    def test_an_error_without_a_pgconn_falls_back_to_transient(self):
        probe = self._probe("unknown")
        with self._connect_raising(self._error(needs=True, pgconn=False)):
            self.assertFalse(probe.probe_connectable("", {"dbname": "d"}))
