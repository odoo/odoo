import gc
import sys
import threading
import time
import tracemalloc
import unittest
import weakref
from unittest import mock

from odoo.db import metrics
from odoo.tools import profiler as P


class _Payload:
    pass


def _busy(seconds):
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        pass


class _MetricsHost(metrics._MetricsMixin):
    def __init__(self):
        self._thread = threading.current_thread()
        self.sql_log_count = 0
        self.sql_statement_count = 0

    def _format_statement(self, query, params=None):
        return str(query)


def _run_statement(host, query):
    hooks = getattr(threading.current_thread(), "query_hooks", None)
    host._record_metrics(0.001, query=query, hooks=hooks)


class TestSamplerLeavesNothingBehind(unittest.TestCase):
    def test_the_profiled_function_locals_die_with_the_profile(self):
        def work():
            payload = _Payload()
            _busy(0.05)
            return weakref.ref(payload)

        collector = P.PeriodicCollector(interval=0.001)
        with P.Profiler(collectors=[collector], db=None, description="t"):
            ref = work()
        gc.collect()
        self.assertIsNone(collector.last_frame)
        self.assertIsNone(ref(), "the sampler's last frame kept the locals alive")

    def test_the_profiler_does_not_pin_the_frame_that_opened_it(self):
        def opener():
            payload = _Payload()
            profiler = P.Profiler(collectors=[], db=None, description="t")
            with profiler:
                pass
            return profiler, weakref.ref(payload)

        profiler, ref = opener()
        gc.collect()
        self.assertIsNone(profiler.init_frame)
        self.assertIsNone(ref(), "init_frame kept the opener's locals alive")
        self.assertTrue(profiler.init_stack_trace)


class _SlowAtStop(P.PeriodicCollector):
    def add(self, entry=None, frame=None):
        if getattr(self, "_stopping", False):
            time.sleep(0.05)
        super().add(entry, frame)

    def stop(self):
        self._stopping = True
        time.sleep(0.01)
        super().stop()


class _LateSampler(P.PeriodicCollector):
    def run(self):
        time.sleep(0.05)
        super().run()


class TestSamplerStop(unittest.TestCase):
    def test_the_terminator_is_the_last_entry(self):
        collector = _SlowAtStop(interval=0.001)
        with P.Profiler(collectors=[collector], db=None, description="t"):
            _busy(0.02)
        entries = collector.entries
        self.assertEqual(entries[-1]["stack"], [], "a sample landed after the end")
        self.assertTrue(entries[-2]["stack"])

    def test_a_stop_that_beats_the_sampler_does_not_hang(self):
        collector = _LateSampler(interval=0.001)
        done = threading.Event()

        def profile():
            with P.Profiler(collectors=[collector], db=None, description="t"):
                pass
            done.set()

        runner = threading.Thread(target=profile, daemon=True)
        runner.start()
        self.assertTrue(done.wait(2), "stop() waited forever on the sampler")
        runner.join(2)

    def test_the_sampler_does_not_keep_the_process_alive(self):
        collector = P.PeriodicCollector()
        self.assertTrue(collector._BasePeriodicCollector__thread.daemon)


class TestMemoryCollectorOwnsOnlyItsTrace(unittest.TestCase):
    def test_a_trace_started_elsewhere_survives_the_profile(self):
        tracemalloc.start()
        self.addCleanup(tracemalloc.stop)
        with P.Profiler(collectors=["memory"], db=None, description="t"):
            pass
        self.assertTrue(tracemalloc.is_tracing())

    def test_a_trace_it_started_is_stopped(self):
        self.assertFalse(tracemalloc.is_tracing())
        with P.Profiler(collectors=["memory"], db=None, description="t"):
            self.assertTrue(tracemalloc.is_tracing())
        self.assertFalse(tracemalloc.is_tracing())


class TestHookListsSurviveAnEndingProfiler(unittest.TestCase):
    def setUp(self):
        thread = threading.current_thread()
        for name in ("query_hooks", "profile_hooks"):
            if hasattr(thread, name):
                self.addCleanup(setattr, thread, name, getattr(thread, name))
                delattr(thread, name)
            else:
                self.addCleanup(lambda n=name: vars(thread).pop(n, None))

    def test_a_profiler_hitting_its_limit_does_not_blind_a_nested_one(self):
        host = _MetricsHost()
        outer = P.Profiler(
            collectors=["sql"],
            db=None,
            description="outer",
            params={"entry_count_limit": 1},
        )
        inner = P.Profiler(collectors=["sql"], db=None, description="inner")
        with outer, inner:
            for query in ("q1", "q2", "q3"):
                _run_statement(host, query)
        self.assertTrue(outer.done)
        self.assertEqual(
            [entry["query"] for entry in inner.collectors[0].entries],
            ["q1", "q2", "q3"],
        )

    def test_force_hook_reaches_every_sampler_when_one_ends(self):
        seen = []

        class _Recording(P.PeriodicCollector):
            _default_interval = 5

            def add(self, entry=None, frame=None):
                seen.append(self.profiler.description)

        outer = P.Profiler(
            collectors=[_Recording()],
            db=None,
            description="outer",
            params={"entry_count_limit": 1},
        )
        inner = P.Profiler(collectors=[_Recording()], db=None, description="inner")
        with outer, inner:
            time.sleep(0.05)
            seen.clear()
            outer.counter = outer.entry_count_limit
            P.force_hook()
        self.assertTrue(outer.done)
        self.assertEqual(seen, ["inner"])


class TestProfilerSummary(unittest.TestCase):
    def test_each_section_names_its_own_profiler(self):
        parent = P.Profiler(collectors=["sql"], db=None, description="parent")
        child = P.Profiler(collectors=["sql"], db=None, description="child")
        parent.sub_profilers.append(child)
        summary = parent.summary()
        self.assertEqual(summary.count("\nparent\n"), 1)
        self.assertEqual(summary.count("\nchild\n"), 1)


class TestCurrentFrame(unittest.TestCase):
    def test_the_current_thread_is_read_without_the_frame_table(self):
        def boom():
            msg = "sys._current_frames() walked for the current thread"
            raise AssertionError(msg)

        with mock.patch.object(sys, "_current_frames", boom):
            frame = P.get_current_frame(threading.current_thread())
        self.assertIs(
            frame.f_code,
            self.test_the_current_thread_is_read_without_the_frame_table.__code__,
        )

    def test_another_thread_is_read_from_the_frame_table(self):
        started, release = threading.Event(), threading.Event()

        def parked():
            started.set()
            release.wait(5)

        thread = threading.Thread(target=parked, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(release.set)
        started.wait(5)
        frame = P.get_current_frame(thread)
        names = []
        while frame is not None:
            names.append(frame.f_code.co_name)
            frame = frame.f_back
        self.assertIn("parked", names)


class TestCollectorRegistry(unittest.TestCase):
    def test_collectors_are_named_by_their_name_only(self):
        self.assertIs(P.Collector._registry["sql"], P.SQLCollector)
        self.assertNotIn("SQLCollector", P.Collector._registry)


if __name__ == "__main__":
    unittest.main()
