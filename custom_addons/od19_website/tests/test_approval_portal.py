from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestApprovalPortal(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create({
            "name": "Approval Tester",
            "login": "approval_tester",
            "password": "approval_tester",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })

    def test_my_approvals_page_renders(self):
        self.authenticate("approval_tester", "approval_tester")
        response = self.url_open("/my/approvals")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"od19-tab-approver", response.content)
        self.assertIn(b"od19-tab-requester", response.content)

    def test_portal_card_links_to_approvals(self):
        self.authenticate("approval_tester", "approval_tester")
        response = self.url_open("/employee-portal")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/my/approvals", response.content)
