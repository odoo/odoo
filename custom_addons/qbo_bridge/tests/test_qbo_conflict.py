"""Tests for qbo.conflict model and resolution wizard."""
import json

from odoo.tests.common import TransactionCase


class TestQboConflict(TransactionCase):

    def setUp(self):
        super().setUp()
        self.realm = self.env["qbo.realm"].create({
            "name": "Conflict Test Realm",
            "realm_id": "111222333",
            "client_id": "cid",
            "client_secret": "csec",
            "state": "connected",
        })
        self.mapping = self.env["qbo.company.mapping"].create({
            "company_id": self.env.company.id,
            "realm_id": self.realm.id,
        })

    def _make_conflict(self, odoo_data=None, qbo_data=None):
        return self.env["qbo.conflict"].create({
            "mapping_id": self.mapping.id,
            "entity_type": "account",
            "qbo_id": "QBO-C-001",
            "odoo_model": "account.account",
            "odoo_record_id": 1,
            "odoo_data": json.dumps(odoo_data or {"Name": "Odoo Name", "AccountType": "Bank"}),
            "qbo_data": json.dumps(qbo_data or {"Name": "QBO Name", "AccountType": "Bank"}),
        })

    def test_conflict_defaults_to_pending(self):
        c = self._make_conflict()
        self.assertEqual(c.status, "pending")

    def test_diff_summary_shows_changed_fields(self):
        c = self._make_conflict(
            odoo_data={"Name": "Odoo Name", "AccountType": "Bank"},
            qbo_data={"Name": "QBO Name", "AccountType": "Bank"},
        )
        self.assertIn("Name", c.diff_summary)
        self.assertNotIn("AccountType", c.diff_summary)

    def test_diff_summary_no_differences(self):
        same = {"Name": "Same", "AccountType": "Bank"}
        c = self._make_conflict(odoo_data=same, qbo_data=same)
        self.assertIn("No differences", c.diff_summary)

    def test_mark_resolved_sets_fields(self):
        c = self._make_conflict()
        c._mark_resolved("resolved_odoo", notes="Odoo is correct")
        self.assertEqual(c.status, "resolved_odoo")
        self.assertEqual(c.resolved_by.id, self.env.uid)
        self.assertTrue(c.resolved_date)
        self.assertEqual(c.resolution_notes, "Odoo is correct")

    def test_skip_resolution(self):
        c = self._make_conflict()
        c._mark_resolved("skipped")
        self.assertEqual(c.status, "skipped")

    def test_action_open_resolve_wizard_returns_action(self):
        c = self._make_conflict()
        action = c.action_open_resolve_wizard()
        self.assertEqual(action["res_model"], "qbo.conflict.resolve.wizard")
        self.assertEqual(action["context"]["default_conflict_id"], c.id)

    def test_conflict_count_on_mapping(self):
        self._make_conflict()
        self._make_conflict()
        # Refresh to trigger compute
        self.mapping.invalidate_recordset(["conflict_count"])
        self.assertEqual(self.mapping.conflict_count, 2)

    def test_resolved_conflict_not_counted(self):
        c = self._make_conflict()
        c._mark_resolved("resolved_qbo")
        self.mapping.invalidate_recordset(["conflict_count"])
        self.assertEqual(self.mapping.conflict_count, 0)
