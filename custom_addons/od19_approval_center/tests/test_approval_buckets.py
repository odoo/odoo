from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


class TestApprovalConfig(TransactionCase):
    def test_models_and_defaults(self):
        source = self.env["od19.approval.source"].create({
            "name": "Unit Source",
            "model_id": self.env["ir.model"]._get("hr.expense").id,
        })
        self.assertEqual(source.strategy, "field")
        self.assertEqual(source.requester_kind, "user")
        self.assertEqual(source.sla_days, 0)
        self.assertTrue(source.active)

        step = self.env["od19.approval.step"].create({
            "source_id": source.id,
            "label": "Step 1",
            "state_value": "submitted",
            "approver_field": "create_uid",
        })
        self.assertEqual(step.state_field, "state")
        self.assertEqual(step.approver_kind, "user")
        self.assertEqual(step.sequence, 10)
        self.assertIn(step, source.step_ids)


@tagged("post_install", "-at_install")
class TestPendingBucket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver = cls.env["res.users"].create({
            "name": "Approver A", "login": "approver_a",
        })
        cls.other = cls.env["res.users"].create({
            "name": "Other B", "login": "other_b",
        })
        # hr.expense requires a linked employee and a non-zero amount.
        cls.employee = cls.env["hr.employee"].create({
            "name": "Approver Employee",
            "user_id": cls.env.user.id,
        })
        cls.expense = cls.env["hr.expense"].create({
            "name": "Taxi",
            "employee_id": cls.employee.id,
            "total_amount_currency": 100.0,
            "total_amount": 100.0,
        })
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Expense Test",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "strategy": "field",
            "requester_field": "create_uid",
            "requester_kind": "user",
            "rejected_states": "refused",
            "success_states": "approved,posted,in_payment,paid",
            "step_ids": [(0, 0, {
                "sequence": 10, "label": "Approve",
                "state_field": "state", "state_value": "submitted",
                "approver_field": "create_uid", "approver_kind": "user",
            })],
        })

    def test_pending_only_for_the_approver(self):
        # The record waits at 'submitted'; the approver field is create_uid.
        self.expense.write({"state": "submitted"})
        buckets = self.source.with_user(self.env.user)._od19_classify_for_approver()
        pending_ids = [r.id for r in buckets["pending"]]
        self.assertIn(self.expense.id, pending_ids)

    def test_other_user_sees_nothing(self):
        self.expense.write({"state": "submitted"})
        buckets = self.source.with_user(self.other)._od19_classify_for_approver()
        self.assertEqual(buckets["pending"], [])
