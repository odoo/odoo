from datetime import timedelta

from odoo import exceptions, tools
from odoo.fields import Date
from odoo.tests import Form, tagged, users
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class CrmPlsCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_main = cls.env.user.company_id
        cls.user_sales_manager = mail_new_test_user(
            cls.env,
            login="user_sales_manager",
            name="Martin PLS Sales Manager",
            email="crm_manager@test.example.com",
            company_id=cls.company_main.id,
            notification_type="inbox",
            groups="sale.group_sale_manager,base.group_partner_manager",
        )

        cls.pls_team = cls.env["team.team"].create(
            {
                "use_sale": True,
                "name": "PLS Team",
            }
        )

        cls.env["crm.lead"].with_context({"active_test": False}).search([]).unlink()
        cls.env["crm.lead.scoring.frequency"].search([]).unlink()
        cls.cr.flush()

    def _prepare_test_lead_values(
        self,
        team_id,
        name_suffix,
        country_id,
        state_id,
        email_state,
        phone_state,
        source_id,
        stage_id,
    ):
        return {
            "name": "lead_" + name_suffix,
            "stage_id": stage_id,
            "team_id": team_id,
            "type": "opportunity",
            "email_state": email_state,
            "phone_state": phone_state,
            "country_id": country_id,
            "state_id": state_id,
            "source_id": source_id,
        }

    def _generate_leads_with_tags(self, tag_ids):
        team_id = (
            self.env["team.team"]
            .create(
                {
                    "use_sale": True,
                    "name": "blup",
                }
            )
            .id
        )

        leads_to_create = []
        for i in range(150):
            if i < 50:
                leads_to_create.append(
                    {
                        "name": "lead_tag_%s" % str(i),
                        "tag_ids": [(4, tag_ids[0])],
                        "team_id": team_id,
                    }
                )
            elif i < 100:
                leads_to_create.append(
                    {
                        "name": "lead_tag_%s" % str(i),
                        "tag_ids": [(4, tag_ids[1])],
                        "team_id": team_id,
                    }
                )
            else:
                leads_to_create.append(
                    {
                        "name": "lead_tag_%s" % str(i),
                        "tag_ids": [(6, 0, tag_ids)],
                        "team_id": team_id,
                    }
                )

        leads_with_tags = self.env["crm.lead"].create(leads_to_create)

        return leads_with_tags


@tagged("post_install", "-at_install", "crm_lead_pls")
class TestConfig(CrmPlsCommon):
    def test_crm_lead_pls_update(self):
        frequency_fields = self.env["crm.lead.scoring.frequency.field"].search([])
        pls_fields_str = ",".join(frequency_fields.mapped("field_id.name"))
        pls_start_date_str = "2021-01-01"
        IrConfigSudo = self.env["ir.config_parameter"].sudo()
        IrConfigSudo.set_param("crm.pls_start_date", pls_start_date_str)
        IrConfigSudo.set_param("crm.pls_fields", pls_fields_str)

        date_to_update = "2021-02-02"
        fields_to_remove = frequency_fields.filtered(
            lambda f: f.field_id.name in ["source_id", "lang_id"]
        )
        fields_after_updation_str = ",".join(
            (frequency_fields - fields_to_remove).mapped("field_id.name")
        )

        pls_update_wizard = Form(self.env["crm.lead.pls.update"])
        with pls_update_wizard:
            self.assertEqual(
                Date.to_string(pls_update_wizard.pls_start_date),
                pls_start_date_str,
                "Correct date is taken from config",
            )
            self.assertEqual(
                ",".join([f.field_id.name for f in pls_update_wizard.pls_fields]),
                pls_fields_str,
                "Correct fields are taken from config",
            )
            pls_update_wizard.pls_start_date = date_to_update
            for field in fields_to_remove:
                pls_update_wizard.pls_fields.remove(field.id)

        pls_update_wizard0 = pls_update_wizard.save()
        pls_update_wizard0.action_update_crm_lead_probabilities()

        self.assertEqual(
            IrConfigSudo.get_param("crm.pls_start_date"),
            date_to_update,
            "Correct date is updated in config",
        )
        self.assertEqual(
            IrConfigSudo.get_param("crm.pls_fields"),
            fields_after_updation_str,
            "Correct fields are updated in config",
        )

    def test_settings_pls_start_date(self):
        str_date_8_days_ago = Date.to_string(Date.today() - timedelta(days=8))

        for value, expected in [
            ("2021-10-10", "2021-10-10"),
            ("", str_date_8_days_ago),
            (
                "One does not simply walk into system parameters to corrupt them",
                str_date_8_days_ago,
            ),
        ]:
            with self.subTest(value=value):
                self.env["ir.config_parameter"].sudo().set_param(
                    "crm.pls_start_date", value
                )
                res_config_new = self.env["res.config.settings"].new()
                self.assertEqual(
                    Date.to_string(res_config_new.predictive_lead_scoring_start_date),
                    expected,
                )


@tagged("post_install", "-at_install", "crm_lead_pls")
class TestCrmPls(CrmPlsCommon):
    def test_predictive_lead_scoring(self):
        Lead = self.env["crm.lead"]
        LeadScoringFrequency = self.env["crm.lead.scoring.frequency"]
        state_values = ["correct", "incorrect", None]
        source_ids = self.env["utm.source"].search([], limit=3).ids
        state_ids = self.env["res.country.state"].search([], limit=3).ids
        country_ids = self.env["res.country"].search([], limit=3).ids
        stage_ids = self.env["crm.stage"].search([], limit=3).ids
        won_stage_id = self.env["crm.stage"].search([("is_won", "=", True)], limit=1).id
        team_ids = (
            self.env["team.team"]
            .create(
                [
                    {"use_sale": True, "name": "Team Test 1"},
                    {"use_sale": True, "name": "Team Test 2"},
                    {"use_sale": True, "name": "Team Test 3"},
                ]
            )
            .ids
        )
        leads_to_create = []
        for i in range(3):
            leads_to_create.append(
                self._prepare_test_lead_values(
                    team_ids[0],
                    "team_1_%s" % str(i),
                    country_ids[i],
                    state_ids[i],
                    state_values[i],
                    state_values[i],
                    source_ids[i],
                    stage_ids[i],
                )
            )
        leads_to_create.append(
            self._prepare_test_lead_values(
                team_ids[0],
                "team_1_%s" % str(3),
                country_ids[0],
                state_ids[1],
                state_values[2],
                state_values[0],
                source_ids[2],
                stage_ids[1],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                team_ids[0],
                "team_1_%s" % str(4),
                country_ids[1],
                state_ids[1],
                state_values[1],
                state_values[0],
                source_ids[1],
                stage_ids[0],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                team_ids[1],
                "team_2_%s" % str(5),
                country_ids[0],
                state_ids[1],
                state_values[2],
                state_values[0],
                source_ids[1],
                stage_ids[2],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                team_ids[1],
                "team_2_%s" % str(6),
                country_ids[0],
                state_ids[1],
                state_values[0],
                state_values[1],
                source_ids[2],
                stage_ids[1],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                team_ids[1],
                "team_2_%s" % str(7),
                country_ids[0],
                state_ids[2],
                state_values[0],
                state_values[1],
                source_ids[2],
                stage_ids[0],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                team_ids[1],
                "team_2_%s" % str(8),
                country_ids[0],
                state_ids[1],
                state_values[2],
                state_values[0],
                source_ids[2],
                stage_ids[1],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                team_ids[1],
                "team_2_%s" % str(9),
                country_ids[1],
                state_ids[0],
                state_values[1],
                state_values[0],
                source_ids[1],
                stage_ids[1],
            )
        )

        leads_to_create.append(
            self._prepare_test_lead_values(
                False,
                "no_team_%s" % str(10),
                country_ids[1],
                state_ids[1],
                state_values[2],
                state_values[0],
                source_ids[1],
                stage_ids[2],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                False,
                "no_team_%s" % str(11),
                country_ids[0],
                state_ids[1],
                state_values[1],
                state_values[1],
                source_ids[0],
                stage_ids[0],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                False,
                "no_team_%s" % str(12),
                country_ids[1],
                state_ids[2],
                state_values[0],
                state_values[1],
                source_ids[2],
                stage_ids[0],
            )
        )
        leads_to_create.append(
            self._prepare_test_lead_values(
                False,
                "no_team_%s" % str(13),
                country_ids[0],
                state_ids[1],
                state_values[2],
                state_values[0],
                source_ids[2],
                stage_ids[1],
            )
        )

        leads = Lead.create(leads_to_create)

        existing_leads = Lead.with_context({"active_filter": False}).search([])
        self.assertEqual(existing_leads, leads)
        self.assertEqual(
            existing_leads.filtered(lambda lead: not lead.team_id), leads[-4::]
        )

        leads[-4::].team_id = team_ids[2]

        self.env["ir.config_parameter"].sudo().set_param(
            "crm.pls_start_date", "2000-01-01"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "crm.pls_fields",
            "country_id,state_id,email_state,phone_state,source_id,tag_ids",
        )

        leads[0].action_set_lost()
        leads[1].action_set_lost()
        leads[2].action_set_won()
        leads[5].action_set_lost()
        leads[6].action_set_lost()
        leads[7].action_set_won()
        leads[10].action_set_won()
        leads[11].action_set_lost()
        leads[12].action_set_lost()

        Lead._cron_update_automated_probabilities()

        self.env.invalidate_all()

        self.assertEqual(
            tools.float_compare(leads[3].automated_probability, 33.49, 2), 0
        )
        self.assertEqual(
            tools.float_compare(leads[8].automated_probability, 7.74, 2), 0
        )
        lead_13_team_3_proba = leads[13].automated_probability
        self.assertEqual(tools.float_compare(lead_13_team_3_proba, 35.09, 2), 0)

        leads[-4::].write({"team_id": False})
        leads[-4::].flush_recordset()

        Lead._cron_update_automated_probabilities()
        lead_13_no_team_proba = leads[13].automated_probability
        self.assertTrue(
            lead_13_team_3_proba != leads[13].automated_probability,
            "Probability for leads with no team should be different than if they where in their own team.",
        )
        self.assertAlmostEqual(lead_13_no_team_proba, 35.19, places=2)

        lead_4_stage_0_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[4].team_id.id),
                ("variable", "=", "stage_id"),
                ("value", "=", stage_ids[0]),
            ]
        )
        lead_4_stage_won_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[4].team_id.id),
                ("variable", "=", "stage_id"),
                ("value", "=", won_stage_id),
            ]
        )
        lead_4_country_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[4].team_id.id),
                ("variable", "=", "country_id"),
                ("value", "=", leads[4].country_id.id),
            ]
        )
        lead_4_email_state_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[4].team_id.id),
                ("variable", "=", "email_state"),
                ("value", "=", str(leads[4].email_state)),
            ]
        )

        lead_9_stage_0_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[9].team_id.id),
                ("variable", "=", "stage_id"),
                ("value", "=", stage_ids[0]),
            ]
        )
        lead_9_stage_won_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[9].team_id.id),
                ("variable", "=", "stage_id"),
                ("value", "=", won_stage_id),
            ]
        )
        lead_9_country_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[9].team_id.id),
                ("variable", "=", "country_id"),
                ("value", "=", leads[9].country_id.id),
            ]
        )
        lead_9_email_state_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[9].team_id.id),
                ("variable", "=", "email_state"),
                ("value", "=", str(leads[9].email_state)),
            ]
        )

        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)
        self.assertEqual(lead_4_country_freq.won_count, 0.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)

        self.assertEqual(lead_9_stage_0_freq.won_count, 1.1)
        self.assertEqual(lead_9_stage_won_freq.won_count, 1.1)
        self.assertEqual(lead_9_country_freq.won_count, 0.0)
        self.assertEqual(lead_9_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_9_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_9_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_9_country_freq.lost_count, 0.0)
        self.assertEqual(lead_9_email_state_freq.lost_count, 2.1)

        leads[4].action_set_lost()
        leads[9].action_set_won()

        lead_9_country_freq = LeadScoringFrequency.search(
            [
                ("team_id", "=", leads[9].team_id.id),
                ("variable", "=", "country_id"),
                ("value", "=", leads[9].country_id.id),
            ]
        )

        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)
        self.assertEqual(lead_4_country_freq.won_count, 0.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 3.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 2.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 3.1)

        self.assertEqual(lead_9_stage_0_freq.won_count, 2.1)
        self.assertEqual(lead_9_stage_won_freq.won_count, 2.1)
        self.assertEqual(lead_9_country_freq.won_count, 1.1)
        self.assertEqual(lead_9_email_state_freq.won_count, 2.1)
        self.assertEqual(lead_9_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_9_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_9_country_freq.lost_count, 0.1)
        self.assertEqual(lead_9_email_state_freq.lost_count, 2.1)

        self.assertEqual(
            tools.float_compare(leads[3].automated_probability, 33.49, 2), 0
        )
        self.assertEqual(
            tools.float_compare(leads[8].automated_probability, 7.74, 2), 0
        )

        self.assertEqual(leads[3].is_automated_probability, True)
        self.assertEqual(leads[8].is_automated_probability, True)

        leads[4].action_unarchive()
        self.assertEqual(leads[4].won_status, "pending")
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)
        self.assertEqual(lead_4_country_freq.won_count, 0.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)

        self.assertEqual(lead_9_stage_0_freq.won_count, 2.1)
        self.assertEqual(lead_9_stage_won_freq.won_count, 2.1)
        self.assertEqual(lead_9_country_freq.won_count, 1.1)
        self.assertEqual(lead_9_email_state_freq.won_count, 2.1)
        self.assertEqual(lead_9_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_9_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_9_country_freq.lost_count, 0.1)
        self.assertEqual(lead_9_email_state_freq.lost_count, 2.1)

        leads[4].stage_id = won_stage_id
        self.assertEqual(leads[4].won_status, "won")
        self.assertEqual(lead_4_stage_0_freq.won_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 2.1)
        self.assertEqual(lead_4_country_freq.won_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 2.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)

        leads[4].action_archive()
        self.assertEqual(leads[4].won_status, "won")
        self.assertEqual(lead_4_stage_0_freq.won_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 2.1)
        self.assertEqual(lead_4_country_freq.won_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 2.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)

        leads[4].stage_id = stage_ids[0]
        self.assertEqual(leads[4].won_status, "pending")
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)
        self.assertEqual(lead_4_country_freq.won_count, 0.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)

        leads[4].probability = 0
        self.assertEqual(leads[4].won_status, "lost")
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)
        self.assertEqual(lead_4_country_freq.won_count, 0.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 3.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 2.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 3.1)

        leads[4].action_unarchive()
        self.assertEqual(leads[4].won_status, "pending")
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)
        self.assertEqual(lead_4_country_freq.won_count, 0.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)

        leads[3].stage_id = stage_ids[0]
        leads[8].stage_id = stage_ids[0]

        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)
        self.assertEqual(lead_4_country_freq.won_count, 0.1)
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)

        self.assertEqual(lead_9_stage_0_freq.won_count, 2.1)
        self.assertEqual(lead_9_stage_won_freq.won_count, 2.1)
        self.assertEqual(lead_9_country_freq.won_count, 1.1)
        self.assertEqual(lead_9_email_state_freq.won_count, 2.1)
        self.assertEqual(lead_9_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_9_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_9_country_freq.lost_count, 0.1)
        self.assertEqual(lead_9_email_state_freq.lost_count, 2.1)

        leads[3].probability = 40

        self.assertEqual(leads[3].is_automated_probability, False)
        self.assertEqual(leads[8].is_automated_probability, True)

        self.assertEqual(
            tools.float_compare(leads[3].automated_probability, 20.87, 2), 0
        )
        self.assertEqual(
            tools.float_compare(leads[8].automated_probability, 2.43, 2), 0
        )
        self.assertEqual(tools.float_compare(leads[3].probability, 40, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].probability, 2.43, 2), 0)

        leads[8].country_id = country_ids[1]
        self.assertEqual(
            tools.float_compare(leads[8].automated_probability, 34.38, 2), 0
        )
        self.assertEqual(tools.float_compare(leads[8].probability, 34.38, 2), 0)

        leads[8].country_id = country_ids[0]
        self.assertEqual(
            tools.float_compare(leads[8].automated_probability, 2.43, 2), 0
        )
        self.assertEqual(tools.float_compare(leads[8].probability, 2.43, 2), 0)

        tag_ids = (
            self.env["crm.tag"]
            .create(
                [
                    {"name": "Tag_test_1"},
                    {"name": "Tag_test_2"},
                ]
            )
            .ids
        )
        leads_with_tags = self._generate_leads_with_tags(tag_ids)

        leads_with_tags[:30].action_set_lost()
        leads_with_tags[31:50].action_set_won()
        leads_with_tags[50:90].action_set_lost()
        leads_with_tags[91:100].action_set_won()
        leads_with_tags[100:135].action_set_lost()
        leads_with_tags[136:150].action_set_won()

        tag_1_freq = LeadScoringFrequency.search(
            [("variable", "=", "tag_id"), ("value", "=", tag_ids[0])]
        )
        tag_2_freq = LeadScoringFrequency.search(
            [("variable", "=", "tag_id"), ("value", "=", tag_ids[1])]
        )
        self.assertEqual(tools.float_compare(tag_1_freq.won_count, 33.1, 1), 0)
        self.assertEqual(tools.float_compare(tag_1_freq.lost_count, 65.1, 1), 0)
        self.assertEqual(tools.float_compare(tag_2_freq.won_count, 23.1, 1), 0)
        self.assertEqual(tools.float_compare(tag_2_freq.lost_count, 75.1, 1), 0)

        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        lead_tag_1 = leads_with_tags[30]
        lead_tag_2 = leads_with_tags[90]
        lead_tag_1_2 = leads_with_tags[135]

        self.assertEqual(
            tools.float_compare(lead_tag_1.automated_probability, 33.69, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_2.automated_probability, 23.51, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_1_2.automated_probability, 28.05, 2), 0
        )

        lead_tag_1.tag_ids = [(5, 0, 0)]
        lead_tag_1_2.tag_ids = [(3, tag_ids[1], 0)]

        self.assertEqual(
            tools.float_compare(lead_tag_1.automated_probability, 28.6, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_2.automated_probability, 23.51, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_1_2.automated_probability, 33.69, 2), 0
        )

        lead_tag_1.tag_ids = [(4, tag_ids[1])]
        lead_tag_2.tag_ids = [(4, tag_ids[0])]
        lead_tag_1_2.tag_ids = [(3, tag_ids[0]), (4, tag_ids[1])]

        self.assertEqual(
            tools.float_compare(lead_tag_1.automated_probability, 23.51, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_2.automated_probability, 28.05, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_1_2.automated_probability, 23.51, 2), 0
        )

        lead_tag_1.tag_ids = [(3, tag_ids[1]), (4, tag_ids[0])]
        lead_tag_2.tag_ids = [(3, tag_ids[0])]
        lead_tag_1_2.tag_ids = [(4, tag_ids[0])]

        self.assertEqual(
            tools.float_compare(lead_tag_1.automated_probability, 33.69, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_2.automated_probability, 23.51, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_1_2.automated_probability, 28.05, 2), 0
        )

        leads.filtered(lambda lead: lead.id % 2 == 0).email_state = "correct"
        leads.filtered(lambda lead: lead.id % 2 == 1).email_state = "incorrect"
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        self.assertEqual(
            tools.float_compare(leads[3].automated_probability, 4.21, 2), 0
        )
        self.assertEqual(
            tools.float_compare(leads[8].automated_probability, 0.23, 2), 0
        )

        self.env["ir.config_parameter"].sudo().set_param("crm.pls_fields", False)
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        self.assertEqual(
            tools.float_compare(leads[3].automated_probability, 34.38, 2), 0
        )
        self.assertEqual(
            tools.float_compare(leads[8].automated_probability, 50.0, 2), 0
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "crm.pls_fields", "country_id,state_id,email_state,phone_state,source_id"
        )
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        self.assertEqual(
            tools.float_compare(leads[3].automated_probability, 4.21, 2), 0
        )
        self.assertEqual(
            tools.float_compare(leads[8].automated_probability, 0.23, 2), 0
        )

        self.assertEqual(
            tools.float_compare(lead_tag_1.automated_probability, 28.6, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_2.automated_probability, 28.6, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_1_2.automated_probability, 28.6, 2), 0
        )

        lead_tag_1.tag_ids = [(5, 0, 0)]
        lead_tag_2.tag_ids = [(4, tag_ids[0])]
        lead_tag_1_2.tag_ids = [(3, tag_ids[1], 0)]

        self.assertEqual(
            tools.float_compare(lead_tag_1.automated_probability, 28.6, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_2.automated_probability, 28.6, 2), 0
        )
        self.assertEqual(
            tools.float_compare(lead_tag_1_2.automated_probability, 28.6, 2), 0
        )

    def test_predictive_lead_scoring_always_won(self):
        Lead = self.env["crm.lead"]
        LeadScoringFrequency = self.env["crm.lead.scoring.frequency"]
        country_id = self.env["res.country"].search([], limit=1).id
        stage_id = self.env["crm.stage"].search([], limit=1).id
        team_id = (
            self.env["team.team"].create({"use_sale": True, "name": "Team Test 1"}).id
        )
        leads = Lead.create(
            [
                self._prepare_test_lead_values(
                    team_id,
                    "edge pending",
                    country_id,
                    False,
                    False,
                    False,
                    False,
                    stage_id,
                ),
                self._prepare_test_lead_values(
                    team_id,
                    "edge lost",
                    country_id,
                    False,
                    False,
                    False,
                    False,
                    stage_id,
                ),
                self._prepare_test_lead_values(
                    team_id,
                    "edge won",
                    country_id,
                    False,
                    False,
                    False,
                    False,
                    stage_id,
                ),
            ]
        )
        leads.tag_ids = self.env["crm.tag"].create({"name": "lead scoring edge case"})

        self.env["ir.config_parameter"].sudo().set_param(
            "crm.pls_start_date", "2000-01-01"
        )
        self.env["ir.config_parameter"].sudo().set_param("crm.pls_fields", "country_id")

        leads[1].action_set_lost()
        leads[2].action_set_won()

        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        freq_stage = LeadScoringFrequency.search(
            [("variable", "=", "stage_id"), ("value", "=", str(stage_id))]
        )
        freq_tag = LeadScoringFrequency.search(
            [("variable", "=", "tag_id"), ("value", "=", str(leads.tag_ids.id))]
        )
        freqs = freq_stage + freq_tag

        freqs.write({"won_count": 10000000, "lost_count": 1})
        leads._compute_probabilities()
        self.assertEqual(tools.float_compare(leads[2].probability, 100, 2), 0)
        self.assertEqual(tools.float_compare(leads[1].probability, 0, 2), 0)
        self.assertEqual(tools.float_compare(leads[0].probability, 99.99, 2), 0)

        freqs.write({"won_count": 1, "lost_count": 10000000})
        leads._compute_probabilities()
        self.assertEqual(tools.float_compare(leads[2].probability, 100, 2), 0)
        self.assertEqual(tools.float_compare(leads[1].probability, 0, 2), 0)
        self.assertEqual(tools.float_compare(leads[0].probability, 0.01, 2), 0)

    def test_pls_no_share_stage(self):
        Lead = self.env["crm.lead"]
        team_id = (
            self.env["team.team"].create([{"use_sale": True, "name": "Team Test"}]).id
        )
        self.env["crm.stage"].search([("team_ids", "=", False)]).write(
            {"team_ids": [team_id]}
        )
        lead = Lead.create({"name": "team", "team_id": team_id, "probability": 41.23})
        Lead._cron_update_automated_probabilities()
        self.assertEqual(tools.float_compare(lead.probability, 41.23, 2), 0)
        self.assertEqual(tools.float_compare(lead.automated_probability, 0, 2), 0)

    def test_pls_tooltip_data(self):
        Lead = self.env["crm.lead"]
        self.env["ir.config_parameter"].sudo().set_param(
            "crm.pls_fields", "country_id,state_id,email_state,phone_state,source_id"
        )
        country_ids = self.env["res.country"].search([], limit=2).ids
        source_ids = self.env["utm.source"].search([], limit=2).ids
        stage_ids = self.env["crm.stage"].search([], limit=3).ids
        state_ids = self.env["res.country.state"].search([], limit=2).ids
        team_id = (
            self.env["team.team"]
            .create([{"use_sale": True, "name": "Team Tooltip"}])
            .id
        )
        leads = Lead.create(
            [
                self._prepare_test_lead_values(
                    team_id,
                    "lead Won A",
                    country_ids[0],
                    state_ids[0],
                    False,
                    False,
                    source_ids[1],
                    stage_ids[0],
                ),
                self._prepare_test_lead_values(
                    team_id,
                    "lead Won B",
                    country_ids[1],
                    state_ids[0],
                    False,
                    False,
                    False,
                    stage_ids[0],
                ),
                self._prepare_test_lead_values(
                    team_id,
                    "lead Lost C",
                    False,
                    False,
                    False,
                    False,
                    source_ids[0],
                    stage_ids[0],
                ),
                self._prepare_test_lead_values(
                    team_id,
                    "lead Lost D",
                    country_ids[0],
                    False,
                    False,
                    False,
                    source_ids[0],
                    stage_ids[0],
                ),
                self._prepare_test_lead_values(
                    team_id,
                    "lead Lost E",
                    False,
                    state_ids[1],
                    False,
                    False,
                    False,
                    stage_ids[2],
                ),
                self._prepare_test_lead_values(
                    team_id,
                    "lead Tooltip",
                    country_ids[0],
                    state_ids[0],
                    False,
                    False,
                    source_ids[0],
                    stage_ids[1],
                ),
            ]
        )

        leads.email_state = "correct"
        (leads[0] | leads[1] | leads[4] | leads[5]).phone_state = "correct"
        (leads[2] | leads[3]).phone_state = "incorrect"

        leads[:2].action_set_won()
        leads[2:5].action_set_lost()
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        expected_low_3 = ["source_id", "country_id"]
        expected_top_3 = ["state_id", "phone_state", "stage_id"]

        tooltip_data = leads[5].update_and_get_pls_tooltip_data()
        self.assertEqual("Team Tooltip", tooltip_data["team_name"])
        self.assertEqual(tools.float_compare(tooltip_data["probability"], 74.30, 2), 0)

        self.assertListEqual(
            [top_entry.get("field") for top_entry in tooltip_data["top_3_data"]],
            expected_top_3,
        )
        self.assertListEqual(
            [low_entry.get("field") for low_entry in tooltip_data["low_3_data"]],
            expected_low_3,
        )

        self.env["ir.config_parameter"].sudo().set_param(
            "crm.pls_fields", "email_state,phone_state"
        )

        leads[5].phone_state = False
        leads[5].email_state = "incorrect"
        leads[:2].phone_state = False
        leads[:2].email_state = "incorrect"
        leads[2:5].phone_state = "correct"
        leads[2:5].email_state = "correct"
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        tooltip_data = leads[5].update_and_get_pls_tooltip_data()
        self.assertEqual(
            ["stage_id"], [entry["field"] for entry in tooltip_data["top_3_data"]]
        )
        self.assertFalse(tooltip_data["low_3_data"])

        leads[5].email_state = "correct"
        leads[5].phone_state = "incorrect"
        leads[:2].phone_state = "incorrect"
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        tooltip_data = leads[5].update_and_get_pls_tooltip_data()
        self.assertEqual(
            ["stage_id"], [entry["field"] for entry in tooltip_data["top_3_data"]]
        )
        self.assertFalse(tooltip_data["low_3_data"])


@tagged("post_install", "-at_install", "crm_lead_pls")
class TestCrmPlsTeamPriors(CrmPlsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "crm.pls_start_date", "2000-01-01"
        )
        cls.env["ir.config_parameter"].sudo().set_param("crm.pls_fields", "country_id")
        cls.env.registry.setup_models(cls.env.cr, ["crm.lead"])
        cls.country = cls.env.ref("base.be")

        cls.env["crm.stage"].search([]).write({"sequence": 9999})
        cls.stage_generic = cls.env["crm.stage"].create(
            {
                "name": "Generic New",
                "sequence": 50,
                "team_ids": False,
            }
        )
        cls.team_healthy, cls.team_unscoreable = cls.env["team.team"].create(
            [
                {"use_sale": True, "name": "Healthy Team"},
                {"use_sale": True, "name": "Unscoreable Team"},
            ]
        )
        cls.stage_healthy, cls.stage_healthy_won, cls.stage_unscoreable = cls.env[
            "crm.stage"
        ].create(
            [
                {"name": "H New", "sequence": 1, "team_ids": [cls.team_healthy.id]},
                {
                    "name": "H Won",
                    "sequence": 10,
                    "team_ids": [cls.team_healthy.id],
                    "is_won": True,
                },
                {"name": "U New", "sequence": 1, "team_ids": [cls.team_unscoreable.id]},
            ]
        )

    def _new_lead(self, team, stage, name):
        return self.env["crm.lead"].create(
            {
                "country_id": self.country.id,
                "name": name,
                "stage_id": stage.id,
                "team_id": team.id,
                "type": "opportunity",
            }
        )

    @users("user_sales_manager")
    def test_pls_unscoreable_team_does_not_inherit_another_team_prior(self):
        for index in range(6):
            self._new_lead(
                self.team_healthy, self.stage_healthy, f"won_{index}"
            ).action_set_won()
        self._new_lead(self.team_healthy, self.stage_healthy, "lost").action_set_lost()
        for index in range(4):
            self._new_lead(
                self.team_unscoreable, self.stage_unscoreable, f"lost_{index}"
            ).action_set_lost()
        self.env.flush_all()

        frequencies = self.env["crm.lead.scoring.frequency"].search(
            [
                ("team_id", "=", self.team_unscoreable.id),
                ("value", "=", str(self.stage_generic.id)),
                ("variable", "=", "stage_id"),
            ]
        )
        self.assertFalse(
            frequencies,
            "Precondition: the unscoreable team has no row for the reference stage",
        )

        healthy = self._new_lead(self.team_healthy, self.stage_healthy, "probe_healthy")
        first, second = (
            self._new_lead(self.team_unscoreable, self.stage_unscoreable, "probe_1"),
            self._new_lead(self.team_unscoreable, self.stage_unscoreable, "probe_2"),
        )
        self.env.flush_all()

        for label, leads in (
            ("alone", first),
            ("after a scoreable team", healthy + first + second),
            ("among themselves", first + second),
        ):
            with self.subTest(order=label):
                self.env.invalidate_all()
                probabilities, _tooltip = leads._pls_get_naive_bayes_probabilities()
                for lead in leads & (first + second):
                    self.assertNotIn(
                        lead.id,
                        probabilities,
                        f"{lead.name} belongs to a team PLS cannot score, so it must be "
                        f"left alone whatever else is in the recordset ({label})",
                    )

    @users("user_sales_manager")
    def test_pls_probabilities_of_an_empty_recordset(self):
        probabilities, tooltip = (
            self.env["crm.lead"].browse()._pls_get_naive_bayes_probabilities()
        )
        self.assertEqual(probabilities, {})
        self.assertEqual(tooltip, {})


class TestCrmPlsSides(CrmPlsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env["team.team"].create(
            [{"use_sale": True, "name": "Team Test"}]
        )
        cls.stage_new, cls.stage_in_progress, cls.stage_won = cls.env[
            "crm.stage"
        ].create(
            [
                {
                    "name": "New Stage",
                    "sequence": 1,
                    "team_ids": [cls.team.id],
                },
                {
                    "name": "In Progress Stage",
                    "sequence": 2,
                    "team_ids": [cls.team.id],
                },
                {
                    "is_won": True,
                    "name": "Won Stage",
                    "sequence": 3,
                    "team_ids": [cls.team.id],
                },
            ]
        )

    @users("user_sales_manager")
    def test_stage_update(self):
        team_id = self.team.with_user(self.env.user).id
        stage_new, _stage_in_progress, stage_won = (
            self.stage_new + self.stage_in_progress + self.stage_won
        ).with_user(self.env.user)
        leads = self.env["crm.lead"].create(
            [
                {
                    "name": "Test Lead 1",
                    "probability": 50,
                    "stage_id": stage_new.id,
                    "team_id": team_id,
                },
                {
                    "name": "Test Lead 2",
                    "probability": 50,
                    "stage_id": stage_new.id,
                    "team_id": team_id,
                },
            ]
        )
        leads.action_set_lost()
        for lead in leads:
            self.assertFalse(lead.active)
            self.assertFalse(lead.probability)
        leads[0].active = True

        leads.write({"stage_id": stage_won.id})
        for lead in leads:
            self.assertTrue(lead.active)
            self.assertEqual(lead.probability, 100)

    @users("user_sales_manager")
    def test_won_lost_validity(self):
        team_id = self.team.with_user(self.env.user).id
        stage_new, stage_in_progress, stage_won = (
            self.stage_new + self.stage_in_progress + self.stage_won
        ).with_user(self.env.user)
        lead = self.env["crm.lead"].create(
            [
                {
                    "name": "Test Lead",
                    "probability": 50,
                    "stage_id": stage_new.id,
                    "team_id": team_id,
                }
            ]
        )
        self.assertEqual(lead.won_status, "pending")

        lead.write({"probability": 100})
        self.assertEqual(lead.won_status, "pending")

        lead.write({"probability": 90})
        self.assertEqual(lead.won_status, "pending")
        lead.action_set_won()
        self.assertEqual(lead.probability, 100)
        self.assertTrue(lead.stage_id.is_won)
        self.assertEqual(lead.won_status, "won")
        with self.assertRaises(
            exceptions.ValidationError, msg="A won lead cannot be set as lost."
        ):
            lead.action_set_lost()

        lead.write({"active": False})
        self.assertEqual(lead.probability, 100)
        self.assertEqual(lead.won_status, "won")
        with self.assertRaises(
            exceptions.ValidationError, msg="A won lead cannot have probability < 100"
        ):
            lead.write({"probability": 75})

        lead.write({"stage_id": stage_in_progress.id, "active": True})
        self.assertFalse(lead.probability == 100)
        self.assertEqual(lead.won_status, "pending")

        lead.action_set_lost()
        self.assertFalse(lead.active)
        self.assertEqual(lead.probability, 0)
        self.assertEqual(lead.won_status, "lost")

        lead.write({"stage_id": stage_won.id})
        self.assertTrue(lead.active)
        self.assertEqual(lead.probability, 100)
        self.assertEqual(lead.won_status, "won")

        lead.write({"active": False, "probability": 0, "stage_id": stage_new.id})
        self.assertEqual(lead.won_status, "lost")

        lead.write({"active": True})
        self.assertEqual(lead.won_status, "pending", "An active lead cannot be lost")

    @users("user_sales_manager")
    def test_team_unlink(self):
        pls_team = self.env["team.team"].browse(self.pls_team.ids)

        noteam_scoring_data = [
            ("stage_id", "1", 20, 10),
            ("stage_id", "2", 0.1, 0.1),
            ("stage_id", "3", 10, 0),
            ("country_id", "1", 10, 0.1),
        ]
        self.env["crm.lead.scoring.frequency"].sudo().create(
            [
                {
                    "lost_count": lost_count,
                    "team_id": False,
                    "value": value,
                    "variable": variable,
                    "won_count": won_count,
                }
                for variable, value, won_count, lost_count in noteam_scoring_data
            ]
        )

        team_scoring_data = [
            ("stage_id", "1", 20, 10),
            ("country_id", "1", 0.1, 10),
            ("country_id", "2", 0.1, 0),
            ("country_id", "3", 30, 30),
        ]
        existing_plsteam = (
            self.env["crm.lead.scoring.frequency"]
            .sudo()
            .create(
                [
                    {
                        "lost_count": lost_count,
                        "team_id": pls_team.id,
                        "value": value,
                        "variable": variable,
                        "won_count": won_count,
                    }
                    for variable, value, won_count, lost_count in team_scoring_data
                ]
            )
        )

        pls_team.unlink()

        final_noteam = [
            ("stage_id", "1", 40, 20),
            ("stage_id", "2", 0.1, 0.1),
            ("stage_id", "3", 10, 0),
            ("country_id", "1", 10, 10),
            ("country_id", "3", 30, 30),
        ]
        self.assertEqual(
            existing_plsteam.exists(),
            self.env["crm.lead.scoring.frequency"],
            "Frequencies of unlinked teams should be unlinked (cascade)",
        )
        existing_noteam = (
            self.env["crm.lead.scoring.frequency"]
            .sudo()
            .search(
                [
                    ("team_id", "=", False),
                    ("variable", "in", ["stage_id", "country_id"]),
                ]
            )
        )
        for frequency in existing_noteam:
            stat = next(
                item
                for item in final_noteam
                if item[0] == frequency.variable and item[1] == frequency.value
            )
            self.assertEqual(frequency.won_count, stat[2])
            self.assertEqual(frequency.lost_count, stat[3])
        self.assertEqual(len(existing_noteam), len(final_noteam))


@tagged("lead_manage", "crm_lead_pls")
class TestLeadLost(TestCrmCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lost_reason = cls.env["crm.lost.reason"].create({"name": "Test Reason"})

    @users("user_sales_salesman")
    def test_lead_lost(self):
        self.assertEqual(
            len(self.lead_1.message_ids), 1, "Should contain creation message"
        )
        creation_message = self.lead_1.message_ids[0]
        self.assertEqual(
            creation_message.subtype_id, self.env.ref("crm.mt_lead_create")
        )
        self.assertEqual(
            self.lead_1.message_partner_ids,
            self.user_sales_leads.partner_id,
            "Responsible should be follower",
        )

        with self.mock_mail_gateway():
            self.lead_1.with_user(self.user_sales_manager).write(
                {
                    "user_id": self.user_sales_salesman.id,
                    "probability": 32,
                }
            )
            self.flush_tracking()

        lead = self.env["crm.lead"].browse(self.lead_1.ids)
        self.assertFalse(lead.lost_reason_id)
        self.assertEqual(
            self.lead_1.message_partner_ids,
            self.user_sales_leads.partner_id + self.user_sales_salesman.partner_id,
            "New responsible should be follower",
        )
        self.assertEqual(lead.probability, 32)
        self.assertEqual(
            len(lead.message_ids), 2, "Should have tracked new responsible"
        )
        update_message = lead.message_ids[0]
        self.assertMessageFields(
            update_message,
            {
                "notified_partner_ids": self.env["res.partner"],
                "partner_ids": self.env["res.partner"],
                "subtype_id": self.env.ref("mail.mt_note"),
                "tracking_field_names": ["user_id"],
            },
        )

        lost_wizard = self.env["crm.lead.lost"].create(
            {
                "lead_ids": lead.ids,
                "lost_reason_id": self.lost_reason.id,
                "lost_feedback": "<p></p>",
            }
        )
        lost_wizard.action_lost_reason_apply()
        self.flush_tracking()

        self.assertFalse(lead.active)
        self.assertEqual(lead.automated_probability, 0)
        self.assertEqual(lead.lost_reason_id, self.lost_reason)
        self.assertEqual(lead.probability, 0)
        self.assertEqual(
            len(lead.message_ids),
            3,
            "Should have logged a tracking message for lost lead with reason",
        )
        lost_message = lead.message_ids[0]
        self.assertMessageFields(
            lost_message,
            {
                "notified_partner_ids": self.env["res.partner"],
                "partner_ids": self.env["res.partner"],
                "subtype_id": self.env.ref("crm.mt_lead_lost"),
                "tracking_field_names": ["active", "lost_reason_id", "won_status"],
                "tracking_values": [
                    ("active", "boolean", True, False),
                    ("lost_reason_id", "many2one", False, self.lost_reason),
                    ("won_status", "char", "Pending", "Lost"),
                ],
            },
        )

    @users("user_sales_leads")
    def test_lead_lost_batch_wfeedback(self):
        leads = self._create_leads_batch(
            lead_type="lead", count=10, probabilities=[10, 20, 30]
        )
        self.assertEqual(len(leads), 10)
        self.flush_tracking()

        lost_wizard = self.env["crm.lead.lost"].create(
            {
                "lead_ids": leads.ids,
                "lost_reason_id": self.lost_reason.id,
                "lost_feedback": "<p>I cannot find it. It was in my closet and pouf, disappeared.</p>",
            }
        )
        lost_wizard.action_lost_reason_apply()
        self.flush_tracking()

        for lead in leads:
            self.assertFalse(lead.active)
            self.assertEqual(lead.automated_probability, 0)
            self.assertEqual(lead.probability, 0)
            self.assertEqual(lead.lost_reason_id, self.lost_reason)
            self.assertEqual(
                len(lead.message_ids),
                2,
                "Should have 2 messages: creation, lost with log",
            )
            lost_message = lead.message_ids.filtered(
                lambda msg: msg.subtype_id == self.env.ref("crm.mt_lead_lost")
            )
            self.assertTrue(lost_message)
            self.assertTracking(
                lost_message,
                [
                    ("active", "boolean", True, False),
                    ("lost_reason_id", "many2one", False, self.lost_reason),
                ],
            )
            self.assertIn(
                "<p>I cannot find it. It was in my closet and pouf, disappeared.</p>",
                lost_message.body,
                "Feedback should be included directly within tracking message",
            )

    @users("user_sales_salesman")
    @mute_logger("odoo.addons.base.models")
    def test_lead_lost_crm_rights(self):
        lead = self.lead_1.with_user(self.env.user)

        with self.assertRaises(exceptions.AccessError):
            lost_reason = self.env["crm.lost.reason"].create({"name": "Test Reason"})

        with self.with_user("user_sales_manager"):
            lost_reason = self.env["crm.lost.reason"].create({"name": "Test Reason"})

        with self.assertRaises(exceptions.AccessError):
            lost_wizard = self.env["crm.lead.lost"].create(
                {"lead_ids": lead.ids, "lost_reason_id": lost_reason.id}
            )
            lost_wizard.action_lost_reason_apply()
