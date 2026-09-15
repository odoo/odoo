from odoo.tests import users

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_team.tests.common import TestSalesCommon


class TestMembershipQueries(TestSalesCommon):
    @users("user_sales_manager")
    def test_member_warning_is_batched(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sale_team.membership_multi", True)
        salespersons = (
            self.env["res.users"]
            .sudo()
            .create(
                [
                    {
                        "name": f"Batch member {i}",
                        "login": f"batch_member_{i}",
                        "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                    }
                    for i in range(3)
                ]
            )
        )
        teams = (
            self.env["team.team"]
            .sudo()
            .create(
                [
                    {"use_sale": True, "name": f"Batch {i}", "company_id": False}
                    for i in range(20)
                ]
            )
        )
        self.env["team.member"].sudo().create(
            [
                {"team_id": team.id, "user_id": salesperson.id}
                for team in teams
                for salesperson in salespersons
            ]
        )
        self.env.flush_all()
        ICP.set_param("sale_team.membership_multi", False)
        self.env.invalidate_all()

        with self.assertQueryCount(user_sales_manager=10):
            teams.mapped("member_warning")


class TestMemberWarningVisibility(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_2 = cls.env["res.company"].create({"name": "Warning Co2"})
        cls.local_manager = mail_new_test_user(
            cls.env,
            login="warn_mgr",
            name="Warn Mgr",
            company_id=cls.company_main.id,
            company_ids=[(6, 0, [cls.company_main.id])],
            groups="sale.group_sale_manager",
        )
        cls.shared_user = mail_new_test_user(
            cls.env,
            login="warn_shared",
            name="Warn Shared",
            company_id=cls.company_main.id,
            company_ids=[(6, 0, [cls.company_main.id, cls.company_2.id])],
            groups="base.group_user",
        )
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.foreign_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "FOREIGN TEAM",
                "company_id": cls.company_2.id,
            }
        )
        cls.local_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Local Team",
                "company_id": cls.company_main.id,
            }
        )
        cls.env["team.member"].create(
            [
                {"team_id": cls.foreign_team.id, "user_id": cls.shared_user.id},
                {"team_id": cls.local_team.id, "user_id": cls.shared_user.id},
            ]
        )
        cls.env.flush_all()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )

    def test_team_warning_hides_the_foreign_team(self):
        self.env.invalidate_all()
        warning = self.local_team.with_user(self.local_manager).member_warning
        self.assertNotIn("FOREIGN TEAM", warning or "")

    def test_membership_warning_hides_the_foreign_team(self):
        self.env.invalidate_all()
        membership = self.env["team.member"].search(
            [
                ("team_id", "=", self.local_team.id),
                ("user_id", "=", self.shared_user.id),
            ]
        )
        self.assertNotIn(
            "FOREIGN TEAM",
            membership.with_user(self.local_manager).member_warning or "",
        )

    def test_a_visible_team_is_still_reported(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        self.env.invalidate_all()
        third = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Third Local",
                "company_id": self.company_main.id,
            }
        )
        self.env["team.member"].create(
            {"team_id": third.id, "user_id": self.shared_user.id}
        )
        self.env.flush_all()
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )
        self.env.invalidate_all()
        warning = self.local_team.with_user(self.local_manager).member_warning
        self.assertIn("Third Local", warning or "")


class TestWarningFollowsTheParameter(TestSalesCommon):
    def test_a_computed_warning_is_recomputed_when_mono_mode_returns(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sale_team.membership_multi", True)
        second = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Flip Second",
                "company_id": False,
            }
        )
        membership = self.env["team.member"].create(
            {"team_id": second.id, "user_id": self.user_sales_leads.id}
        )
        self.assertFalse(self.sales_team_1.member_warning)
        self.assertFalse(membership.member_warning)

        ICP.set_param("sale_team.membership_multi", False)
        self.assertIn("Flip Second", self.sales_team_1.member_warning or "")
        self.assertIn(self.sales_team_1.name, membership.member_warning or "")

        ICP.set_param("sale_team.membership_multi", True)
        self.assertFalse(self.sales_team_1.member_warning)
        self.assertFalse(membership.member_warning)


class TestMonoModeIsNotRetroactive(TestSalesCommon):
    def test_flipping_to_mono_leaves_the_extra_memberships_live(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sale_team.membership_multi", True)
        second = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Mono Second",
                "company_id": False,
            }
        )
        self.env["team.member"].create(
            {"team_id": second.id, "user_id": self.user_sales_leads.id}
        )
        self.assertEqual(len(self.user_sales_leads.sale_team_ids), 2)

        ICP.set_param("sale_team.membership_multi", False)
        self.assertEqual(
            len(self.user_sales_leads.sale_team_ids),
            2,
            "mono mode constrains writes, it does not rewrite history",
        )

    def test_the_state_is_surfaced_rather_than_silently_kept(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sale_team.membership_multi", True)
        second = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Mono Second",
                "company_id": False,
            }
        )
        self.env["team.member"].create(
            {"team_id": second.id, "user_id": self.user_sales_leads.id}
        )
        ICP.set_param("sale_team.membership_multi", False)

        self.assertIn("Mono Second", self.sales_team_1.member_warning or "")
