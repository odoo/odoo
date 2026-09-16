from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestStepWithoutApprovers(ApprovalCommon):
    """A company that staffs no step blocks the request, never the document.

    Confirming a request whose step can never reach its quorum is refused on
    purpose: it would sit pending forever. But a document raises its request as it
    is created, and whoever creates one rarely governs who may approve it -- an
    employee asking for time off in a company that has named no officer cannot
    appoint one. Letting that refusal out of the automatic create refused the
    employee's record for a configuration they cannot see. The document is kept and
    says why it carries no request; the backfill raises one once the company staffs
    the step.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_company = cls.env["res.company"].create({"name": "Elsewhere"})
        cls.elsewhere_approver = mail_new_test_user(
            cls.env,
            login="approver_elsewhere",
            groups="base.group_user",
            company_id=cls.other_company.id,
            company_ids=[(6, 0, cls.other_company.ids)],
        )

    def _category_staffed_elsewhere(self):
        category = self._make_category(
            name=f"Elsewhere {self.id()}", approvers=[], company_id=False
        )
        self.env["approval.category.step"].create(
            {
                "category_id": category.id,
                "name": "Officer",
                "sequence": 10,
                "minimum": 1,
                "user_ids": [(6, 0, self.elsewhere_approver.ids)],
            }
        )
        return category

    def _document(self, category):
        return (
            self.env["approval.test.synced.document"]
            .with_user(self.owner_user)
            .sudo()
            .create(
                {
                    "name": f"Doc {self.id()}",
                    "state": "submitted",
                    "test_category_id": category.id,
                    "company_id": self.env.company.id,
                }
            )
        )

    def test_confirming_a_request_nobody_here_can_approve_is_refused(self):
        category = self._category_staffed_elsewhere()

        with self.assertRaises(UserError):
            self._prepare_request(category, company_id=self.env.company.id)

    def test_the_document_is_still_created(self):
        category = self._category_staffed_elsewhere()

        document = self._document(category)

        self.assertTrue(document.exists())
        self.assertFalse(document.approval_request_id)

    def test_the_document_says_why_it_has_no_request(self):
        category = self._category_staffed_elsewhere()

        document = self._document(category)

        self.assertIn(
            "Officer",
            "".join(document.message_ids.mapped("body")),
        )

    def test_the_backfill_raises_the_request_once_the_step_is_staffed_here(self):
        category = self._category_staffed_elsewhere()
        document = self._document(category)

        category.step_ids.write({"user_ids": [(6, 0, self.approver_1.ids)]})
        document._backfill_approval_requests()

        self.assertTrue(document.approval_request_id)
        self.assertEqual(document.approval_request_id.state, "pending")
