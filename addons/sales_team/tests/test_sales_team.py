from odoo import exceptions
from odoo.tests import tagged, users

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sales_team.tests.common import (
    SalesTeamCommon,
    TestSalesCommon,
    TestSalesMC,
)


class TestDefaultTeam(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].set_param("sales_team.membership_multi", True)

        cls.company_2 = cls.env["res.company"].create(
            {
                "name": "New Test Company",
                "email": "company.2@test.example.com",
                "country_id": cls.env.ref("base.fr").id,
            }
        )
        cls.team_c2 = cls.env["crm.team"].create(
            {
                "name": "C2 Team1",
                "sequence": 1,
                "company_id": cls.company_2.id,
                "user_id": False,
            }
        )
        cls.team_sequence = cls.env["crm.team"].create(
            {
                "company_id": False,
                "name": "Team LowSequence",
                "member_ids": [(4, cls.user_sales_leads.id)],
                "sequence": 0,
                "user_id": False,
            }
        )
        cls.team_responsible = cls.env["crm.team"].create(
            {
                "company_id": cls.company_main.id,
                "name": "Team 3",
                "user_id": cls.user_sales_manager.id,
                "sequence": 3,
            }
        )

    def test_default_team_fallback(self):
        self.sales_team_1.member_ids = [(5,)]
        self.team_sequence.member_ids = [(5,)]
        (self.sales_team_1 + self.team_sequence).flush_model()
        self.assertFalse(
            self.env["crm.team.member"].search(
                [("user_id", "=", self.user_sales_leads.id)]
            )
        )

        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.team_sequence)

        self.team_sequence.active = False
        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.team_responsible)

        self.user_sales_leads.write(
            {
                "company_ids": [(4, self.company_2.id)],
                "company_id": self.company_2.id,
            }
        )
        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.team_c2)

    def test_default_team_member(self):
        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.team_sequence)

        self.team_sequence.member_ids = [(5,)]
        self.team_sequence.flush_model()
        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.sales_team_1)

        self.team_responsible.user_id = self.user_sales_leads.id
        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.team_responsible)

        self.team_responsible.sequence = self.sales_team_1.sequence
        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.team_responsible)

    def test_default_team_wcontext(self):
        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.team_sequence)

            team = (
                self.env["crm.team"]
                .with_context(default_team_id=self.sales_team_1.id)
                ._get_default_team_id()
            )
            self.assertEqual(
                team,
                self.sales_team_1,
                "SalesTeam: default takes over ordering when member / responsible",
            )

        self.sales_team_1.member_ids = [(5,)]
        self.team_sequence.member_ids = [(5,)]
        (self.sales_team_1 + self.team_sequence).flush_model()
        self.assertFalse(
            self.env["crm.team.member"].search(
                [("user_id", "=", self.user_sales_leads.id)]
            )
        )

        with self.with_user("user_sales_leads"):
            team = self.env["crm.team"]._get_default_team_id()
            self.assertEqual(team, self.team_sequence)

            team = (
                self.env["crm.team"]
                .with_context(default_team_id=self.sales_team_1.id)
                ._get_default_team_id()
            )
            self.assertEqual(
                team,
                self.sales_team_1,
                "SalesTeam: default taken into account when no member / responsible",
            )


class TestMultiCompany(TestSalesMC):
    @users("user_sales_manager")
    def test_team_members(self):
        team_c2 = self.env["crm.team"].browse(self.team_c2.id)
        team_c2.write({"name": "Manager Update"})
        self.assertEqual(team_c2.member_ids, self.env["res.users"])

        self.env.user.write({"company_id": self.company_2.id})
        team_c2.write({"member_ids": [(4, self.env.user.id)]})
        self.assertEqual(team_c2.member_ids, self.env.user)

        with self.assertRaises(exceptions.UserError):
            team_c2.write({"member_ids": [(4, self.user_sales_salesman.id)]})

        team_c2.write({"member_ids": [(5, 0)], "company_id": self.company_main.id})
        self.assertEqual(team_c2.member_ids, self.env["res.users"])
        team_c2.write({"member_ids": [(4, self.user_sales_salesman.id)]})
        self.assertEqual(team_c2.member_ids, self.user_sales_salesman)

        with self.assertRaises(exceptions.UserError):
            team_c2.write({"company_id": self.company_2.id})

        team_c2.write({"member_ids": [(5, 0)]})
        team_c2.write({"company_id": self.company_2.id})
        c1, c2 = self.company_main, self.company_2
        with self.with_user("admin"):
            user_c1_c2 = mail_new_test_user(
                self.env,
                login=f"Test_user_default_to_c{c1.id}_allowed_c{'c'.join(map(str, [c1.id, c2.id]))}",
                company_id=c1.id,
                company_ids=[(4, company.id) for company in c1 + c2],
            )
        user_c1_c2 = user_c1_c2.with_env(self.env)
        team_c2.write({"member_ids": [(4, user_c1_c2.id)]})
        self.assertIn(user_c1_c2, team_c2.member_ids)

    @users("user_sales_manager")
    def test_team_memberships(self):
        team_c2 = self.env["crm.team"].browse(self.team_c2.id)
        team_c2.write({"name": "Manager Update"})
        self.assertEqual(team_c2.member_ids, self.env["res.users"])

        self.env.user.write({"company_id": self.company_2.id})
        team_c2.write({"crm_team_member_ids": [(0, 0, {"user_id": self.env.user.id})]})
        self.assertEqual(team_c2.member_ids, self.env.user)

        with self.assertRaises(exceptions.UserError):
            team_c2.write(
                {
                    "crm_team_member_ids": [
                        (0, 0, {"user_id": self.user_sales_salesman.id})
                    ]
                }
            )

        team_c2.write({"member_ids": [(5, 0)], "company_id": self.company_main.id})
        self.assertEqual(team_c2.member_ids, self.env["res.users"])
        team_c2.write(
            {"crm_team_member_ids": [(0, 0, {"user_id": self.user_sales_salesman.id})]}
        )
        self.assertEqual(team_c2.member_ids, self.user_sales_salesman)

        with self.assertRaises(exceptions.UserError):
            team_c2.write({"company_id": self.company_2.id})


@tagged("post_install", "-at_install")
class TestAccessRights(SalesTeamCommon):
    @users("salesmanager")
    def test_access_sales_manager(self):
        india_channel = (
            self.env["crm.team"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "India",
                }
            )
        )
        self.assertIn(
            india_channel.id,
            self.env["crm.team"].search([]).ids,
            "Sales manager should be able to create a Sales Team",
        )

        india_channel.write({"name": "new_india"})
        self.assertEqual(
            india_channel.name,
            "new_india",
            "Sales manager should be able to edit a Sales Team",
        )

        india_channel.unlink()
        self.assertNotIn(
            india_channel.id,
            self.env["crm.team"].search([]).ids,
            "Sales manager should be able to delete a Sales Team",
        )
