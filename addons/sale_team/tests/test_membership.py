from odoo import exceptions
from odoo.tests import TransactionCase, users

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_team.tests.common import TestSalesCommon


class TestCornerCases(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user_sales_leads = mail_new_test_user(
            self.env,
            login="user_sales_leads",
            name="Laetitia Sales Leads",
            email="crm_leads@test.example.com",
            company_id=self.env.user.company_id.id,
            notification_type="inbox",
            groups="sale.group_sale_salesman_all_leads,base.group_partner_manager",
        )
        self.sales_team_1 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Test Sales Team",
                "sequence": 5,
                "company_id": False,
                "user_id": self.env.user.id,
            }
        )

    def test_unicity(self):
        sales_team_1_m1 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_leads.id,
                "team_id": self.sales_team_1.id,
            }
        )

        sales_team_1_m1.write({"active": False})
        sales_team_1_m1.flush_recordset()

        sales_team_1_m2 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_leads.id,
                "team_id": self.sales_team_1.id,
            }
        )

        found = self.env["team.member"].search(
            [
                ("user_id", "=", self.user_sales_leads.id),
                ("team_id", "=", self.sales_team_1.id),
            ]
        )
        self.assertEqual(found, sales_team_1_m2)

        with self.assertRaises(exceptions.ValidationError):
            self.env["team.member"].create(
                {
                    "user_id": self.user_sales_leads.id,
                    "team_id": self.sales_team_1.id,
                }
            )

    def test_unicity_multicreate(self):
        with self.assertRaises(exceptions.ValidationError):
            self.env["team.member"].create(
                [
                    {
                        "user_id": self.user_sales_leads.id,
                        "team_id": self.sales_team_1.id,
                    },
                    {
                        "user_id": self.user_sales_leads.id,
                        "team_id": self.sales_team_1.id,
                    },
                ]
            )


class TestMembership(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Test Specific",
                "sequence": 10,
            }
        )
        cls.env["ir.config_parameter"].set_param("sale_team.membership_multi", True)

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
        led_team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Led Not Member",
                "company_id": False,
                "user_id": salesman.id,
            }
        )
        foreign_team = self.env["team.team"].create(
            {
                "use_sale": True,
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
            "sale_team.membership_multi", False
        )
        self.assertFalse(self.sales_team_1.with_user(self.env.user).is_membership_multi)
        self.assertFalse(self.new_team.with_user(self.env.user).is_membership_multi)

    @users("user_sales_manager")
    def test_members_mono(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
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
            self.env["team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertEqual(len(memberships), 3)
        self.assertEqual(memberships.team_id, sales_team_1 | new_team)
        self.assertFalse(
            memberships.filtered(lambda m: m.team_id == sales_team_1).active
        )
        new_team_memberships = memberships.filtered(lambda m: m.team_id == new_team)
        self.assertEqual(len(new_team_memberships), 2)
        self.assertEqual(set(new_team_memberships.mapped("active")), {False, True})

        with self.assertRaises(exceptions.UserError):
            self.env["team.member"].create(
                {"team_id": new_team.id, "user_id": new_user.id}
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
            self.env["team.member"].create(
                {"team_id": new_team.id, "user_id": new_user.id}
            )

    @users("user_sales_manager")
    def test_memberships_mono(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )
        sales_team_1 = self.env["team.team"].browse(self.sales_team_1.ids)
        new_team = self.env["team.team"].browse(self.new_team.ids)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )

        self.assertEqual(new_team.member_ids, self.env["res.users"])
        new_team.write(
            {
                "team_member_ids": [
                    (0, 0, {"user_id": self.user_sales_leads.id}),
                    (0, 0, {"user_id": self.uid}),
                ]
            }
        )
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)
        self.assertEqual(sales_team_1.member_ids, self.user_admin)
        self.env.flush_all()

        memberships = (
            self.env["team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertEqual(memberships.team_id, sales_team_1 | new_team)
        self.assertFalse(
            memberships.filtered(lambda m: m.team_id == sales_team_1).active
        )
        self.assertTrue(memberships.filtered(lambda m: m.team_id == new_team).active)

        sales_team_1.write(
            {"team_member_ids": [(0, 0, {"user_id": self.user_sales_leads.id})]}
        )
        memberships_new = (
            self.env["team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertTrue(memberships < memberships_new)
        self.assertEqual(memberships.team_id, sales_team_1 | new_team)

        old_st_1 = memberships_new.filtered(
            lambda m: m.team_id == sales_team_1 and m in memberships
        )
        new_st_1 = memberships_new.filtered(
            lambda m: m.team_id == sales_team_1 and m not in memberships
        )
        new_nt = memberships_new.filtered(lambda m: m.team_id == new_team)
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
        sales_team_1 = self.env["team.team"].browse(self.sales_team_1.ids)
        new_team = self.env["team.team"].browse(self.new_team.ids)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )

        self.assertEqual(new_team.member_ids, self.env["res.users"])
        new_team.write(
            {
                "team_member_ids": [
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
            self.env["team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertEqual(memberships.team_id, sales_team_1 | new_team)
        self.assertTrue(
            memberships.filtered(lambda m: m.team_id == sales_team_1).active
        )
        self.assertTrue(memberships.filtered(lambda m: m.team_id == new_team).active)

        memberships.filtered(lambda m: m.team_id == sales_team_1).write(
            {"active": False}
        )
        sales_team_1.write(
            {"team_member_ids": [(0, 0, {"user_id": self.user_sales_leads.id})]}
        )
        memberships_new = (
            self.env["team.member"]
            .with_context(active_test=False)
            .search([("user_id", "=", self.user_sales_leads.id)])
        )
        self.assertTrue(memberships < memberships_new)
        self.assertEqual(memberships.team_id, sales_team_1 | new_team)

        old_st_1 = memberships_new.filtered(
            lambda m: m.team_id == sales_team_1 and m in memberships
        )
        new_st_1 = memberships_new.filtered(
            lambda m: m.team_id == sales_team_1 and m not in memberships
        )
        new_nt = memberships_new.filtered(lambda m: m.team_id == new_team)
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
        sales_team_1 = self.env["team.team"].browse(self.sales_team_1.ids)
        new_team = self.env["team.team"].browse(self.new_team.ids)
        self.assertEqual(
            sales_team_1.member_ids, self.user_sales_leads | self.user_admin
        )
        self.assertEqual(new_team.team_member_ids, self.env["team.member"])
        self.assertEqual(new_team.team_member_all_ids, self.env["team.member"])
        self.assertEqual(new_team.member_ids, self.env["res.users"])

        new_member = self.env["team.member"].create(
            {
                "user_id": self.env.user.id,
                "team_id": self.new_team.id,
            }
        )
        self.assertEqual(new_team.team_member_ids, new_member)
        self.assertEqual(new_team.team_member_all_ids, new_member)
        self.assertEqual(new_team.member_ids, self.env.user)

        new_team.write({"member_ids": [(4, self.user_sales_leads.id)]})
        added = self.env["team.member"].search(
            [
                ("team_id", "=", new_team.id),
                ("user_id", "=", self.user_sales_leads.id),
            ]
        )
        self.assertEqual(new_team.team_member_ids, new_member + added)
        self.assertEqual(new_team.team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        added.write({"active": False})
        self.assertEqual(new_team.team_member_ids, new_member)
        self.assertEqual(new_team.team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user)

        added.write({"active": True})
        self.assertEqual(new_team.team_member_ids, new_member + added)
        self.assertEqual(new_team.team_member_all_ids, new_member + added)
        self.assertEqual(new_team.member_ids, self.env.user | self.user_sales_leads)

        admin_original = self.env["team.member"].search(
            [
                ("team_id", "=", sales_team_1.id),
                ("user_id", "=", self.user_admin.id),
            ]
        )
        self.assertTrue(bool(admin_original))
        admin_archived = self.env["team.member"].create(
            {
                "team_id": new_team.id,
                "user_id": self.user_admin.id,
                "active": False,
            }
        )
        admin_original.write({"team_id": new_team.id})
        self.env.flush_all()
        self.assertTrue(self.user_admin in new_team.member_ids)
        self.assertTrue(admin_original.active)
        self.assertTrue(admin_archived.exists())
        self.assertFalse(admin_archived.active)

        with self.assertRaises(exceptions.ValidationError):
            added.write({"team_id": sales_team_1.id})

    def test_users_sale_team_id(self):
        self.assertTrue(self.sales_team_1.sequence < self.new_team.sequence)

        self.assertEqual(self.user_sales_leads.sale_team_ids, self.sales_team_1)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        self.new_team.write({"member_ids": [(4, self.user_sales_leads.id)]})
        self.assertEqual(
            self.user_sales_leads.sale_team_ids, self.sales_team_1 | self.new_team
        )
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        self.sales_team_1_m1.write({"active": False})
        self.assertEqual(self.user_sales_leads.sale_team_ids, self.new_team)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.new_team)

        self.sales_team_1_m1.write({"active": True})
        self.assertEqual(
            self.user_sales_leads.sale_team_ids, self.sales_team_1 | self.new_team
        )
        self.assertEqual(self.user_sales_leads.sale_team_id, self.sales_team_1)

        self.sales_team_1_m1.unlink()
        self.assertEqual(self.user_sales_leads.sale_team_ids, self.new_team)
        self.assertEqual(self.user_sales_leads.sale_team_id, self.new_team)


class TestMonoMembership(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )
        cls.team_a = cls.env["team.team"].create(
            {"use_sale": True, "name": "A", "company_id": False}
        )
        cls.team_b = cls.env["team.team"].create(
            {"use_sale": True, "name": "B", "company_id": False}
        )
        cls.salesperson = mail_new_test_user(
            cls.env,
            login="mono_user",
            name="Mono User",
            groups="sale.group_sale_salesman",
        )

    def _active_memberships(self):
        return self.env["team.member"].search(
            [("user_id", "=", self.salesperson.id), ("active", "=", True)]
        )

    def test_creating_archived_membership_keeps_the_active_one(self):
        live = self.env["team.member"].create(
            {"user_id": self.salesperson.id, "team_id": self.team_a.id}
        )
        self.env.flush_all()

        self.env["team.member"].create(
            {
                "user_id": self.salesperson.id,
                "team_id": self.team_b.id,
                "active": False,
            }
        )
        self.env.flush_all()

        self.assertTrue(
            live.active, "an archived membership must not archive the live one"
        )
        self.assertEqual(self._active_memberships(), live)
        self.assertEqual(self.salesperson.sale_team_id, self.team_a)

    def test_batch_unarchive_keeps_a_single_team(self):
        member_a = self.env["team.member"].create(
            {"user_id": self.salesperson.id, "team_id": self.team_a.id}
        )
        member_b = self.env["team.member"].create(
            {"user_id": self.salesperson.id, "team_id": self.team_b.id}
        )
        (member_a | member_b).action_archive()
        self.env.flush_all()

        (member_a | member_b).action_unarchive()
        self.env.flush_all()

        self.assertEqual(len(self._active_memberships()), 1)
        self.assertEqual(self._active_memberships(), member_b, "the last one wins")

    def test_batch_create_keeps_a_single_team(self):
        self.env["team.member"].create(
            [
                {"user_id": self.salesperson.id, "team_id": self.team_a.id},
                {"user_id": self.salesperson.id, "team_id": self.team_b.id},
            ]
        )
        self.env.flush_all()
        self.assertEqual(len(self._active_memberships()), 1)

    def test_same_team_duplicate_still_raises(self):
        self.env["team.member"].create(
            {"user_id": self.salesperson.id, "team_id": self.team_a.id}
        )
        self.env.flush_all()
        with self.assertRaises(exceptions.ValidationError):
            self.env["team.member"].create(
                {"user_id": self.salesperson.id, "team_id": self.team_a.id}
            )


class TestMonoMembershipReassignment(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )
        cls.team_a = cls.env["team.team"].create(
            {"use_sale": True, "name": "RA", "company_id": False}
        )
        cls.team_b = cls.env["team.team"].create(
            {"use_sale": True, "name": "RB", "company_id": False}
        )
        cls.alice = mail_new_test_user(
            cls.env, login="reass_alice", name="Alice", groups="base.group_user"
        )
        cls.bob = mail_new_test_user(
            cls.env, login="reass_bob", name="Bob", groups="base.group_user"
        )

    def _live_teams(self, user):
        return (
            self.env["team.member"]
            .search([("user_id", "=", user.id), ("active", "=", True)])
            .team_id
        )

    def test_reassigning_user_id_evicts_the_other_team(self):
        on_a = self.env["team.member"].create(
            {"team_id": self.team_a.id, "user_id": self.alice.id}
        )
        self.env["team.member"].create(
            {"team_id": self.team_b.id, "user_id": self.bob.id}
        )
        self.env.flush_all()

        on_a.write({"user_id": self.bob.id})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            self._live_teams(self.bob),
            self.team_a,
            "the membership just handed over wins",
        )
        self.assertEqual(self.bob.sale_team_ids, self.team_a)
        self.assertEqual(self.bob.sale_team_id, self.team_a)
        self.assertFalse(self._live_teams(self.alice))

    def test_multi_mode_keeps_both(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        self.env.invalidate_all()
        on_a = self.env["team.member"].create(
            {"team_id": self.team_a.id, "user_id": self.alice.id}
        )
        self.env["team.member"].create(
            {"team_id": self.team_b.id, "user_id": self.bob.id}
        )
        self.env.flush_all()

        on_a.write({"user_id": self.bob.id})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(self._live_teams(self.bob), self.team_a | self.team_b)


class TestMemberIdsDependencies(TestSalesCommon):
    def test_member_ids_follows_a_membership_reassignment(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        self.env.invalidate_all()
        team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Reassign",
                "company_id": False,
            }
        )
        first = mail_new_test_user(
            self.env, login="reassign_1", name="Reassign One", groups="base.group_user"
        )
        second = mail_new_test_user(
            self.env, login="reassign_2", name="Reassign Two", groups="base.group_user"
        )
        membership = self.env["team.member"].create(
            {"team_id": team.id, "user_id": first.id}
        )
        self.env.flush_all()
        self.assertEqual(team.member_ids, first)

        membership.write({"user_id": second.id})
        self.assertEqual(team.member_ids, second)


class TestMembershipCompanyChecks(TestSalesCommon):
    def test_unarchive_rechecks_company(self):
        company_2 = self.env["res.company"].create({"name": "Regression Co2"})
        team = self.env["team.team"].create(
            {"use_sale": True, "name": "Movable", "company_id": False}
        )
        membership = self.env["team.member"].create(
            {"user_id": self.user_sales_leads.id, "team_id": team.id}
        )
        membership.action_archive()
        self.env.flush_all()

        team.company_id = company_2.id
        self.env.flush_all()

        with self.assertRaises(exceptions.UserError):
            membership.action_unarchive()


class TestCompanyMembershipMessage(TestSalesCommon):
    def test_a_team_moving_company_names_every_member_left_behind(self):
        company_2 = self.env["res.company"].create({"name": "Message Co2"})
        self.sales_team_1.user_id = False
        with self.assertRaises(exceptions.ValidationError) as caught:
            self.sales_team_1.write({"company_id": company_2.id})
        message = str(caught.exception)
        self.assertIn(self.user_sales_leads.name, message)
        self.assertIn(self.user_admin.name, message)


class TestCompanyRevocation(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.company_2 = cls.env["res.company"].create({"name": "Revoked Co"})
        cls.salesperson = mail_new_test_user(
            cls.env,
            login="revoked_user",
            name="Revoked User",
            company_id=cls.company_main.id,
            company_ids=[(6, 0, [cls.company_main.id, cls.company_2.id])],
            groups="base.group_user",
        )
        cls.team_c2 = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Revoked Team",
                "company_id": cls.company_2.id,
            }
        )
        cls.team_shared = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Shared Team",
                "company_id": False,
            }
        )
        cls.member_c2 = cls.env["team.member"].create(
            {"team_id": cls.team_c2.id, "user_id": cls.salesperson.id}
        )
        cls.member_shared = cls.env["team.member"].create(
            {"team_id": cls.team_shared.id, "user_id": cls.salesperson.id}
        )
        cls.env.flush_all()

    def test_revoking_a_company_archives_its_memberships(self):
        self.salesperson.write({"company_ids": [(6, 0, [self.company_main.id])]})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertFalse(
            self.member_c2.active,
            "the membership on the revoked company's team is archived",
        )
        self.assertTrue(self.member_shared.active, "a company-less team is unaffected")
        self.assertEqual(self.salesperson.sale_team_ids, self.team_shared)
        self.assertEqual(self.salesperson.sale_team_id, self.team_shared)

    def test_the_surviving_state_passes_the_constraints(self):
        self.salesperson.write({"company_ids": [(6, 0, [self.company_main.id])]})
        self.env.flush_all()
        self.team_c2._constrains_company_members()
        self.env["team.member"].search(
            [("user_id", "=", self.salesperson.id)]
        )._constrains_company_membership()

    def test_granting_a_company_changes_nothing(self):
        extra = self.env["res.company"].create({"name": "Extra Co"})
        self.salesperson.write({"company_ids": [(4, extra.id)]})
        self.env.flush_all()
        self.assertTrue(self.member_c2.active, "granting a company evicts nobody")
        self.assertTrue(self.member_shared.active)

    def test_a_settings_admin_can_revoke(self):
        settings_admin = mail_new_test_user(
            self.env,
            login="rev_settings_admin",
            name="Rev Settings Admin",
            groups="base.group_user,base.group_system,base.group_partner_manager",
        )
        self.assertFalse(settings_admin.has_group("sale.group_sale_manager"))

        self.salesperson.with_user(settings_admin).write(
            {"company_ids": [(6, 0, [self.company_main.id])]}
        )
        self.env.flush_all()
        self.assertFalse(self.member_c2.active)
