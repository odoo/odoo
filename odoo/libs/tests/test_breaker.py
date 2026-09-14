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
        self.breaker = CircuitBreaker(max_cooldown=1200, initial_cooldown=0.0)

    def test_the_window_elapsing_admits_a_probe(self):
        self.breaker.record_failure()
        self.assertTrue(self.breaker.acquire_attempt())

    def test_only_one_caller_probes(self):
        self.breaker.record_failure()
        self.assertEqual(sum(1 for _ in range(50) if self.breaker.acquire_attempt()), 1)

    def test_a_successful_probe_closes_and_resets_the_backoff(self):
        for _ in range(3):
            self.breaker.record_failure()
        self.assertTrue(self.breaker.acquire_attempt())
        self.breaker.record_success()
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
