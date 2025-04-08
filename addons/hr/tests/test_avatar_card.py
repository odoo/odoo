# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo


class TestAvatarCardMultiCompanies(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._mc_enabled = True
        cls.company_1 = cls.env["res.company"].search([("name", "=", "YourCompany")], limit=1)
        cls.company_2 = cls.env["res.company"].create(
            {
                "name": "Test Company 2",
            }
        )
        cls.user_1 = cls.env["res.users"].create(
            {
                "name": "Test User 1",
                "login": "test_user_1",
            }
        )
        cls.user_2 = cls.env["res.users"].create(
            {
                "name": "Test User 2",
                "login": "test_user_2",
            }
        )
        cls.user_admin.write(
            {
                "company_ids": [(4, cls.company_1.id), (4, cls.company_2.id)],
            }
        )
        cls.employee_1 = cls.env["hr.employee"].create(
            {
                "name": "Test Employee 1",
                "user_id": cls.user_1.id,
                "company_id": cls.company_1.id,
                "work_email": "test_employee_1@test.com",
            }
        )

        cls.employee_2 = cls.env["hr.employee"].create(
            {
                "name": "Test Employee 2",
                "user_id": cls.user_2.id,
                "company_id": cls.company_2.id,
                "work_email": "test_employee_2@test.com",
            }
        )

    def test_avatar_card_multi_company_takes_default_company(self):
        self.authenticate("admin", "admin")
        response = self.make_jsonrpc_request(
            "/mail/avatar_card/get_user_info", {"user_id": self.user_1.id}
        )
        self.assertEqual(
            response["work_email"],
            "test_employee_1@test.com"
        )

    def test_avatar_card_multi_company_takes_other_company(self):
        self.authenticate("admin", "admin")
        response = self.make_jsonrpc_request(
            "/mail/avatar_card/get_user_info", {"user_id": self.user_2.id}
        )
        self.assertEqual(
            response["work_email"],
            "test_employee_2@test.com"
        )
