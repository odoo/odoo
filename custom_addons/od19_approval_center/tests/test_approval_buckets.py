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


@tagged("post_install", "-at_install")
class TestIncomingBucket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # hr.expense requires a linked employee and a non-zero amount.
        cls.owner_employee = cls.env["hr.employee"].create({
            "name": "Requester Employee",
            "user_id": cls.env.user.id,
        })
        cls.expense = cls.env["hr.expense"].create({
            "name": "Hotel",
            "employee_id": cls.owner_employee.id,
            "total_amount_currency": 100.0,
            "total_amount": 100.0,
        })
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Two Tier",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "requester_field": "create_uid",
            "success_states": "approved",
            "rejected_states": "refused",
            "step_ids": [
                (0, 0, {
                    "sequence": 10, "label": "L1", "state_field": "state",
                    "state_value": "submitted", "approver_field": "first_approver_id",
                    "approver_kind": "user",
                }),
                (0, 0, {
                    "sequence": 20, "label": "L2", "state_field": "state",
                    "state_value": "approved", "approver_field": "second_approver_id",
                    "approver_kind": "user",
                }),
            ],
        })

    def test_level2_approver_sees_incoming_not_pending(self):
        # Approvers run inside the Approval Center, so they carry its group
        # (the source model is readable only for that group).
        approver_group = self.env.ref("od19_approval_center.group_approval_admin")
        first = self.env["res.users"].create({
            "name": "L1", "login": "l1_user",
            "group_ids": [(4, approver_group.id)],
        })
        second = self.env["res.users"].create({
            "name": "L2", "login": "l2_user",
            "group_ids": [(4, approver_group.id)],
        })
        # The approver fields are Many2one on hr.employee; map users to employees.
        first_emp = self.env["hr.employee"].create({
            "name": "L1 Emp", "user_id": first.id,
        })
        second_emp = self.env["hr.employee"].create({
            "name": "L2 Emp", "user_id": second.id,
        })
        self.expense.write({
            "state": "submitted",
            "first_approver_id": first_emp.id,
            "second_approver_id": second_emp.id,
        })
        buckets = self.source.with_user(second)._od19_classify_for_approver()
        self.assertIn(self.expense.id, [r.id for r in buckets["incoming"]])
        self.assertNotIn(self.expense.id, [r.id for r in buckets["pending"]])
        # The level 1 approver is the actionable one.
        l1 = self.source.with_user(first)._od19_classify_for_approver()
        self.assertIn(self.expense.id, [r.id for r in l1["pending"]])
