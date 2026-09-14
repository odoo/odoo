from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import common, tagged

from .common import (
    ApprovalCommon,
    add_category_approver,
    add_rule_step,
    new_trip_category,
)


@tagged("post_install", "-at_install")
class TestAutoActionRules(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver_user = cls.env["res.users"].create(
            {
                "name": "Action Approver",
                "login": "action_approver",
                "email": "action_approver@test.com",
            }
        )
        cls.owner = cls.env.ref("base.user_admin")
        cls.category = new_trip_category(cls.env)
        add_category_approver(
            cls.category, cls.approver_user, required=True, sequence=10
        )

    def _create_request(self, **kwargs):
        vals = {
            "name": "Auto Action Test",
            "category_id": self.category.id,
            "request_owner_id": self.owner.id,
            "date_start": fields.Datetime.now(),
            "date_end": fields.Datetime.now(),
        }
        vals.update(kwargs)
        return self.env["approval.request"].create(vals)

    def test_auto_approve_below_threshold(self):
        self.env["approval.rule"].create(
            {
                "name": "Auto-Approve Small",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "lt",
                "threshold": 100,
                "action_type": "auto_approve",
            }
        )
        request = self._create_request(amount=50)
        request.action_confirm()
        self.assertEqual(request.state, "approved")
        self.assertTrue(request.applied_rule_ids)
        self.assertEqual(request.applied_rule_ids.name, "Auto-Approve Small")

    def test_auto_approve_does_not_trigger_above_threshold(self):
        self.env["approval.rule"].create(
            {
                "name": "Auto-Approve Small",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "lt",
                "threshold": 100,
                "action_type": "auto_approve",
            }
        )
        request = self._create_request(amount=500)
        request.action_confirm()
        self.assertEqual(request.state, "pending")
        self.assertFalse(request.applied_rule_ids)

    def test_auto_refuse_above_threshold(self):
        self.env["approval.rule"].create(
            {
                "name": "Auto-Refuse Excessive",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 100000,
                "action_type": "auto_refuse",
            }
        )
        request = self._create_request(amount=200000)
        request.action_confirm()
        self.assertEqual(request.state, "refused")
        self.assertTrue(request.applied_rule_ids)

    def test_auto_refuse_does_not_trigger_below(self):
        self.env["approval.rule"].create(
            {
                "name": "Auto-Refuse Excessive",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 100000,
                "action_type": "auto_refuse",
            }
        )
        request = self._create_request(amount=5000)
        request.action_confirm()
        self.assertEqual(request.state, "pending")

    def test_auto_approve_sets_date_confirmed(self):
        self.env["approval.rule"].create(
            {
                "name": "Auto Small",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "lt",
                "threshold": 100,
                "action_type": "auto_approve",
            }
        )
        request = self._create_request(amount=10)
        request.action_confirm()
        self.assertTrue(request.date_confirmed)

    def test_a_step_condition_rule_is_not_treated_as_auto_action(self):
        extra_user = self.env["res.users"].create(
            {
                "name": "Extra",
                "login": "extra_auto_test",
                "email": "extra@test.com",
            }
        )
        add_rule_step(
            self.category,
            extra_user,
            name="Add Extra",
            condition_field="amount",
            operator="gt",
            threshold=1000,
        )
        request = self._create_request(amount=5000)
        request.action_confirm()
        self.assertEqual(request.state, "pending")
        approver_users = request.approver_ids.mapped("user_id")
        self.assertIn(extra_user, approver_users)

    def test_overlapping_auto_approve_and_auto_refuse_rejected(self):
        self.env["approval.rule"].create(
            {
                "name": "Auto-Approve Above 100",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 100,
                "action_type": "auto_approve",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["approval.rule"].create(
                {
                    "name": "Auto-Refuse Above 50",
                    "category_id": self.category.id,
                    "condition_field": "amount",
                    "operator": "gt",
                    "threshold": 50,
                    "action_type": "auto_refuse",
                }
            )

    def test_disjoint_auto_approve_and_auto_refuse_allowed(self):
        self.env["approval.rule"].create(
            {
                "name": "Auto-Approve Below 100",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "lt",
                "threshold": 100,
                "action_type": "auto_approve",
            }
        )
        rule2 = self.env["approval.rule"].create(
            {
                "name": "Auto-Refuse Above 100000",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 100000,
                "action_type": "auto_refuse",
            }
        )
        self.assertTrue(rule2)

    def test_same_action_type_overlap_allowed(self):
        self.env["approval.rule"].create(
            {
                "name": "Auto-Approve Above 50",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 50,
                "action_type": "auto_approve",
            }
        )
        rule2 = self.env["approval.rule"].create(
            {
                "name": "Auto-Approve Above 100",
                "category_id": self.category.id,
                "condition_field": "amount",
                "operator": "gt",
                "threshold": 100,
                "action_type": "auto_approve",
            }
        )
        self.assertTrue(rule2)


@tagged("post_install", "-at_install")
class TestAutoActionRulesAuditRegressions(ApprovalCommon):
    def test_h2_date_confirmed_before_date_approval_granted(self):
        category = self._make_category(
            approvers=[self.approver_1],
        )
        self.env["approval.rule"].create(
            {
                "name": "auto-approve any",
                "category_id": category.id,
                "condition_field": "amount",
                "operator": "gte",
                "threshold": 0.0,
                "action_type": "auto_approve",
            }
        )

        request = self._prepare_request(category, confirm=False, amount=100.0)
        request.action_confirm()

        self.assertEqual(
            request.state,
            "approved",
            "auto-approve rule should drive the request straight into "
            "approved on confirm.",
        )
        self.assertTrue(request.date_confirmed)
        self.assertTrue(request.date_approval_granted)
        self.assertLessEqual(
            request.date_confirmed,
            request.date_approval_granted,
            "date_confirmed is AFTER date_approval_granted "
            f"(confirmed={request.date_confirmed}, "
            f"granted={request.date_approval_granted}). SLA metrics "
            "that read 'granted - confirmed' will be negative.",
        )
