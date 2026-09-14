import random
from ast import literal_eval
from datetime import datetime, timedelta
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.fields import Datetime
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.crm.tests.common import TestLeadConvertCommon


class TestLeadAssignCommon(TestLeadConvertCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._switch_to_multi_membership()
        cls._switch_to_auto_assign()

        cls.sales_teams = cls.sales_team_1 + cls.sales_team_convert
        cls.members = (
            cls.sales_team_1_m1
            + cls.sales_team_1_m2
            + cls.sales_team_1_m3
            + cls.sales_team_convert_m1
            + cls.sales_team_convert_m2
        )
        cls.env["team.team"].search([("id", "not in", cls.sales_teams.ids)]).write(
            {"active": False}
        )

        with mute_logger("odoo.models.unlink"):
            cls.env["crm.lead"].with_context(active_test=False).search(
                [
                    "|",
                    ("team_id", "=", False),
                    ("user_id", "in", cls.sales_teams.member_ids.ids),
                ]
            ).unlink()
        cls.bundle_size = 50
        cls.env["ir.config_parameter"].set_param(
            "crm.assignment.commit.bundle", "%s" % cls.bundle_size
        )
        cls.env["ir.config_parameter"].set_param("crm.assignment.delay", "0")

    def assertInitialData(self):
        self.assertEqual(self.sales_team_1.lead_assignment_max, 75)
        self.assertEqual(self.sales_team_convert.lead_assignment_max, 90)

        self.assertEqual(self.sales_team_1.lead_assignment_domain, False)
        self.assertEqual(self.sales_team_1_m1.lead_assignment_domain, False)
        self.assertEqual(
            self.sales_team_1_m2.lead_assignment_domain, "[('probability', '>=', 10)]"
        )
        self.assertEqual(
            self.sales_team_1_m3.lead_assignment_domain, "[('probability', '>=', 20)]"
        )

        self.assertEqual(
            self.sales_team_convert.lead_assignment_domain,
            "[('priority', 'in', ['1', '2', '3'])]",
        )
        self.assertEqual(
            self.sales_team_convert_m1.lead_assignment_domain,
            "[('probability', '>=', 20)]",
        )
        self.assertEqual(self.sales_team_convert_m2.lead_assignment_domain, False)

        self.assertEqual(self.sales_team_1_m1.lead_month_count, 0)
        self.assertEqual(self.sales_team_1_m2.lead_month_count, 0)
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 0)
        self.assertEqual(self.sales_team_convert_m1.lead_month_count, 0)
        self.assertEqual(self.sales_team_convert_m2.lead_month_count, 0)


@tagged("lead_assign")
class TestLeadAssign(TestLeadAssignCommon):
    def test_assign_configuration(self):
        now_patch = datetime(2020, 11, 2, 10, 0, 0)

        with patch.object(fields.Datetime, "now", return_value=now_patch):
            config = self.env["res.config.settings"].create(
                {
                    "crm_use_auto_assignment": True,
                    "crm_auto_assignment_action": "auto",
                    "crm_auto_assignment_repeat_interval": 19,
                    "crm_auto_assignment_repeat_unit": "hour",
                }
            )
            config._onchange_crm_auto_assignment_run_datetime()
            config.execute()
            self.assertTrue(self.assign_cron.active)
            self.assertEqual(
                self.assign_cron.nextcall,
                datetime(2020, 11, 2, 10, 0, 0) + relativedelta(hours=19),
            )

            config.write(
                {
                    "crm_auto_assignment_repeat_interval": 2,
                    "crm_auto_assignment_repeat_unit": "day",
                }
            )
            config._onchange_crm_auto_assignment_run_datetime()
            config.execute()
            self.assertTrue(self.assign_cron.active)
            self.assertEqual(
                self.assign_cron.nextcall,
                datetime(2020, 11, 2, 10, 0, 0) + relativedelta(days=2),
            )

            config.write(
                {
                    "crm_auto_assignment_run_datetime": fields.Datetime.to_string(
                        datetime(2020, 11, 1, 10, 0, 0)
                    ),
                }
            )
            config.execute()
            self.assertTrue(self.assign_cron.active)
            self.assertEqual(self.assign_cron.nextcall, datetime(2020, 11, 1, 10, 0, 0))

            config.write(
                {
                    "crm_auto_assignment_action": "manual",
                }
            )
            config.execute()
            self.assertFalse(self.assign_cron.active)
            self.assertEqual(self.assign_cron.nextcall, datetime(2020, 11, 1, 10, 0, 0))

            config.write(
                {
                    "crm_use_auto_assignment": False,
                    "crm_auto_assignment_action": "auto",
                }
            )
            config.execute()
            self.assertFalse(self.assign_cron.active)
            self.assertEqual(self.assign_cron.nextcall, datetime(2020, 11, 1, 10, 0, 0))

    def test_assign_count(self):
        leads = self._create_leads_batch(
            lead_type="lead",
            user_ids=[False],
            partner_ids=[False, False, False, self.contact_1.id],
            probabilities=[30],
            count=8,
            suffix="Initial",
        )
        leads.flush_recordset()
        self.assertInitialData()

        self.sales_team_1_m1.action_archive()
        self.sales_team_1_m2.lead_assignment_max = 0

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        for idx, lead in enumerate(leads):
            lead.probability = idx * 10
        leads.flush_recordset()
        self.assertEqual(leads[0].probability, 0)

        existing_leads = self._create_leads_batch(
            lead_type="lead",
            user_ids=[self.user_sales_salesman.id],
            probabilities=[10],
            count=14,
            suffix="Existing",
        )
        self.assertEqual(
            existing_leads.team_id, self.sales_team_1, "Team should have lower sequence"
        )
        existing_leads[0].action_set_lost()
        existing_leads[1].probability = 100
        existing_leads[2].probability = 0
        existing_leads.flush_recordset()

        self.members.invalidate_model(["lead_month_count"])
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 14)
        self.assertEqual(self.sales_team_convert_m1.lead_month_count, 0)

        existing_leads[-2:]._handle_salesmen_assignment(
            user_ids=self.user_sales_manager.ids
        )
        leads.flush_recordset()
        self.members.invalidate_model(["lead_month_count"])
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 12)

        self.sales_team_1_m2.update(
            {"lead_assignment_max": 45, "lead_assignment_optout": True}
        )
        self.sales_team_1_m3.update({"lead_assignment_max": 45})
        with self.with_user("user_sales_manager"):
            teams_data, members_data = self.sales_team_1._action_assign_leads(
                force_quota=True
            )

        Leads = self.env["crm.lead"]

        self.assertEqual(
            sorted(
                Leads.browse(teams_data[self.sales_team_1]["assigned"]).mapped("name")
            ),
            [
                "TestLeadInitial_0000",
                "TestLeadInitial_0001",
                "TestLeadInitial_0002",
                "TestLeadInitial_0004",
                "TestLeadInitial_0005",
                "TestLeadInitial_0006",
            ],
        )
        self.assertEqual(
            Leads.browse(teams_data[self.sales_team_1]["merged"]).mapped("name"),
            ["TestLeadInitial_0003"],
        )

        self.assertEqual(len(teams_data[self.sales_team_1]["duplicates"]), 1)

        self.assertEqual(
            sorted(members_data[self.sales_team_1_m3]["assigned"].mapped("name")),
            ["TestLeadInitial_0000", "TestLeadInitial_0005"],
        )

        self.members.invalidate_model(["lead_month_count"])
        self.assertEqual(self.sales_team_1_m1.lead_month_count, 0)
        self.assertEqual(self.sales_team_1_m2.lead_month_count, 0)
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 14)

        with self.with_user("user_sales_manager"):
            self.env["team.team"].browse(self.sales_team_1.ids)._action_assign_leads(
                force_quota=True
            )

        self.members.invalidate_model(["lead_month_count"])
        self.assertEqual(self.sales_team_1_m1.lead_month_count, 0)
        self.assertEqual(self.sales_team_1_m2.lead_month_count, 0)
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 16)

    @mute_logger("odoo.models.unlink")
    def test_assign_duplicates(self):
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
            self.env["team.team"].browse(self.sales_teams.ids)._action_assign_leads()

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        self.assertEqual(len(leads), 122)
        leads_st1 = leads.filtered_domain([("team_id", "=", self.sales_team_1.id)])
        leads_stc = leads.filtered_domain(
            [("team_id", "=", self.sales_team_convert.id)]
        )

        self.assertEqual(len(leads_st1), 76)
        self.assertEqual(len(leads_stc), 46)
        self.assertEqual(len(leads_st1) + len(leads_stc), len(leads))

        self.members.invalidate_model(["lead_month_count", "lead_day_count"])
        self.assertMemberAssign(self.sales_team_1_m1, 2)
        self.assertMemberAssign(self.sales_team_1_m2, 1)
        self.assertMemberAssign(self.sales_team_1_m3, 1)
        self.assertMemberAssign(self.sales_team_convert_m1, 1)
        self.assertMemberAssign(self.sales_team_convert_m2, 2)

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        self.assertEqual(len(leads.filtered_domain([("team_id", "=", False)])), 0)

        new_assigned_leads_wpartner = self.env["crm.lead"].search(
            [
                ("partner_id", "in", (self.contact_1 | self.contact_2).ids),
                ("id", "in", leads.ids),
            ]
        )
        self.assertEqual(len(new_assigned_leads_wpartner), 2)

    @mute_logger("odoo.models.unlink")
    def test_assign_no_duplicates(self):
        random.seed(1945)

        leads = self._create_leads_batch(
            lead_type="lead", user_ids=[False], partner_ids=[False], count=150
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
            self.env["team.team"].browse(self.sales_teams.ids)._action_assign_leads()

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        leads_st1 = leads.filtered_domain([("team_id", "=", self.sales_team_1.id)])
        leads_stc = leads.filtered_domain(
            [("team_id", "=", self.sales_team_convert.id)]
        )
        self.assertEqual(len(leads), 150)

        self.assertEqual(len(leads_st1), 104)
        self.assertEqual(len(leads_stc), 46)
        self.assertEqual(len(leads_st1) + len(leads_stc), len(leads))

        self.members.invalidate_model(["lead_month_count", "lead_day_count"])
        self.assertMemberAssign(self.sales_team_1_m1, 2)
        self.assertMemberAssign(self.sales_team_1_m2, 1)
        self.assertMemberAssign(self.sales_team_1_m3, 1)
        self.assertMemberAssign(self.sales_team_convert_m1, 1)
        self.assertMemberAssign(self.sales_team_convert_m2, 2)

    @mute_logger("odoo.models.unlink")
    def test_assign_populated(self):
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
        sales_teams = self.sales_teams + sales_team_3
        self.assertEqual(sum(team.lead_assignment_max for team in sales_teams), 300)
        self.assertEqual(len(leads), 650)

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        for idx in range(5):
            sliced_leads = leads[idx : len(leads) : 5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)
        leads.flush_recordset()

        with self.with_user("user_sales_manager"):
            self.env["team.team"].browse(sales_teams.ids)._action_assign_leads()

        leads = self.env["crm.lead"].search([("id", "in", leads.ids)])
        self.assertEqual(leads.team_id, sales_teams)
        self.assertEqual(leads.user_id, sales_teams.member_ids)
        self.assertEqual(len(leads), 600)

        leads_st1 = leads.filtered_domain([("team_id", "=", self.sales_team_1.id)])
        leads_st2 = leads.filtered_domain(
            [("team_id", "=", self.sales_team_convert.id)]
        )
        leads_st3 = leads.filtered_domain([("team_id", "=", sales_team_3.id)])
        self.assertEqual(len(leads_st1), 170)
        self.assertEqual(len(leads_st2), 116)
        self.assertEqual(len(leads_st3), 314)

        self.members.invalidate_model(["lead_month_count", "lead_day_count"])
        self.assertMemberAssign(self.sales_team_1_m1, 2)
        self.assertMemberAssign(self.sales_team_1_m2, 1)
        self.assertMemberAssign(self.sales_team_1_m3, 1)
        self.assertMemberAssign(self.sales_team_convert_m1, 1)
        self.assertMemberAssign(self.sales_team_convert_m2, 2)
        self.assertMemberAssign(sales_team_3_m1, 2)
        self.assertMemberAssign(sales_team_3_m2, 2)
        self.assertMemberAssign(sales_team_3_m3, 1)

    def test_assign_preferred_domain(self):
        random.seed(1914)
        preferred_tag = self.env["crm.tag"].create({"name": "preferred"})

        leads = self._create_leads_batch(
            lead_type="lead",
            user_ids=[False],
            count=11,
        )
        leads[:8].write({"tag_ids": [(6, 0, preferred_tag.ids)]})
        leads.flush_recordset()
        self.assertInitialData()
        test_sales_team = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Sales Team 5",
                "sequence": 15,
                "lead_alias_name": False,
                "use_leads": True,
                "use_opportunities": True,
                "company_id": False,
                "user_id": False,
            }
        )
        test_sales_team_m1 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_manager.id,
                "team_id": test_sales_team.id,
                "lead_assignment_max": 150,
                "lead_assignment_domain": False,
                "lead_assignment_domain_preferred": "[('tag_ids', 'in', %s)]"
                % preferred_tag.ids,
            }
        )
        test_sales_team_m2 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_leads.id,
                "team_id": test_sales_team.id,
                "lead_assignment_max": 150,
                "lead_assignment_domain": False,
                "lead_assignment_domain_preferred": False,
            }
        )
        test_sales_team_m3 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_salesman.id,
                "team_id": test_sales_team.id,
                "lead_assignment_max": 150,
                "lead_assignment_domain": False,
                "lead_assignment_domain_preferred": False,
            }
        )

        test_sales_team._action_assign_leads()

        member_leads = self.env["crm.lead"].search(
            [
                ("user_id", "=", test_sales_team_m1.user_id.id),
                ("team_id", "=", test_sales_team_m1.team_id.id),
                ("date_open", ">=", Datetime.now() - timedelta(hours=24)),
            ]
        )
        self.assertEqual(
            member_leads.filtered_domain(
                literal_eval(test_sales_team_m1.lead_assignment_domain_preferred)
            ),
            member_leads,
        )
        self.assertMemberAssign(test_sales_team_m1, 5)
        self.assertMemberAssign(test_sales_team_m2, 3)
        self.assertMemberAssign(test_sales_team_m3, 3)

    def test_assign_quota(self):
        self.assertInitialData()

        self.assertEqual(
            self.sales_team_1_m1._get_assignment_quota(),
            2,
            "Assignment quota: 45 max -> 2 daily (round(45/30))",
        )

        existing_leads = self._create_leads_batch(
            lead_type="lead",
            user_ids=[self.user_sales_leads.id],
            probabilities=[10],
            count=30,
        )
        self.assertEqual(
            existing_leads.team_id, self.sales_team_1, "Team should have lower sequence"
        )
        existing_leads.flush_recordset()

        self.sales_team_1_m1.invalidate_model(["lead_month_count", "lead_day_count"])
        self.assertEqual(self.sales_team_1_m1.lead_month_count, 30)
        self.assertEqual(self.sales_team_1_m1.lead_day_count, 30)

        self.assertEqual(
            self.sales_team_1_m1._get_assignment_quota(),
            -28,
            "Assignment quota: 45 max -> 2 daily ; 30 daily lead already assign -> 2 - 30 -> -28",
        )
        self.assertEqual(
            self.sales_team_1_m1._get_assignment_quota(True),
            2,
            "Assignment quota: 45 max ignoring existing daily lead -> 2",
        )

    def test_assign_specific_won_lost(self):
        leads = self._create_leads_batch(
            lead_type="lead",
            user_ids=[False],
            partner_ids=[False, False, False, self.contact_1.id],
            probabilities=[30],
            count=6,
        )
        leads[0].stage_id = self.stage_gen_won.id
        leads[1].stage_id = False
        leads[2].update({"stage_id": False, "probability": 0})
        leads[3].update({"stage_id": False, "probability": False})
        leads[4].active = False
        leads[5].update(
            {
                "team_id": self.sales_team_convert.id,
                "user_id": self.user_sales_manager.id,
            }
        )

        leads.flush_recordset()

        self.sales_team_1.team_member_ids.write({"lead_assignment_max": 45})
        with self.with_user("user_sales_manager"):
            self.env["team.team"].browse(self.sales_team_1.ids)._action_assign_leads()

        self.assertEqual(
            leads[0].team_id, self.env["team.team"], "Won lead should not be assigned"
        )
        self.assertEqual(
            leads[0].user_id, self.env["res.users"], "Won lead should not be assigned"
        )
        for lead in leads[1:4]:
            self.assertIn(lead.user_id, self.sales_team_1.member_ids)
            self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(
            leads[4].team_id, self.env["team.team"], "Lost lead should not be assigned"
        )
        self.assertEqual(
            leads[4].user_id, self.env["res.users"], "Lost lead should not be assigned"
        )
        self.assertEqual(
            leads[5].team_id,
            self.sales_team_convert,
            "Assigned lead should not be reassigned",
        )
        self.assertEqual(
            leads[5].user_id,
            self.user_sales_manager,
            "Assigned lead should not be reassigned",
        )

    def test_assign_team_and_salesperson_on_duplicate_lead(self):
        duplicate_lead = (
            self.env["crm.lead"]
            .create(
                {
                    "name": "Test Lead",
                    "type": "opportunity",
                    "probability": 15,
                    "partner_id": self.contact_1.id,
                    "team_id": False,
                    "user_id": False,
                }
            )
            .copy()
        )
        self.assertFalse(duplicate_lead.date_open)

        sales_team = self.sales_team_1
        sales_team.lead_assignment_domain = [("user_id", "=", False)]
        with self.with_user("user_sales_manager"):
            sales_team._action_assign_leads()

        self.assertEqual(duplicate_lead.team_id, sales_team)
        self.assertTrue(duplicate_lead.user_id)

    @mute_logger("odoo.models.unlink")
    def test_merge_assign_keep_master_team(self):
        sales_team_dupe = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Sales Team Dupe",
                "sequence": 15,
                "lead_alias_name": False,
                "use_leads": True,
                "use_opportunities": True,
                "company_id": False,
                "user_id": False,
                "lead_assignment_domain": "[]",
            }
        )
        self.env["team.member"].create(
            {
                "user_id": self.user_sales_salesman.id,
                "team_id": sales_team_dupe.id,
                "lead_assignment_max": 10,
                "lead_assignment_domain": "[]",
            }
        )

        master_opp = self.env["crm.lead"].create(
            {
                "name": "Master",
                "type": "opportunity",
                "probability": 50,
                "partner_id": self.contact_1.id,
                "team_id": self.sales_team_1.id,
                "user_id": self.user_sales_manager.id,
            }
        )
        dupe_lead = self.env["crm.lead"].create(
            {
                "name": "Dupe",
                "type": "lead",
                "email_from": "Duplicate Email <%s>" % master_opp.email_normalized,
                "probability": 10,
                "team_id": False,
                "user_id": False,
            }
        )

        sales_team_dupe._action_assign_leads()
        self.assertFalse(dupe_lead.exists())
        self.assertEqual(
            master_opp.team_id,
            self.sales_team_1,
            "Opportunity: should keep its sales team",
        )
        self.assertEqual(
            master_opp.user_id,
            self.user_sales_manager,
            "Opportunity: should keep its salesman",
        )

    def test_no_assign_if_exceed_max_assign(self):
        leads = self._create_leads_batch(lead_type="lead", user_ids=[False], count=1)

        sales_team_4 = self.env["team.team"].create(
            {
                "use_sale": True,
                "name": "Sales Team 4",
                "sequence": 15,
                "use_leads": True,
            }
        )
        sales_team_4_m1 = self.env["team.member"].create(
            {
                "user_id": self.user_sales_salesman.id,
                "team_id": sales_team_4.id,
                "lead_assignment_max": 30,
            }
        )

        sales_team_4_m1.lead_month_count = 30
        sales_team_4_m1.lead_day_count = 2
        leads.team_id = sales_team_4.id

        members_data = sales_team_4._update_members_with_leads()
        self.assertFalse(
            members_data,
            "If team member has lead count greater than max assign,then do not assign any more",
        )
