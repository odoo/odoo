import os
import unittest
from types import SimpleNamespace
from unittest import mock

import psutil

from odoo.service import db as db_service
from odoo.service._limits import get_memory_over_soft_limit, get_memory_rss


def _proc(rss):
    return SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=rss))


class TestMemorySoftLimit(unittest.TestCase):
    def test_disabled_limit_skips_the_proc_read(self):
        class Boom:
            def memory_info(self):
                raise AssertionError("RSS must not be read when the limit is 0")

        self.assertIsNone(get_memory_over_soft_limit(Boom(), 0))

    def test_under_limit_returns_none(self):
        self.assertIsNone(get_memory_over_soft_limit(_proc(100), 200))

    def test_at_limit_is_not_over(self):
        self.assertIsNone(get_memory_over_soft_limit(_proc(200), 200))

    def test_over_limit_returns_current_rss(self):
        self.assertEqual(get_memory_over_soft_limit(_proc(300), 200), 300)

    def test_the_reader_speaks_psutil_and_not_a_fake(self):
        # The fakes above answer whatever name the reader asks for, so a rename
        # of the psutil call inside `get_memory_rss` keeps them green while
        # every threaded server dies on its first `check_limits`. Measured
        # 2026-09-01 at 2176e0fd942: `process.get_memory_rss()` on a real
        # `psutil.Process`, AttributeError, warm server gone in 1.1s.
        self.assertGreater(get_memory_rss(psutil.Process(os.getpid())), 0)


class TestInternalDropIsUngated(unittest.TestCase):
    def test_drop_database_internal_ignores_allowlist(self):
        with (
            mock.patch.object(db_service.listing, "list_dbs") as list_dbs_mock,
            mock.patch("odoo.db.db_connect") as db_connect_mock,
        ):
            probe_cr = db_connect_mock.return_value.cursor.return_value
            probe_cr.fetchone.return_value = None
            result = db_service.drop_database("never_exposed_db")
        self.assertFalse(result)
        list_dbs_mock.assert_not_called()


class TestMemoryReadUsesTheRealPsutilContract(unittest.TestCase):
    def test_get_memory_rss_reads_a_real_psutil_process(self):
        import psutil

        from odoo.service._limits import get_memory_rss

        self.assertGreater(get_memory_rss(psutil.Process()), 0)
