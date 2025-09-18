"""Tests for the aggregate ORM profiler (odoo.tools.orm_profiler)."""

from odoo.orm.models.mixins import (
    cache as _cache_mod,
)

# The consuming modules import _orm_profiling_enabled as a local name,
# so we must patch them directly (changing the source module alone is not enough).
from odoo.orm.models.mixins import (
    crud as _crud_mod,
)
from odoo.orm.models.mixins import (
    read as _read_mod,
)
from odoo.orm.models.mixins import (
    search as _search_mod,
)
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import orm_profiler

_CONSUMER_MODULES = (_crud_mod, _read_mod, _search_mod, _cache_mod)


@tagged("-standard", "profiler")
class TestOrmProfiler(TransactionCase):
    """Test ORM profiler recording and reporting when enabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Save and enable the flag on the source module + all consumers
        cls._originals = [
            (orm_profiler, orm_profiler._orm_profiling_enabled),
            *((mod, mod._orm_profiling_enabled) for mod in _CONSUMER_MODULES),
        ]
        orm_profiler._orm_profiling_enabled = True
        for mod in _CONSUMER_MODULES:
            mod._orm_profiling_enabled = True
        # Create a fresh profiler on the transaction
        cls._original_profiler = cls.env.transaction._orm_profiler
        cls.env.transaction._orm_profiler = orm_profiler.OrmProfiler()

    @classmethod
    def tearDownClass(cls):
        for mod, val in cls._originals:
            mod._orm_profiling_enabled = val
        cls.env.transaction._orm_profiler = cls._original_profiler
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.profiler = self.env.transaction._orm_profiler
        self.profiler.clear()

    def test_create_recorded(self):
        """create() operations are recorded in profiler."""
        self.env["res.partner.category"].create(
            [{"name": f"Prof Cat {i}"} for i in range(3)]
        )

        entries = {
            key: stats
            for key, stats in self.profiler._data.items()
            if key[0] == "create" and key[1] == "res.partner.category"
        }
        self.assertTrue(entries, "create should be recorded")
        stats = next(iter(entries.values()))
        self.assertGreaterEqual(stats.count, 1)
        self.assertGreaterEqual(stats.records, 3)
        self.assertGreater(stats.time, 0)

    def test_write_recorded(self):
        """write() operations are recorded in profiler."""
        categories = self.env["res.partner.category"].create(
            [{"name": f"Prof Cat {i}"} for i in range(3)]
        )
        self.profiler.clear()

        categories.write({"name": "Updated"})

        entries = {
            key: stats
            for key, stats in self.profiler._data.items()
            if key[0] == "write" and key[1] == "res.partner.category"
        }
        self.assertTrue(entries, "write should be recorded")
        stats = next(iter(entries.values()))
        self.assertEqual(stats.records, 3)

    def test_unlink_recorded(self):
        """unlink() operations are recorded in profiler."""
        categories = self.env["res.partner.category"].create(
            [{"name": f"Prof Cat {i}"} for i in range(3)]
        )
        self.profiler.clear()

        categories.unlink()

        entries = {
            key: stats
            for key, stats in self.profiler._data.items()
            if key[0] == "unlink" and key[1] == "res.partner.category"
        }
        self.assertTrue(entries, "unlink should be recorded")

    def test_search_recorded(self):
        """search() operations are recorded in profiler."""
        self.profiler.clear()

        self.env["res.partner.category"].search([("name", "like", "Prof")])

        entries = {
            key: stats
            for key, stats in self.profiler._data.items()
            if key[0] == "search" and key[1] == "res.partner.category"
        }
        self.assertTrue(entries, "search should be recorded")

    def test_read_recorded(self):
        """read() operations are recorded in profiler."""
        categories = self.env["res.partner.category"].create(
            [{"name": f"Prof Cat {i}"} for i in range(3)]
        )
        self.profiler.clear()

        categories.read(["name"])

        entries = {
            key: stats
            for key, stats in self.profiler._data.items()
            if key[0] == "read" and key[1] == "res.partner.category"
        }
        self.assertTrue(entries, "read should be recorded")

    def test_report_emits_warning(self):
        """report() emits structured warning log."""
        self.env["res.partner.category"].create(
            [{"name": f"Report Cat {i}"} for i in range(3)]
        )

        with self.assertLogs("odoo.orm.profile", level="WARNING") as log:
            self.profiler.report()

        self.assertTrue(
            any("ORM Profile Summary" in msg for msg in log.output),
            "Report should emit ORM Profile Summary",
        )
        self.assertTrue(
            any("res.partner.category" in msg for msg in log.output),
            "Report should mention the model name",
        )

    def test_clear_resets_data(self):
        """clear() resets all profiler data."""
        self.env["res.partner.category"].create({"name": "Clear Test"})
        self.assertTrue(self.profiler._data, "Data should exist before clear")

        self.profiler.clear()

        self.assertFalse(self.profiler._data, "Data should be empty after clear")
        self.assertEqual(self.profiler._total_time, 0.0)

    def test_timing_accumulates(self):
        """Multiple operations accumulate timing correctly."""
        for i in range(3):
            self.env["res.partner.category"].create({"name": f"Acc Cat {i}"})

        total = sum(stats.time for stats in self.profiler._data.values())
        self.assertAlmostEqual(
            total,
            self.profiler._total_time,
            places=10,
            msg="Individual times should sum to _total_time",
        )


@tagged("-standard", "profiler")
class TestOrmProfilerDisabled(TransactionCase):
    """Test that profiling is zero-cost when disabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._originals = [
            (orm_profiler, orm_profiler._orm_profiling_enabled),
            *((mod, mod._orm_profiling_enabled) for mod in _CONSUMER_MODULES),
        ]
        orm_profiler._orm_profiling_enabled = False
        for mod in _CONSUMER_MODULES:
            mod._orm_profiling_enabled = False

    @classmethod
    def tearDownClass(cls):
        for mod, val in cls._originals:
            mod._orm_profiling_enabled = val
        super().tearDownClass()

    def test_no_profiler_when_disabled(self):
        """When disabled, CRUD operations succeed without profiler."""
        self.assertFalse(orm_profiler._orm_profiling_enabled)
        # Operations should not fail even without a profiler
        cat = self.env["res.partner.category"].create({"name": "Disabled Test"})
        cat.write({"name": "Updated"})
        cat.unlink()
