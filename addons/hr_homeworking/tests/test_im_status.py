# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestImStatusMultiCompany(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Company B"})
        cls.user_employee = mail_new_test_user(
            cls.env,
            company_id=cls.company_a.id,
            company_ids=[cls.company_a.id, cls.company_b.id],
            login="user_employee",
        )
        cls.alice_user = cls._create_user_at_home("alice_user", cls.company_b, cls.company_b)
        cls.clara_user = cls._create_user_at_home("clara_user", cls.company_a, cls.company_a)
        cls.dana_user = cls._create_user_at_home(
            "dana_user",
            cls.company_a | cls.company_b,
            cls.company_b,
        )
        cls.eva_user = cls._create_user_at_home(
            "eva_user",
            cls.company_a | cls.company_b,
            cls.company_a,
        )
        cls._create_employee(cls.eva_user, cls.company_b, "office")
        company_c = cls.env["res.company"].create({"name": "Company C"})
        cls.fanny_user = mail_new_test_user(
            cls.env,
            company_id=cls.company_a.id,
            company_ids=[cls.company_a.id, cls.company_b.id, company_c.id],
            login="fanny_user",
        )
        cls._create_employee(cls.fanny_user, cls.company_b, "office")
        cls._create_employee(cls.fanny_user, company_c, "home")
        cls.users_at_home = (
            cls.alice_user | cls.clara_user | cls.dana_user | cls.eva_user | cls.fanny_user
        )
        cls.group = (
            cls.env["discuss.channel"]
            .with_user(cls.user_employee)
            .create_group(cls.users_at_home.partner_id.ids)
        )

    @classmethod
    def _create_user_at_home(cls, login, companies, employee_company):
        user = mail_new_test_user(
            cls.env,
            company_id=companies[0].id,
            company_ids=companies.ids,
            login=login,
        )
        cls._create_employee(user, employee_company, "home")
        return user

    @classmethod
    def _create_employee(cls, user, company, location_type):
        location = cls.env["hr.work.location"].create(
            {
                "address_id": company.partner_id.id,
                "company_id": company.id,
                "location_type": location_type,
                "name": location_type,
            },
        )
        cls.env["hr.employee"].create(
            {
                "company_id": company.id,
                "friday_location_id": location.id,
                "monday_location_id": location.id,
                "name": user.login,
                "saturday_location_id": location.id,
                "sunday_location_id": location.id,
                "thursday_location_id": location.id,
                "tuesday_location_id": location.id,
                "user_id": user.id,
                "wednesday_location_id": location.id,
            },
        )

    def test_im_status_same_on_every_route(self):
        self.authenticate(self.user_employee.login, self.user_employee.login)
        channels_as_member = self.make_jsonrpc_request(
            "/mail/data",
            {
                "channels_as_member": True,
                "context": {"allowed_company_ids": [self.company_b.id, self.company_a.id]},
            },
        )
        channel_members = self.make_jsonrpc_request(
            "/discuss/channel/members",
            {"channel_id": self.group.id, "known_member_ids": []},
        )
        for route, result in [
            ("/mail/data", channels_as_member),
            ("/discuss/channel/members", channel_members),
        ]:
            partner_by_id = {p["id"]: p for p in result["res.partner"]}
            for user in self.users_at_home:
                with self.subTest(route=route, user=user.login):
                    self.assertEqual(partner_by_id[user.partner_id.id]["im_status"], "home_offline")

    def test_user_im_status_same_in_every_company(self):
        for companies in [self.company_a, self.company_b | self.company_a]:
            users = self.users_at_home.with_user(self.user_employee).with_context(
                allowed_company_ids=companies.ids,
            )
            users.invalidate_recordset(["im_status"])
            for user in users:
                with self.subTest(companies=companies.ids, user=user.login):
                    self.assertEqual(user.im_status, "presence_home_offline")
