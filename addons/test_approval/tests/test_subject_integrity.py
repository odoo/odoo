from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestSubjectIntegrity(ApprovalCommon):
    """An approval covers the document as it was approved. Changing what was
    approved sends the approval back to draft and says why; writing the same
    values back, or changing a field nobody approved, leaves it alone."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            "Integrity", approvers=[(cls.approver_1, True, 10)]
        )
        cls.partner = cls.env["res.partner"].create({"name": "Integrity Partner"})
        cls.other_partner = cls.env["res.partner"].create({"name": "Other Partner"})

    def _approved(self, **vals):
        document = self.env["approval.test.document"].create(
            {
                "name": "Integrity",
                "partner_id": self.partner.id,
                "amount": 100.0,
                "test_category_id": self.category.id,
                "protected_field_names": "amount,partner_id",
                **vals,
            }
        )
        document.action_create_approval_request()
        document.approval_request_id.with_user(self.approver_1).action_approve()
        self.assertEqual(document.approval_state, "approved")
        return document

    def test_changing_an_approved_amount_resets_the_approval(self):
        document = self._approved()
        document.write({"amount": 999999.0})
        self.assertEqual(document.approval_state, "new")
        reset = document.approval_request_id.decision_log_ids.filtered(
            lambda log: log.verdict == "reset"
        )
        self.assertIn("Amount", reset.note)

    def test_the_superuser_does_not_keep_an_approval_it_changed_either(self):
        document = self._approved()
        document.sudo().write({"partner_id": self.other_partner.id})
        self.assertEqual(document.approval_state, "new")

    def test_no_context_key_keeps_an_approval_across_a_change(self):
        document = self._approved()
        document.with_context(approval_keep_on_subject_change=True).write(
            {"partner_id": self.other_partner.id}
        )
        self.assertEqual(
            document.approval_state,
            "new",
            "a client-sent context is no authority over what was approved",
        )

    def test_writing_the_approved_values_back_changes_nothing(self):
        document = self._approved()
        document.write({"amount": 100.0, "partner_id": self.partner.id})
        self.assertEqual(document.approval_state, "approved")
        self.assertFalse(
            document.approval_request_id.decision_log_ids.filtered(
                lambda log: log.verdict == "reset"
            )
        )

    def test_a_field_nobody_approved_may_change(self):
        document = self._approved()
        document.write({"description": "a note after approval"})
        self.assertEqual(document.approval_state, "approved")

    def test_a_document_may_say_its_changes_keep_the_approval(self):
        document = self._approved(keeps_approval_on_change=True)
        document.write({"amount": 5.0})
        self.assertEqual(document.approval_state, "approved")

    def test_the_approval_can_be_asked_again_on_the_new_values(self):
        document = self._approved()
        document.write({"amount": 250.0})
        request = document.approval_request_id
        request.action_confirm()
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(document.approval_state, "approved")
        self.assertEqual(
            [log.verdict for log in request.decision_log_ids.sorted("id")],
            ["approved", "reset", "approved"],
        )

    def test_a_request_that_cannot_be_reset_refuses_the_change(self):
        document = self._approved()
        Request = type(self.env["approval.request"])

        def veto(request):
            raise UserError("released")

        with patch.object(Request, "_check_reset_allowed", veto):
            with self.assertRaises(UserError):
                document.write({"amount": 1.0})
        document.invalidate_recordset(["amount"])
        self.assertEqual(document.amount, 100.0)
        self.assertEqual(document.approval_state, "approved")
