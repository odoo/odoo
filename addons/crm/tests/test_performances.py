import random

from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.crm.tests.test_crm_lead_assignment import TestLeadAssignCommon


@tagged("lead_assign", "crm_performance", "post_install", "-at_install")
class TestLeadAssignPerf(TestLeadAssignCommon):
    def setUp(self):
        super().setUp()
        self.patch(self.env.registry, "ready", True)
        self._mock_smtplib_connection()

    @mute_logger(
        "odoo.models.unlink",
        "odoo.addons.crm.models.team_team",
        "odoo.addons.crm.models.team_member",
    )
    def test_assign_perf_duplicates(self):
        random.seed(1940)

        leads = self._create_leads_batch(
            lead_type="lead",
            user_ids=[False],
            partner_ids=[self.contact_1.id, self.contact_2.id, False, False, False],
            count=200,
        )
        leads.flush_recordset()
        self.assertInitialData()

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        for idx in range(5):
            sliced_leads = leads[idx : len(leads) : 5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)
        leads.flush_recordset()

        with self.with_user("user_sales_manager"):
            self.env.user._is_internal()
            # Counted after a rolled-back rehearsal (assertQueryCountWarm), so
            # the figure is the assignment's own and reads the same on
            # `-i sale_team,crm --with-demo` and on a seven-module closure to
            # within two queries. Pinned at the wider closure; a reading one
            # or two below on the narrower one is that difference, not slack.
            # `assertQueryCount` only fails on an over-count, so a budget met
            # from further below is a guard that has retired: re-pin it.
            self.assertQueryCountWarm(
                lambda: (
                    self.env["team.team"]
                    .browse(self.sales_teams.ids)
                    ._action_assign_leads()
                ),
                user_sales_manager=414,
            )

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        leads_st1 = leads.filtered_domain([("team_id", "=", self.sales_team_1.id)])
        leads_stc = leads.filtered_domain(
            [("team_id", "=", self.sales_team_convert.id)]
        )
        self.assertLessEqual(len(leads_st1), 128)
        self.assertLessEqual(len(leads_stc), 96)
        self.assertEqual(len(leads_st1) + len(leads_stc), len(leads))

        self.members.invalidate_model(["lead_month_count", "lead_day_count"])
        self.assertMemberAssign(self.sales_team_1_m1, 2)
        self.assertMemberAssign(self.sales_team_1_m2, 1)
        self.assertMemberAssign(self.sales_team_1_m3, 1)
        self.assertMemberAssign(self.sales_team_convert_m1, 1)
        self.assertMemberAssign(self.sales_team_convert_m2, 2)

    @mute_logger(
        "odoo.models.unlink",
        "odoo.addons.crm.models.team_team",
        "odoo.addons.crm.models.team_member",
    )
    def test_assign_perf_no_duplicates(self):
        random.seed(1945)

        leads = self._create_leads_batch(
            lead_type="lead", user_ids=[False], partner_ids=[False], count=100
        )
        leads.flush_recordset()
        self.assertInitialData()

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        for idx in range(5):
            sliced_leads = leads[idx : len(leads) : 5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)
        leads.flush_recordset()

        with self.with_user("user_sales_manager"):
            self.assertQueryCountWarm(
                lambda: (
                    self.env["team.team"]
                    .browse(self.sales_teams.ids)
                    ._action_assign_leads()
                ),
                user_sales_manager=111,
            )

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        leads_st1 = leads.filtered_domain([("team_id", "=", self.sales_team_1.id)])
        leads_stc = leads.filtered_domain(
            [("team_id", "=", self.sales_team_convert.id)]
        )
        self.assertEqual(len(leads_st1) + len(leads_stc), 100)

        self.members.invalidate_model(["lead_month_count", "lead_day_count"])
        self.assertMemberAssign(self.sales_team_1_m1, 2)
        self.assertMemberAssign(self.sales_team_1_m2, 1)
        self.assertMemberAssign(self.sales_team_1_m3, 1)
        self.assertMemberAssign(self.sales_team_convert_m1, 1)
        self.assertMemberAssign(self.sales_team_convert_m2, 2)

    @mute_logger(
        "odoo.models.unlink",
        "odoo.addons.crm.models.team_team",
        "odoo.addons.crm.models.team_member",
    )
    def test_assign_perf_populated(self):
        random.seed(1871)

        _lead_count, _email_dup_count, _partner_count = 600, 50, 150
        leads = self._create_leads_batch(
            lead_type="lead",
            user_ids=[False],
            partner_count=_partner_count,
            country_ids=[self.env.ref("base.be").id, self.env.ref("base.fr").id, False],
            count=_lead_count,
            email_dup_count=_email_dup_count,
        )
        leads.flush_recordset()
        self.assertInitialData()

        self.env.ref("crm.ir_cron_crm_lead_assign").write(
            {"repeat_unit": "day", "repeat_interval": 30}
        )
        sales_team_3 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Sales Team 3",
                "sequence": 15,
                "lead_alias_name": False,
                "use_leads": True,
                "use_opportunities": True,
                "company_id": False,
                "user_id": False,
                "lead_assignment_domain": [("country_id", "!=", False)],
            }
        )
        sales_team_3_m1 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_manager.id,
                "team_id": sales_team_3.id,
                "lead_assignment_max": 60,
                "lead_assignment_domain": False,
            }
        )
        sales_team_3_m2 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_leads.id,
                "team_id": sales_team_3.id,
                "lead_assignment_max": 60,
                "lead_assignment_domain": False,
            }
        )
        sales_team_3_m3 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_salesman.id,
                "team_id": sales_team_3.id,
                "lead_assignment_max": 15,
                "lead_assignment_domain": [("probability", ">=", 10)],
            }
        )
        sales_teams = self.sales_teams | sales_team_3
        self.assertEqual(sum(team.lead_assignment_max for team in sales_teams), 300)
        self.assertEqual(len(leads), 650)

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        for idx in range(5):
            sliced_leads = leads[idx : len(leads) : 5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)
        leads.flush_recordset()

        with self.with_user("user_sales_manager"):
            self.assertQueryCountWarm(
                lambda: (
                    self.env["team.team"].browse(sales_teams.ids)._action_assign_leads()
                ),
                user_sales_manager=990,
            )

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        self.assertEqual(leads.team_id, sales_teams)
        self.assertEqual(leads.user_id, sales_teams.member_ids)

        self.members.invalidate_model(["lead_month_count", "lead_day_count"])
        self.assertMemberAssign(self.sales_team_1_m1, 2)
        self.assertMemberAssign(self.sales_team_1_m2, 1)
        self.assertMemberAssign(self.sales_team_1_m3, 1)
        self.assertMemberAssign(self.sales_team_convert_m1, 1)
        self.assertMemberAssign(self.sales_team_convert_m2, 2)
        self.assertMemberAssign(sales_team_3_m1, 2)
        self.assertMemberAssign(sales_team_3_m2, 2)
        self.assertMemberAssign(sales_team_3_m3, 1)

    @mute_logger(
        "odoo.models.unlink",
        "odoo.addons.crm.models.team_team",
        "odoo.addons.crm.models.team_member",
    )
    def test_allocate_leads_marginal_cost(self):
        counts = {}
        for index, count in enumerate((2, 20)):
            random.seed(2026 + index)
            team = self.env["team.team"].create(
                {
                    "use_sale": True,
                    "lead_alias_name": False,
                    "lead_assignment_domain": False,
                    "lead_assignment_optout": False,
                    "name": f"Marginal Team {count}",
                    "use_leads": True,
                    "use_opportunities": True,
                    "user_id": False,
                }
            )
            self.env["team.member"].create(
                {
                    "lead_assignment_domain": False,
                    "lead_assignment_max": 200,
                    "team_id": team.id,
                    "user_id": self.user_sales_manager.id,
                }
            )
            self._create_leads_batch(
                lead_type="lead",
                user_ids=[False],
                partner_ids=[False],
                count=count,
                suffix=f"Marginal{count}",
            )
            self.env.flush_all()
            self.env.invalidate_all()

            before = self.cr.sql_statement_count
            team._allocate_leads(creation_delta_days=0)
            self.env.flush_all()
            counts[count] = self.cr.sql_statement_count - before

        marginal = (counts[20] - counts[2]) / 18.0
        self.assertLess(
            marginal,
            1.5,
            f"_allocate_leads costs {marginal:.2f} queries per extra lead; "
            f"{counts}. Something in the per-lead loop is querying again.",
        )
