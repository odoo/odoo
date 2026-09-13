from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from odoo.addons.approval.tests.common import ApprovalCommon


@tagged("post_install", "-at_install")
class TestApprovalAccess(ApprovalCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls._make_category(
            name="Access Requests", approvers=[cls.approver_1], company_id=False
        )
        cls.document = cls.env["approval.test.access.document"].create(
            {"name": "Shared Folder", "test_category_id": cls.category.id}
        )
        cls.partner = cls.owner_user.partner_id

    def test_a_request_names_the_record_the_partner_and_the_role(self):
        request = self.document._request_access(self.partner, "edit")

        self.assertEqual(request.state, "pending")
        self.assertEqual(request.subject_key, f"access:{self.partner.id}:edit")
        self.assertEqual(
            request.name, f"Access to Shared Folder for {self.partner.name}"
        )
        self.assertEqual(
            self.document._get_access_subject(request.subject_key),
            (self.partner, "edit"),
        )

    def test_approving_grants_the_role_asked_for(self):
        request = self.document._request_access(self.partner, "edit")

        request.with_user(self.approver_1).action_approve()

        self.assertIn(self.partner, self.document.editor_partner_ids)
        self.assertNotIn(self.partner, self.document.viewer_partner_ids)

    def test_refusing_grants_nothing(self):
        request = self.document._request_access(self.partner, "view")

        request.with_user(self.approver_1).with_context(
            skip_wizard=True
        ).action_refuse()

        self.assertEqual(request.state, "refused")
        self.assertFalse(self.document._has_access(self.partner, "view"))

    def test_access_already_held_is_not_asked_for(self):
        self.document.editor_partner_ids = self.partner

        with self.assertRaises(UserError):
            self.document._request_access(self.partner, "view")
        self.assertFalse(self.document.approval_request_ids)

    def test_an_edit_request_is_a_different_subject_from_a_view_request(self):
        view = self.document._request_access(self.partner, "view")
        edit = self.document._request_access(self.partner, "edit")

        self.assertNotEqual(view, edit)
        self.assertEqual(
            self.document._get_live_access_request(self.partner, "view"), view
        )

    def test_an_approver_deciding_from_the_record_records_a_decision(self):
        request = self.document._request_access(self.partner, "view")

        decided = self.document.with_user(self.approver_1)._decide_access_request(
            self.partner, "view", approve=True
        )

        self.assertTrue(decided)
        self.assertEqual(request.state, "approved")
        self.assertEqual(
            request.approver_ids.filtered("decision_date").decided_by_user_id,
            self.approver_1,
        )
        self.assertIn(self.partner, self.document.viewer_partner_ids)

    def test_whoever_may_write_the_record_decides_without_a_decision(self):
        request = self.document._request_access(self.partner, "view")

        self.document._decide_access_request(self.partner, "view", approve=False)

        self.assertEqual(request.state, "refused")
        self.assertFalse(request.approver_ids.filtered("decision_date"))

    def test_nobody_else_decides(self):
        request = self.document._request_access(self.partner, "view")

        with self.assertRaises(AccessError):
            self.document.with_user(self.approver_2)._decide_access_request(
                self.partner, "view", approve=True
            )
        self.assertEqual(request.state, "pending")

    def test_no_waiting_request_decides_nothing(self):
        self.assertFalse(
            self.document._decide_access_request(self.partner, "view", approve=True)
        )

    def test_a_key_of_another_kind_names_no_partner(self):
        partner, role = self.document._get_access_subject("stage:3")

        self.assertFalse(partner)
        self.assertFalse(role)
