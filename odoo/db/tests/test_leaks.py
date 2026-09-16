import threading
import unittest
from time import monotonic

from odoo.db.leaks import Checkout, CheckoutTracker


class _Conn:
    pass


def _aged(seconds, thread="Thread-1", caller=None):
    return Checkout(monotonic() - seconds, thread, caller)


class TestTracking(unittest.TestCase):
    def setUp(self):
        self.tracker = CheckoutTracker()

    def test_a_tracked_connection_is_outstanding(self):
        self.tracker.track(_Conn())
        self.assertEqual(len(self.tracker), 1)

    def test_a_returned_connection_is_forgotten(self):
        conn = _Conn()
        self.tracker.track(conn)
        self.tracker.release(conn)
        self.assertEqual(len(self.tracker), 0)
        self.assertEqual(self.tracker.get_checkouts_outstanding(), [])

    def test_release_reports_how_long_it_was_held(self):
        conn = _Conn()
        self.tracker.track(conn)
        held = self.tracker.release(conn)
        assert held is not None
        self.assertGreaterEqual(held, 0.0)

    def test_releasing_an_untracked_connection_is_harmless(self):
        self.assertIsNone(self.tracker.release(_Conn()))

    def test_two_connections_are_tracked_independently(self):
        a, b = _Conn(), _Conn()
        self.tracker.track(a)
        self.tracker.track(b)
        self.tracker.release(a)
        self.assertEqual(len(self.tracker), 1)

    def test_re_tracking_the_same_connection_replaces_the_entry(self):
        conn = _Conn()
        self.tracker.track(conn)
        self.tracker._out[conn] = _aged(500)
        self.tracker.track(conn)
        self.assertLess(self.tracker.get_oldest_age(), 1.0)
        self.assertEqual(len(self.tracker), 1)

    def test_the_holding_thread_is_recorded(self):
        self.tracker.track(_Conn())
        self.assertEqual(
            self.tracker.get_checkouts_outstanding()[0].thread,
            threading.current_thread().name,
        )


class TestOutstanding(unittest.TestCase):
    def setUp(self):
        self.tracker = CheckoutTracker()

    def _put(self, seconds, thread="w", caller=None):
        conn = _Conn()
        self.tracker._out[conn] = _aged(seconds, thread, caller)
        return conn

    def test_older_than_filters(self):
        self._put(1)
        self._put(100)
        self.assertEqual(len(self.tracker.get_checkouts_outstanding(older_than=10)), 1)

    def test_results_are_oldest_first(self):
        self._put(5)
        self._put(300)
        self._put(50)
        ages = [c.get_age() for c in self.tracker.get_checkouts_outstanding()]
        self.assertEqual(ages, sorted(ages, reverse=True))

    def test_oldest_age_of_an_empty_tracker_is_zero(self):
        self.assertEqual(self.tracker.get_oldest_age(), 0.0)

    def test_oldest_age_tracks_the_longest_hold(self):
        self._put(5)
        self._put(300)
        self.assertGreater(self.tracker.get_oldest_age(), 299)


class TestDescribe(unittest.TestCase):
    def setUp(self):
        self.tracker = CheckoutTracker()

    def _put(self, seconds, thread="w", caller=None):
        self.tracker._out[_Conn()] = _aged(seconds, thread, caller)

    def test_nothing_outstanding_describes_as_empty(self):
        self.assertEqual(self.tracker.describe(), "")

    def test_nothing_past_the_threshold_describes_as_empty(self):
        self._put(1)
        self.assertEqual(self.tracker.describe(older_than=60), "")

    def test_it_names_the_thread_and_age(self):
        self._put(120, thread="odoo.service.http.request.5")
        described = self.tracker.describe()
        self.assertIn("odoo.service.http.request.5", described)
        self.assertIn("120", described)

    def test_it_includes_the_caller_when_one_was_captured(self):
        self._put(120, caller="/opt/odoo/addons/x/models/y.py:42")
        self.assertIn("y.py:42", self.tracker.describe())

    def test_it_omits_the_caller_when_none_was_recorded(self):
        self._put(120)
        self.assertNotIn(" at ", self.tracker.describe())

    def test_it_caps_the_list_and_counts_the_rest(self):
        for _ in range(10):
            self._put(120)
        described = self.tracker.describe(limit=3)
        self.assertEqual(described.count(";"), 2)
        self.assertIn("+7 more", described)


class TestReportThrottle(unittest.TestCase):
    def test_the_first_report_is_due(self):
        self.assertTrue(CheckoutTracker().acquire_report_interval(60))

    def test_a_second_report_is_throttled(self):
        tracker = CheckoutTracker()
        self.assertTrue(tracker.acquire_report_interval(60))
        self.assertFalse(tracker.acquire_report_interval(60))

    def test_only_one_of_many_racing_callers_reports(self):
        tracker = CheckoutTracker()
        self.assertEqual(
            sum(1 for _ in range(50) if tracker.acquire_report_interval(60)), 1
        )

    def test_the_throttle_is_independent_of_the_reaper(self):
        from odoo.db.reaper import IdlePoolReaper

        tracker, reaper = CheckoutTracker(), IdlePoolReaper(10)
        self.assertTrue(tracker.acquire_report_interval(60))
        self.assertTrue(
            reaper.acquire_check_interval(), "the reaper's slot must be untouched"
        )


if __name__ == "__main__":
    unittest.main()


class TestConnectionsOfAThread(unittest.TestCase):
    def test_only_the_named_threads_checkouts(self):
        tracker = CheckoutTracker()
        a, b, c = object(), object(), object()
        tracker.track(a)
        tracker.track(b)
        tracker._out[c] = tracker._out[b]._replace(thread="other")
        mine = tracker.get_connections_of(threading.current_thread().name)
        self.assertEqual({id(x) for x in mine}, {id(a), id(b)})
        self.assertEqual(tracker.get_connections_of("nobody"), [])
