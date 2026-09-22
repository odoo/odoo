import psycopg

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestDecisionLedgerKept(ApprovalCommon):
    """What was decided about a request stays on file: no caller deletes a request
    that holds decisions, and deleting its document keeps it, cancelled."""

    def setUp(self):
        super().setUp()
        self.category = self._make_category(
            name=f"Ledger Cat {self.id()}", approvers=[self.approver_1]
        )

    def _refused_then_reset(self, request, resetter):
        request.with_user(self.approver_1).with_context(
            skip_wizard=True
        ).action_refuse()
        request.with_user(resetter).action_reset_to_draft()
        self.assertEqual(request.state, "new")
        return request

    def _ledger(self, request):
        return self.env["approval.decision.log"].search(
            [("request_id", "=", request.id)]
        )

    def test_the_owner_cannot_erase_a_refusal_by_resetting_and_deleting(self):
        request = self._refused_then_reset(
            self._prepare_request(self.category), self.owner_user
        )
        verdicts = sorted(self._ledger(request).mapped("verdict"))
        self.assertEqual(sorted(verdicts), ["refused", "reset"])
        with self.assertRaises(ValidationError):
            request.with_user(self.owner_user).unlink()
        with self.assertRaises(ValidationError):
            request.sudo().unlink()
        self.assertTrue(request.exists())
        self.assertEqual(sorted(self._ledger(request).mapped("verdict")), verdicts)

    def test_the_database_refuses_to_cascade_the_ledger_away(self):
        request = self._refused_then_reset(
            self._prepare_request(self.category), self.owner_user
        )
        with (
            self.assertRaises(psycopg.errors.RestrictViolation),
            mute_logger("odoo.sql_db"),
            self.env.cr.savepoint(),
        ):
            self.env.cr.execute(
                "DELETE FROM approval_request WHERE id = %s", [request.id]
            )

    def test_a_draft_nobody_decided_is_still_deleted(self):
        request = self._prepare_request(self.category, confirm=False)
        request.with_user(self.owner_user).unlink()
        self.assertFalse(request.exists())

    def test_deleting_the_document_keeps_its_decided_request_cancelled(self):
        document = self.env["approval.test.document"].create(
            {
                "name": "Ledger Document",
                "partner_id": self.partner.id,
                "test_category_id": self.category.id,
            }
        )
        document.action_create_approval_request()
        request = self._refused_then_reset(document.approval_request_id, self.env.user)
        self.assertEqual(document.approval_state, "new")

        document.unlink()

        self.assertTrue(request.exists(), "the request carries decisions")
        self.assertEqual(request.state, "cancelled")
        self.assertEqual(
            sorted(self._ledger(request).mapped("verdict")),
            ["cancelled", "refused", "reset"],
        )
