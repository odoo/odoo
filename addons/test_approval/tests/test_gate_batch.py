from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestGateBatchSurvivesAnUnstaffedStep(ApprovalCommon):
    """A batch is one transaction, so who gets to end it matters.

    Validating five documents at once raises a request for each that needs one. A
    refusal from any of them rolls back the whole transaction, including documents
    that needed no approval and were already done. A document's own refusal earns
    that -- something about that document is wrong, and the person asked for it by
    acting on it. A company that has staffed no approver does not: nobody in the
    batch caused it and nobody in the batch can fix it, so that one document is
    reported and the rest stand.
    """

    def setUp(self):
        super().setUp()
        self.elsewhere = self.env["res.company"].create({"name": f"Elsewhere {self.id()}"})
        self.approver_elsewhere = mail_new_test_user(
            self.env,
            login=f"approver_elsewhere_{self.id()}",
            groups="base.group_user",
            company_id=self.elsewhere.id,
            company_ids=[(6, 0, self.elsewhere.ids)],
        )
        self.here = self._make_category(
            name=f"Staffed {self.id()}", approvers=[self.approver_1], company_id=False
        )
        self.staffed_elsewhere = self._make_category(
            name=f"Unstaffed {self.id()}", approvers=[], company_id=False
        )
        self.env["approval.category.step"].create(
            {
                "category_id": self.staffed_elsewhere.id,
                "name": "Officer",
                "sequence": 10,
                "minimum": 1,
                "user_ids": [(6, 0, self.approver_elsewhere.ids)],
            }
        )

    def _document(self, name, category):
        return self.env["approval.test.gated"].create(
            {
                "name": name,
                "partner_id": self.partner.id,
                "amount_total": 100.0,
                "company_id": self.env.company.id,
                "test_category_id": category.id if category else False,
            }
        )

    def _batch(self):
        plain = self._document("Needs nothing", None)
        asked = self._document("Asks here", self.here)
        blocked = self._document("Nobody here can approve", self.staffed_elsewhere)
        return plain, asked, blocked

    def test_the_documents_that_could_be_asked_are_asked(self):
        plain, asked, blocked = self._batch()

        (plain | asked | blocked).action_ship()

        self.assertEqual(asked.approval_state, "pending")
        self.assertFalse(blocked.approval_request_id)

    def test_the_document_that_needed_no_approval_still_went_through(self):
        plain, asked, blocked = self._batch()

        (plain | asked | blocked).action_ship()

        self.assertEqual(
            plain.ship_count, 1, "a rollback would have undone this one too"
        )

    def test_the_batch_says_which_document_could_not_be_sent_and_why(self):
        plain, asked, blocked = self._batch()

        action = (plain | asked | blocked).action_ship()

        message = action["params"]["message"]
        self.assertIn(blocked.display_name, message)
        self.assertIn("Officer", message)
        self.assertIn(self.env.company.display_name, message)

    def test_a_document_refused_for_its_own_sake_still_ends_the_batch(self):
        plain, asked, _blocked = self._batch()
        refusing = self._document("No category at all", None)
        refusing.approval_required = True

        with self.assertRaises(UserError):
            (plain | asked | refusing).action_ship()

    def test_one_document_alone_is_told_rather_than_reported(self):
        blocked = self._document("Nobody here can approve", self.staffed_elsewhere)

        with self.assertRaises(UserError):
            blocked.action_ship()
