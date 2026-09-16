import collections
import threading
import unittest
from time import monotonic

from odoo.db.reaper import (
    _LAST_BORROW_ATTR,
    IdlePoolReaper,
    close_idle_connections,
    get_checked_out_count,
    mark_active,
    trim_idle_to_ceiling,
)


class _FakePool:
    def __init__(self, size=1, available=1):
        self._size = size
        self._available = available

    def get_stats(self):
        return {"pool_size": self._size, "pool_available": self._available}


def _aged(seconds, **kwargs):
    pool = _FakePool(**kwargs)
    setattr(pool, _LAST_BORROW_ATTR, monotonic() - seconds)
    return pool


class TestCheckedOut(unittest.TestCase):
    def test_idle_pool_has_nothing_checked_out(self):
        self.assertEqual(get_checked_out_count(_FakePool(size=3, available=3)), 0)

    def test_a_held_connection_is_visible(self):
        self.assertEqual(get_checked_out_count(_FakePool(size=3, available=1)), 2)

    def test_a_pool_with_no_stats_reads_as_empty(self):
        class _Bare:
            def get_stats(self):
                return {}

        self.assertEqual(get_checked_out_count(_Bare()), 0)


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.reaper = IdlePoolReaper(10.0)

    def test_a_pool_idle_past_the_ttl_is_reapable(self):
        self.assertEqual(self.reaper.get_keys_reapable({"a": _aged(60)}), ["a"])

    def test_a_recently_active_pool_is_spared(self):
        self.assertEqual(self.reaper.get_keys_reapable({"a": _aged(1)}), [])

    def test_a_pool_still_holding_a_connection_is_spared(self):
        self.assertEqual(
            self.reaper.get_keys_reapable({"a": _aged(60, available=0)}), []
        )

    def test_the_excluded_key_is_never_reaped(self):
        pools = {"a": _aged(60), "b": _aged(60)}
        self.assertEqual(self.reaper.get_keys_reapable(pools, exclude_key="a"), ["b"])

    def test_an_unstamped_pool_is_treated_as_fresh(self):
        self.assertEqual(self.reaper.get_keys_reapable({"a": _FakePool()}), [])

    def test_note_activity_rescues_a_stale_pool(self):
        pool = _aged(60)
        mark_active(pool)
        self.assertEqual(self.reaper.get_keys_reapable({"a": pool}), [])

    def test_reaping_disabled_collects_nothing(self):
        self.assertEqual(IdlePoolReaper(0).get_keys_reapable({"a": _aged(1e6)}), [])
        self.assertFalse(IdlePoolReaper(0).enabled)


class TestThrottle(unittest.TestCase):
    def test_interval_is_a_quarter_of_the_ttl(self):
        self.assertEqual(IdlePoolReaper(400).check_interval, 100)

    def test_interval_is_floored_at_one_second(self):
        self.assertEqual(IdlePoolReaper(0.4).check_interval, 1.0)

    def test_disabled_reaping_has_no_interval(self):
        self.assertEqual(IdlePoolReaper(0).check_interval, 0.0)

    def test_the_first_sweep_is_due(self):
        self.assertTrue(IdlePoolReaper(10).acquire_check_interval())

    def test_a_second_sweep_is_throttled(self):
        reaper = IdlePoolReaper(10)
        self.assertTrue(reaper.acquire_check_interval())
        self.assertFalse(
            reaper.acquire_check_interval(), "two sweeps within the interval"
        )

    def test_only_one_of_many_racing_callers_claims_the_sweep(self):
        reaper = IdlePoolReaper(10)
        self.assertEqual(
            sum(1 for _ in range(50) if reaper.acquire_check_interval()), 1
        )

    def test_probably_due_agrees_with_due_before_any_sweep(self):
        reaper = IdlePoolReaper(10)
        self.assertTrue(reaper.is_probably_due())
        reaper.acquire_check_interval()
        self.assertFalse(reaper.is_probably_due(), "the cheap pre-check must follow")

    def test_probably_due_does_not_consume_the_slot(self):
        reaper = IdlePoolReaper(10)
        reaper.is_probably_due()
        self.assertTrue(
            reaper.acquire_check_interval(), "the lock-free pre-check must not stamp"
        )

    def test_disabled_reaping_is_never_due(self):
        self.assertFalse(IdlePoolReaper(0).acquire_check_interval())
        self.assertFalse(IdlePoolReaper(0).is_probably_due())


class _IdlePool:
    # The four psycopg_pool attributes close_idle_connections reads, shaped
    # as the contract suite pins them; `closed` records what went.
    def __init__(self, idle: int, checked_out: int = 0, min_size: int = 0, age=0.0):
        self._lock = threading.Lock()
        self._pool = collections.deque(f"c{i}" for i in range(idle))
        self._nconns = idle + checked_out
        self._nconns_min = idle
        self.min_size = min_size
        self.closed: list = []
        setattr(self, _LAST_BORROW_ATTR, monotonic() - age)

    def _close_connection(self, conn):
        self.closed.append(conn)


class TestTrimToCeiling(unittest.TestCase):
    def test_nothing_goes_while_the_total_is_within_the_ceiling(self):
        pools = {"a": _IdlePool(2), "b": _IdlePool(2)}
        self.assertEqual(trim_idle_to_ceiling(pools, 4), 0)
        self.assertEqual([p.closed for p in pools.values()], [[], []])

    def test_the_oldest_idle_of_the_least_recently_borrowed_pool_goes_first(self):
        fresh, stale = _IdlePool(3, age=1.0), _IdlePool(3, age=60.0)
        pools = {"fresh": fresh, "stale": stale}
        self.assertEqual(trim_idle_to_ceiling(pools, 4), 2)
        self.assertEqual(stale.closed, ["c0", "c1"], "oldest idle first, FIFO")
        self.assertEqual(fresh.closed, [])
        self.assertEqual((stale._nconns, len(stale._pool)), (1, 1))

    def test_checked_out_connections_count_but_cannot_be_trimmed(self):
        busy = _IdlePool(0, checked_out=3, age=60.0)
        other = _IdlePool(2, age=1.0)
        self.assertEqual(trim_idle_to_ceiling({"busy": busy, "o": other}, 3), 2)
        self.assertEqual(busy.closed, [])
        self.assertEqual(other.closed, ["c0", "c1"], "the excess comes from idle")

    def test_min_size_is_a_floor(self):
        pool = _IdlePool(3, min_size=2, age=60.0)
        self.assertEqual(close_idle_connections(pool, 3), 1)
        self.assertEqual(pool._nconns, 2)
        self.assertEqual(pool._nconns_min, 2, "the shrink bookkeeping follows")


if __name__ == "__main__":
    unittest.main()
