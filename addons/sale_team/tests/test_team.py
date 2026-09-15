from odoo import exceptions

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_team.tests.common import TestSalesCommon


class TestDefaultTeamProtection(TestSalesCommon):
    def test_default_teams_cannot_be_deleted(self):
        for xmlid in (
            "sale_team.team_sales_department",
            "sale_team.salesteam_website_sales",
            "sale_team.pos_sales_team",
        ):
            with self.assertRaises(exceptions.UserError), self.env.cr.savepoint():
                self.env.ref(xmlid).unlink()

    def test_unlink_survives_a_missing_default_xmlid(self):
        self.env["ir.model.data"].search(
            [("module", "=", "sale_team"), ("name", "=", "pos_sales_team")]
        ).unlink()
        self.env.flush_all()
        self.env.registry.clear_cache()

        disposable = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Disposable",
                "company_id": False,
            }
        )
        self.env.flush_all()
        disposable.unlink()
        self.assertFalse(disposable.exists())


class TestFavorite(TestSalesCommon):
    def test_is_user_favorite_is_per_user(self):
        team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Favorite",
                "company_id": False,
            }
        )
        team.favorite_user_ids = [(6, 0, [self.user_sales_manager.id])]
        self.env.flush_all()

        for first, second in (
            (self.user_sales_manager, self.user_sales_leads),
            (self.user_sales_leads, self.user_sales_manager),
        ):
            self.env.invalidate_all()
            expected_first = first == self.user_sales_manager
            self.assertEqual(team.with_user(first).is_user_favorite, expected_first)
            self.assertEqual(
                team.with_user(second).is_user_favorite, not expected_first
            )

    def test_is_user_favorite_follows_favorite_user_ids(self):
        team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Favorite 2",
                "company_id": False,
            }
        )
        as_leads = team.with_user(self.user_sales_leads)
        self.assertFalse(as_leads.is_user_favorite)

        team.favorite_user_ids = [(4, self.user_sales_leads.id)]
        self.assertTrue(as_leads.is_user_favorite)

        team.favorite_user_ids = [(3, self.user_sales_leads.id)]
        self.assertFalse(as_leads.is_user_favorite)

    def test_adding_members_refreshes_the_flag(self):
        team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Favorite 3",
                "company_id": False,
                "member_ids": [(4, self.user_sales_leads.id)],
            }
        )
        self.env.flush_all()
        self.assertTrue(team.with_user(self.user_sales_leads).is_user_favorite)

    def test_every_way_of_joining_a_team_grants_the_favorite(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        leads = self.user_sales_leads
        teams = {}

        teams["member_ids on create"] = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Join A",
                "company_id": False,
                "member_ids": [(4, leads.id)],
            }
        )

        teams["member_ids on write"] = team = self.env["team.team"].create(
            {"use_sale": True, "name": "Join B", "company_id": False}
        )
        team.write({"member_ids": [(4, leads.id)]})

        teams["team_member_ids on create"] = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Join C",
                "company_id": False,
                "team_member_ids": [(0, 0, {"user_id": leads.id})],
            }
        )

        teams["team_member_ids on write"] = team = self.env["team.team"].create(
            {"use_sale": True, "name": "Join D", "company_id": False}
        )
        team.write({"team_member_ids": [(0, 0, {"user_id": leads.id})]})

        teams["team.member.create"] = team = self.env["team.team"].create(
            {"use_sale": True, "name": "Join E", "company_id": False}
        )
        self.env["team.member"].create({"team_id": team.id, "user_id": leads.id})

        self.env.flush_all()
        for label, team in teams.items():
            self.assertIn(leads, team.member_ids, f"{label}: membership")
            self.assertIn(leads, team.favorite_user_ids, f"{label}: favorite")


class TestFavoriteOnEveryJoin(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.first = mail_new_test_user(cls.env, login="fav_first", name="Fav First")
        cls.second = mail_new_test_user(cls.env, login="fav_second", name="Fav Second")

    def test_handing_a_membership_over_favorites_the_new_salesperson(self):
        team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Handover",
                "company_id": False,
            }
        )
        membership = self.env["team.member"].create(
            {"team_id": team.id, "user_id": self.first.id}
        )
        membership.write({"user_id": self.second.id})
        self.assertIn(self.second, team.favorite_user_ids)

    def test_moving_a_membership_favorites_the_new_team(self):
        team, target = self.env["team.team"].create(
            [
                {
                    "use_sale": True,
                    "name": "Move From",
                    "company_id": False,
                },
                {
                    "use_sale": True,
                    "name": "Move To",
                    "company_id": False,
                },
            ]
        )
        membership = self.env["team.member"].create(
            {"team_id": team.id, "user_id": self.first.id}
        )
        membership.write({"team_id": target.id})
        self.assertIn(self.first, target.favorite_user_ids)

    def test_rejoining_favorites_again(self):
        team = self.env["team.team"].create(
            {"use_sale": True, "name": "Rejoin", "company_id": False}
        )
        membership = self.env["team.member"].create(
            {"team_id": team.id, "user_id": self.first.id}
        )
        membership.action_archive()
        team.favorite_user_ids = [(3, self.first.id)]
        membership.action_unarchive()
        self.assertIn(self.first, team.favorite_user_ids)

    def test_an_archived_membership_does_not_favorite(self):
        team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Archived",
                "company_id": False,
            }
        )
        self.env["team.member"].create(
            {"team_id": team.id, "user_id": self.first.id, "active": False}
        )
        self.assertNotIn(self.first, team.favorite_user_ids)
