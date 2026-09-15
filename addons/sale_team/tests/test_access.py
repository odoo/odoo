from odoo import exceptions
from odoo.tests import tagged, users

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_team.tests.common import (
    SalesTeamCommon,
    TestSalesCommon,
    TestSalesMC,
)


@tagged("post_install", "-at_install")
class TestAccessRights(SalesTeamCommon):
    @users("salesmanager")
    def test_access_sales_manager(self):
        india_channel = (
            self.env["team.team"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "use_sale": True,
                    "name": "India",
                }
            )
        )
        self.assertIn(
            india_channel.id,
            self.env["team.team"].search([]).ids,
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
            self.env["team.team"].search([]).ids,
            "Sales manager should be able to delete a Sales Team",
        )


class TestSecurity(TestSalesMC):
    @users("user_sales_leads")
    def test_team_access(self):
        sales_team = self.sales_team_1.with_user(self.env.user)

        sales_team.read(["name"])
        for member in sales_team.member_ids:
            member.read(["name"])

        with self.assertRaises(exceptions.AccessError):
            sales_team.write({"name": "Trolling"})

        for membership in sales_team.team_member_ids:
            membership.read(["name"])
            with self.assertRaises(exceptions.AccessError):
                membership.write({"active": False})

        with self.assertRaises(exceptions.AccessError):
            sales_team.write({"member_ids": [(5, 0)]})

    @users("user_sales_leads")
    def test_team_multi_company(self):
        self.sales_team_1.with_user(self.env.user).read(["name"])
        with self.assertRaises(exceptions.AccessError):
            self.team_c2.with_user(self.env.user).read(["name"])


class TestMultiCompany(TestSalesMC):
    @users("user_sales_manager")
    def test_team_members(self):
        team_c2 = self.env["team.team"].browse(self.team_c2.id)
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
        team_c2 = self.env["team.team"].browse(self.team_c2.id)
        team_c2.write({"name": "Manager Update"})
        self.assertEqual(team_c2.member_ids, self.env["res.users"])

        self.env.user.write({"company_id": self.company_2.id})
        team_c2.write({"team_member_ids": [(0, 0, {"user_id": self.env.user.id})]})
        self.assertEqual(team_c2.member_ids, self.env.user)

        with self.assertRaises(exceptions.UserError):
            team_c2.write(
                {"team_member_ids": [(0, 0, {"user_id": self.user_sales_salesman.id})]}
            )

        team_c2.write({"member_ids": [(5, 0)], "company_id": self.company_main.id})
        self.assertEqual(team_c2.member_ids, self.env["res.users"])
        team_c2.write(
            {"team_member_ids": [(0, 0, {"user_id": self.user_sales_salesman.id})]}
        )
        self.assertEqual(team_c2.member_ids, self.user_sales_salesman)

        with self.assertRaises(exceptions.UserError):
            team_c2.write({"company_id": self.company_2.id})


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
        cls.foreign_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Foreign Team",
                "company_id": cls.company_2.id,
            }
        )
        cls.foreign_membership = cls.env["team.member"].create(
            {"team_id": cls.foreign_team.id, "user_id": cls.foreign_user.id}
        )
        cls.shared_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Shared Team",
                "company_id": False,
            }
        )
        cls.shared_membership = cls.env["team.member"].create(
            {"team_id": cls.shared_team.id, "user_id": cls.user_sales_leads.id}
        )

    def test_rule_exists(self):
        self.assertTrue(self.env.ref("team.team_member_comp_rule"))

    def test_foreign_membership_is_hidden(self):
        reader = self.user_sales_leads
        self.assertNotIn(self.company_2, reader.company_ids)
        with self.assertRaises(exceptions.AccessError):
            self.foreign_team.with_user(reader).read(["name"])
        with self.assertRaises(exceptions.AccessError):
            self.foreign_membership.with_user(reader).read(["name"])
        self.assertNotIn(
            self.foreign_membership,
            self.env["team.member"].with_user(reader).search([]),
        )

    def test_company_less_and_own_memberships_stay_readable(self):
        reader = self.user_sales_leads
        self.assertTrue(self.shared_membership.with_user(reader).read(["name"]))
        self.assertIn(
            self.shared_membership,
            self.env["team.member"].with_user(reader).search([]),
        )
        self.assertTrue(
            self.foreign_membership.with_user(self.foreign_user).read(["name"])
        )


class TestMembershipVisibility(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.my_team = cls.env["team.team"].create(
            {"use_sale": True, "name": "My Team", "company_id": False}
        )
        cls.led_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Led Team",
                "company_id": False,
            }
        )
        cls.foreign_team = cls.env["team.team"].create(
            {"use_sale": True, "name": "Foreign", "company_id": False}
        )
        cls.salesman = mail_new_test_user(
            cls.env,
            login="vis_salesman",
            name="Vis Salesman",
            groups="sale.group_sale_salesman",
        )
        cls.teammate = mail_new_test_user(
            cls.env, login="vis_teammate", name="Vis Teammate", groups="base.group_user"
        )
        cls.stranger = mail_new_test_user(
            cls.env, login="vis_stranger", name="Vis Stranger", groups="base.group_user"
        )
        cls.led_team.user_id = cls.salesman.id
        cls.mine, cls.mates, cls.theirs = cls.env["team.member"].create(
            [
                {"team_id": cls.my_team.id, "user_id": cls.salesman.id},
                {"team_id": cls.my_team.id, "user_id": cls.teammate.id},
                {"team_id": cls.foreign_team.id, "user_id": cls.stranger.id},
            ]
        )
        cls.led = cls.env["team.member"].create(
            {"team_id": cls.led_team.id, "user_id": cls.teammate.id}
        )
        cls.env.flush_all()

    def test_foreign_membership_is_not_searchable(self):
        visible = self.env["team.member"].with_user(self.salesman).search([])
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
        "salesman own": "sale.group_sale_salesman",
        "salesman team": "sale.group_sale_salesman_team",
        "salesman all": "sale.group_sale_salesman_all_leads",
        "sales manager": "sale.group_sale_manager",
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
            visible = self.env["team.member"].with_user(reader).search([])
            readable_teams = self.env["team.team"].with_user(reader).search([])
            self.assertIn(
                self.foreign_team,
                readable_teams,
                f"{label}: a team's row must be readable so team_id can render",
            )
            if reader.has_group("sale.group_sale_salesman_all_leads"):
                continue
            self.assertNotIn(
                self.theirs,
                visible,
                f"{label}: a foreign roster must stay hidden",
            )

    def test_the_ladder_never_narrows_either_model(self):
        for model in ("team.team", "team.member"):
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
        self.assertFalse(self.env["team.member"].with_user(reader).search([]))
        self.assertIn(
            self.foreign_team,
            self.env["team.team"].with_user(reader).search([]),
            "team names must stay readable outside the Sales app",
        )

    def test_own_memberships_stay_readable_without_a_sales_group(self):
        member = mail_new_test_user(
            self.env, login="vis_own", name="Vis Own", groups="base.group_user"
        )
        own_team = self.env["team.team"].create(
            {"use_sale": True, "name": "Own", "company_id": False}
        )
        self.env["team.member"].create({"user_id": member.id, "team_id": own_team.id})
        readable = self.env["team.member"].with_user(member).search([])
        self.assertEqual(readable.team_id, own_team)

    def test_the_team_roster_still_renders(self):
        team = self.my_team.with_user(self.salesman)
        self.assertEqual(team.member_ids, self.salesman | self.teammate)
        self.assertEqual(team.team_member_ids, self.mine | self.mates)

    def test_all_documents_and_managers_are_unaffected(self):
        for user in (
            self.user_sales_leads,
            self.user_sales_manager,
        ):
            visible = self.env["team.member"].with_user(user).search([])
            self.assertIn(
                self.theirs, visible, f"{user.login} must still see everything"
            )

    def test_own_teams_still_resolve(self):
        as_self = self.salesman.with_user(self.salesman)
        self.assertEqual(as_self.sale_team_ids, self.my_team)
        self.assertEqual(as_self.sale_team_id, self.my_team)


class TestRosterVisibilityFollowsMembership(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.salesman = mail_new_test_user(
            cls.env,
            login="roster_salesman",
            name="Roster Salesman",
            groups="sale.group_sale_salesman",
        )
        cls.stranger = mail_new_test_user(
            cls.env, login="roster_stranger", name="Roster Stranger"
        )
        cls.team = cls.env["team.team"].create(
            {"use_sale": True, "name": "Roster", "company_id": False}
        )
        cls.roster = cls.env["team.member"].create(
            {"team_id": cls.team.id, "user_id": cls.stranger.id}
        )
        cls.env.flush_all()

    def _sees_roster(self):
        self.env.flush_all()
        readable = self.env["team.member"].with_user(self.salesman).search([])
        return self.roster in readable

    def test_joining_and_leaving_a_team_is_seen_at_once(self):
        self.assertFalse(self._sees_roster())

        membership = self.env["team.member"].create(
            {"team_id": self.team.id, "user_id": self.salesman.id}
        )
        self.assertTrue(self._sees_roster(), "a new member reads the roster")

        membership.action_archive()
        self.assertFalse(self._sees_roster(), "a former member no longer does")

        membership.action_unarchive()
        self.assertTrue(self._sees_roster())

        membership.unlink()
        self.assertFalse(self._sees_roster())

    def test_moving_a_membership_is_seen_at_once(self):
        elsewhere = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Elsewhere",
                "company_id": False,
            }
        )
        membership = self.env["team.member"].create(
            {"team_id": elsewhere.id, "user_id": self.salesman.id}
        )
        self.assertFalse(self._sees_roster())

        membership.write({"team_id": self.team.id})
        self.assertTrue(self._sees_roster())

    def test_archiving_the_team_is_seen_at_once(self):
        self.env["team.member"].create(
            {"team_id": self.team.id, "user_id": self.salesman.id}
        )
        self.assertTrue(self._sees_roster())

        self.team.action_archive()
        self.assertFalse(self._sees_roster())


class TestTeamWriteGrantsOutsideSales(TestSalesCommon):
    def test_a_sales_group_never_takes_a_team_write_grant_away(self):
        writers = self.env["res.groups"].create({"name": "Team writers"})
        self.env["ir.model.access"].create(
            {
                "name": "team writers",
                "model_id": self.env.ref("team.model_team_team").id,
                "group_id": writers.id,
                "perm_read": True,
                "perm_write": True,
            }
        )
        writer = mail_new_test_user(self.env, login="team_writer", name="Team Writer")
        writer.group_ids = [(4, writers.id)]
        team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Writable",
                "company_id": False,
            }
        )

        team.with_user(writer).write({"name": "Written without Sales"})
        writer.group_ids = [(4, self.env.ref("sale.group_sale_salesman").id)]
        team.with_user(writer).write({"name": "Written with Sales"})
        self.assertEqual(team.name, "Written with Sales")
