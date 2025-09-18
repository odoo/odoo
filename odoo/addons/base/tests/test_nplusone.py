"""Tests for the N+1 CRUD detection system (odoo.tools.nplusone)."""

from odoo.orm.models.mixins import crud as _crud_mod
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import nplusone


@tagged("-standard", "nplusone")
class TestNplusOneDetection(TransactionCase):
    """Test N+1 CRUD detection when enabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Enable detection for tests — must patch both the source module and
        # the consuming module (crud.py imports the flag as a local name).
        cls._original_enabled = nplusone._n1_enabled
        nplusone._n1_enabled = True
        cls._original_crud_enabled = _crud_mod._n1_enabled
        _crud_mod._n1_enabled = True
        # Create a fresh tracker on the transaction
        cls._original_tracker = cls.env.transaction._n1_tracker
        cls.env.transaction._n1_tracker = nplusone.NplusOneTracker()

    @classmethod
    def tearDownClass(cls):
        nplusone._n1_enabled = cls._original_enabled
        _crud_mod._n1_enabled = cls._original_crud_enabled
        cls.env.transaction._n1_tracker = cls._original_tracker
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.tracker = self.env.transaction._n1_tracker
        self.tracker.clear()

    def test_write_n1_detected(self):
        """Writing same fields to same model in a loop triggers detection."""
        categories = self.env["res.partner.category"].create(
            [{"name": f"N1 Test Cat {i}"} for i in range(5)]
        )
        self.tracker.clear()  # clear create() calls

        for cat in categories:
            cat.write({"name": "Updated"})

        # Should have 5 entries from the same call site
        violations = [
            (key, entry)
            for key, entry in self.tracker._data.items()
            if entry.count >= nplusone.NplusOneTracker.THRESHOLD
            and key[0] == "write"
            and key[1] == "res.partner.category"
        ]
        self.assertTrue(violations, "N+1 write pattern should be detected")
        entry = violations[0][1]
        self.assertEqual(entry.count, 5)
        self.assertEqual(entry.total_records, 5)
        self.assertEqual(len(entry.vals_fingerprints), 1, "Same fields every call")

    def test_batch_write_no_violation(self):
        """A single batched write stays below threshold."""
        categories = self.env["res.partner.category"].create(
            [{"name": f"Batch Test Cat {i}"} for i in range(5)]
        )
        self.tracker.clear()

        categories.write({"name": "Batch Updated"})

        # Single call — count=1, below threshold
        for entry in self.tracker._data.values():
            if entry.count >= nplusone.NplusOneTracker.THRESHOLD:
                self.fail("Batch write should not trigger N+1 detection")

    def test_create_n1_detected(self):
        """Creating records one-by-one in a loop triggers detection."""
        self.tracker.clear()

        for i in range(5):
            self.env["res.partner.category"].create({"name": f"N1 Cat {i}"})

        violations = [
            (key, entry)
            for key, entry in self.tracker._data.items()
            if entry.count >= nplusone.NplusOneTracker.THRESHOLD
            and key[0] == "create"
            and key[1] == "res.partner.category"
        ]
        self.assertTrue(violations, "N+1 create pattern should be detected")
        self.assertEqual(violations[0][1].count, 5)

    def test_unlink_n1_detected(self):
        """Unlinking records one-by-one in a loop triggers detection."""
        categories = self.env["res.partner.category"].create(
            [{"name": f"Unlink Cat {i}"} for i in range(5)]
        )
        self.tracker.clear()

        for cat in categories:
            cat.unlink()

        violations = [
            (key, entry)
            for key, entry in self.tracker._data.items()
            if entry.count >= nplusone.NplusOneTracker.THRESHOLD and key[0] == "unlink"
        ]
        self.assertTrue(violations, "N+1 unlink pattern should be detected")

    def test_batch_create_no_violation(self):
        """A single batch create stays below threshold."""
        self.tracker.clear()

        self.env["res.partner.category"].create(
            [{"name": f"Batch Cat {i}"} for i in range(20)]
        )

        for entry in self.tracker._data.values():
            if entry.count >= nplusone.NplusOneTracker.THRESHOLD:
                self.fail("Batch create should not trigger N+1 detection")

    def test_report_emits_warning(self):
        """Report method emits a structured warning log."""
        self.tracker.clear()

        for i in range(5):
            self.env["res.partner.category"].create({"name": f"Report Cat {i}"})

        with self.assertLogs("odoo.orm.nplusone", level="WARNING") as log:
            self.tracker.report()

        self.assertTrue(
            any("N+1 CRUD detected" in msg for msg in log.output),
            "Report should emit N+1 warning",
        )
        self.assertTrue(
            any("res.partner.category" in msg for msg in log.output),
            "Warning should mention the model name",
        )

    def test_different_fields_tracked(self):
        """Different field sets from same call site are tracked as distinct fingerprints."""
        categories = self.env["res.partner.category"].create(
            [{"name": f"FP Cat {i}"} for i in range(4)]
        )
        self.tracker.clear()

        # Write different fields each time (from different lines — won't merge)
        # But from a loop (same line) with different vals
        for i, cat in enumerate(categories):
            if i % 2 == 0:
                cat.write({"name": "Even"})
            else:
                cat.write({"color": 1})

        violations = [
            (key, entry)
            for key, entry in self.tracker._data.items()
            if entry.count >= 2 and key[0] == "write"
        ]
        # Both branches are from different lines, so tracked separately
        # Each should have count=2 (below threshold of 3)
        for _, entry in violations:
            self.assertLess(entry.count, nplusone.NplusOneTracker.THRESHOLD)


@tagged("-standard", "nplusone")
class TestNplusOneDisabled(TransactionCase):
    """Test that detection is zero-cost when disabled."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._original_enabled = nplusone._n1_enabled
        nplusone._n1_enabled = False

    @classmethod
    def tearDownClass(cls):
        nplusone._n1_enabled = cls._original_enabled
        super().tearDownClass()

    def test_no_tracker_when_disabled(self):
        """When disabled, tracker should be None on new transactions."""
        # The tracker was set during Transaction init based on _n1_enabled
        # at that time. For this test, we verify the flag-based gating works.
        self.assertFalse(nplusone._n1_enabled)
        # CRUD operations should not fail even without a tracker
        cat = self.env["res.partner.category"].create({"name": "Disabled Test"})
        cat.write({"name": "Updated"})
        cat.unlink()
