from odoo import exceptions
from odoo.tests.common import users
from odoo.tools.safe_eval import safe_eval

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sales_team.tests.common import TestSalesCommon


def _salesperson_domain(env, team_id, record_id):
    return safe_eval(
        env["crm.team.member"]._fields["user_id"].domain,
        {
            "crm_team_id": team_id,
            "id": record_id,
            "user_company_ids": env["res.company"].search([]).ids,
        },
    )


class TestMembershipMultiParameter(TestSalesCommon):
    def test_parameter_string_false_is_false(self):
        ICP = self.env["ir.config_parameter"].sudo()
        for raw, expected in (
            ("False", False),
            ("0", False),
            ("off", False),
            ("True", True),
            ("1", True),
        ):
            ICP.search([("key", "=", "sales_team.membership_multi")]).unlink()
            ICP.create({"key": "sales_team.membership_multi", "value": raw})
            self.env.invalidate_all()
            self.assertEqual(
                self.env["crm.team"]._is_membership_multi(),
                expected,
                f"parameter {raw!r} should read as {expected}",
            )
            team = self.env["crm.team"].create(
                {"name": f"P {raw}", "company_id": False}
            )
            self.assertEqual(team.is_membership_multi, expected)

    def test_parameter_absent_defaults_to_mono(self):
        self.env["ir.config_parameter"].sudo().search(
            [("key", "=", "sales_team.membership_multi")]
        ).unlink()
        self.env.invalidate_all()
        self.assertFalse(self.env["crm.team"]._is_membership_multi())


class TestArchivedMembershipVisibility(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.other_team = cls.env["crm.team"].create(
            {"name": "Other", "company_id": False}
        )
        cls.other_membership = cls.env["crm.team.member"].create(
            {
                "user_id": cls.user_sales_leads.id,
                "crm_team_id": cls.other_team.id,
            }
        )

    def test_search_crm_team_ids_matches_compute(self):
        self.sales_team_1_m1.action_archive()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertNotIn(self.sales_team_1, self.user_sales_leads.crm_team_ids)
        matched = self.env["res.users"].search(
            [("crm_team_ids", "in", self.sales_team_1.ids)]
        )
        self.assertNotIn(self.user_sales_leads, matched)
        self.assertIn(self.other_team, self.user_sales_leads.crm_team_ids)
        self.assertIn(
            self.user_sales_leads,
            self.env["res.users"].search([("crm_team_ids", "in", self.other_team.ids)]),
        )

    def test_search_crm_team_ids_keeps_archived_users(self):
        self.user_sales_leads.with_context(active_test=False).write({"active": False})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertFalse(self.user_sales_leads.with_context(active_test=False).active)
        matched = (
            self.env["res.users"]
            .with_context(active_test=False)
            .search([("crm_team_ids", "=", False)])
        )
        self.assertIn(
            self.user_sales_leads,
            matched,
            "an archived user must stay searchable by team",
        )
        self.assertNotIn(
            self.user_sales_leads,
            self.env["res.users"].search([("crm_team_ids", "=", False)]),
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
            "sales_team.membership_multi", False
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


class TestMonoMembership(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )
        cls.team_a = cls.env["crm.team"].create({"name": "A", "company_id": False})
        cls.team_b = cls.env["crm.team"].create({"name": "B", "company_id": False})
        cls.salesperson = mail_new_test_user(
            cls.env,
            login="mono_user",
            name="Mono User",
            groups="sales_team.group_sale_salesman",
        )

    def _active_memberships(self):
        return self.env["crm.team.member"].search(
            [("user_id", "=", self.salesperson.id), ("active", "=", True)]
        )

    def test_creating_archived_membership_keeps_the_active_one(self):
        live = self.env["crm.team.member"].create(
            {"user_id": self.salesperson.id, "crm_team_id": self.team_a.id}
        )
        self.env.flush_all()

        self.env["crm.team.member"].create(
            {
                "user_id": self.salesperson.id,
                "crm_team_id": self.team_b.id,
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
        member_a = self.env["crm.team.member"].create(
            {"user_id": self.salesperson.id, "crm_team_id": self.team_a.id}
        )
        member_b = self.env["crm.team.member"].create(
            {"user_id": self.salesperson.id, "crm_team_id": self.team_b.id}
        )
        (member_a | member_b).action_archive()
        self.env.flush_all()

        (member_a | member_b).action_unarchive()
        self.env.flush_all()

        self.assertEqual(len(self._active_memberships()), 1)
        self.assertEqual(self._active_memberships(), member_b, "the last one wins")

    def test_batch_create_keeps_a_single_team(self):
        self.env["crm.team.member"].create(
            [
                {"user_id": self.salesperson.id, "crm_team_id": self.team_a.id},
                {"user_id": self.salesperson.id, "crm_team_id": self.team_b.id},
            ]
        )
        self.env.flush_all()
        self.assertEqual(len(self._active_memberships()), 1)

    def test_same_team_duplicate_still_raises(self):
        self.env["crm.team.member"].create(
            {"user_id": self.salesperson.id, "crm_team_id": self.team_a.id}
        )
        self.env.flush_all()
        with self.assertRaises(exceptions.ValidationError):
            self.env["crm.team.member"].create(
                {"user_id": self.salesperson.id, "crm_team_id": self.team_a.id}
            )


class TestMembershipCompanyChecks(TestSalesCommon):
    def test_unarchive_rechecks_company(self):
        company_2 = self.env["res.company"].create({"name": "Regression Co2"})
        team = self.env["crm.team"].create({"name": "Movable", "company_id": False})
        membership = self.env["crm.team.member"].create(
            {"user_id": self.user_sales_leads.id, "crm_team_id": team.id}
        )
        membership.action_archive()
        self.env.flush_all()

        team.company_id = company_2.id
        self.env.flush_all()

        with self.assertRaises(exceptions.UserError):
            membership.action_unarchive()


class TestMembershipMultiCompany(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_2 = cls.env["res.company"].create({"name": "Foreign Co"})
        cls.foreign_user = mail_new_test_user(
            cls.env,
            login="foreign_user",
            name="Foreign User",
            company_id=cls.company_2.id,
            company_ids=[(6, 0, [cls.company_2.id])],
            groups="base.group_user",
        )
        cls.foreign_team = cls.env["crm.team"].create(
            {"name": "Foreign Team", "company_id": cls.company_2.id}
        )
        cls.foreign_membership = cls.env["crm.team.member"].create(
            {"crm_team_id": cls.foreign_team.id, "user_id": cls.foreign_user.id}
        )
        cls.shared_team = cls.env["crm.team"].create(
            {"name": "Shared Team", "company_id": False}
        )
        cls.shared_membership = cls.env["crm.team.member"].create(
            {"crm_team_id": cls.shared_team.id, "user_id": cls.user_sales_leads.id}
        )

    def test_rule_exists(self):
        self.assertTrue(self.env.ref("sales_team.crm_team_member_comp_rule"))

    def test_foreign_membership_is_hidden(self):
        reader = self.user_sales_leads
        self.assertNotIn(self.company_2, reader.company_ids)
        with self.assertRaises(exceptions.AccessError):
            self.foreign_team.with_user(reader).read(["name"])
        with self.assertRaises(exceptions.AccessError):
            self.foreign_membership.with_user(reader).read(["name"])
        self.assertNotIn(
            self.foreign_membership,
            self.env["crm.team.member"].with_user(reader).search([]),
        )

    def test_company_less_and_own_memberships_stay_readable(self):
        reader = self.user_sales_leads
        self.assertTrue(self.shared_membership.with_user(reader).read(["name"]))
        self.assertIn(
            self.shared_membership,
            self.env["crm.team.member"].with_user(reader).search([]),
        )
        self.assertTrue(
            self.foreign_membership.with_user(self.foreign_user).read(["name"])
        )


class TestDefaultTeamProtection(TestSalesCommon):
    def test_default_teams_cannot_be_deleted(self):
        for xmlid in (
            "sales_team.team_sales_department",
            "sales_team.salesteam_website_sales",
            "sales_team.pos_sales_team",
        ):
            with self.assertRaises(exceptions.UserError), self.env.cr.savepoint():
                self.env.ref(xmlid).unlink()

    def test_unlink_survives_a_missing_default_xmlid(self):
        self.env["ir.model.data"].search(
            [("module", "=", "sales_team"), ("name", "=", "pos_sales_team")]
        ).unlink()
        self.env.flush_all()
        self.env.registry.clear_cache()

        disposable = self.env["crm.team"].create(
            {"name": "Disposable", "company_id": False}
        )
        self.env.flush_all()
        disposable.unlink()
        self.assertFalse(disposable.exists())


class TestUserArchiving(TestSalesCommon):
    def test_settings_admin_can_archive_a_salesperson(self):
        settings_admin = mail_new_test_user(
            self.env,
            login="settings_admin",
            name="Settings Admin",
            groups="base.group_user,base.group_system",
        )
        self.assertFalse(settings_admin.has_group("sales_team.group_sale_manager"))

        self.user_sales_leads.with_user(settings_admin).action_archive()
        self.env.flush_all()

        self.assertFalse(self.user_sales_leads.active)
        self.assertFalse(self.sales_team_1_m1.active, "the membership follows the user")


class TestCompanyRevocation(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
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
        cls.team_c2 = cls.env["crm.team"].create(
            {"name": "Revoked Team", "company_id": cls.company_2.id}
        )
        cls.team_shared = cls.env["crm.team"].create(
            {"name": "Shared Team", "company_id": False}
        )
        cls.member_c2 = cls.env["crm.team.member"].create(
            {"crm_team_id": cls.team_c2.id, "user_id": cls.salesperson.id}
        )
        cls.member_shared = cls.env["crm.team.member"].create(
            {"crm_team_id": cls.team_shared.id, "user_id": cls.salesperson.id}
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
        self.assertEqual(self.salesperson.crm_team_ids, self.team_shared)
        self.assertEqual(self.salesperson.sale_team_id, self.team_shared)

    def test_the_surviving_state_passes_the_constraints(self):
        self.salesperson.write({"company_ids": [(6, 0, [self.company_main.id])]})
        self.env.flush_all()
        self.team_c2._constrains_company_members()
        self.env["crm.team.member"].search(
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
        self.assertFalse(settings_admin.has_group("sales_team.group_sale_manager"))

        self.salesperson.with_user(settings_admin).write(
            {"company_ids": [(6, 0, [self.company_main.id])]}
        )
        self.env.flush_all()
        self.assertFalse(self.member_c2.active)


class TestFavorite(TestSalesCommon):
    def test_is_user_favorite_is_per_user(self):
        team = self.env["crm.team"].create({"name": "Favorite", "company_id": False})
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
        team = self.env["crm.team"].create({"name": "Favorite 2", "company_id": False})
        as_leads = team.with_user(self.user_sales_leads)
        self.assertFalse(as_leads.is_user_favorite)

        team.favorite_user_ids = [(4, self.user_sales_leads.id)]
        self.assertTrue(as_leads.is_user_favorite)

        team.favorite_user_ids = [(3, self.user_sales_leads.id)]
        self.assertFalse(as_leads.is_user_favorite)

    def test_adding_members_refreshes_the_flag(self):
        team = self.env["crm.team"].create(
            {
                "name": "Favorite 3",
                "company_id": False,
                "member_ids": [(4, self.user_sales_leads.id)],
            }
        )
        self.env.flush_all()
        self.assertTrue(team.with_user(self.user_sales_leads).is_user_favorite)

    def test_every_way_of_joining_a_team_grants_the_favorite(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        leads = self.user_sales_leads
        teams = {}

        teams["member_ids on create"] = self.env["crm.team"].create(
            {"name": "Join A", "company_id": False, "member_ids": [(4, leads.id)]}
        )

        teams["member_ids on write"] = team = self.env["crm.team"].create(
            {"name": "Join B", "company_id": False}
        )
        team.write({"member_ids": [(4, leads.id)]})

        teams["crm_team_member_ids on create"] = self.env["crm.team"].create(
            {
                "name": "Join C",
                "company_id": False,
                "crm_team_member_ids": [(0, 0, {"user_id": leads.id})],
            }
        )

        teams["crm_team_member_ids on write"] = team = self.env["crm.team"].create(
            {"name": "Join D", "company_id": False}
        )
        team.write({"crm_team_member_ids": [(0, 0, {"user_id": leads.id})]})

        teams["crm.team.member.create"] = team = self.env["crm.team"].create(
            {"name": "Join E", "company_id": False}
        )
        self.env["crm.team.member"].create(
            {"crm_team_id": team.id, "user_id": leads.id}
        )

        self.env.flush_all()
        for label, team in teams.items():
            self.assertIn(leads, team.member_ids, f"{label}: membership")
            self.assertIn(leads, team.favorite_user_ids, f"{label}: favorite")


class TestMultiMembershipActivation(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )

    def test_sales_administrator_can_activate(self):
        self.assertFalse(self.env["crm.team"]._is_membership_multi())
        self.env["crm.team"].with_user(
            self.user_sales_manager
        ).action_activate_multi_membership()
        self.env.invalidate_all()
        self.assertTrue(self.env["crm.team"]._is_membership_multi())

    def test_salesman_cannot_activate(self):
        salesman = self.user_sales_salesman
        self.assertFalse(salesman.has_group("sales_team.group_sale_manager"))
        with self.assertRaises(exceptions.AccessError):
            self.env["crm.team"].with_user(salesman).action_activate_multi_membership()
        self.env.invalidate_all()
        self.assertFalse(self.env["crm.team"]._is_membership_multi())

    def test_activation_does_not_require_settings_rights(self):
        manager = self.user_sales_manager
        self.assertFalse(manager.has_group("base.group_system"))
        with self.assertRaises(exceptions.AccessError), self.env.cr.savepoint():
            self.env["ir.config_parameter"].with_user(manager).set_param(
                "sales_team.membership_multi", True
            )
        self.env["crm.team"].with_user(manager).action_activate_multi_membership()
        self.env.invalidate_all()
        self.assertTrue(self.env["crm.team"]._is_membership_multi())


class TestMembershipQueries(TestSalesCommon):
    @users("user_sales_manager")
    def test_member_warning_is_batched(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sales_team.membership_multi", True)
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
            self.env["crm.team"]
            .sudo()
            .create([{"name": f"Batch {i}", "company_id": False} for i in range(20)])
        )
        self.env["crm.team.member"].sudo().create(
            [
                {"crm_team_id": team.id, "user_id": salesperson.id}
                for team in teams
                for salesperson in salespersons
            ]
        )
        self.env.flush_all()
        ICP.set_param("sales_team.membership_multi", False)
        self.env.invalidate_all()

        with self.assertQueryCount(user_sales_manager=10):
            teams.mapped("member_warning")


class TestSearchCrmTeamIds(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.team_a = cls.env["crm.team"].create({"name": "SA", "company_id": False})
        cls.team_b = cls.env["crm.team"].create({"name": "SB", "company_id": False})
        cls.user_ab = mail_new_test_user(
            cls.env, login="search_ab", name="Search AB", groups="base.group_user"
        )
        cls.user_none = mail_new_test_user(
            cls.env, login="search_none", name="Search None", groups="base.group_user"
        )
        cls.env["crm.team.member"].create(
            [
                {"user_id": cls.user_ab.id, "crm_team_id": cls.team_a.id},
                {"user_id": cls.user_ab.id, "crm_team_id": cls.team_b.id},
            ]
        )
        cls.env["crm.team.member"].create(
            {"user_id": cls.user_none.id, "crm_team_id": cls.team_a.id}
        ).action_archive()
        cls.env.flush_all()

    def _search(self, operator, value):
        return self.env["res.users"].search(
            [
                ("id", "in", (self.user_ab | self.user_none).ids),
                ("crm_team_ids", operator, value),
            ]
        )

    def test_negative_operators(self):
        for operator, value in (("not in", self.team_a.ids), ("!=", self.team_a.id)):
            found = self._search(operator, value)
            self.assertNotIn(
                self.user_ab, found, f"{operator}: a member of A must not match"
            )
            self.assertIn(
                self.user_none,
                found,
                f"{operator}: a user with no live team must match",
            )

    def test_positive_operators_are_unchanged(self):
        for operator, value in (("in", self.team_a.ids), ("=", self.team_a.id)):
            found = self._search(operator, value)
            self.assertIn(self.user_ab, found)
            self.assertNotIn(
                self.user_none,
                found,
                f"{operator}: an archived membership must not match",
            )

    def test_empty_relation(self):
        found = self._search("=", False)
        self.assertIn(
            self.user_none, found, "a user with no live team must be findable"
        )
        self.assertNotIn(self.user_ab, found)
        self.assertEqual(self._search("!=", False), self.user_ab)

    def test_matches_a_stored_many2many(self):
        cat_a, cat_b = self.env["res.partner.tag"].create(
            [{"name": "MA"}, {"name": "MB"}]
        )
        p_ab = self.env["res.partner"].create(
            {"name": "P AB", "tag_ids": [(6, 0, (cat_a | cat_b).ids)]}
        )
        p_none = self.env["res.partner"].create({"name": "P None"})
        pairs = {self.user_ab: p_ab, self.user_none: p_none}
        for operator, team_value, cat_value in (
            ("in", self.team_a.ids, cat_a.ids),
            ("not in", self.team_a.ids, cat_a.ids),
            ("=", self.team_a.id, cat_a.id),
            ("!=", self.team_a.id, cat_a.id),
            ("=", False, False),
            ("!=", False, False),
        ):
            reference = self.env["res.partner"].search(
                [
                    ("id", "in", (p_ab | p_none).ids),
                    ("tag_ids", operator, cat_value),
                ]
            )
            self.assertEqual(
                set(self._search(operator, team_value)),
                {user for user, partner in pairs.items() if partner in reference},
                f"crm_team_ids {operator} {team_value!r} disagrees with a stored m2m",
            )


class TestSearchMemberIds(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.team_a = cls.env["crm.team"].create({"name": "MA", "company_id": False})
        cls.team_b = cls.env["crm.team"].create({"name": "MB", "company_id": False})
        cls.team_empty = cls.env["crm.team"].create(
            {"name": "MEmpty", "company_id": False}
        )
        cls.member_a = mail_new_test_user(
            cls.env, login="mi_a", name="Mi A", groups="base.group_user"
        )
        cls.member_b = mail_new_test_user(
            cls.env, login="mi_b", name="Mi B", groups="base.group_user"
        )
        cls.env["crm.team.member"].create(
            [
                {"user_id": cls.member_a.id, "crm_team_id": cls.team_a.id},
                {"user_id": cls.member_b.id, "crm_team_id": cls.team_b.id},
            ]
        )
        cls.env["crm.team.member"].create(
            {"user_id": cls.member_b.id, "crm_team_id": cls.team_a.id}
        ).action_archive()
        cls.teams = cls.team_a | cls.team_b | cls.team_empty
        cls.env.flush_all()

    def _search(self, operator, value):
        return self.env["crm.team"].search(
            [("id", "in", self.teams.ids), ("member_ids", operator, value)]
        )

    def test_negative_operators(self):
        for operator, value in (
            ("not in", self.member_a.ids),
            ("!=", self.member_a.id),
        ):
            found = self._search(operator, value)
            self.assertNotIn(self.team_a, found, f"{operator}: A has that member")
            self.assertIn(self.team_b, found, f"{operator}: B has another member")
            self.assertIn(self.team_empty, found, f"{operator}: an empty team matches")

    def test_positive_operators_ignore_archived_memberships(self):
        for operator, value in (("in", self.member_b.ids), ("=", self.member_b.id)):
            found = self._search(operator, value)
            self.assertIn(self.team_b, found)
            self.assertNotIn(
                self.team_a, found, f"{operator}: a former member must not match"
            )

    def test_empty_relation(self):
        self.assertEqual(
            self._search("=", False),
            self.team_empty,
            "a team with no member must be findable",
        )
        self.assertEqual(self._search("!=", False), self.team_a | self.team_b)

    def test_mixed_false_and_ids(self):
        self.assertEqual(
            self._search("in", [False] + self.member_a.ids),
            self.team_a | self.team_empty,
            "a list mixing False with ids reads as 'empty OR one of these'",
        )

    def test_matches_a_stored_many2many(self):
        cat_a, cat_b = self.env["res.partner.tag"].create(
            [{"name": "TA"}, {"name": "TB"}]
        )
        p_a = self.env["res.partner"].create(
            {"name": "T PA", "tag_ids": [(6, 0, cat_a.ids)]}
        )
        p_b = self.env["res.partner"].create(
            {"name": "T PB", "tag_ids": [(6, 0, cat_b.ids)]}
        )
        p_empty = self.env["res.partner"].create({"name": "T PEmpty"})
        pairs = {self.team_a: p_a, self.team_b: p_b, self.team_empty: p_empty}
        partners = p_a | p_b | p_empty
        for operator, member_value, cat_value in (
            ("in", self.member_a.ids, cat_a.ids),
            ("not in", self.member_a.ids, cat_a.ids),
            ("=", self.member_a.id, cat_a.id),
            ("!=", self.member_a.id, cat_a.id),
            ("=", False, False),
            ("!=", False, False),
            ("in", [False] + self.member_a.ids, [False] + cat_a.ids),
        ):
            reference = self.env["res.partner"].search(
                [("id", "in", partners.ids), ("tag_ids", operator, cat_value)]
            )
            self.assertEqual(
                set(self._search(operator, member_value)),
                {team for team, partner in pairs.items() if partner in reference},
                f"member_ids {operator} {member_value!r} disagrees with a stored m2m",
            )


class TestSearchCrmTeamIdsMixedFalse(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.team = cls.env["crm.team"].create({"name": "MF", "company_id": False})
        cls.on_team = mail_new_test_user(
            cls.env, login="mf_on", name="MF On", groups="base.group_user"
        )
        cls.teamless = mail_new_test_user(
            cls.env, login="mf_off", name="MF Off", groups="base.group_user"
        )
        cls.env["crm.team.member"].create(
            {"user_id": cls.on_team.id, "crm_team_id": cls.team.id}
        )
        cls.env.flush_all()

    def test_mixed_false_and_ids(self):
        found = self.env["res.users"].search(
            [
                ("id", "in", (self.on_team | self.teamless).ids),
                ("crm_team_ids", "in", [False] + self.team.ids),
            ]
        )
        self.assertEqual(
            found,
            self.on_team | self.teamless,
            "'no team OR that team' must return both",
        )


class TestMonoMembershipReassignment(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )
        cls.team_a = cls.env["crm.team"].create({"name": "RA", "company_id": False})
        cls.team_b = cls.env["crm.team"].create({"name": "RB", "company_id": False})
        cls.alice = mail_new_test_user(
            cls.env, login="reass_alice", name="Alice", groups="base.group_user"
        )
        cls.bob = mail_new_test_user(
            cls.env, login="reass_bob", name="Bob", groups="base.group_user"
        )

    def _live_teams(self, user):
        return (
            self.env["crm.team.member"]
            .search([("user_id", "=", user.id), ("active", "=", True)])
            .crm_team_id
        )

    def test_reassigning_user_id_evicts_the_other_team(self):
        on_a = self.env["crm.team.member"].create(
            {"crm_team_id": self.team_a.id, "user_id": self.alice.id}
        )
        self.env["crm.team.member"].create(
            {"crm_team_id": self.team_b.id, "user_id": self.bob.id}
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
        self.assertEqual(self.bob.crm_team_ids, self.team_a)
        self.assertEqual(self.bob.sale_team_id, self.team_a)
        self.assertFalse(self._live_teams(self.alice))

    def test_multi_mode_keeps_both(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        self.env.invalidate_all()
        on_a = self.env["crm.team.member"].create(
            {"crm_team_id": self.team_a.id, "user_id": self.alice.id}
        )
        self.env["crm.team.member"].create(
            {"crm_team_id": self.team_b.id, "user_id": self.bob.id}
        )
        self.env.flush_all()

        on_a.write({"user_id": self.bob.id})
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(self._live_teams(self.bob), self.team_a | self.team_b)


class TestDefaultTeamFromContext(TestSalesCommon):
    def test_archived_context_team_is_not_proposed(self):
        live = self.env["crm.team"].create({"name": "Live", "company_id": False})
        dead = self.env["crm.team"].create({"name": "Dead", "company_id": False})
        dead.action_archive()
        self.env.flush_all()

        team = (
            self.env["crm.team"]
            .with_context(default_team_id=dead.id)
            ._get_default_team_id()
        )
        self.assertNotEqual(team, dead, "an archived team must not be proposed")
        self.assertTrue(not team or team.active)
        self.assertTrue(
            self.env["crm.team"]
            .with_context(default_team_id=live.id)
            ._get_default_team_id()
        )

    def test_deleted_context_team_is_not_proposed(self):
        dangling = self.env["crm.team"].create(
            {"name": "Dangling", "company_id": False}
        )
        dangling_id = dangling.id
        dangling.unlink()
        self.env.flush_all()

        team = (
            self.env["crm.team"]
            .with_context(default_team_id=dangling_id)
            ._get_default_team_id()
        )
        self.assertNotEqual(team.id, dangling_id)

    def test_foreign_company_context_team_is_not_proposed(self):
        salesman = self.user_sales_salesman
        other_company = self.env["res.company"].create({"name": "Ctx Other Co"})
        foreign = self.env["crm.team"].create(
            {"name": "Foreign", "company_id": other_company.id}
        )
        self.env.flush_all()

        team = (
            self.env["crm.team"]
            .with_user(salesman)
            .with_context(default_team_id=foreign.id)
            ._get_default_team_id()
        )
        self.assertNotEqual(
            team,
            foreign,
            "a team of a company the document cannot carry must not be proposed",
        )
        self.assertFalse(team.env.su, "and whatever comes back is not sudoed")

    def test_context_team_outside_the_allowed_companies_is_not_proposed(self):
        company_2 = self.env["res.company"].create({"name": "Ctx Allowed Co2"})
        self.user_sales_salesman.write({"company_ids": [(4, company_2.id)]})
        team_c2 = self.env["crm.team"].create(
            {"name": "Team Co2", "company_id": company_2.id}
        )
        self.env.flush_all()

        CrmTeam = self.env["crm.team"].with_user(self.user_sales_salesman)
        allowed_c2 = CrmTeam.with_context(
            default_team_id=team_c2.id, allowed_company_ids=[company_2.id]
        )._get_default_team_id()
        self.assertEqual(allowed_c2, team_c2)
        allowed_main = CrmTeam.with_context(
            default_team_id=team_c2.id, allowed_company_ids=[self.company_main.id]
        )._get_default_team_id()
        self.assertNotEqual(allowed_main, team_c2)

    def test_readable_context_team_still_wins(self):
        own = self.env["crm.team"].create(
            {
                "name": "Own",
                "company_id": False,
                "sequence": 99,
                "member_ids": [(4, self.user_sales_leads.id)],
            }
        )
        self.env.flush_all()
        team = (
            self.env["crm.team"]
            .with_user(self.user_sales_leads)
            .with_context(default_team_id=own.id)
            ._get_default_team_id()
        )
        self.assertEqual(team, own)
        self.assertFalse(team.env.su)


class TestMembershipVisibility(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.my_team = cls.env["crm.team"].create(
            {"name": "My Team", "company_id": False}
        )
        cls.led_team = cls.env["crm.team"].create(
            {"name": "Led Team", "company_id": False}
        )
        cls.foreign_team = cls.env["crm.team"].create(
            {"name": "Foreign", "company_id": False}
        )
        cls.salesman = mail_new_test_user(
            cls.env,
            login="vis_salesman",
            name="Vis Salesman",
            groups="sales_team.group_sale_salesman",
        )
        cls.teammate = mail_new_test_user(
            cls.env, login="vis_teammate", name="Vis Teammate", groups="base.group_user"
        )
        cls.stranger = mail_new_test_user(
            cls.env, login="vis_stranger", name="Vis Stranger", groups="base.group_user"
        )
        cls.led_team.user_id = cls.salesman.id
        cls.mine, cls.mates, cls.theirs = cls.env["crm.team.member"].create(
            [
                {"crm_team_id": cls.my_team.id, "user_id": cls.salesman.id},
                {"crm_team_id": cls.my_team.id, "user_id": cls.teammate.id},
                {"crm_team_id": cls.foreign_team.id, "user_id": cls.stranger.id},
            ]
        )
        cls.led = cls.env["crm.team.member"].create(
            {"crm_team_id": cls.led_team.id, "user_id": cls.teammate.id}
        )
        cls.env.flush_all()

    def test_foreign_membership_is_not_searchable(self):
        visible = self.env["crm.team.member"].with_user(self.salesman).search([])
        self.assertNotIn(
            self.theirs,
            visible,
            "the roster of an unreadable team must not be searchable",
        )
        self.assertIn(self.mine, visible)
        self.assertIn(
            self.mates, visible, "a teammate's row on my own team stays visible"
        )
        self.assertIn(self.led, visible, "so does the roster of a team I lead")

    PROFILES = {
        "plain internal": "base.group_user",
        "salesman own": "sales_team.group_sale_salesman",
        "salesman team": "sales_team.group_sale_salesman_team",
        "salesman all": "sales_team.group_sale_salesman_all_leads",
        "sales manager": "sales_team.group_sale_manager",
    }

    def _reader(self, label, group):
        cache = self.__dict__.setdefault("_reader_cache", {})
        if group not in cache:
            cache[group] = mail_new_test_user(
                self.env,
                login=f"vis_{group.rsplit('.', 1)[-1]}",
                name=label,
                groups=group,
            )
        return cache[group]

    def test_a_readable_team_never_implies_a_readable_roster(self):
        for label, group in self.PROFILES.items():
            reader = self._reader(label, group)
            visible = self.env["crm.team.member"].with_user(reader).search([])
            readable_teams = self.env["crm.team"].with_user(reader).search([])
            self.assertIn(
                self.foreign_team,
                readable_teams,
                f"{label}: a team's row must be readable so team_id can render",
            )
            if reader.has_group("sales_team.group_sale_salesman_all_leads"):
                continue
            self.assertNotIn(
                self.theirs,
                visible,
                f"{label}: a foreign roster must stay hidden",
            )

    def test_the_ladder_never_narrows_either_model(self):
        for model in ("crm.team", "crm.team.member"):
            counts = [
                len(self.env[model].with_user(self._reader(label, group)).search([]))
                for label, group in self.PROFILES.items()
            ]
            self.assertEqual(
                counts,
                sorted(counts),
                f"{model}: visibility is not monotone along "
                f"{list(self.PROFILES)}: {counts}",
            )

    def test_a_plain_internal_user_reads_no_foreign_roster(self):
        reader = self._reader("plain internal", "base.group_user")
        self.assertFalse(self.env["crm.team.member"].with_user(reader).search([]))
        self.assertIn(
            self.foreign_team,
            self.env["crm.team"].with_user(reader).search([]),
            "team names must stay readable outside the Sales app",
        )

    def test_own_memberships_stay_readable_without_a_sales_group(self):
        member = mail_new_test_user(
            self.env, login="vis_own", name="Vis Own", groups="base.group_user"
        )
        own_team = self.env["crm.team"].create({"name": "Own", "company_id": False})
        self.env["crm.team.member"].create(
            {"user_id": member.id, "crm_team_id": own_team.id}
        )
        readable = self.env["crm.team.member"].with_user(member).search([])
        self.assertEqual(readable.crm_team_id, own_team)

    def test_the_team_roster_still_renders(self):
        team = self.my_team.with_user(self.salesman)
        self.assertEqual(team.member_ids, self.salesman | self.teammate)
        self.assertEqual(team.crm_team_member_ids, self.mine | self.mates)

    def test_all_documents_and_managers_are_unaffected(self):
        for user in (
            self.user_sales_leads,
            self.user_sales_manager,
        ):
            visible = self.env["crm.team.member"].with_user(user).search([])
            self.assertIn(
                self.theirs, visible, f"{user.login} must still see everything"
            )

    def test_own_teams_still_resolve(self):
        as_self = self.salesman.with_user(self.salesman)
        self.assertEqual(as_self.crm_team_ids, self.my_team)
        self.assertEqual(as_self.sale_team_id, self.my_team)


class TestDefaultTeamFallbackQueries(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["crm.team"].search([]).write({"sequence": 50})
        cls.wanted = cls.env["crm.team"].create(
            {"name": "Wanted", "company_id": False, "sequence": 1, "user_id": False}
        )
        cls.filler = cls.env["crm.team"].create(
            [
                {
                    "name": f"Filler {i}",
                    "company_id": False,
                    "sequence": 10,
                    "user_id": False,
                }
                for i in range(30)
            ]
        )
        cls.loner = mail_new_test_user(
            cls.env,
            login="fallback_loner",
            name="Fallback Loner",
            groups="sales_team.group_sale_salesman_all_leads",
        )
        cls.env.flush_all()

    def test_domain_fallback_picks_the_same_team_as_filtered_domain(self):
        domain = [("name", "=", "Wanted")]
        team = (
            self.env["crm.team"]
            .with_user(self.loner)
            ._get_default_team_id(domain=domain)
        )
        reference = self.env["crm.team"].with_user(self.loner).search([])
        self.assertEqual(team, reference.filtered_domain(domain)[:1])
        self.assertEqual(team, self.wanted)

    def test_domain_fallback_falls_back_to_the_first_team(self):
        domain = [("name", "=", "No Such Team")]
        team = (
            self.env["crm.team"]
            .with_user(self.loner)
            ._get_default_team_id(domain=domain)
        )
        reference = self.env["crm.team"].with_user(self.loner).search([])
        self.assertEqual(team, reference[:1])
        self.assertEqual(team, self.wanted, "sequence 1 ranks first")

    def _rows_fetched_by_fallback(self):
        rows = [0]
        cursor_cls = type(self.env.cr)
        original = cursor_cls.execute

        def counting(cr, query, params=None, **kwargs):
            result = original(cr, query, params, **kwargs)
            rows[0] += max(cr.rowcount, 0)
            return result

        cursor_cls.execute = counting
        try:
            self.env["crm.team"].with_user(self.loner)._get_default_team_id(
                domain=[("name", "=", "Wanted")]
            )
        finally:
            cursor_cls.execute = original
        return rows[0]

    def test_fallback_does_not_scale_with_the_table(self):
        self._rows_fetched_by_fallback()
        small = self._rows_fetched_by_fallback()
        self.env["crm.team"].create(
            [
                {
                    "name": f"Bulk {i}",
                    "company_id": False,
                    "sequence": 10,
                    "user_id": False,
                }
                for i in range(120)
            ]
        )
        self.env.flush_all()
        large = self._rows_fetched_by_fallback()
        self.assertEqual(
            small,
            large,
            f"{small} rows fetched with 31 teams but {large} with 151: the "
            "fallback still scales with the table",
        )


class TestArchivedTeamMembership(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.team = cls.env["crm.team"].create({"name": "Doomed", "company_id": False})
        cls.member = cls.env["crm.team.member"].create(
            {"crm_team_id": cls.team.id, "user_id": cls.user_sales_leads.id}
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
            self.env["crm.team.member"].create(
                {"crm_team_id": self.team.id, "user_id": other.id}
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
            self.env["crm.team.member"].create(
                {"crm_team_id": self.team.id, "user_id": ghost.id}
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
            self.team.crm_team_member_ids.user_id.ids,
            "the many2many and the one2many must report the same people",
        )
        self.assertNotIn(
            self.team,
            self.env["crm.team"].search(
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
            groups="sales_team.group_sale_manager",
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
            "sales_team.membership_multi", True
        )
        cls.foreign_team = cls.env["crm.team"].create(
            {"name": "FOREIGN TEAM", "company_id": cls.company_2.id}
        )
        cls.local_team = cls.env["crm.team"].create(
            {"name": "Local Team", "company_id": cls.company_main.id}
        )
        cls.env["crm.team.member"].create(
            [
                {"crm_team_id": cls.foreign_team.id, "user_id": cls.shared_user.id},
                {"crm_team_id": cls.local_team.id, "user_id": cls.shared_user.id},
            ]
        )
        cls.env.flush_all()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )

    def test_team_warning_hides_the_foreign_team(self):
        self.env.invalidate_all()
        warning = self.local_team.with_user(self.local_manager).member_warning
        self.assertNotIn("FOREIGN TEAM", warning or "")

    def test_membership_warning_hides_the_foreign_team(self):
        self.env.invalidate_all()
        membership = self.env["crm.team.member"].search(
            [
                ("crm_team_id", "=", self.local_team.id),
                ("user_id", "=", self.shared_user.id),
            ]
        )
        self.assertNotIn(
            "FOREIGN TEAM",
            membership.with_user(self.local_manager).member_warning or "",
        )

    def test_a_visible_team_is_still_reported(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        self.env.invalidate_all()
        third = self.env["crm.team"].create(
            {"name": "Third Local", "company_id": self.company_main.id}
        )
        self.env["crm.team.member"].create(
            {"crm_team_id": third.id, "user_id": self.shared_user.id}
        )
        self.env.flush_all()
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )
        self.env.invalidate_all()
        warning = self.local_team.with_user(self.local_manager).member_warning
        self.assertIn("Third Local", warning or "")


class TestMemberIdsDependencies(TestSalesCommon):
    def test_member_ids_follows_a_membership_reassignment(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        self.env.invalidate_all()
        team = self.env["crm.team"].create({"name": "Reassign", "company_id": False})
        first = mail_new_test_user(
            self.env, login="reassign_1", name="Reassign One", groups="base.group_user"
        )
        second = mail_new_test_user(
            self.env, login="reassign_2", name="Reassign Two", groups="base.group_user"
        )
        membership = self.env["crm.team.member"].create(
            {"crm_team_id": team.id, "user_id": first.id}
        )
        self.env.flush_all()
        self.assertEqual(team.member_ids, first)

        membership.write({"user_id": second.id})
        self.assertEqual(team.member_ids, second)


class TestSalespersonDomain(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.team_a = cls.env["crm.team"].create({"name": "DA", "company_id": False})
        cls.team_b = cls.env["crm.team"].create({"name": "DB", "company_id": False})
        cls.in_a = mail_new_test_user(
            cls.env, login="dom_in_a", name="Dom In A", groups="base.group_user"
        )
        cls.in_b = mail_new_test_user(
            cls.env, login="dom_in_b", name="Dom In B", groups="base.group_user"
        )
        cls.free = mail_new_test_user(
            cls.env, login="dom_free", name="Dom Free", groups="base.group_user"
        )
        cls.former = mail_new_test_user(
            cls.env, login="dom_former", name="Dom Former", groups="base.group_user"
        )
        cls.env["crm.team.member"].create(
            [
                {"user_id": cls.in_a.id, "crm_team_id": cls.team_a.id},
                {"user_id": cls.in_b.id, "crm_team_id": cls.team_b.id},
            ]
        )
        cls.env["crm.team.member"].create(
            {"user_id": cls.former.id, "crm_team_id": cls.team_a.id}
        ).action_archive()
        cls.env.flush_all()

    def _selectable(self, team_id):
        return self.env["res.users"].search(
            [
                ("id", "in", (self.in_a | self.in_b | self.free | self.former).ids),
                *_salesperson_domain(self.env, team_id, False),
            ]
        )

    def test_excludes_only_live_members_of_the_target_team(self):
        selectable = self._selectable(self.team_a.id)
        self.assertNotIn(self.in_a, selectable)
        self.assertIn(
            self.in_b, selectable, "a member of another team stays selectable"
        )
        self.assertIn(self.free, selectable)
        self.assertIn(
            self.former, selectable, "an archived membership does not exclude"
        )

    def test_blank_team_excludes_nobody(self):
        selectable = self._selectable(False)
        for user in (self.in_a, self.in_b, self.free, self.former):
            self.assertIn(user, selectable)

    def test_is_the_same_in_both_membership_modes(self):
        multi = self._selectable(self.team_a.id)
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )
        self.env.invalidate_all()
        self.assertEqual(self._selectable(self.team_a.id), multi)

    def test_mono_mode_transfer_goes_through(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )
        self.env.invalidate_all()
        self.assertIn(
            self.in_a,
            self._selectable(self.team_b.id),
            "mono mode must offer a salesperson from another team",
        )

        moved = self.env["crm.team.member"].create(
            {"crm_team_id": self.team_b.id, "user_id": self.in_a.id}
        )
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertTrue(moved.active)
        self.assertEqual(
            self.in_a.crm_team_ids,
            self.team_b,
            "the salesperson ends on exactly one team",
        )
        self.assertEqual(self.in_a.sale_team_id, self.team_b)

    def test_agrees_with_the_constraint_it_anticipates(self):
        for user in self._selectable(self.team_a.id):
            with self.env.cr.savepoint():
                self.env["crm.team.member"].create(
                    {"crm_team_id": self.team_a.id, "user_id": user.id}
                )
                self.env.flush_all()
        with self.assertRaises(exceptions.ValidationError), self.env.cr.savepoint():
            self.env["crm.team.member"].create(
                {"crm_team_id": self.team_a.id, "user_id": self.in_a.id}
            )
            self.env.flush_all()


class TestMembershipMultiIsInvalidatedEverywhere(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", False
        )

    def _cached_copies(self):
        return {
            name
            for name, model in self.env.registry.items()
            if (field := model._fields.get("is_membership_multi"))
            and field.compute
            and not field.store
        }

    def test_only_crm_team_caches_the_setting(self):
        self.assertEqual(self._cached_copies(), {"crm.team"})

    def test_every_cached_copy_follows_the_parameter(self):
        ICP = self.env["ir.config_parameter"].sudo()
        for expected, value in ((True, True), (False, False)):
            with self.subTest(value=value):
                ICP.set_param("sales_team.membership_multi", value)
                self.assertEqual(self.env["crm.team"]._is_membership_multi(), expected)
                for name in self._cached_copies():
                    record = self.env[name].search([], limit=1)
                    if record:
                        self.assertEqual(record.is_membership_multi, expected)

    def test_unsetting_the_parameter_also_invalidates(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sales_team.membership_multi", True)
        self.assertTrue(self.sales_team_1.is_membership_multi)

        ICP.search([("key", "=", "sales_team.membership_multi")]).unlink()
        self.assertFalse(self.sales_team_1.is_membership_multi)


class TestMonoModeIsNotRetroactive(TestSalesCommon):
    def test_flipping_to_mono_leaves_the_extra_memberships_live(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sales_team.membership_multi", True)
        second = self.env["crm.team"].create(
            {"name": "Mono Second", "company_id": False}
        )
        self.env["crm.team.member"].create(
            {"crm_team_id": second.id, "user_id": self.user_sales_leads.id}
        )
        self.assertEqual(len(self.user_sales_leads.crm_team_ids), 2)

        ICP.set_param("sales_team.membership_multi", False)
        self.assertEqual(
            len(self.user_sales_leads.crm_team_ids),
            2,
            "mono mode constrains writes, it does not rewrite history",
        )

    def test_the_state_is_surfaced_rather_than_silently_kept(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sales_team.membership_multi", True)
        second = self.env["crm.team"].create(
            {"name": "Mono Second", "company_id": False}
        )
        self.env["crm.team.member"].create(
            {"crm_team_id": second.id, "user_id": self.user_sales_leads.id}
        )
        ICP.set_param("sales_team.membership_multi", False)

        self.assertIn("Mono Second", self.sales_team_1.member_warning or "")


class TestDefaultTeamIsNotCallerDependent(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.env["crm.team"].search([]).write({"sequence": 9000})
        cls.filer = mail_new_test_user(
            cls.env,
            login="dep_filer",
            name="Dep Filer",
            groups="sales_team.group_sale_salesman_team",
        )
        cls.owner = mail_new_test_user(
            cls.env,
            login="dep_owner",
            name="Dep Owner",
            groups="sales_team.group_sale_salesman_team",
        )
        cls.owner_team = cls.env["crm.team"].create(
            {"name": "Owner Team", "sequence": 10, "company_id": False}
        )
        cls.shared_team = cls.env["crm.team"].create(
            {"name": "Shared Team", "sequence": 20, "company_id": False}
        )
        cls.env["crm.team.member"].create(
            [
                {"crm_team_id": cls.owner_team.id, "user_id": cls.owner.id},
                {"crm_team_id": cls.shared_team.id, "user_id": cls.owner.id},
                {"crm_team_id": cls.shared_team.id, "user_id": cls.filer.id},
            ]
        )
        cls.env.flush_all()

    def test_every_caller_gets_the_same_team(self):
        CrmTeam = self.env["crm.team"]
        for actor in (self.env.user, self.filer, self.owner):
            self.assertEqual(
                CrmTeam.with_user(actor)._get_default_team_id(user_id=self.owner.id),
                self.owner_team,
                f"{actor.login} got a different default team for the same salesperson",
            )

    def test_the_answer_is_not_sudoed(self):
        team = (
            self.env["crm.team"]
            .with_user(self.filer)
            ._get_default_team_id(user_id=self.owner.id)
        )
        self.assertFalse(team.env.su)

    def test_the_company_fallback_is_caller_independent_too(self):
        loner = mail_new_test_user(
            self.env,
            login="dep_loner",
            name="Dep Loner",
            groups="sales_team.group_sale_salesman",
        )
        self.env.flush_all()
        CrmTeam = self.env["crm.team"]
        answers = {
            CrmTeam.with_user(actor)._get_default_team_id(user_id=loner.id)
            for actor in (self.env.user, self.filer, self.owner)
        }
        self.assertEqual(len(answers), 1, f"the fallback differed by caller: {answers}")
        self.assertEqual(answers.pop(), self.owner_team)

    def test_a_document_opens_for_the_person_who_filed_it(self):
        team = (
            self.env["crm.team"]
            .with_user(self.filer)
            ._get_default_team_id(user_id=self.owner.id)
        )
        self.assertEqual(team, self.owner_team)
        self.env.invalidate_all()
        self.assertEqual(
            team.with_user(self.filer).display_name,
            "Owner Team",
            "the filer cannot open a document carrying the team they just "
            "filed it under",
        )


class TestSalespersonDomainSelfExclusion(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env["crm.team"].create({"name": "Excl", "company_id": False})
        cls.member_user = mail_new_test_user(
            cls.env,
            login="excl_user",
            name="Excl User",
            groups="sales_team.group_sale_salesman",
        )
        cls.membership = cls.env["crm.team.member"].create(
            {"crm_team_id": cls.team.id, "user_id": cls.member_user.id}
        )
        cls.env.flush_all()

    def _offered(self, record_id):
        return self.env["res.users"].search(
            _salesperson_domain(self.env, self.team.id, record_id)
        )

    def test_the_saved_record_offers_its_own_salesperson(self):
        self.assertIn(self.member_user, self._offered(self.membership.id))

    def test_a_new_record_still_excludes_existing_members(self):
        self.assertNotIn(self.member_user, self._offered(False))

    def test_another_membership_still_excludes_them(self):
        other = self.env["crm.team.member"].create(
            {
                "crm_team_id": self.env["crm.team"]
                .create({"name": "Excl2", "company_id": False})
                .id,
                "user_id": mail_new_test_user(
                    self.env, login="excl_other", name="Excl Other"
                ).id,
            }
        )
        self.assertNotIn(self.member_user, self._offered(other.id))


class TestDefaultTeamIgnoresArchived(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leader = mail_new_test_user(
            cls.env,
            login="arch_leader",
            name="Arch Leader",
            groups="sales_team.group_sale_salesman",
        )
        cls.env["crm.team"].search([]).write({"active": False})
        cls.dead_team = cls.env["crm.team"].create(
            {"name": "Dead", "company_id": False, "user_id": cls.leader.id}
        )
        cls.dead_team.action_archive()
        cls.env.flush_all()

    def test_no_live_team_means_no_default(self):
        team = self.env["crm.team"].with_user(self.leader)._get_default_team_id()
        self.assertFalse(team)

    def test_archived_team_is_not_proposed_under_active_test_false(self):
        team = (
            self.env["crm.team"]
            .with_user(self.leader)
            .with_context(active_test=False)
            ._get_default_team_id()
        )
        self.assertFalse(team, "an archived team is never a default for a new document")

    def test_the_company_fallback_is_archive_blind_too(self):
        stranger = mail_new_test_user(
            self.env,
            login="arch_stranger",
            name="Arch Stranger",
            groups="sales_team.group_sale_salesman_all_leads",
        )
        for domain in (False, [("name", "=", "Dead")]):
            with self.subTest(domain=domain):
                team = (
                    self.env["crm.team"]
                    .with_user(stranger)
                    .with_context(active_test=False)
                    ._get_default_team_id(domain=domain)
                )
                self.assertFalse(team)

    def test_a_live_team_is_still_found(self):
        live = self.env["crm.team"].create(
            {"name": "Alive", "company_id": False, "user_id": self.leader.id}
        )
        for context in ({}, {"active_test": False}):
            with self.subTest(context=context):
                self.assertEqual(
                    self.env["crm.team"]
                    .with_user(self.leader)
                    .with_context(**context)
                    ._get_default_team_id(),
                    live,
                )


class TestWarningFollowsTheParameter(TestSalesCommon):
    def test_a_computed_warning_is_recomputed_when_mono_mode_returns(self):
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("sales_team.membership_multi", True)
        second = self.env["crm.team"].create(
            {"name": "Flip Second", "company_id": False}
        )
        membership = self.env["crm.team.member"].create(
            {"crm_team_id": second.id, "user_id": self.user_sales_leads.id}
        )
        self.assertFalse(self.sales_team_1.member_warning)
        self.assertFalse(membership.member_warning)

        ICP.set_param("sales_team.membership_multi", False)
        self.assertIn("Flip Second", self.sales_team_1.member_warning or "")
        self.assertIn(self.sales_team_1.name, membership.member_warning or "")

        ICP.set_param("sales_team.membership_multi", True)
        self.assertFalse(self.sales_team_1.member_warning)
        self.assertFalse(membership.member_warning)


class TestRosterVisibilityFollowsMembership(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.salesman = mail_new_test_user(
            cls.env,
            login="roster_salesman",
            name="Roster Salesman",
            groups="sales_team.group_sale_salesman",
        )
        cls.stranger = mail_new_test_user(
            cls.env, login="roster_stranger", name="Roster Stranger"
        )
        cls.team = cls.env["crm.team"].create({"name": "Roster", "company_id": False})
        cls.roster = cls.env["crm.team.member"].create(
            {"crm_team_id": cls.team.id, "user_id": cls.stranger.id}
        )
        cls.env.flush_all()

    def _sees_roster(self):
        self.env.flush_all()
        readable = self.env["crm.team.member"].with_user(self.salesman).search([])
        return self.roster in readable

    def test_joining_and_leaving_a_team_is_seen_at_once(self):
        self.assertFalse(self._sees_roster())

        membership = self.env["crm.team.member"].create(
            {"crm_team_id": self.team.id, "user_id": self.salesman.id}
        )
        self.assertTrue(self._sees_roster(), "a new member reads the roster")

        membership.action_archive()
        self.assertFalse(self._sees_roster(), "a former member no longer does")

        membership.action_unarchive()
        self.assertTrue(self._sees_roster())

        membership.unlink()
        self.assertFalse(self._sees_roster())

    def test_moving_a_membership_is_seen_at_once(self):
        elsewhere = self.env["crm.team"].create(
            {"name": "Elsewhere", "company_id": False}
        )
        membership = self.env["crm.team.member"].create(
            {"crm_team_id": elsewhere.id, "user_id": self.salesman.id}
        )
        self.assertFalse(self._sees_roster())

        membership.write({"crm_team_id": self.team.id})
        self.assertTrue(self._sees_roster())

    def test_archiving_the_team_is_seen_at_once(self):
        self.env["crm.team.member"].create(
            {"crm_team_id": self.team.id, "user_id": self.salesman.id}
        )
        self.assertTrue(self._sees_roster())

        self.team.action_archive()
        self.assertFalse(self._sees_roster())


class TestFavoriteOnEveryJoin(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sales_team.membership_multi", True
        )
        cls.first = mail_new_test_user(cls.env, login="fav_first", name="Fav First")
        cls.second = mail_new_test_user(cls.env, login="fav_second", name="Fav Second")

    def test_handing_a_membership_over_favorites_the_new_salesperson(self):
        team = self.env["crm.team"].create({"name": "Handover", "company_id": False})
        membership = self.env["crm.team.member"].create(
            {"crm_team_id": team.id, "user_id": self.first.id}
        )
        membership.write({"user_id": self.second.id})
        self.assertIn(self.second, team.favorite_user_ids)

    def test_moving_a_membership_favorites_the_new_team(self):
        team, target = self.env["crm.team"].create(
            [
                {"name": "Move From", "company_id": False},
                {"name": "Move To", "company_id": False},
            ]
        )
        membership = self.env["crm.team.member"].create(
            {"crm_team_id": team.id, "user_id": self.first.id}
        )
        membership.write({"crm_team_id": target.id})
        self.assertIn(self.first, target.favorite_user_ids)

    def test_rejoining_favorites_again(self):
        team = self.env["crm.team"].create({"name": "Rejoin", "company_id": False})
        membership = self.env["crm.team.member"].create(
            {"crm_team_id": team.id, "user_id": self.first.id}
        )
        membership.action_archive()
        team.favorite_user_ids = [(3, self.first.id)]
        membership.action_unarchive()
        self.assertIn(self.first, team.favorite_user_ids)

    def test_an_archived_membership_does_not_favorite(self):
        team = self.env["crm.team"].create({"name": "Archived", "company_id": False})
        self.env["crm.team.member"].create(
            {"crm_team_id": team.id, "user_id": self.first.id, "active": False}
        )
        self.assertNotIn(self.first, team.favorite_user_ids)


class TestArchiveCascadeOnFalsyValues(TestSalesCommon):
    def test_a_falsy_active_archives_the_team_memberships(self):
        self.sales_team_1.write({"active": 0})
        self.assertFalse(self.sales_team_1_m1.active)
        self.assertFalse(self.sales_team_1_m2.active)

    def test_a_falsy_active_archives_the_user_memberships(self):
        self.user_sales_leads.write({"active": 0})
        self.assertFalse(self.sales_team_1_m1.active)


class TestTeamWriteGrantsOutsideSales(TestSalesCommon):
    def test_a_sales_group_never_takes_a_team_write_grant_away(self):
        writers = self.env["res.groups"].create({"name": "Team writers"})
        self.env["ir.model.access"].create(
            {
                "name": "team writers",
                "model_id": self.env.ref("sales_team.model_crm_team").id,
                "group_id": writers.id,
                "perm_read": True,
                "perm_write": True,
            }
        )
        writer = mail_new_test_user(self.env, login="team_writer", name="Team Writer")
        writer.group_ids = [(4, writers.id)]
        team = self.env["crm.team"].create({"name": "Writable", "company_id": False})

        team.with_user(writer).write({"name": "Written without Sales"})
        writer.group_ids = [(4, self.env.ref("sales_team.group_sale_salesman").id)]
        team.with_user(writer).write({"name": "Written with Sales"})
        self.assertEqual(team.name, "Written with Sales")


class TestCompanyMembershipMessage(TestSalesCommon):
    def test_a_team_moving_company_names_every_member_left_behind(self):
        company_2 = self.env["res.company"].create({"name": "Message Co2"})
        self.sales_team_1.user_id = False
        with self.assertRaises(exceptions.ValidationError) as caught:
            self.sales_team_1.write({"company_id": company_2.id})
        message = str(caught.exception)
        self.assertIn(self.user_sales_leads.name, message)
        self.assertIn(self.user_admin.name, message)
