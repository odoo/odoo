import gc
import subprocess
import sys
import unittest

from odoo.libs.gc import (
    _record_gc_timing,
    disabling_gc,
    freeze_survivors,
    gc_info,
    gc_set_timing,
    thaw,
)


class TestDisablingGc(unittest.TestCase):
    def setUp(self):
        was_enabled = gc.isenabled()
        gc.enable()
        self.addCleanup(gc.enable if was_enabled else gc.disable)

    def test_reenables_after_exception(self):
        with self.assertRaises(RuntimeError):
            with disabling_gc() as active:
                self.assertTrue(active)
                self.assertFalse(gc.isenabled())
                raise RuntimeError("boom")
        self.assertTrue(gc.isenabled())

    def test_reenables_after_normal_exit(self):
        with disabling_gc():
            self.assertFalse(gc.isenabled())
        self.assertTrue(gc.isenabled())

    def test_noop_when_already_disabled(self):
        gc.disable()
        try:
            with disabling_gc() as active:
                self.assertFalse(active)
                self.assertFalse(gc.isenabled())
        finally:
            gc.enable()


class TestGcSetTiming(unittest.TestCase):
    def tearDown(self):
        gc_set_timing(enable=False)

    def test_enable_registers_callback_once(self):
        self.assertNotIn(_record_gc_timing, gc.callbacks)
        gc_set_timing(enable=True)
        self.assertIn(_record_gc_timing, gc.callbacks)
        gc_set_timing(enable=True)
        self.assertEqual(gc.callbacks.count(_record_gc_timing), 1)

    def test_disable_unregisters_callback(self):
        gc_set_timing(enable=True)
        gc_set_timing(enable=False)
        self.assertNotIn(_record_gc_timing, gc.callbacks)

    def test_callback_is_gone_before_the_interpreter_tears_modules_down(self):
        script = (
            "import atexit, gc\n"
            "from odoo.libs import gc as libgc\n"
            "atexit.register(lambda: print(libgc._record_gc_timing in gc.callbacks))\n"
            "libgc.gc_set_timing(enable=True)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
        self.assertEqual(result.stdout.strip(), "False", result.stderr)
        self.assertNotIn("Exception ignored", result.stderr)

    def test_disable_when_not_registered_is_a_noop(self):
        gc_set_timing(enable=False)
        self.assertNotIn(_record_gc_timing, gc.callbacks)


class TestGcInfo(unittest.TestCase):
    def tearDown(self):
        gc_set_timing(enable=False)

    def test_shape_without_timing_enabled(self):
        info = gc_info()
        self.assertEqual(info["time"], ())
        self.assertIsInstance(info["cumulative_time"], float)
        self.assertEqual(len(info["count"]), len(gc.get_stats()))
        thresholds, limits = info["thresholds"]
        self.assertEqual(len(thresholds), len(gc.get_count()))
        self.assertEqual(limits, gc.get_threshold())

    def test_shape_with_timing_enabled_and_zero_collections(self):
        gc_set_timing(enable=True)
        info = gc_info()
        self.assertIsInstance(info["time"], list)
        self.assertEqual(len(info["time"]), len(gc.get_stats()))
        for entry in info["time"]:
            self.assertIn("avg_time_ms", entry)
            self.assertIn("time_ms", entry)
            self.assertIn("share", entry)
            self.assertEqual(entry["avg_time_ms"], 0.0)

    def test_share_after_a_real_collection(self):
        gc_set_timing(enable=True)
        gc.collect()
        info = gc_info()
        self.assertGreaterEqual(sum(entry["share"] for entry in info["time"]), 0.0)


if __name__ == "__main__":
    unittest.main()


class TestFreezeSurvivors(unittest.TestCase):
    def tearDown(self):
        gc.unfreeze()

    def test_garbage_is_collected_not_frozen(self):
        import weakref

        class Node:
            self: Node

        survivor = Node()
        cycle = Node()
        cycle.self = cycle
        cycle_ref = weakref.ref(cycle)
        del cycle
        freeze_survivors()
        self.assertIsNone(
            cycle_ref(), "a cycle frozen instead of collected leaks forever"
        )
        self.assertGreater(gc.get_freeze_count(), 0)
        self.assertNotIn(
            survivor, gc.get_objects(), "survivors leave the collected generations"
        )

    def test_thaw_returns_frozen_objects_to_collection(self):
        import weakref

        class Node:
            self: Node

        node = Node()
        node.self = node
        ref = weakref.ref(node)
        freeze_survivors()
        del node
        gc.collect()
        self.assertIsNotNone(ref(), "a frozen cycle is invisible to the collector")
        thaw()
        gc.collect()
        self.assertIsNone(ref())
        self.assertEqual(gc.get_freeze_count(), 0)
