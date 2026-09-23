import unittest

from odoo.libs.breaker import CircuitBreaker


class TestClosedBreaker(unittest.TestCase):
    def test_a_fresh_breaker_allows_everything(self):
        breaker = CircuitBreaker(max_cooldown=1200)
        self.assertTrue(breaker.closed)
        self.assertTrue(all(breaker.acquire_attempt() for _ in range(10)))

    def test_success_on_a_closed_breaker_changes_nothing(self):
        breaker = CircuitBreaker(max_cooldown=1200)
        breaker.record_success()
        self.assertTrue(breaker.closed)
        self.assertEqual(breaker.cooldown_remaining, 0.0)


class TestOpening(unittest.TestCase):
    def setUp(self):
        self.breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)

    def test_one_failure_opens_it(self):
        self.breaker.record_failure()
        self.assertFalse(self.breaker.closed)
        self.assertFalse(self.breaker.acquire_attempt())

    def test_the_first_window_is_the_initial_cooldown(self):
        self.breaker.record_failure()
        self.assertAlmostEqual(self.breaker.cooldown_remaining, 60, delta=1)

    def _fail_a_probe(self, breaker):
        breaker._opened_at -= breaker._cooldown + 1
        assert breaker.acquire_attempt(), (
            "probe should be admitted once the window elapsed"
        )
        breaker.record_failure()

    def test_repeated_probe_cycles_double_the_window(self):
        widths = [round(self.breaker.cooldown_remaining)]
        self.breaker.record_failure()
        widths.append(round(self.breaker.cooldown_remaining))
        for _ in range(4):
            self._fail_a_probe(self.breaker)
            widths.append(round(self.breaker.cooldown_remaining))
        self.assertEqual(widths, [0, 60, 120, 240, 480, 960])

    def test_the_window_is_capped(self):
        self.breaker.record_failure()
        for _ in range(20):
            self._fail_a_probe(self.breaker)
        self.assertLessEqual(self.breaker.cooldown_remaining, 1200)

    def test_the_cap_is_never_worse_than_the_flat_window_it_replaced(self):
        breaker = CircuitBreaker(max_cooldown=20 * 60)
        breaker.record_failure()
        for _ in range(50):
            self._fail_a_probe(breaker)
        self.assertLessEqual(breaker.cooldown_remaining, 20 * 60)

    def test_a_burst_of_concurrent_failures_opens_only_the_initial_window(self):
        for _ in range(12):
            self.breaker.record_failure()
        self.assertEqual(self.breaker.trips, 1)
        self.assertEqual(self.breaker.failures, 12)
        self.assertAlmostEqual(self.breaker.cooldown_remaining, 60, delta=1)

    def test_trips_counts_open_transitions_not_failures(self):
        for _ in range(4):
            self.breaker.record_failure()
        self.assertEqual(self.breaker.trips, 1)
        self.assertEqual(self.breaker.failures, 4)


class TestProbing(unittest.TestCase):
    def setUp(self):
        self.breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)

    def _trip_and_elapse(self, failures=1):
        for _ in range(failures):
            self.breaker.record_failure()
        self.breaker._opened_at -= 61

    def test_the_window_elapsing_admits_a_probe(self):
        self._trip_and_elapse()
        self.assertTrue(self.breaker.acquire_attempt())

    def test_only_one_caller_probes(self):
        self._trip_and_elapse()
        self.assertEqual(sum(1 for _ in range(50) if self.breaker.acquire_attempt()), 1)

    def test_a_successful_probe_closes_and_resets_the_backoff(self):
        self._trip_and_elapse(3)
        probe = self.breaker.acquire_attempt()
        self.assertTrue(probe)
        self.breaker.record_success(probe)
        self.assertTrue(self.breaker.closed)
        self.breaker.record_failure()
        self.assertEqual(self.breaker.failures, 1, "the backoff must start over")

    def test_a_failed_probe_widens_the_window_again(self):
        breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)
        breaker.record_failure()
        first = breaker.cooldown_remaining
        breaker._opened_at -= 61
        self.assertTrue(breaker.acquire_attempt())
        breaker.record_failure()
        self.assertGreater(breaker.cooldown_remaining, first)

    def test_an_abandoned_probe_does_not_wedge_the_breaker(self):
        breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)
        breaker.record_failure()
        breaker._opened_at -= 61
        self.assertTrue(breaker.acquire_attempt(), "first probe claimed")
        self.assertFalse(
            breaker.acquire_attempt(), "second blocked while the probe runs"
        )
        breaker._probing_since -= 61
        self.assertTrue(
            breaker.acquire_attempt(), "an abandoned probe must be reclaimable"
        )


class TestAttemptTickets(unittest.TestCase):
    def setUp(self):
        self.breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)

    def test_a_call_started_before_the_trip_does_not_touch_the_probe(self):
        late = self.breaker.acquire_attempt()
        self.breaker.record_failure(self.breaker.acquire_attempt())
        self.breaker._opened_at -= 61
        probe = self.breaker.acquire_attempt()
        self.assertTrue(probe and probe.probe)
        self.breaker.record_failure(late)
        self.assertAlmostEqual(self.breaker.cooldown_remaining, 0, delta=1)
        self.assertIsNone(
            self.breaker.acquire_attempt(), "the probe is still in flight"
        )
        self.breaker.record_failure(probe)
        self.assertAlmostEqual(self.breaker.cooldown_remaining, 120, delta=2)

    def test_a_late_success_from_before_the_trip_does_not_close(self):
        late = self.breaker.acquire_attempt()
        self.breaker.record_failure(self.breaker.acquire_attempt())
        self.breaker.record_success(late)
        self.assertFalse(self.breaker.closed)

    def test_an_abandoned_probe_reporting_late_is_ignored(self):
        self.breaker.record_failure()
        self.breaker._opened_at -= 61
        first = self.breaker.acquire_attempt()
        self.breaker._probing_since -= 61
        second = self.breaker.acquire_attempt()
        self.assertTrue(second)
        self.breaker.record_failure(first)
        self.assertIsNone(self.breaker.acquire_attempt())
        self.breaker.record_success(second)
        self.assertTrue(self.breaker.closed)

    def test_a_failure_from_before_a_recovery_does_not_count_after_it(self):
        breaker = CircuitBreaker(
            max_cooldown=1200, initial_cooldown=60, failure_threshold=2
        )
        late = breaker.acquire_attempt()
        breaker.record_failure()
        breaker.record_failure()
        breaker._opened_at -= 61
        breaker.record_success(breaker.acquire_attempt())
        breaker.record_failure(late)
        breaker.record_failure(breaker.acquire_attempt())
        self.assertTrue(breaker.closed, "one current failure is below threshold")


class TestConcurrentPileOn(unittest.TestCase):
    def test_a_thundering_herd_of_failures_still_opens_one_short_window(self):
        import threading

        breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)
        barrier = threading.Barrier(24)

        def fail():
            barrier.wait()
            breaker.record_failure()

        threads = [threading.Thread(target=fail) for _ in range(24)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(breaker.trips, 1, "exactly one closed→open transition")
        self.assertEqual(breaker.failures, 24)
        self.assertAlmostEqual(breaker.cooldown_remaining, 60, delta=2)


class TestSnapshot(unittest.TestCase):
    def test_a_healthy_breaker_reports_closed(self):
        snap = CircuitBreaker(max_cooldown=1200).get_snapshot()
        self.assertTrue(snap["closed"])
        self.assertEqual(snap["failures"], 0)
        self.assertEqual(snap["cooldown_seconds"], 0.0)

    def test_an_open_breaker_reports_its_window(self):
        breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)
        breaker.record_failure()
        snap = breaker.get_snapshot()
        self.assertFalse(snap["closed"])
        self.assertEqual(snap["failures"], 1)
        self.assertEqual(snap["trips"], 1)
        self.assertEqual(snap["cooldown_seconds"], 60.0)


class TestConstruction(unittest.TestCase):
    def test_a_non_positive_first_step_is_rejected(self):
        for cooldown in (0.0, -1.0):
            with self.subTest(cooldown=cooldown), self.assertRaises(ValueError):
                CircuitBreaker(max_cooldown=1200, initial_cooldown=cooldown)

    def test_a_ceiling_below_the_first_step_is_rejected(self):
        with self.assertRaises(ValueError):
            CircuitBreaker(max_cooldown=0.5, initial_cooldown=1.0)


class TestFailureThreshold(unittest.TestCase):
    def test_the_default_still_opens_on_the_first_failure(self):
        breaker = CircuitBreaker(max_cooldown=1200)
        breaker.record_failure()
        self.assertFalse(breaker.closed)

    def test_failures_below_the_threshold_keep_it_closed(self):
        breaker = CircuitBreaker(max_cooldown=1200, failure_threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        self.assertTrue(breaker.closed)
        self.assertTrue(breaker.acquire_attempt())
        breaker.record_failure()
        self.assertFalse(breaker.closed)
        self.assertEqual(breaker.trips, 1)
        self.assertEqual(breaker.failures, 3)

    def test_a_success_resets_the_count_toward_the_threshold(self):
        breaker = CircuitBreaker(max_cooldown=1200, failure_threshold=2)
        breaker.record_failure()
        breaker.record_success()
        breaker.record_failure()
        self.assertTrue(breaker.closed)

    def test_failures_older_than_the_window_do_not_count(self):
        breaker = CircuitBreaker(
            max_cooldown=1200, failure_threshold=2, failure_window=30
        )
        breaker.record_failure()
        breaker._recent_failures[0] -= 31
        breaker.record_failure()
        self.assertTrue(breaker.closed, "the first failure fell out of the window")
        breaker.record_failure()
        self.assertFalse(breaker.closed)

    def test_reopening_after_a_probe_counts_from_zero_again(self):
        breaker = CircuitBreaker(
            max_cooldown=1200, initial_cooldown=60, failure_threshold=2
        )
        breaker.record_failure()
        breaker.record_failure()
        breaker._opened_at -= 61
        self.assertTrue(breaker.acquire_attempt())
        breaker.record_success()
        breaker.record_failure()
        self.assertTrue(breaker.closed)

    def test_the_snapshot_names_the_threshold_and_window(self):
        snap = CircuitBreaker(
            max_cooldown=1200, failure_threshold=5, failure_window=60
        ).get_snapshot()
        self.assertEqual(snap["failure_threshold"], 5)
        self.assertEqual(snap["failure_window_seconds"], 60)

    def test_an_impossible_threshold_or_window_is_rejected(self):
        with self.assertRaises(ValueError):
            CircuitBreaker(max_cooldown=10, failure_threshold=0)
        with self.assertRaises(ValueError):
            CircuitBreaker(max_cooldown=10, failure_window=0)


class TestUnsettledAttempts(unittest.TestCase):
    def _probing(self):
        breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)
        breaker.record_failure()
        breaker._opened_at -= 61
        probe = breaker.acquire_attempt()
        self.assertTrue(probe.probe)
        self.assertIsNone(breaker.acquire_attempt())
        return breaker, probe

    def test_a_released_probe_frees_the_slot_for_the_next_caller(self):
        breaker, probe = self._probing()
        breaker.release(probe)
        self.assertTrue(breaker.acquire_attempt().probe)

    def test_releasing_a_stale_or_ordinary_attempt_changes_nothing(self):
        breaker, probe = self._probing()
        breaker.release(None)
        stale = type(probe)(probe.generation - 1, probe=True, breaker=probe.breaker)
        breaker.release(stale)
        self.assertIsNone(breaker.acquire_attempt())

    def test_a_stale_success_on_a_closed_breaker_keeps_the_failure_count(self):
        breaker = CircuitBreaker(
            max_cooldown=1200, initial_cooldown=60, failure_threshold=2
        )
        early = breaker.acquire_attempt()
        breaker.record_failure(breaker.acquire_attempt())
        breaker.record_failure(breaker.acquire_attempt())
        self.assertFalse(breaker.closed)
        breaker._opened_at -= 61
        breaker.record_success(breaker.acquire_attempt())
        self.assertTrue(breaker.closed)
        breaker.record_failure(breaker.acquire_attempt())
        breaker.record_success(early)
        self.assertEqual(len(breaker._recent_failures), 1)
        self.assertEqual(breaker.failures, 1)

    def test_an_attempt_of_another_breaker_is_stale(self):
        old = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)
        new = CircuitBreaker(max_cooldown=1200, initial_cooldown=60)
        foreign = old.acquire_attempt()
        new.record_failure(new.acquire_attempt())
        self.assertEqual(new.acquire_attempt(), None)
        new._opened_at -= 61
        probe = new.acquire_attempt()
        forged = type(probe)(probe.generation, probe=True, breaker=old._id)
        new.release(forged)
        self.assertIsNone(new.acquire_attempt(), "a foreign release freed the slot")
        new.record_success(foreign)
        new.record_success(forged)
        self.assertFalse(new.closed)
        new.record_success(probe)
        self.assertTrue(new.closed)
