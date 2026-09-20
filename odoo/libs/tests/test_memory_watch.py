import logging
import unittest
import unittest.mock

from odoo.libs import memory_watch
from odoo.libs.memory_watch import MemoryWatch

MIB = 1024 * 1024


class TestMemoryWatch(unittest.TestCase):
    def _watch(self, readings, limit=0):
        readings = iter(readings)
        aborted = []
        watch = MemoryWatch(
            step=1024 * MIB,
            limit=limit,
            rss=lambda: next(readings),
            abort=lambda: aborted.append(True),
        )
        return watch, aborted

    def test_reports_once_per_step_crossed(self):
        watch, aborted = self._watch(
            [100 * MIB, 900 * MIB, 1100 * MIB, 1500 * MIB, 3200 * MIB]
        )
        with self.assertLogs(memory_watch._logger, logging.WARNING) as logs:
            reported = [watch.check() for _ in range(5)]
        self.assertEqual(reported, [True, False, True, False, True])
        self.assertEqual(len(logs.records), 3)
        self.assertIn("rss 3200 MiB", logs.records[-1].getMessage())
        self.assertIn("next report at 4096 MiB", logs.records[-1].getMessage())
        self.assertIn("test_memory_watch.py", logs.records[0].getMessage())
        self.assertFalse(aborted)

    def test_aborts_past_the_limit(self):
        watch, aborted = self._watch([500 * MIB, 2100 * MIB], limit=2048 * MIB)
        with self.assertLogs(memory_watch._logger, logging.WARNING) as logs:
            watch.check()
            watch.check()
        self.assertEqual(aborted, [True])
        self.assertEqual(logs.records[-1].levelno, logging.CRITICAL)
        self.assertIn("passed the limit of 2048 MiB", logs.records[-1].getMessage())

    def test_environ_off_by_default(self):
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(memory_watch.start_from_environ())

    def test_environ_limit_alone_reports_at_the_limit_step_and_starts_once(self):
        env = {memory_watch.LIMIT_VAR: "4096"}
        with (
            unittest.mock.patch.dict("os.environ", env, clear=True),
            unittest.mock.patch.object(MemoryWatch, "start") as start,
            unittest.mock.patch.object(memory_watch, "_started", []),
        ):
            watch = memory_watch.start_from_environ()
            self.assertIs(memory_watch.start_from_environ(), watch)
        assert watch is not None
        self.assertEqual((watch.step, watch.limit), (4096 * MIB, 4096 * MIB))
        self.assertEqual(start.call_count, 1)

    def test_read_rss_is_positive(self):
        self.assertGreater(memory_watch.read_rss(), 0)
