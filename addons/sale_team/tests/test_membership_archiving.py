from odoo import exceptions
from odoo.tests import TransactionCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_team.tests.common import TestSalesCommon


class TestArchivedTeamMembership(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.team = cls.env["team.team"].create(
            {"use_sale": True, "name": "Doomed", "company_id": False}
        )
        cls.member = cls.env["team.member"].create(
            {"team_id": cls.team.id, "user_id": cls.user_sales_leads.id}
        )
        cls.env.flush_all()

    def test_write_active_false_cascades_like_the_action(self):
        self.team.write({"active": False})
        self.env.flush_all()
        self.assertFalse(self.member.active)

    def test_archiving_a_user_by_write_cascades(self):
        self.user_sales_leads.with_context(active_test=False).write({"active": False})
        self.env.flush_all()
        self.assertFalse(self.member.active)

    def test_cannot_join_an_archived_team(self):
        self.team.action_archive()
        self.env.flush_all()
        other = mail_new_test_user(
            self.env, login="joins_dead", name="Joins Dead", groups="base.group_user"
        )
        with self.assertRaises(exceptions.ValidationError):
            self.env["team.member"].create(
                {"team_id": self.team.id, "user_id": other.id}
            )
            self.env.flush_all()

    def test_cannot_unarchive_onto_an_archived_team(self):
        self.team.action_archive()
        self.env.flush_all()
        self.assertFalse(self.member.active)
        with self.assertRaises(exceptions.ValidationError):
            self.member.action_unarchive()
            self.env.flush_all()

    def test_cannot_join_a_team_as_an_archived_user(self):
        ghost = mail_new_test_user(
            self.env, login="ghost_user", name="Ghost User", groups="base.group_user"
        )
        ghost.action_archive()
        self.env.flush_all()
        with self.assertRaises(exceptions.ValidationError):
            self.env["team.member"].create(
                {"team_id": self.team.id, "user_id": ghost.id}
            )
            self.env.flush_all()

    def test_cannot_unarchive_a_membership_of_an_archived_user(self):
        self.user_sales_leads.action_archive()
        self.env.flush_all()
        self.assertFalse(self.member.active)
        with self.assertRaises(exceptions.ValidationError):
            self.member.action_unarchive()
            self.env.flush_all()

    def test_reads_and_searches_agree_on_an_archived_user(self):
        self.user_sales_leads.action_archive()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            self.team.member_ids.ids,
            self.team.team_member_ids.user_id.ids,
            "the many2many and the one2many must report the same people",
        )
        self.assertNotIn(
            self.team,
            self.env["team.team"].search(
                [("member_ids", "in", [self.user_sales_leads.id])]
            ),
            "search must agree with the many2many read",
        )
        self.env.cr.execute(
            "SELECT sale_team_id FROM res_users WHERE id = %s",
            (self.user_sales_leads.id,),
        )
        self.assertNotEqual(
            self.env.cr.fetchone()[0],
            self.team.id,
            "the stored column must not stay pinned to the team",
        )

    def test_stored_sale_team_id_never_holds_an_archived_team(self):
        self.team.write({"active": False})
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT sale_team_id FROM res_users WHERE id = %s",
            (self.user_sales_leads.id,),
        )
        self.assertNotEqual(self.env.cr.fetchone()[0], self.team.id)


class TestArchivedMembershipVisibility(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.other_team = cls.env["team.team"].create(
            {"use_sale": True, "name": "Other", "company_id": False}
        )
        cls.other_membership = cls.env["team.member"].create(
            {
                "user_id": cls.user_sales_leads.id,
                "team_id": cls.other_team.id,
            }
        )

    def test_search_sale_team_ids_matches_compute(self):
        self.sales_team_1_m1.action_archive()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertNotIn(self.sales_team_1, self.user_sales_leads.sale_team_ids)
        matched = self.env["res.users"].search(
            [("sale_team_ids", "in", self.sales_team_1.ids)]
        )
        self.assertNotIn(self.user_sales_leads, matched)
        self.assertIn(self.other_team, self.user_sales_leads.sale_team_ids)
        self.assertIn(
            self.user_sales_leads,
            self.env["res.users"].search(
                [("sale_team_ids", "in", self.other_team.ids)]
            ),
        )

    def test_search_sale_team_ids_keeps_archived_users(self):
        self.user_sales_leads.with_context(active_test=False).write({"active": False})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertFalse(self.user_sales_leads.with_context(active_test=False).active)
        matched = (
            self.env["res.users"]
            .with_context(active_test=False)
            .search([("sale_team_ids", "=", False)])
        )
        self.assertIn(
            self.user_sales_leads,
            matched,
            "an archived user must stay searchable by team",
        )
        self.assertNotIn(
            self.user_sales_leads,
            self.env["res.users"].search([("sale_team_ids", "=", False)]),
            "and must not leak into a default-context search",
        )

    def test_an_archived_user_cannot_keep_a_live_membership(self):
        self.user_sales_leads.with_context(active_test=False).write({"active": False})
        self.env.flush_all()
        self.assertFalse(self.other_membership.active, "the cascade archived it")
        with self.assertRaises(exceptions.ValidationError):
            self.other_membership.action_unarchive()
            self.env.flush_all()

    def test_sale_team_id_ignores_archived_membership(self):
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)
        archiving_env = self.env(context=dict(self.env.context, active_test=False))
        self.sales_team_1_m1.with_env(archiving_env).action_archive()
        archiving_env.flush_all()

        self.env.cr.execute(
            "SELECT sale_team_id FROM res_users WHERE id = %s",
            (self.user_sales_leads.id,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], self.other_team.id)
        self.env.invalidate_all()
        self.assertEqual(self.user_sales_leads.sale_team_id, self.other_team)

    def test_member_warning_ignores_archived_membership(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )
        self.other_membership.action_archive()
        self.env.flush_all()
        self.env.invalidate_all()

        for context_label, team in (
            ("default", self.sales_team_1),
            ("active_test=False", self.sales_team_1.with_context(active_test=False)),
        ):
            self.env.invalidate_all()
            self.assertNotIn(
                self.other_team.name,
                team.member_warning or "",
                f"{context_label}: an archived membership must not raise a warning",
            )


class TestArchiveCascadeOnFalsyValues(TestSalesCommon):
    def test_a_falsy_active_archives_the_team_memberships(self):
        self.sales_team_1.write({"active": 0})
        self.assertFalse(self.sales_team_1_m1.active)
        self.assertFalse(self.sales_team_1_m2.active)

    def test_a_falsy_active_archives_the_user_memberships(self):
        self.user_sales_leads.write({"active": 0})
        self.assertFalse(self.sales_team_1_m1.active)


class TestUserArchiving(TestSalesCommon):
    def test_settings_admin_can_archive_a_salesperson(self):
        settings_admin = mail_new_test_user(
            self.env,
            login="settings_admin",
            name="Settings Admin",
            groups="base.group_user,base.group_system",
        )
        self.assertFalse(settings_admin.has_group("sale.group_sale_manager"))

        self.user_sales_leads.with_user(settings_admin).action_archive()
        self.env.flush_all()

        self.assertFalse(self.user_sales_leads.active)
        self.assertFalse(self.sales_team_1_m1.active, "the membership follows the user")


@tagged("post_install", "-at_install")
class TestUserSaleTeam(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = mail_new_test_user(
            cls.env,
            login="sale_team_user",
            email="sale.team@example.com",
            groups="sale.group_sale_salesman",
        )
        cls.team = cls.env["team.team"].create({"use_sale": True, "name": "STU team"})

    def test_no_membership_no_team(self):
        self.user.invalidate_recordset(["sale_team_id"])
        self.assertFalse(self.user.sale_team_id)

    def test_membership_sets_sale_team(self):
        self.env["team.member"].create(
            {"user_id": self.user.id, "team_id": self.team.id}
        )
        self.user.invalidate_recordset(["sale_team_id"])
        self.assertEqual(self.user.sale_team_id, self.team)

    def test_archive_user_archives_memberships(self):
        member = self.env["team.member"].create(
            {"user_id": self.user.id, "team_id": self.team.id}
        )
        self.user.action_archive()
        self.assertFalse(member.active)
