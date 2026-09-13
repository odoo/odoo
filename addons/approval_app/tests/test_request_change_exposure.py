from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestRequestChangeFollowsTheForm(ApprovalCommon):
    def _pending(self, **category_vals):
        category = self._make_category(
            name=f"Reach Cat {self.id()}",
            approval_minimum=1,
            approvers=[(self.approver_1, True, 10)],
            **category_vals,
        )
        return self._prepare_request(category)

    def _request_change(self, request, field):
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
            requested_change_field=field,
        ).action_request_change(approver=approver)

    def test_date_change_refused_when_neither_the_category_nor_the_request_has_one(
        self,
    ):
        request = self._pending(has_date="no", has_date_range="no")

        with self.assertRaises(UserError):
            self._request_change(request, "date")

        self.assertFalse(
            request.pending_change_field,
            "A request must not be frozen on a field nobody can edit.",
        )
        self.assertEqual(request.state, "pending")
        self._request_change(request, "reason")
        self.assertEqual(request.pending_change_field, "reason")

    def test_date_change_allowed_when_only_the_period_is_exposed(self):
        request = self._pending(has_date="no", has_date_range="optional")

        self._request_change(request, "date")

        self.assertEqual(request.pending_change_field, "date")
        request.with_user(self.owner_user).write(
            {
                "date_start": fields.Datetime.now(),
                "date_end": fields.Datetime.now() + timedelta(days=2),
            },
        )
        request.with_user(self.owner_user).action_resubmit()
        self.assertFalse(request.pending_change_field)

    def test_reason_is_always_reachable(self):
        request = self._pending(has_date="no", has_date_range="no")
        self.assertEqual(
            request._get_pending_change_candidates(),
            frozenset({"reason"}),
        )

    def test_the_wizard_surfaces_the_same_refusal(self):
        request = self._pending(has_date="no", has_date_range="no")
        approver = request.approver_ids.filtered(
            lambda a: a.user_id == self.approver_1,
        )
        wizard = (
            self.env["approval.decision.wizard"]
            .with_user(self.approver_1)
            .create(
                {
                    "approver_id": approver.id,
                    "decision_type": "change",
                    "change_field": "date",
                    "note": "Please move it.",
                },
            )
        )

        with self.assertRaises(UserError):
            wizard.action_confirm_change()

        self.assertFalse(request.pending_change_field)
