from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestStateGuards(ApprovalCommon):
    def _parallel_category(self, **vals):
        return self._make_category(
            name=f"A2 Parallel {self.id()}",
            approvers=[self.approver_1, self.approver_2],
            approval_minimum=2,
            **vals,
        )

    def test_context_key_alone_does_not_bypass_access(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        row = request.approver_ids[0]

        with self.assertRaises(AccessError):
            self.env["approval.approver"].with_user(self.approver_1).with_context(
                approver_ids_computation=True
            ).create(
                {"request_id": request.id, "user_id": self.approver_2.id},
            )
        with self.assertRaises(AccessError):
            row.with_user(self.approver_1).with_context(
                approver_ids_computation=True
            ).unlink()
        with self.assertRaises((AccessError, ValidationError)):
            request.with_user(self.approver_1).with_context(
                approver_ids_computation=True
            ).write({"approver_ids": [(0, 0, {"user_id": self.manager_user.id})]})

    def test_an_approver_status_written_under_sudo_is_refused(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)

        for state in ("approved", "refused", "pending", "waiting"):
            with self.assertRaisesRegex(AccessError, "derived from the decisions"):
                row.sudo().write({"state": state})
        with self.assertRaisesRegex(AccessError, "derived from the decisions"):
            self.env["approval.approver"].sudo().create(
                {
                    "request_id": request.id,
                    "user_id": self.manager_user.id,
                    "state": "approved",
                }
            )
        self.assertEqual(row.state, "pending")
        self.assertEqual(request.state, "pending")

    def test_approver_status_follows_the_decision_ledger(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)

        row.sudo().write({"flow_state": "waiting"})
        self.assertEqual(row.state, "waiting")

        row.sudo()._record_decision("approved")
        self.assertEqual(row.state, "approved")
        row.sudo().write({"flow_state": "pending"})
        self.assertEqual(row.state, "approved")

        request.sudo()._append_decision_log("reset", rows=row)
        self.assertEqual(row.state, "pending")

    def test_approver_cannot_write_own_state(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)

        with self.assertRaises(AccessError):
            row.with_user(self.approver_1).write({"state": "approved"})
        with self.assertRaises(AccessError):
            row.with_user(self.approver_1).write({"sequence": 5})
        row.with_user(self.approver_1).write({"note": "context note"})
        self.assertEqual(row.note, "context note")

    def test_request_change_inline_requires_pending_approver(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        with self.assertRaises(UserError):
            request.with_user(self.owner_user).with_context(
                skip_wizard=True, requested_change_field="reason"
            ).action_request_change()
        self.assertFalse(request.pending_change_field)

    def test_parallel_refusal_closes_sibling_and_blocks_late_approve(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        row1 = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        row2 = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)

        request.with_user(self.approver_1).with_context(skip_wizard=True).action_refuse(
            approver=row1
        )
        self.assertEqual(request.state, "refused")
        self.assertNotEqual(row2.state, "pending")
        with self.assertRaises(UserError):
            request.with_user(self.approver_2).action_approve(approver=row2)
        self.assertEqual(request.state, "refused")

    def test_sync_on_approved_does_not_regress_state(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")

        request._sync_approvers()
        self.assertEqual(request.state, "approved")

    def test_search_is_delegated_returns_active_delegations(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        row = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        today = fields.Date.today()
        row.sudo().write(
            {
                "delegate_id": self.manager_user.id,
                "delegate_start_date": today - timedelta(days=1),
                "delegate_end_date": today + timedelta(days=1),
            }
        )
        found = self.env["approval.approver"].search([("is_delegated", "=", True)])
        self.assertIn(row, found)
        not_found = self.env["approval.approver"].search([("is_delegated", "=", False)])
        self.assertNotIn(row, not_found)

    def test_delegate_cannot_be_owner_or_coapprover(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        row1 = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        today = fields.Date.today()
        window = {
            "delegate_start_date": today,
            "delegate_end_date": today + timedelta(days=1),
        }
        with self.assertRaises(ValidationError):
            row1.sudo().write({"delegate_id": self.owner_user.id, **window})
        with self.assertRaises(ValidationError):
            row1.sudo().write({"delegate_id": self.approver_2.id, **window})
        with self.assertRaises(ValidationError):
            row1.sudo().write({"delegate_id": self.approver_1.id, **window})

    def test_withdraw_blocked_on_terminal_request(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        request.with_user(self.owner_user).action_cancel()
        self.assertEqual(request.state, "cancelled")
        with self.assertRaises(UserError):
            request.with_user(self.approver_1).action_withdraw()

    def test_manager_can_reset_approved_request(self):
        category = self._parallel_category()
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()
        request.with_user(self.approver_2).action_approve()
        self.assertEqual(request.state, "approved")

        with self.assertRaises(AccessError):
            request.with_user(self.owner_user).action_reset_to_draft()

        request.with_user(self.manager_user).action_reset_to_draft()
        self.assertEqual(request.state, "new")
        self.assertFalse(request.date_approval_granted)
        self.assertFalse(request.date_confirmed)
        self.assertTrue(all(a.state == "new" for a in request.approver_ids))


@tagged("post_install", "-at_install")
class TestSubmittedRequestGuards(ApprovalCommon):
    def _category(self, **vals):
        return self._make_category(
            name=f"A2 Minor {self.id()}",
            approvers=[self.approver_1, self.approver_2],
            approval_minimum=2,
            **vals,
        )

    def test_decision_date_stamped_only_on_genuine_decisions(self):
        category = self._category()
        request = self._prepare_request(category)
        row1 = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        row2 = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)

        request.with_user(self.approver_1).action_approve()
        self.assertTrue(row1.decision_date, "genuine approval stamps decision_date")

        request.with_user(self.approver_2).with_context(skip_wizard=True).action_refuse(
            approver=row2
        )
        self.assertTrue(row2.decision_date)
        request.with_user(self.manager_user).action_reset_to_draft()
        self.assertFalse(row1.decision_date)
        self.assertFalse(row2.decision_date)

    def test_cascade_refusal_leaves_no_decision_date(self):
        category = self._category()
        request = self._prepare_request(category)
        row1 = request.approver_ids.filtered(lambda a: a.user_id == self.approver_1)
        row2 = request.approver_ids.filtered(lambda a: a.user_id == self.approver_2)
        request.with_user(self.approver_1).with_context(skip_wizard=True).action_refuse(
            approver=row1
        )
        self.assertTrue(row1.decision_date, "the refuser's own row is stamped")
        self.assertFalse(
            row2.decision_date, "the cascade-closed sibling is not credited"
        )

    def test_to_review_count_ignores_already_approved_row(self):
        category = self._category()
        request = self._prepare_request(category)
        request.with_user(self.approver_1).action_approve()

        domain = self.env["approval.request"]._get_domain_pending_review(
            self.approver_1
        )
        awaiting_1 = self.env["approval.request"].search(domain)
        self.assertNotIn(
            request, awaiting_1, "already-approved row must not await approver_1"
        )
        domain2 = self.env["approval.request"]._get_domain_pending_review(
            self.approver_2
        )
        self.assertIn(request, self.env["approval.request"].search(domain2))

    def test_copy_of_confirmed_request_drops_date_confirmed(self):
        category = self._category()
        request = self._prepare_request(category)
        self.assertTrue(request.date_confirmed)
        clone = request.copy()
        self.assertEqual(clone.state, "new")
        self.assertFalse(
            clone.date_confirmed, "a fresh draft clone must not inherit submission time"
        )


@tagged("post_install", "-at_install")
class TestLockedFields(ApprovalCommon):
    def _category(self, **vals):
        return self._make_category(
            name=f"A3 Lock {self.id()}",
            approvers=[self.approver_1, self.approver_2],
            approval_minimum=2,
            **vals,
        )

    def test_frozen_fields_reject_rpc_write_after_send(self):
        category = self._category()
        request = self._prepare_request(category)
        self.assertEqual(request.state, "pending")

        frozen_attempts = {
            "request_owner_id": self.approver_1.id,
            "company_id": request.company_id.id,
            "name": "HACKED-0001",
            "date_confirmed": "2020-01-01 00:00:00",
            "quantity": 7.0,
            "amount": 999.0,
        }
        for field, value in frozen_attempts.items():
            with self.assertRaises(
                ValidationError, msg=f"{field} must be frozen after send"
            ):
                request.with_user(self.owner_user).write({field: value})

        request.with_user(self.owner_user).write({"priority": "3"})
        self.assertEqual(request.priority, "3")

    def test_approval_minimum_frozen_for_user_but_syncable_by_system(self):
        category = self._category()
        request = self._prepare_request(category)
        self.assertEqual(request.approval_minimum, 2)

        with self.assertRaises(ValidationError):
            request.with_user(self.owner_user).write({"approval_minimum": 1})

        request.with_user(self.approver_1).action_approve()
        self.assertEqual(request.state, "pending")

        request.sudo().write({"approval_minimum": 1})
        self.assertEqual(request.approval_minimum, 1)

    def test_frozen_fields_editable_in_draft(self):
        category = self._category()
        draft = self._prepare_request(category, confirm=False)
        self.assertEqual(draft.state, "new")
        draft.with_user(self.owner_user).write({"priority": "3", "quantity": 3.0})
        self.assertEqual(draft.priority, "3")
        self.assertEqual(draft.quantity, 3.0)

    def test_reset_to_draft_reopens_frozen_fields(self):
        category = self._category()
        request = self._prepare_request(category)
        request.with_user(self.owner_user).action_cancel()
        request.with_user(self.manager_user).action_reset_to_draft()
        self.assertEqual(request.state, "new")
        self.assertFalse(request.date_confirmed)
        request.with_user(self.owner_user).write({"quantity": 4.0})
        self.assertEqual(request.quantity, 4.0)
