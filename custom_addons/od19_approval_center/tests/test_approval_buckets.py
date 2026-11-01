import datetime
import unittest

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
        expense_model = cls.env.get("hr.expense")
        if (
            expense_model is None
            or "first_approver_id" not in expense_model._fields
            or "second_approver_id" not in expense_model._fields
        ):
            raise unittest.SkipTest(
                "Requires hr.expense with od19 approval fields "
                "(od19_hr_expense_enhanced and od19_hr_expense_thai)"
            )
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
        internal_group = self.env.ref("base.group_user")
        first = self.env["res.users"].create({
            "name": "L1", "login": "l1_user",
            "group_ids": [
                (4, internal_group.id),
                (4, approver_group.id),
            ],
        })
        second = self.env["res.users"].create({
            "name": "L2", "login": "l2_user",
            "group_ids": [
                (4, internal_group.id),
                (4, approver_group.id),
            ],
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


@tagged("post_install", "-at_install")
class TestRequesterAndAge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # hr.expense requires a linked employee and a non-zero amount.
        cls.employee = cls.env["hr.employee"].create({
            "name": "Requester Employee",
            "user_id": cls.env.user.id,
        })
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Age Source",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "requester_field": "create_uid",
            "requester_kind": "user",
            "submitted_date_field": "create_date",
            "success_states": "approved",
            "rejected_states": "refused",
            "sla_days": 3,
            "step_ids": [(0, 0, {
                "sequence": 10, "label": "L1", "state_field": "state",
                "state_value": "submitted", "approver_field": "create_uid",
                "approver_kind": "user",
            })],
        })

    def test_requester_sees_own_pending(self):
        expense = self.env["hr.expense"].create({
            "name": "My Expense",
            "employee_id": self.employee.id,
            "total_amount_currency": 100.0,
            "total_amount": 100.0,
        })
        expense.write({"state": "submitted"})
        buckets = self.source.with_user(self.env.user)._od19_classify_for_requester()
        self.assertIn(expense.id, [r.id for r in buckets["pending"]])

    def test_age_days_from_submitted_field(self):
        expense = self.env["hr.expense"].create({
            "name": "Old",
            "employee_id": self.employee.id,
            "total_amount_currency": 100.0,
            "total_amount": 100.0,
        })
        expense.write({"state": "submitted"})
        # The ORM strips log-access fields (create_date) from create()/write(),
        # so the submitted date must be set directly in SQL.
        self.env.cr.execute(
            "UPDATE hr_expense SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - datetime.timedelta(days=5), expense.id),
        )
        expense.invalidate_recordset(["create_date"])
        self.assertEqual(self.source._od19_age_days(expense), 5)

    def test_sla_state_thresholds(self):
        self.assertEqual(self.source._od19_sla_state(1), "normal")
        self.assertEqual(self.source._od19_sla_state(3), "warning")
        self.assertEqual(self.source._od19_sla_state(6), "over")


@tagged("post_install", "-at_install")
class TestRowsAndSummary(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # hr.expense requires a linked employee and a non-zero amount.
        cls.employee = cls.env["hr.employee"].create({
            "name": "Rows Employee",
            "user_id": cls.env.user.id,
        })
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Rows Source",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "requester_field": "create_uid",
            "success_states": "approved",
            "rejected_states": "refused",
            "sla_days": 3,
            "step_ids": [(0, 0, {
                "sequence": 10, "label": "L1", "state_field": "state",
                "state_value": "submitted", "approver_field": "create_uid",
                "approver_kind": "user",
            })],
        })

    def test_row_carries_deep_link_age_and_sla(self):
        expense = self.env["hr.expense"].create({
            "name": "Paper",
            "employee_id": self.employee.id,
            "total_amount_currency": 100.0,
            "total_amount": 100.0,
        })
        expense.write({"state": "submitted"})
        # The ORM strips log-access fields (create_date) from create()/write(),
        # so the submitted date must be set directly in SQL.
        self.env.cr.execute(
            "UPDATE hr_expense SET create_date = %s WHERE id = %s",
            (fields.Datetime.now() - datetime.timedelta(days=7), expense.id),
        )
        expense.invalidate_recordset(["create_date"])
        rows = self.source._od19_build_rows(expense)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], expense.id)
        self.assertEqual(rows[0]["model"], "hr.expense")
        self.assertIn("/web#id=%s" % expense.id, rows[0]["url"])
        self.assertEqual(rows[0]["age_days"], 7)
        self.assertEqual(rows[0]["sla_state"], "over")
        self.assertEqual(rows[0]["label"], "Paper")

    def test_summary_kpis(self):
        buckets = self.source._od19_classify_for_approver()
        rows = self.source._od19_build_rows(buckets["pending"])
        summary = self.source._od19_summary(rows)
        self.assertEqual(summary["pending_count"], len(rows))
        self.assertIn("max_age_days", summary)
        self.assertIn("over_sla_count", summary)


@tagged("post_install", "-at_install")
class TestFurthestStep(TransactionCase):
    """`_od19_current_index` must report the furthest step the record reached."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        expense_model = cls.env.get("hr.expense")
        if (
            expense_model is None
            or "first_approver_id" not in expense_model._fields
            or "second_approver_id" not in expense_model._fields
            or "second_approval_state" not in expense_model._fields
        ):
            raise unittest.SkipTest(
                "Requires hr.expense with od19 approval fields "
                "(od19_hr_expense_enhanced and od19_hr_expense_thai)"
            )
        # hr.expense requires a linked employee and a non-zero amount.
        cls.employee = cls.env["hr.employee"].create({
            "name": "Furthest Employee",
            "user_id": cls.env.user.id,
        })
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Furthest",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "step_ids": [
                (0, 0, {
                    "sequence": 10, "label": "L1", "state_field": "state",
                    "state_value": "submitted", "approver_field": "first_approver_id",
                    "approver_kind": "employee",
                }),
                (0, 0, {
                    "sequence": 20, "label": "L2",
                    "state_field": "second_approval_state", "state_value": "pending",
                    "approver_field": "second_approver_id", "approver_kind": "employee",
                }),
            ],
        })

    def test_highest_matching_step_wins(self):
        if "second_approval_state" not in self.env["hr.expense"]._fields:
            self.skipTest("od19_hr_expense_thai not installed")
        expense = self.env["hr.expense"].create({
            "name": "Two tier",
            "employee_id": self.employee.id,
            "total_amount_currency": 100.0,
            "total_amount": 100.0,
        })
        expense.write({"state": "submitted", "second_approval_state": "pending"})
        steps = self.source.step_ids.sorted("sequence")
        self.assertEqual(self.source._od19_current_index(expense, steps), 1)


@tagged("post_install", "-at_install")
class TestMultiStepSameApprover(TransactionCase):
    """A user who is the approver on more than one step must still see the
    record while it waits at one of their steps (furthest-step regression)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        expense_model = cls.env.get("hr.expense")
        if (
            expense_model is None
            or "first_approver_id" not in expense_model._fields
            or "second_approver_id" not in expense_model._fields
            or "second_approval_state" not in expense_model._fields
        ):
            raise unittest.SkipTest("Requires od19 hr.expense approval fields")
        cls.employee = cls.env["hr.employee"].create({
            "name": "Dual Approver",
            "user_id": cls.env.user.id,
        })
        cls.source = cls.env["od19.approval.source"].create({
            "name": "Dual",
            "model_id": cls.env["ir.model"]._get("hr.expense").id,
            "requester_field": "create_uid",
            "success_states": "approved",
            "rejected_states": "refused",
            "step_ids": [
                (0, 0, {
                    "sequence": 10, "label": "L1", "state_field": "state",
                    "state_value": "submitted", "approver_field": "first_approver_id",
                    "approver_kind": "employee",
                }),
                (0, 0, {
                    "sequence": 20, "label": "L2", "state_field": "second_approval_state",
                    "state_value": "pending", "approver_field": "second_approver_id",
                    "approver_kind": "employee",
                }),
            ],
        })

    def test_dual_approver_sees_pending_at_second_step(self):
        expense = self.env["hr.expense"].create({
            "name": "Dual tier",
            "employee_id": self.employee.id,
            "total_amount_currency": 100.0,
            "total_amount": 100.0,
        })
        expense.write({
            "state": "submitted",
            "second_approval_state": "pending",
            "first_approver_id": self.employee.id,
            "second_approver_id": self.employee.id,
        })
        buckets = self.source.with_user(self.env.user)._od19_classify_for_approver()
        self.assertIn(expense.id, [r.id for r in buckets["pending"]])


@tagged("post_install", "-at_install")
class TestSharedPoolStep(TransactionCase):
    """A step without approver_field is actionable by every internal user."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        expense_model = cls.env.get("hr.expense")
        if expense_model is None or "state" not in expense_model._fields:
            raise unittest.SkipTest("Requires hr.expense with a state field")
        # hr.expense requires a linked employee and a non-zero amount.
        cls.employee = cls.env["hr.employee"].create({
            "name": "Pool Employee",
            "user_id": cls.env.user.id,
        })

    def test_pool_step_is_pending_for_anyone(self):
        source = self.env["od19.approval.source"].create({
            "name": "Pool Source",
            "model_id": self.env["ir.model"]._get("hr.expense").id,
            "success_states": "approved",
            "rejected_states": "refused",
            "step_ids": [(0, 0, {
                "sequence": 10, "label": "Any approver", "state_field": "state",
                "state_value": "submitted",
            })],
        })
        expense = self.env["hr.expense"].create({
            "name": "Pool doc",
            "employee_id": self.employee.id,
            "total_amount_currency": 100.0,
            "total_amount": 100.0,
        })
        expense.write({"state": "submitted"})
        # The source is readable only for the Approval Center group.
        approver_group = self.env.ref("od19_approval_center.group_approval_admin")
        internal_group = self.env.ref("base.group_user")
        other = self.env["res.users"].create({
            "name": "Pool Z", "login": "pool_z",
            "group_ids": [
                (4, internal_group.id),
                (4, approver_group.id),
            ],
        })
        buckets = source.with_user(other)._od19_classify_for_approver()
        self.assertIn(expense.id, [r.id for r in buckets["pending"]])
