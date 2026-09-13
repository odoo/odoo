from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestSourceDocumentIsNotified(ApprovalCommon):
    def test_the_source_document_is_told_once(self):
        category = self._make_category(
            name=f"Grant Notify Cat {self.id()}", approvers=[self.approver_1]
        )
        doc = self.env["approval.test.document"].create(
            {
                "name": "Doc approved without a decision",
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()

        doc.approval_request_id._approve_without_decision("Validated by the system")

        self.assertEqual(doc.last_approval_state, "approved")
        self.assertEqual(doc.hook_call_count, 1)

    def test_withdraw_notifies_source_document(self):
        category = self._make_category(
            name=f"Withdraw Notify Cat {self.id()}",
            approvers=[self.approver_1],
        )
        doc = self.env["approval.test.document"].create(
            {
                "name": "Doc to un-approve",
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()
        request = doc.approval_request_id
        request.with_user(self.approver_1).action_approve()
        self.assertEqual(doc.last_approval_state, "approved")
        self.assertEqual(doc.hook_call_count, 1)

        request.with_user(self.approver_1).action_withdraw()

        self.assertEqual(request.state, "pending")
        self.assertEqual(doc.last_approval_state, "pending")
        self.assertEqual(doc.hook_call_count, 2)

    def test_cancel_notifies_source_document(self):
        category = self._make_category(
            name=f"Cancel Notify Cat {self.id()}",
            approvers=[self.approver_1, self.approver_2],
        )
        doc = self.env["approval.test.document"].create(
            {
                "name": "Doc to cancel",
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()
        request = doc.approval_request_id
        self.assertEqual(request.state, "pending")

        request.action_cancel()

        self.assertEqual(doc.last_approval_state, "cancelled")
        self.assertEqual(doc.hook_call_count, 1)
        doc._clear_refused_approval_link()
        self.assertFalse(doc.approval_request_id)

    def _refused_document(self, name):
        category = self._make_category(name=name, approvers=[self.approver_1])
        doc = self.env["approval.test.document"].create(
            {
                "name": name,
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()
        doc.approval_request_id.with_user(self.approver_1).with_context(
            skip_wizard=True
        ).action_refuse()
        return doc

    def test_reset_of_a_refused_request_notifies_source_document(self):
        doc = self._refused_document(f"Refused Reset Cat {self.id()}")
        self.assertEqual(doc.last_approval_state, "refused")

        doc.approval_request_id.action_reset_to_draft()

        self.assertEqual(doc.approval_request_id.state, "new")
        self.assertEqual(doc.last_approval_state, "new")
        self.assertEqual(doc.hook_call_count, 2)
        bodies = doc.message_ids.mapped("body")
        self.assertTrue(any("can be submitted again" in body for body in bodies))
        self.assertFalse(
            any("prior approval is no longer valid" in body for body in bodies)
        )

    def test_reset_of_an_approved_request_says_the_approval_no_longer_holds(self):
        category = self._make_category(
            name=f"Approved Reset Cat {self.id()}", approvers=[self.approver_1]
        )
        doc = self.env["approval.test.document"].create(
            {
                "name": "Doc approved then reset",
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()
        doc.approval_request_id.with_user(self.approver_1).action_approve()

        doc.approval_request_id.action_reset_to_draft()

        self.assertEqual(doc.last_approval_state, "new")
        bodies = doc.message_ids.mapped("body")
        self.assertTrue(
            any("prior approval is no longer valid" in body for body in bodies)
        )

    def test_revoking_an_approved_request_notifies_source_document_once(self):
        category = self._make_category(
            name=f"Revoke Notify Cat {self.id()}", approvers=[self.approver_1]
        )
        doc = self.env["approval.test.document"].create(
            {
                "name": "Doc approved then revoked",
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()
        doc.approval_request_id.with_user(self.approver_1).action_approve()
        self.assertEqual(doc.hook_call_count, 1)

        doc.approval_request_id._revoke("refused", "Refused after validation")

        self.assertEqual(doc.last_approval_state, "refused")
        self.assertEqual(doc.state, "rejected")
        self.assertEqual(doc.hook_call_count, 2)

    def test_reset_blocked_when_source_document_released_link(self):
        category = self._make_category(
            name=f"Reset Release Cat {self.id()}",
            approvers=[self.approver_1],
        )
        doc = self.env["approval.test.document"].create(
            {
                "name": "Doc releasing link",
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()
        request = doc.approval_request_id
        request.with_user(self.approver_1).with_context(
            skip_wizard=True,
        ).action_refuse()
        doc._clear_refused_approval_link()

        with self.assertRaises(UserError):
            request.action_reset_to_draft()

    def test_cascade_refusal_records_reason(self):
        category = self._make_category(
            name=f"Cascade Cat {self.id()}",
            approvers=[self.approver_1],
        )
        doc = self.env["approval.test.document"].create(
            {
                "name": "Doc being cancelled",
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()
        request = doc.approval_request_id

        doc.action_refuse_approval()

        self.assertEqual(request.state, "refused")
        self.assertEqual(
            request.refusal_reason_id,
            self.env.ref("approval.refusal_reason_parent_cancelled"),
        )
        self.assertTrue(request.refusal_note)

    def test_granting_without_a_decision_notifies_source_document_once(self):
        category = self._make_category(
            name=f"Grant Notify Cat {self.id()}", approvers=[self.approver_1]
        )
        doc = self.env["approval.test.document"].create(
            {
                "name": "Doc approved without a decision",
                "partner_id": self.partner.id,
                "test_category_id": category.id,
            },
        )
        doc.action_create_approval_request()

        doc.approval_request_id._approve_without_decision("Validated by the system")

        self.assertEqual(doc.last_approval_state, "approved")
        self.assertEqual(doc.hook_call_count, 1)
