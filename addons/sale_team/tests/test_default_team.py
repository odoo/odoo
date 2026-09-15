from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_team.tests.common import TestSalesCommon
from odoo.addons.team.models.team import TEAM_SEARCHES


class TestDefaultTeam(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].set_param("sale_team.membership_multi", True)

        cls.company_2 = cls.env["res.company"].create(
            {
                "name": "New Test Company",
                "email": "company.2@test.example.com",
                "country_id": cls.env.ref("base.fr").id,
            }
        )
        cls.team_c2 = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "C2 Team1",
                "sequence": 1,
                "company_id": cls.company_2.id,
                "user_id": False,
            }
        )
        cls.team_sequence = cls.env["team.team"].create(
            {
                "use_sale": True,
                "company_id": False,
                "name": "Team LowSequence",
                "member_ids": [(4, cls.user_sales_leads.id)],
                "sequence": 0,
                "user_id": False,
            }
        )
        cls.team_responsible = cls.env["team.team"].create(
            {
                "use_sale": True,
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
            self.env["team.member"].search([("user_id", "=", self.user_sales_leads.id)])
        )

        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.team_sequence)

        self.team_sequence.active = False
        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.team_responsible)

        self.user_sales_leads.write(
            {
                "company_ids": [(4, self.company_2.id)],
                "company_id": self.company_2.id,
            }
        )
        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.team_c2)

    def test_default_team_member(self):
        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.team_sequence)

        self.team_sequence.member_ids = [(5,)]
        self.team_sequence.flush_model()
        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.sales_team_1)

        self.team_responsible.user_id = self.user_sales_leads.id
        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.team_responsible)

        self.team_responsible.sequence = self.sales_team_1.sequence
        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.team_responsible)

    def test_default_team_wcontext(self):
        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.team_sequence)

            team = (
                self.env["team.team"]
                .with_context(default_team_id=self.sales_team_1.id)
                ._get_default_team("sale")
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
            self.env["team.member"].search([("user_id", "=", self.user_sales_leads.id)])
        )

        with self.with_user("user_sales_leads"):
            team = self.env["team.team"]._get_default_team("sale")
            self.assertEqual(team, self.team_sequence)

            team = (
                self.env["team.team"]
                .with_context(default_team_id=self.sales_team_1.id)
                ._get_default_team("sale")
            )
            self.assertEqual(
                team,
                self.sales_team_1,
                "SalesTeam: default taken into account when no member / responsible",
            )


class TestDefaultTeamFromContext(TestSalesCommon):
    def test_archived_context_team_is_not_proposed(self):
        live = self.env["team.team"].create(
            {"use_sale": True, "name": "Live", "company_id": False}
        )
        dead = self.env["team.team"].create(
            {"use_sale": True, "name": "Dead", "company_id": False}
        )
        dead.action_archive()
        self.env.flush_all()

        team = (
            self.env["team.team"]
            .with_context(default_team_id=dead.id)
            ._get_default_team("sale")
        )
        self.assertNotEqual(team, dead, "an archived team must not be proposed")
        self.assertTrue(not team or team.active)
        self.assertTrue(
            self.env["team.team"]
            .with_context(default_team_id=live.id)
            ._get_default_team("sale")
        )

    def test_deleted_context_team_is_not_proposed(self):
        dangling = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Dangling",
                "company_id": False,
            }
        )
        dangling_id = dangling.id
        dangling.unlink()
        self.env.flush_all()

        team = (
            self.env["team.team"]
            .with_context(default_team_id=dangling_id)
            ._get_default_team("sale")
        )
        self.assertNotEqual(team.id, dangling_id)

    def test_foreign_company_context_team_is_not_proposed(self):
        salesman = self.user_sales_salesman
        other_company = self.env["res.company"].create({"name": "Ctx Other Co"})
        foreign = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Foreign",
                "company_id": other_company.id,
            }
        )
        self.env.flush_all()

        team = (
            self.env["team.team"]
            .with_user(salesman)
            .with_context(default_team_id=foreign.id)
            ._get_default_team("sale")
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
        team_c2 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Team Co2",
                "company_id": company_2.id,
            }
        )
        self.env.flush_all()

        CrmTeam = self.env["team.team"].with_user(self.user_sales_salesman)
        allowed_c2 = CrmTeam.with_context(
            default_team_id=team_c2.id, allowed_company_ids=[company_2.id]
        )._get_default_team("sale")
        self.assertEqual(allowed_c2, team_c2)
        allowed_main = CrmTeam.with_context(
            default_team_id=team_c2.id, allowed_company_ids=[self.company_main.id]
        )._get_default_team("sale")
        self.assertNotEqual(allowed_main, team_c2)

    def test_readable_context_team_still_wins(self):
        own = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Own",
                "company_id": False,
                "sequence": 99,
                "member_ids": [(4, self.user_sales_leads.id)],
            }
        )
        self.env.flush_all()
        team = (
            self.env["team.team"]
            .with_user(self.user_sales_leads)
            .with_context(default_team_id=own.id)
            ._get_default_team("sale")
        )
        self.assertEqual(team, own)
        self.assertFalse(team.env.su)


class TestDefaultTeamFallbackQueries(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["team.team"].search([]).write({"sequence": 50})
        cls.wanted = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Wanted",
                "company_id": False,
                "sequence": 1,
                "user_id": False,
            }
        )
        cls.filler = cls.env["team.team"].create(
            [
                {
                    "use_sale": True,
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
            groups="sale.group_sale_salesman_all_leads",
        )
        cls.env.flush_all()

    def test_domain_fallback_picks_the_same_team_as_filtered_domain(self):
        domain = [("name", "=", "Wanted")]
        team = (
            self.env["team.team"]
            .with_user(self.loner)
            ._get_default_team("sale", domain=domain)
        )
        reference = self.env["team.team"].with_user(self.loner).search([])
        self.assertEqual(team, reference.filtered_domain(domain)[:1])
        self.assertEqual(team, self.wanted)

    def test_domain_fallback_falls_back_to_the_first_team(self):
        domain = [("name", "=", "No Such Team")]
        team = (
            self.env["team.team"]
            .with_user(self.loner)
            ._get_default_team("sale", domain=domain)
        )
        reference = self.env["team.team"].with_user(self.loner).search([])
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
        TEAM_SEARCHES.discard(self.env)
        try:
            self.env["team.team"].with_user(self.loner)._get_default_team(
                "sale", domain=[("name", "=", "Wanted")]
            )
        finally:
            cursor_cls.execute = original
        return rows[0]

    def test_fallback_does_not_scale_with_the_table(self):
        self._rows_fetched_by_fallback()
        small = self._rows_fetched_by_fallback()
        self.env["team.team"].create(
            [
                {
                    "use_sale": True,
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


class TestDefaultTeamIsNotCallerDependent(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "sale_team.membership_multi", True
        )
        cls.env["team.team"].search([]).write({"sequence": 9000})
        cls.filer = mail_new_test_user(
            cls.env,
            login="dep_filer",
            name="Dep Filer",
            groups="sale.group_sale_salesman_team",
        )
        cls.owner = mail_new_test_user(
            cls.env,
            login="dep_owner",
            name="Dep Owner",
            groups="sale.group_sale_salesman_team",
        )
        cls.owner_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Owner Team",
                "sequence": 10,
                "company_id": False,
            }
        )
        cls.shared_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Shared Team",
                "sequence": 20,
                "company_id": False,
            }
        )
        cls.env["team.member"].create(
            [
                {"team_id": cls.owner_team.id, "user_id": cls.owner.id},
                {"team_id": cls.shared_team.id, "user_id": cls.owner.id},
                {"team_id": cls.shared_team.id, "user_id": cls.filer.id},
            ]
        )
        cls.env.flush_all()

    def test_every_caller_gets_the_same_team(self):
        CrmTeam = self.env["team.team"]
        for actor in (self.env.user, self.filer, self.owner):
            self.assertEqual(
                CrmTeam.with_user(actor)._get_default_team(
                    "sale", user_id=self.owner.id
                ),
                self.owner_team,
                f"{actor.login} got a different default team for the same salesperson",
            )

    def test_the_answer_is_not_sudoed(self):
        team = (
            self.env["team.team"]
            .with_user(self.filer)
            ._get_default_team("sale", user_id=self.owner.id)
        )
        self.assertFalse(team.env.su)

    def test_the_company_fallback_is_caller_independent_too(self):
        loner = mail_new_test_user(
            self.env,
            login="dep_loner",
            name="Dep Loner",
            groups="sale.group_sale_salesman",
        )
        self.env.flush_all()
        CrmTeam = self.env["team.team"]
        answers = {
            CrmTeam.with_user(actor)._get_default_team("sale", user_id=loner.id)
            for actor in (self.env.user, self.filer, self.owner)
        }
        self.assertEqual(len(answers), 1, f"the fallback differed by caller: {answers}")
        self.assertEqual(answers.pop(), self.owner_team)

    def test_a_document_opens_for_the_person_who_filed_it(self):
        team = (
            self.env["team.team"]
            .with_user(self.filer)
            ._get_default_team("sale", user_id=self.owner.id)
        )
        self.assertEqual(team, self.owner_team)
        self.env.invalidate_all()
        self.assertEqual(
            team.with_user(self.filer).display_name,
            "Owner Team",
            "the filer cannot open a document carrying the team they just "
            "filed it under",
        )


class TestDefaultTeamIgnoresArchived(TestSalesCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leader = mail_new_test_user(
            cls.env,
            login="arch_leader",
            name="Arch Leader",
            groups="sale.group_sale_salesman",
        )
        cls.env["team.team"].search([]).write({"active": False})
        cls.dead_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Dead",
                "company_id": False,
                "user_id": cls.leader.id,
            }
        )
        cls.dead_team.action_archive()
        cls.env.flush_all()

    def test_no_live_team_means_no_default(self):
        team = self.env["team.team"].with_user(self.leader)._get_default_team("sale")
        self.assertFalse(team)

    def test_archived_team_is_not_proposed_under_active_test_false(self):
        team = (
            self.env["team.team"]
            .with_user(self.leader)
            .with_context(active_test=False)
            ._get_default_team("sale")
        )
        self.assertFalse(team, "an archived team is never a default for a new document")

    def test_the_company_fallback_is_archive_blind_too(self):
        stranger = mail_new_test_user(
            self.env,
            login="arch_stranger",
            name="Arch Stranger",
            groups="sale.group_sale_salesman_all_leads",
        )
        for domain in (False, [("name", "=", "Dead")]):
            with self.subTest(domain=domain):
                team = (
                    self.env["team.team"]
                    .with_user(stranger)
                    .with_context(active_test=False)
                    ._get_default_team("sale", domain=domain)
                )
                self.assertFalse(team)

    def test_a_live_team_is_still_found(self):
        live = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Alive",
                "company_id": False,
                "user_id": self.leader.id,
            }
        )
        for context in ({}, {"active_test": False}):
            with self.subTest(context=context):
                self.assertEqual(
                    self.env["team.team"]
                    .with_user(self.leader)
                    .with_context(**context)
                    ._get_default_team("sale"),
                    live,
                )
