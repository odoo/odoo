import contextlib
import threading
import unittest

from odoo.db.lag import LAG_SQL, ReplicaLagGate


class TestDisabled(unittest.TestCase):
    def setUp(self):
        self.gate = ReplicaLagGate(0.0)

    def test_a_zero_ceiling_is_disabled(self):
        self.assertFalse(self.gate.enabled)

    def test_it_allows_everything(self):
        self.assertTrue(self.gate.is_replica_usable())

    def test_it_never_asks_for_a_sample(self):
        self.assertFalse(self.gate.acquire_sample_interval())

    def test_even_a_huge_recorded_lag_allows(self):
        self.gate.record(9999.0)
        self.assertTrue(self.gate.is_replica_usable())

    def test_a_negative_ceiling_is_rejected(self):
        with self.assertRaises(ValueError):
            ReplicaLagGate(-1.0)


class TestVerdict(unittest.TestCase):
    def setUp(self):
        self.gate = ReplicaLagGate(30.0)

    def test_a_fresh_gate_allows(self):
        self.assertTrue(self.gate.is_replica_usable())

    def test_lag_under_the_ceiling_allows(self):
        self.gate.record(5.0)
        self.assertTrue(self.gate.is_replica_usable())

    def test_lag_over_the_ceiling_demotes(self):
        self.gate.record(45.0)
        self.assertFalse(self.gate.is_replica_usable())

    def test_exactly_the_ceiling_still_allows(self):
        self.gate.record(30.0)
        self.assertTrue(self.gate.is_replica_usable())

    def test_recovery_reopens_the_gate(self):
        self.gate.record(45.0)
        self.gate.record(1.0)
        self.assertTrue(self.gate.is_replica_usable())

    def test_an_unmeasurable_lag_is_treated_as_healthy(self):
        self.gate.record(45.0)
        self.gate.record(None)
        self.assertTrue(self.gate.is_replica_usable())
        self.assertEqual(self.gate.last_lag, 0.0)

    def test_a_negative_measurement_is_clamped(self):
        self.gate.record(-3.0)
        self.assertEqual(self.gate.last_lag, 0.0)
        self.assertTrue(self.gate.is_replica_usable())


class TestSampling(unittest.TestCase):
    def test_the_interval_defaults_to_a_quarter_of_the_ceiling(self):
        self.assertEqual(ReplicaLagGate(120.0).sample_interval, 30.0)

    def test_the_interval_is_floored_at_a_second(self):
        self.assertEqual(ReplicaLagGate(0.4).sample_interval, 1.0)

    def test_the_first_sample_is_due(self):
        self.assertTrue(ReplicaLagGate(30.0).acquire_sample_interval())

    def test_a_second_sample_is_throttled(self):
        gate = ReplicaLagGate(30.0)
        self.assertTrue(gate.acquire_sample_interval())
        self.assertFalse(gate.acquire_sample_interval())

    def test_repeated_sequential_calls_are_throttled(self):
        gate = ReplicaLagGate(30.0)
        self.assertEqual(sum(1 for _ in range(50) if gate.acquire_sample_interval()), 1)

    def test_a_demoted_gate_still_becomes_due(self):
        gate = ReplicaLagGate(30.0, sample_interval=0.0)
        gate.acquire_sample_interval()
        gate.record(90.0)
        self.assertFalse(gate.is_replica_usable())
        self.assertTrue(gate.acquire_sample_interval())


class TestSampleClaimIsExclusive(unittest.TestCase):
    THREADS = 8
    BARRIER_TIMEOUT = 0.5

    class _BlockingInterval:
        def __init__(self, value, barrier):
            self.value = value
            self.barrier = barrier

        def __gt__(self, other):
            with contextlib.suppress(threading.BrokenBarrierError):
                self.barrier.wait(timeout=TestSampleClaimIsExclusive.BARRIER_TIMEOUT)
            return self.value > other

    def test_only_one_of_many_racing_readers_samples(self):
        gate = ReplicaLagGate(30.0)
        self.assertTrue(
            gate.acquire_sample_interval(), "the first call claims the slot"
        )
        gate._last_sample -= 1000.0

        barrier = threading.Barrier(self.THREADS)
        gate.sample_interval = self._BlockingInterval(30.0, barrier)  # type: ignore[assignment]

        granted = []
        append_lock = threading.Lock()

        def sample():
            claimed = gate.acquire_sample_interval()
            with append_lock:
                granted.append(claimed)

        threads = [threading.Thread(target=sample) for _ in range(self.THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive(), "acquire_sample_interval deadlocked")

        self.assertEqual(
            sum(granted),
            1,
            f"{sum(granted)} of {self.THREADS} readers claimed the sample slot "
            f"once the compare was made to yield; exactly one may. Removing the "
            f"lock from acquire_sample_interval reproduces this at {self.THREADS}",
        )


class TestLagSql(unittest.TestCase):
    def test_it_reports_zero_when_everything_received_is_replayed(self):
        self.assertIn("pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn()", LAG_SQL)

    def test_it_reports_zero_on_a_primary(self):
        self.assertIn("NOT pg_is_in_recovery()", LAG_SQL)

    def test_it_falls_back_to_the_replay_timestamp_only_when_behind(self):
        self.assertIn("pg_last_xact_replay_timestamp()", LAG_SQL)
        receive_check = LAG_SQL.index("pg_last_wal_receive_lsn")
        timestamp_use = LAG_SQL.index("pg_last_xact_replay_timestamp")
        self.assertLess(
            receive_check,
            timestamp_use,
            "the caught-up check must come first, or an idle primary reads as lag",
        )

    def test_the_sample_and_the_verdict_are_published_together(self):
        gate = ReplicaLagGate(10.0)
        stop = threading.Event()
        torn = []

        def writer():
            i = 0
            while not stop.is_set():
                gate.record(99.0 if i % 2 else 0.0)
                i += 1

        def reader():
            while not stop.is_set():
                snap = gate.get_snapshot()
                if (snap["last_lag_seconds"] > gate.max_lag) != snap["lagging"]:
                    torn.append(snap)
                    stop.set()
                    return

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        timer = threading.Timer(1.0, stop.set)
        timer.start()
        for t in threads:
            t.join()
        timer.cancel()
        self.assertEqual(torn, [], "snapshot rendered a sample against a stale verdict")

    def test_it_never_returns_null(self):
        self.assertIn("coalesce(", LAG_SQL)

    def test_a_null_receive_lsn_reads_as_caught_up_not_as_lag(self):
        null_check = LAG_SQL.index("pg_last_wal_receive_lsn() IS NULL")
        self.assertLess(
            null_check,
            LAG_SQL.index("pg_last_xact_replay_timestamp"),
            "the unanswerable case must be settled before the fallback",
        )

    def test_it_never_returns_a_negative(self):
        self.assertIn("greatest(", LAG_SQL)

    def test_outstanding_wal_with_nothing_replayed_yet_is_infinite_lag(self):
        unknown = LAG_SQL.index(
            "pg_last_xact_replay_timestamp() IS NULL THEN 'infinity'"
        )
        self.assertGreater(
            unknown,
            LAG_SQL.index("pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn()"),
            "caught up is settled first; only WAL received and not replayed "
            "reaches the timestamp",
        )
        self.assertLess(
            unknown,
            LAG_SQL.index("greatest("),
            "a NULL timestamp used to fall into the arithmetic, come out NULL, "
            "and be coalesced to 0: a fresh standby behind by 1.5 s of WAL "
            "answered 0 (measured)",
        )

    def test_the_gate_demotes_on_infinite_lag_and_recovers_on_a_number(self):
        gate = ReplicaLagGate(2.0)
        gate.record(float("inf"))
        self.assertFalse(gate.is_replica_usable())
        self.assertEqual(gate.get_snapshot()["last_lag_seconds"], float("inf"))
        gate.record(0.3)
        self.assertTrue(gate.is_replica_usable())


class TestSnapshot(unittest.TestCase):
    def test_a_disabled_gate_reports_disabled(self):
        snap = ReplicaLagGate(0.0).get_snapshot()
        self.assertFalse(snap["enabled"])
        self.assertFalse(snap["lagging"])

    def test_a_lagging_gate_reports_its_measurement(self):
        gate = ReplicaLagGate(10.0)
        gate.record(42.5)
        snap = gate.get_snapshot()
        self.assertTrue(snap["enabled"])
        self.assertTrue(snap["lagging"])
        self.assertEqual(snap["last_lag_seconds"], 42.5)
        self.assertEqual(snap["max_lag_seconds"], 10.0)


if __name__ == "__main__":
    unittest.main()
