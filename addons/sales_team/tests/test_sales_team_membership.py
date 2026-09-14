from odoo import exceptions
from odoo.tests.common import users

from odoo.addons.sales_team.tests.common import TestSalesCommon


class TestMembership(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_team = cls.env["crm.team"].create(
            {
                "name": "Test Specific",
                "sequence": 10,
            }
        )
        cls.env["ir.config_parameter"].set_param("sales_team.membership_multi", True)

    def test_archive_user_archives_team_member(self):
        self.assertTrue(self.sales_team_1_m1.active)
        self.user_sales_leads.action_archive()
        self.assertFalse(self.sales_team_1_m1.active)

    def test_archive_team_archives_team_member(self):
        self.assertTrue(self.sales_team_1_m1.active)
        self.assertTrue(self.sales_team_1_m2.active)
        self.sales_team_1.action_archive()
        self.assertFalse(self.sales_team_1_m1.active)
        self.assertFalse(self.sales_team_1_m2.active)
        self.sales_team_1.action_unarchive()
        self.assertFalse(self.sales_team_1_m1.active)
        self.assertFalse(self.sales_team_1_m2.active)

    def test_leader_can_read_led_team(self):
        salesman = self.user_sales_salesman
        led_team = self.env["crm.team"].create(
            {
                "name": "Led Not Member",
                "company_id": False,
                "user_id": salesman.id,
            }
        )
        foreign_team = self.env["crm.team"].create(
            {
                "name": "Foreign Team",
                "company_id": False,
                "user_id": self.user_sales_manager.id,
            }
        )
        self.assertNotIn(
            salesman, led_team.member_ids, "leader must not be auto-added as member"
        )
        self.assertEqual(
            led_team.with_user(salesman).read(["name"])[0]["name"], "Led Not Member"
        )
        self.assertEqual(
            foreign_team.with_user(salesman).read(["name"])[0]["name"], "Foreign Team"
        )
        with self.assertRaises(exceptions.AccessError):
            foreign_team.with_user(salesman).write({"name": "Trolling"})

    @users("user_sales_manager")
    def test_fields(self):
        self.assertTrue(self.sales_team_1.with_user(self.env.user).is_membership_multi)
        self.assertTrue(self.new_team.with_user(self.env.user).is_membership_multi)

        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )
        self.assertFalse(self.sales_team_1.with_user(self.env.user).is_membership_multi)
        self.assertFalse(self.new_team.with_user(self.env.user).is_membership_multi)

    @users("user_sales_manager")
    def test_members_mono(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )
        sales_team_1 = self.sales_team_1.with_user(self.env.user)
        new_team = self.new_team.with_user(self.env.user)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )

        self.assertEqual(new_team.member_ids, self.env["res.users"])
        new_team.write({"member_ids": [(4, self.env.uid)]})
        self.assertEqual(new_team.member_ids, self.env.user)
        new_team.write({"member_ids": [(4, self.user_sales_leads.id)]})
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        new_team.write({"member_ids": [(3, self.user_sales_leads.id)]})
        self.assertEqual(new_team.member_ids, self.env.user)
        new_team.write(
            {"member_ids": [(6, 0, (self.user_sales_leads | self.env.user).ids)]}
        )
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        self.assertEqual(sales_team_1.member_ids, self.user_admin)

        self.user_sales_manager.write(
            {"group_ids": [(4, self.env.ref("base.group_system").id)]}
        )
        new_team.write(
            {
                "member_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Marty OnTheMCFly",
                            "login": "mcfly@test.example.com",
                        },
                    )
                ]
            }
        )
        new_user = self.env["res.users"].search(
            [("login", "=", "mcfly@test.example.com")]
        )
        self.assertTrue(len(new_user))
        self.assertEqual(
            new_team.member_ids, self.env.user | self.user_sales_leads | new_user
        )
        self.user_sales_manager.write(
            {"group_ids": [(3, self.env.ref("base.group_system").id)]}
        )

        self.env.flush_all()
        memberships = (
            self.env["crm.team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertEqual(len(memberships), 3)
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)
        self.assertFalse(
            memberships.filtered(lambda m: m.crm_team_id == sales_team_1).active
        )
        new_team_memberships = memberships.filtered(lambda m: m.crm_team_id == new_team)
        self.assertEqual(len(new_team_memberships), 2)
        self.assertEqual(set(new_team_memberships.mapped("active")), {False, True})

        with self.assertRaises(exceptions.UserError):
            self.env["crm.team.member"].create(
                {"crm_team_id": new_team.id, "user_id": new_user.id}
            )

    @users("user_sales_manager")
    def test_members_multi(self):
        sales_team_1 = self.sales_team_1.with_user(self.env.user)
        new_team = self.new_team.with_user(self.env.user)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )

        self.assertEqual(new_team.member_ids, self.env["res.users"])
        new_team.write(
            {"member_ids": [(4, self.env.uid), (4, self.user_sales_leads.id)]}
        )
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        new_team.write({"member_ids": [(3, self.user_sales_leads.id)]})
        self.assertEqual(new_team.member_ids, self.env.user)
        new_team.write(
            {"member_ids": [(6, 0, (self.user_sales_leads | self.env.user).ids)]}
        )
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )

        self.user_sales_manager.write(
            {"group_ids": [(4, self.env.ref("base.group_system").id)]}
        )
        new_team.write(
            {
                "member_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Marty OnTheMCFly",
                            "login": "mcfly@test.example.com",
                        },
                    )
                ]
            }
        )
        new_user = self.env["res.users"].search(
            [("login", "=", "mcfly@test.example.com")]
        )
        self.assertTrue(len(new_user))
        self.assertEqual(
            new_team.member_ids, self.env.user | self.user_sales_leads | new_user
        )
        self.user_sales_manager.write(
            {"group_ids": [(3, self.env.ref("base.group_system").id)]}
        )
        self.env.flush_all()

        with self.assertRaises(exceptions.UserError):
            self.env["crm.team.member"].create(
                {"crm_team_id": new_team.id, "user_id": new_user.id}
            )

    @users("user_sales_manager")
    def test_memberships_mono(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )
        sales_team_1 = self.env["crm.team"].browse(self.sales_team_1.ids)
        new_team = self.env["crm.team"].browse(self.new_team.ids)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )

        self.assertEqual(new_team.member_ids, self.env["res.users"])
        new_team.write(
            {
                "crm_team_member_ids": [
                    (0, 0, {"user_id": self.user_sales_leads.id}),
                    (0, 0, {"user_id": self.uid}),
                ]
            }
        )
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        self.assertEqual(sales_team_1.member_ids, self.user_admin)
        self.env.flush_all()

        memberships = (
            self.env["crm.team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)
        self.assertFalse(
            memberships.filtered(lambda m: m.crm_team_id == sales_team_1).active
        )
        self.assertTrue(
            memberships.filtered(lambda m: m.crm_team_id == new_team).active
        )

        sales_team_1.write(
            {"crm_team_member_ids": [(0, 0, {"user_id": self.user_sales_leads.id})]}
        )
        memberships_new = (
            self.env["crm.team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertTrue(memberships < memberships_new)
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)

        old_st_1 = memberships_new.filtered(
            lambda m: m.crm_team_id == sales_team_1 and m in memberships
        )
        new_st_1 = memberships_new.filtered(
            lambda m: m.crm_team_id == sales_team_1 and m not in memberships
        )
        new_nt = memberships_new.filtered(lambda m: m.crm_team_id == new_team)
        self.assertFalse(old_st_1.active)
        self.assertTrue(new_st_1.active)
        self.assertFalse(new_nt.active)

        self.assertEqual(new_team.member_ids, self.env.user)
        self.assertEqual(
            sales_team_1.member_ids, self.user_admin | self.user_sales_leads
        )

        new_nt.action_unarchive()
        self.assertTrue(new_nt.active)
        self.assertFalse(old_st_1.active)
        self.assertFalse(new_st_1.active)
        old_st_1.action_unarchive()
        self.assertFalse(new_nt.active)
        self.assertTrue(old_st_1.active)
        self.assertFalse(new_st_1.active)

        with self.assertRaises(exceptions.UserError):
            new_st_1.action_unarchive()

    @users("user_sales_manager")
    def test_memberships_multi(self):
        sales_team_1 = self.env["crm.team"].browse(self.sales_team_1.ids)
        new_team = self.env["crm.team"].browse(self.new_team.ids)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )

        self.assertEqual(new_team.member_ids, self.env["res.users"])
        new_team.write(
            {
                "crm_team_member_ids": [
                    (0, 0, {"user_id": self.user_sales_leads.id}),
                    (0, 0, {"user_id": self.uid}),
                ]
            }
        )
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )
        self.env.flush_all()

        memberships = (
            self.env["crm.team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)
        self.assertTrue(
            memberships.filtered(lambda m: m.crm_team_id == sales_team_1).active
        )
        self.assertTrue(
            memberships.filtered(lambda m: m.crm_team_id == new_team).active
        )

        memberships.filtered(lambda m: m.crm_team_id == sales_team_1).write(
            {"active": False}
        )
        sales_team_1.write(
            {"crm_team_member_ids": [(0, 0, {"user_id": self.user_sales_leads.id})]}
        )
        memberships_new = (
            self.env["crm.team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertTrue(memberships < memberships_new)
        self.assertEqual(memberships.crm_team_id, sales_team_1 | new_team)

        old_st_1 = memberships_new.filtered(
            lambda m: m.crm_team_id == sales_team_1 and m in memberships
        )
        new_st_1 = memberships_new.filtered(
            lambda m: m.crm_team_id == sales_team_1 and m not in memberships
        )
        new_nt = memberships_new.filtered(lambda m: m.crm_team_id == new_team)
        self.assertFalse(old_st_1.active)
        self.assertTrue(new_st_1.active)
        self.assertTrue(new_nt.active)

        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        self.assertEqual(
            sales_team_1.member_ids, self.user_admin | self.user_sales_leads
        )

        with self.assertRaises(exceptions.UserError):
            old_st_1.action_unarchive()

    @users("user_sales_manager")
    def test_memberships_sync(self):
        sales_team_1 = self.env["crm.team"].browse(self.sales_team_1.ids)
        new_team = self.env["crm.team"].browse(self.new_team.ids)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )
        self.assertEqual(new_team.crm_team_member_ids, self.env["crm.team.member"])
        self.assertEqual(new_team.crm_team_member_all_ids, self.env["crm.team.member"])
        self.assertEqual(new_team.member_ids, self.env["res.users"])

        new_member = self.env["crm.team.member"].create(
            {
                "user_id": self.env.user.id,
                "crm_team_id": self.new_team.id,
            }
        )
        self.assertEqual(new_team.crm_team_member_ids, new_member)
        self.assertEqual(new_team.crm_team_member_all_ids, new_member)
        self.assertEqual(new_team.member_ids, self.env.user)

        new_team.write({"member_ids": [(4, self.user_sales_leads.id)]})
        added = self.env["crm.team.member"].search(
            [
                ("crm_team_id", "=", new_team.id),
                ("user_id", "=", self.user_sales_leads.id),
            ]
        )
        self.assertEqual(new_team.crm_team_member_ids, new_member + added)
        self.assertEqual(new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        added.write({"active": False})
        self.assertEqual(new_team.crm_team_member_ids, new_member)
        self.assertEqual(new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user)

        added.write({"active": True})
        self.assertEqual(new_team.crm_team_member_ids, new_member + added)
        self.assertEqual(new_team.crm_team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        admin_original = self.env["crm.team.member"].search(
            [
                ("crm_team_id", "=", sales_team_1.id),
                ("user_id", "=", self.user_admin.id),
            ]
        )
        self.assertTrue(bool(admin_original))
        admin_archived = self.env["crm.team.member"].create(
            {
                "crm_team_id": new_team.id,
                "user_id": self.user_admin.id,
                "active": False,
            }
        )
        admin_original.write({"crm_team_id": new_team.id})
        self.env.flush_all()
        self.assertTrue(self.user_admin in new_team.member_ids)
        self.assertTrue(admin_original.active)
        self.assertTrue(admin_archived.exists())
        self.assertFalse(admin_archived.active)

        with self.assertRaises(exceptions.ValidationError):
            added.write({"crm_team_id": sales_team_1.id})

    def test_users_sale_team_id(self):
        self.assertTrue(self.sales_team_1.sequence < self.new_team.sequence)

        self.assertEqual(self.user_sales_leads.crm_team_ids, self.sales_team_1)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        self.new_team.write({"member_ids": [(4, self.user_sales_leads.id)]})
        self.assertEqual(
            self.user_sales_leads.crm_team_ids, self.sales_team_1 | self.new_team
        )
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        self.sales_team_1_m1.write({"active": False})
        self.assertEqual(self.user_sales_leads.crm_team_ids, self.new_team)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.new_team)

        self.sales_team_1_m1.write({"active": True})
        self.assertEqual(
            self.user_sales_leads.crm_team_ids, self.sales_team_1 | self.new_team
        )
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        self.sales_team_1_m1.unlink()
        self.assertEqual(self.user_sales_leads.crm_team_ids, self.new_team)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.new_team)
