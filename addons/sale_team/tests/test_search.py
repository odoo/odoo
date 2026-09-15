from odoo import exceptions
from odoo.tools.safe_eval import safe_eval

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_team.tests.common import TestSalesCommon


def _salesperson_domain(env, team_id, record_id):
    return safe_eval(
        env["team.member"]._fields["user_id"].domain,
        {
            "team_id": team_id,
            "id": record_id,
            "user_company_ids": env["res.company"].search([]).ids,
        },
    )


class TestSearchCrmTeamIds(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.team_a = cls.env["team.team"].create(
            {"use_sale": True, "name": "SA", "company_id": False}
        )
        cls.team_b = cls.env["team.team"].create(
            {"use_sale": True, "name": "SB", "company_id": False}
        )
        cls.user_ab = mail_new_test_user(
            cls.env, login="search_ab", name="Search AB", groups="base.group_user"
        )
        cls.user_none = mail_new_test_user(
            cls.env, login="search_none", name="Search None", groups="base.group_user"
        )
        cls.env["team.member"].create(
            [
                {"user_id": cls.user_ab.id, "team_id": cls.team_a.id},
                {"user_id": cls.user_ab.id, "team_id": cls.team_b.id},
            ]
        )
        cls.env["team.member"].create(
            {"user_id": cls.user_none.id, "team_id": cls.team_a.id}
        ).action_archive()
        cls.env.flush_all()

    def _search(self, operator, value):
        return self.env["res.users"].search(
            [
                ("id", "in", (self.user_ab | self.user_none).ids),
                ("sale_team_ids", operator, value),
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
                f"sale_team_ids {operator} {team_value!r} disagrees with a stored m2m",
            )


class TestSearchCrmTeamIdsMixedFalse(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.team = cls.env["team.team"].create(
            {"use_sale": True, "name": "MF", "company_id": False}
        )
        cls.on_team = mail_new_test_user(
            cls.env, login="mf_on", name="MF On", groups="base.group_user"
        )
        cls.teamless = mail_new_test_user(
            cls.env, login="mf_off", name="MF Off", groups="base.group_user"
        )
        cls.env["team.member"].create(
            {"user_id": cls.on_team.id, "team_id": cls.team.id}
        )
        cls.env.flush_all()

    def test_mixed_false_and_ids(self):
        found = self.env["res.users"].search(
            [
                ("id", "in", (self.on_team | self.teamless).ids),
                ("sale_team_ids", "in", [False] + self.team.ids),
            ]
        )
        self.assertEqual(
            found,
            self.on_team | self.teamless,
            "'no team OR that team' must return both",
        )


class TestSearchMemberIds(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.team_a = cls.env["team.team"].create(
            {"use_sale": True, "name": "MA", "company_id": False}
        )
        cls.team_b = cls.env["team.team"].create(
            {"use_sale": True, "name": "MB", "company_id": False}
        )
        cls.team_empty = cls.env["team.team"].create(
            {"use_sale": True, "name": "MEmpty", "company_id": False}
        )
        cls.member_a = mail_new_test_user(
            cls.env, login="mi_a", name="Mi A", groups="base.group_user"
        )
        cls.member_b = mail_new_test_user(
            cls.env, login="mi_b", name="Mi B", groups="base.group_user"
        )
        cls.env["team.member"].create(
            [
                {"user_id": cls.member_a.id, "team_id": cls.team_a.id},
                {"user_id": cls.member_b.id, "team_id": cls.team_b.id},
            ]
        )
        cls.env["team.member"].create(
            {"user_id": cls.member_b.id, "team_id": cls.team_a.id}
        ).action_archive()
        cls.teams = cls.team_a | cls.team_b | cls.team_empty
        cls.env.flush_all()

    def _search(self, operator, value):
        return self.env["team.team"].search(
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


class TestSalespersonDomain(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.team_a = cls.env["team.team"].create(
            {"use_sale": True, "name": "DA", "company_id": False}
        )
        cls.team_b = cls.env["team.team"].create(
            {"use_sale": True, "name": "DB", "company_id": False}
        )
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
        cls.env["team.member"].create(
            [
                {"user_id": cls.in_a.id, "team_id": cls.team_a.id},
                {"user_id": cls.in_b.id, "team_id": cls.team_b.id},
            ]
        )
        cls.env["team.member"].create(
            {"user_id": cls.former.id, "team_id": cls.team_a.id}
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
            "sale_team.membership_multi", False
        )
        self.env.invalidate_all()
        self.assertEqual(self._selectable(self.team_a.id), multi)

    def test_mono_mode_transfer_goes_through(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", False
        )
        self.env.invalidate_all()
        self.assertIn(
            self.in_a,
            self._selectable(self.team_b.id),
            "mono mode must offer a salesperson from another team",
        )

        moved = self.env["team.member"].create(
            {"team_id": self.team_b.id, "user_id": self.in_a.id}
        )
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertTrue(moved.active)
        self.assertEqual(
            self.in_a.sale_team_ids,
            self.team_b,
            "the salesperson ends on exactly one team",
        )
        self.assertEqual(self.in_a.sale_team_id, self.team_b)

    def test_agrees_with_the_constraint_it_anticipates(self):
        for user in self._selectable(self.team_a.id):
            with self.env.cr.savepoint():
                self.env["team.member"].create(
                    {"team_id": self.team_a.id, "user_id": user.id}
                )
                self.env.flush_all()
        with self.assertRaises(exceptions.ValidationError), self.env.cr.savepoint():
            self.env["team.member"].create(
                {"team_id": self.team_a.id, "user_id": self.in_a.id}
            )
            self.env.flush_all()


class TestSalespersonDomainSelfExclusion(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env["team.team"].create(
            {"use_sale": True, "name": "Excl", "company_id": False}
        )
        cls.member_user = mail_new_test_user(
            cls.env,
            login="excl_user",
            name="Excl User",
            groups="sale.group_sale_salesman",
        )
        cls.membership = cls.env["team.member"].create(
            {"team_id": cls.team.id, "user_id": cls.member_user.id}
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
        other = self.env["team.member"].create(
            {
                "team_id": self.env["team.team"]
                .create({"use_sale": True, "name": "Excl2", "company_id": False})
                .id,
                "user_id": mail_new_test_user(
                    self.env, login="excl_other", name="Excl Other"
                ).id,
            }
        )
        self.assertNotIn(self.member_user, self._offered(other.id))
