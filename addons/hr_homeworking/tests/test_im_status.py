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
        cls.group = (
            cls.env["discuss.channel"]
            .with_user(cls.user_employee)
            .create_group(
                (cls.alice_user | cls.clara_user | cls.dana_user | cls.eva_user).partner_id.ids,
            )
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
        init_messaging = self.make_jsonrpc_request(
            "/mail/init_messaging",
            {"context": {"allowed_company_ids": [self.company_b.id, self.company_a.id]}},
        )
        channel_members = self.make_jsonrpc_request(
            "/discuss/channel/members",
            {"channel_id": self.group.id, "known_member_ids": []},
        )
        group_info = next(c for c in init_messaging["channels"] if c["id"] == self.group.id)
        for route, result in [
            ("/mail/init_messaging", group_info),
            ("/discuss/channel/members", channel_members),
        ]:
            im_status_by_partner = {
                m["persona"]["id"]: m["persona"]["im_status"]
                for m in result["channelMembers"][0][1]
            }
            for user in self.alice_user | self.clara_user | self.dana_user | self.eva_user:
                with self.subTest(route=route, user=user.login):
                    self.assertEqual(im_status_by_partner[user.partner_id.id], "home_offline")
