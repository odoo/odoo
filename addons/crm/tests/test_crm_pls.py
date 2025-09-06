from datetime import timedelta

from odoo import exceptions, tools
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.fields import Date
from odoo.tests import Form, tagged, users
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class CrmPlsCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """ Keep a limited setup to ensure tests are not impacted by other
        records created in CRM common. """
        super().setUpClass()

        cls.company_main = cls.env.user.company_id
        cls.user_sales_manager = mail_new_test_user(
            cls.env, login='user_sales_manager',
            name='Martin PLS Sales Manager', email='crm_manager@test.example.com',
            company_id=cls.company_main.id,
            notification_type='inbox',
            groups='sales_team.group_sale_manager,base.group_partner_manager',
        )

        cls.pls_team = cls.env['crm.team'].create({
            'name': 'PLS Team',
        })

        # Ensure independence on demo data
        cls.env['crm.lead'].with_context({'active_test': False}).search([]).unlink()
        cls.env['crm.lead.scoring.frequency'].search([]).unlink()
        cls.cr.flush()

    def _prepare_test_lead_values(self, team_id, name_suffix, country_id, state_id, email_state, phone_state, source_id, stage_id):
        return {
            'name': 'lead_' + name_suffix,
            'stage_id': stage_id,
            'team_id': team_id,
            'type': 'opportunity',
            # contact
            'email_state': email_state,
            'phone_state': phone_state,
            # address
            'country_id': country_id,
            'state_id': state_id,
            # misc
            'source_id': source_id,
        }

    def _generate_leads_with_tags(self, tag_ids):
        team_id = self.env['crm.team'].create({
            'name': 'blup',
        }).id

        leads_to_create = []
        for i in range(150):
            if i < 50:  # tag 1
                leads_to_create.append({
                    'name': 'lead_tag_%s' % str(i),
                    'tag_ids': [(4, tag_ids[0])],
                    'team_id': team_id
                })
            elif i < 100:  # tag 2
                leads_to_create.append({
                    'name': 'lead_tag_%s' % str(i),
                    'tag_ids': [(4, tag_ids[1])],
                    'team_id': team_id
                })
            else:  # tag 1 and 2
                leads_to_create.append({
                    'name': 'lead_tag_%s' % str(i),
                    'tag_ids': [(6, 0, tag_ids)],
                    'team_id': team_id
                })

        leads_with_tags = self.env['crm.lead'].create(leads_to_create)

        return leads_with_tags


@tagged('post_install', '-at_install', 'crm_lead_pls')
class TestConfig(CrmPlsCommon):

    def test_crm_lead_pls_update(self):
        """ Test the wizard for updating probabilities from settings is getting
        correct value from config params and after updating values from the wizard
        config params are correctly updated. """
        # Set the PLS config
        frequency_fields = self.env['crm.lead.scoring.frequency.field'].search([])
        pls_fields_str = ','.join(frequency_fields.mapped('field_id.name'))
        pls_start_date_str = "2021-01-01"
        IrConfigSudo = self.env['ir.config_parameter'].sudo()
        IrConfigSudo.set_param("crm.pls_start_date", pls_start_date_str)
        IrConfigSudo.set_param("crm.pls_fields", pls_fields_str)

        date_to_update = "2021-02-02"
        fields_to_remove = frequency_fields.filtered(lambda f: f.field_id.name in ['source_id', 'lang_id'])
        fields_after_updation_str = ','.join((frequency_fields - fields_to_remove).mapped('field_id.name'))

        # Check that wizard to update lead probabilities has correct value set by default
        pls_update_wizard = Form(self.env['crm.lead.pls.update'])
        with pls_update_wizard:
            self.assertEqual(Date.to_string(pls_update_wizard.pls_start_date), pls_start_date_str, 'Correct date is taken from config')
            self.assertEqual(','.join([f.field_id.name for f in pls_update_wizard.pls_fields]), pls_fields_str, 'Correct fields are taken from config')
            # Update the wizard values and check that config values and probabilities are updated accordingly
            pls_update_wizard.pls_start_date =  date_to_update
            for field in fields_to_remove:
                pls_update_wizard.pls_fields.remove(field.id)

        pls_update_wizard0 = pls_update_wizard.save()
        pls_update_wizard0.action_update_crm_lead_probabilities()

        # Config params should have been updated
        self.assertEqual(IrConfigSudo.get_param("crm.pls_start_date"), date_to_update, 'Correct date is updated in config')
        self.assertEqual(IrConfigSudo.get_param("crm.pls_fields"), fields_after_updation_str, 'Correct fields are updated in config')

    def test_settings_pls_start_date(self):
        """ Test various use cases of 'crm.pls_start_date' """
        str_date_8_days_ago = Date.to_string(Date.today() - timedelta(days=8))

        for value, expected in [
            ("2021-10-10", "2021-10-10"),
            # empty of invalid value -> set to 8 days before today
            ("", str_date_8_days_ago),
            ("One does not simply walk into system parameters to corrupt them", str_date_8_days_ago),
        ]:
            with self.subTest(value=value):
                self.env['ir.config_parameter'].sudo().set_param('crm.pls_start_date', value)
                res_config_new = self.env['res.config.settings'].new()
                self.assertEqual(Date.to_string(res_config_new.predictive_lead_scoring_start_date), expected)


@tagged('post_install', '-at_install', 'crm_lead_pls')
class TestCrmPls(CrmPlsCommon):

    def test_predictive_lead_scoring(self):
        """ We test here computation of lead probability based on PLS Bayes.
                We will use 3 different values for each possible variables:
                country_id : 1,2,3
                state_id: 1,2,3
                email_state: correct, incorrect, None
                phone_state: correct, incorrect, None
                source_id: 1,2,3
                stage_id: 1,2,3 + the won stage
                And we will compute all of this for 2 different team_id
            Note : We assume here that original bayes computation is correct
            as we don't compute manually the probabilities."""
        Lead = self.env['crm.lead']
        LeadScoringFrequency = self.env['crm.lead.scoring.frequency']
        state_values = ['correct', 'incorrect', None]
        source_ids = self.env['utm.source'].search([], limit=3).ids
        state_ids = self.env['res.country.state'].search([], limit=3).ids
        country_ids = self.env['res.country'].search([], limit=3).ids
        stage_ids = self.env['crm.stage'].search([], limit=3).ids
        won_stage_id = self.env['crm.stage'].search([('is_won', '=', True)], limit=1).id
        team_ids = self.env['crm.team'].create([{'name': 'Team Test 1'}, {'name': 'Team Test 2'}, {'name': 'Team Test 3'}]).ids
        # create bunch of lost and won crm_lead
        leads_to_create = []
        #   for team 1
        for i in range(3):
            leads_to_create.append(
                self._prepare_test_lead_values(team_ids[0], 'team_1_%s' % str(i), country_ids[i], state_ids[i], state_values[i], state_values[i], source_ids[i], stage_ids[i]))
        leads_to_create.append(
            self._prepare_test_lead_values(team_ids[0], 'team_1_%s' % str(3), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[2], stage_ids[1]))
        leads_to_create.append(
            self._prepare_test_lead_values(team_ids[0], 'team_1_%s' % str(4), country_ids[1], state_ids[1], state_values[1], state_values[0], source_ids[1], stage_ids[0]))
        #   for team 2
        leads_to_create.append(
            self._prepare_test_lead_values(team_ids[1], 'team_2_%s' % str(5), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[1], stage_ids[2]))
        leads_to_create.append(
            self._prepare_test_lead_values(team_ids[1], 'team_2_%s' % str(6), country_ids[0], state_ids[1], state_values[0], state_values[1], source_ids[2], stage_ids[1]))
        leads_to_create.append(
            self._prepare_test_lead_values(team_ids[1], 'team_2_%s' % str(7), country_ids[0], state_ids[2], state_values[0], state_values[1], source_ids[2], stage_ids[0]))
        leads_to_create.append(
            self._prepare_test_lead_values(team_ids[1], 'team_2_%s' % str(8), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[2], stage_ids[1]))
        leads_to_create.append(
            self._prepare_test_lead_values(team_ids[1], 'team_2_%s' % str(9), country_ids[1], state_ids[0], state_values[1], state_values[0], source_ids[1], stage_ids[1]))

        #   for leads with no team
        leads_to_create.append(
            self._prepare_test_lead_values(False, 'no_team_%s' % str(10), country_ids[1], state_ids[1], state_values[2], state_values[0], source_ids[1], stage_ids[2]))
        leads_to_create.append(
            self._prepare_test_lead_values(False, 'no_team_%s' % str(11), country_ids[0], state_ids[1], state_values[1], state_values[1], source_ids[0], stage_ids[0]))
        leads_to_create.append(
            self._prepare_test_lead_values(False, 'no_team_%s' % str(12), country_ids[1], state_ids[2], state_values[0], state_values[1], source_ids[2], stage_ids[0]))
        leads_to_create.append(
            self._prepare_test_lead_values(False, 'no_team_%s' % str(13), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[2], stage_ids[1]))

        leads = Lead.create(leads_to_create)

        # Assert lead data.
        existing_leads = Lead.with_context({'active_filter': False}).search([])
        self.assertEqual(existing_leads, leads)
        self.assertEqual(existing_leads.filtered(lambda lead: not lead.team_id), leads[-4::])

        # Assign leads without team to team 3 to compare probability
        # as a separate team and the one with no team set. See below (*)
        leads[-4::].team_id = team_ids[2]

        # Set the PLS config
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_start_date", "2000-01-01")
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_fields", "country_id,state_id,email_state,phone_state,source_id,tag_ids")

        # set leads as won and lost
        # for Team 1
        leads[0].action_set_lost()
        leads[1].action_set_lost()
        leads[2].action_set_won()
        # for Team 2
        leads[5].action_set_lost()
        leads[6].action_set_lost()
        leads[7].action_set_won()
        # Leads with no team
        leads[10].action_set_won()
        leads[11].action_set_lost()
        leads[12].action_set_lost()

        # A. Test Full Rebuild
        # rebuild frequencies table and recompute automated_probability for all leads.
        Lead._cron_update_automated_probabilities()

        # As the cron is computing and writing in SQL queries, we need to invalidate the cache
        self.env.invalidate_all()

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 33.49, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 7.74, 2), 0)
        lead_13_team_3_proba = leads[13].automated_probability
        self.assertEqual(tools.float_compare(lead_13_team_3_proba, 35.09, 2), 0)

        # Probability for Lead with no teams should be based on all the leads no matter their team.
        # De-assign team 3 and rebuilt frequency table and recompute.
        # Proba should be different as "no team" is not considered as a separated team. (*)
        leads[-4::].write({'team_id': False})
        leads[-4::].flush_recordset()

        Lead._cron_update_automated_probabilities()
        lead_13_no_team_proba = leads[13].automated_probability
        self.assertTrue(lead_13_team_3_proba != leads[13].automated_probability, "Probability for leads with no team should be different than if they where in their own team.")
        self.assertAlmostEqual(lead_13_no_team_proba, 35.19, places=2)

        # Test frequencies
        lead_4_stage_0_freq = LeadScoringFrequency.search([('team_id', '=', leads[4].team_id.id), ('variable', '=', 'stage_id'), ('value', '=', stage_ids[0])])
        lead_4_stage_won_freq = LeadScoringFrequency.search([('team_id', '=', leads[4].team_id.id), ('variable', '=', 'stage_id'), ('value', '=', won_stage_id)])
        lead_4_country_freq = LeadScoringFrequency.search([('team_id', '=', leads[4].team_id.id), ('variable', '=', 'country_id'), ('value', '=', leads[4].country_id.id)])
        lead_4_email_state_freq = LeadScoringFrequency.search([('team_id', '=', leads[4].team_id.id), ('variable', '=', 'email_state'), ('value', '=', str(leads[4].email_state))])

        lead_9_stage_0_freq = LeadScoringFrequency.search([('team_id', '=', leads[9].team_id.id), ('variable', '=', 'stage_id'), ('value', '=', stage_ids[0])])
        lead_9_stage_won_freq = LeadScoringFrequency.search([('team_id', '=', leads[9].team_id.id), ('variable', '=', 'stage_id'), ('value', '=', won_stage_id)])
        lead_9_country_freq = LeadScoringFrequency.search([('team_id', '=', leads[9].team_id.id), ('variable', '=', 'country_id'), ('value', '=', leads[9].country_id.id)])
        lead_9_email_state_freq = LeadScoringFrequency.search([('team_id', '=', leads[9].team_id.id), ('variable', '=', 'email_state'), ('value', '=', str(leads[9].email_state))])

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
        self.assertEqual(lead_9_country_freq.won_count, 0.0)  # frequency does not exist
        self.assertEqual(lead_9_email_state_freq.won_count, 1.1)
        self.assertEqual(lead_9_stage_0_freq.lost_count, 2.1)
        self.assertEqual(lead_9_stage_won_freq.lost_count, 0.1)
        self.assertEqual(lead_9_country_freq.lost_count, 0.0)  # frequency does not exist
        self.assertEqual(lead_9_email_state_freq.lost_count, 2.1)

        # B. Test Live Increment
        leads[4].action_set_lost()
        leads[9].action_set_won()

        # re-get frequencies that did not exists before
        lead_9_country_freq = LeadScoringFrequency.search([('team_id', '=', leads[9].team_id.id), ('variable', '=', 'country_id'), ('value', '=', leads[9].country_id.id)])

        # B.1. Test frequencies - team 1 should not impact team 2
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_0_freq.lost_count, 3.1)  # + 1
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged - consider stages with <= sequence when lost
        self.assertEqual(lead_4_country_freq.lost_count, 2.1)  # + 1
        self.assertEqual(lead_4_email_state_freq.lost_count, 3.1)  # + 1

        self.assertEqual(lead_9_stage_0_freq.won_count, 2.1)  # + 1
        self.assertEqual(lead_9_stage_won_freq.won_count, 2.1)  # + 1 - consider every stages when won
        self.assertEqual(lead_9_country_freq.won_count, 1.1)  # + 1
        self.assertEqual(lead_9_email_state_freq.won_count, 2.1)  # + 1
        self.assertEqual(lead_9_stage_0_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_9_stage_won_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_9_country_freq.lost_count, 0.1)  # unchanged (did not exists before)
        self.assertEqual(lead_9_email_state_freq.lost_count, 2.1)  # unchanged

        # Propabilities of other leads should not be impacted as only modified lead are recomputed.
        self.assertEqual(tools.float_compare(leads[3].automated_probability, 33.49, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 7.74, 2), 0)

        self.assertEqual(leads[3].is_automated_probability, True)
        self.assertEqual(leads[8].is_automated_probability, True)

        # Restore -> Should decrease lost
        leads[4].action_unarchive()
        self.assertEqual(leads[4].won_status, 'pending')
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)  # - 1
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged - consider stages with <= sequence when lost
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)  # - 1
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)  # - 1

        self.assertEqual(lead_9_stage_0_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_9_stage_won_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_9_country_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_9_email_state_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_9_stage_0_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_9_stage_won_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_9_country_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_9_email_state_freq.lost_count, 2.1)  # unchanged

        # set to won stage -> Should increase won
        leads[4].stage_id = won_stage_id
        self.assertEqual(leads[4].won_status, 'won')
        self.assertEqual(lead_4_stage_0_freq.won_count, 2.1)  # + 1
        self.assertEqual(lead_4_stage_won_freq.won_count, 2.1)  # + 1
        self.assertEqual(lead_4_country_freq.won_count, 1.1)  # + 1
        self.assertEqual(lead_4_email_state_freq.won_count, 2.1)  # + 1
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)  # unchanged

        # Archive in won stage -> Should NOT decrease won NOR increase lost
        # as lost = archived + 0% and WON = won_stage (+ 100%)
        leads[4].action_archive()
        self.assertEqual(leads[4].won_status, 'won')
        self.assertEqual(lead_4_stage_0_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_4_country_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)  # unchanged

        # Move to original stage -> lead is not won anymore but not lost as probability != 0
        leads[4].stage_id = stage_ids[0]
        self.assertEqual(leads[4].won_status, 'pending')
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # -1
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # -1
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # -1
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # -1
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)  # unchanged

        # force proba to 0% -> as already archived, will be lost (lost = archived AND 0%)
        leads[4].probability = 0
        self.assertEqual(leads[4].won_status, 'lost')
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_0_freq.lost_count, 3.1)  # +1
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged - should not increase lost frequency of won stage.
        self.assertEqual(lead_4_country_freq.lost_count, 2.1)  # +1
        self.assertEqual(lead_4_email_state_freq.lost_count, 3.1)  # +1

        # Restore -> Should decrease lost - at the end, frequencies should be like first frequencyes tests (except for 0.0 -> 0.1)
        leads[4].action_unarchive()
        self.assertEqual(leads[4].won_status, 'pending')
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)  # - 1
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged - consider stages with <= sequence when lost
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)  # - 1
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)  # - 1

        # Probabilities should only be recomputed after modifying the lead itself.
        leads[3].stage_id = stage_ids[0]  # probability should only change a bit as frequencies are almost the same (except 0.0 -> 0.1)
        leads[8].stage_id = stage_ids[0]  # probability should change quite a lot

        # Test frequencies (should not have changed)
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)  # unchanged

        self.assertEqual(lead_9_stage_0_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_9_stage_won_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_9_country_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_9_email_state_freq.won_count, 2.1)  # unchanged
        self.assertEqual(lead_9_stage_0_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_9_stage_won_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_9_country_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_9_email_state_freq.lost_count, 2.1)  # unchanged

        # Continue to test probability computation
        leads[3].probability = 40

        self.assertEqual(leads[3].is_automated_probability, False)
        self.assertEqual(leads[8].is_automated_probability, True)

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 20.87, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 2.43, 2), 0)
        self.assertEqual(tools.float_compare(leads[3].probability, 40, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].probability, 2.43, 2), 0)

        # Test modify country_id
        leads[8].country_id = country_ids[1]
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 34.38, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].probability, 34.38, 2), 0)

        leads[8].country_id = country_ids[0]
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 2.43, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].probability, 2.43, 2), 0)

        # ----------------------------------------------
        # Test tag_id frequencies and probability impact
        # ----------------------------------------------

        tag_ids = self.env['crm.tag'].create([
            {'name': "Tag_test_1"},
            {'name': "Tag_test_2"},
        ]).ids
        # tag_ids = self.env['crm.tag'].search([], limit=2).ids
        leads_with_tags = self._generate_leads_with_tags(tag_ids)

        leads_with_tags[:30].action_set_lost()  # 60% lost on tag 1
        leads_with_tags[31:50].action_set_won()   # 40% won on tag 1
        leads_with_tags[50:90].action_set_lost()  # 80% lost on tag 2
        leads_with_tags[91:100].action_set_won()   # 20% won on tag 2
        leads_with_tags[100:135].action_set_lost()  # 70% lost on tag 1 and 2
        leads_with_tags[136:150].action_set_won()   # 30% won on tag 1 and 2
        # tag 1 : won = 19+14  /  lost = 30+35
        # tag 2 : won = 9+14  /  lost = 40+35

        tag_1_freq = LeadScoringFrequency.search([('variable', '=', 'tag_id'), ('value', '=', tag_ids[0])])
        tag_2_freq = LeadScoringFrequency.search([('variable', '=', 'tag_id'), ('value', '=', tag_ids[1])])
        self.assertEqual(tools.float_compare(tag_1_freq.won_count, 33.1, 1), 0)
        self.assertEqual(tools.float_compare(tag_1_freq.lost_count, 65.1, 1), 0)
        self.assertEqual(tools.float_compare(tag_2_freq.won_count, 23.1, 1), 0)
        self.assertEqual(tools.float_compare(tag_2_freq.lost_count, 75.1, 1), 0)

        # Force recompute - A priori, no need to do this as, for each won / lost, we increment tag frequency.
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        lead_tag_1 = leads_with_tags[30]
        lead_tag_2 = leads_with_tags[90]
        lead_tag_1_2 = leads_with_tags[135]

        self.assertEqual(tools.float_compare(lead_tag_1.automated_probability, 33.69, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_2.automated_probability, 23.51, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_1_2.automated_probability, 28.05, 2), 0)

        lead_tag_1.tag_ids = [(5, 0, 0)]  # remove all tags
        lead_tag_1_2.tag_ids = [(3, tag_ids[1], 0)]  # remove tag 2

        self.assertEqual(tools.float_compare(lead_tag_1.automated_probability, 28.6, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_2.automated_probability, 23.51, 2), 0)  # no impact
        self.assertEqual(tools.float_compare(lead_tag_1_2.automated_probability, 33.69, 2), 0)

        lead_tag_1.tag_ids = [(4, tag_ids[1])]  # add tag 2
        lead_tag_2.tag_ids = [(4, tag_ids[0])]  # add tag 1
        lead_tag_1_2.tag_ids = [(3, tag_ids[0]), (4, tag_ids[1])]  # remove tag 1 / add tag 2

        self.assertEqual(tools.float_compare(lead_tag_1.automated_probability, 23.51, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_2.automated_probability, 28.05, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_1_2.automated_probability, 23.51, 2), 0)

        # go back to initial situation
        lead_tag_1.tag_ids = [(3, tag_ids[1]), (4, tag_ids[0])]  # remove tag 2 / add tag 1
        lead_tag_2.tag_ids = [(3, tag_ids[0])]  # remove tag 1
        lead_tag_1_2.tag_ids = [(4, tag_ids[0])]  # add tag 1

        self.assertEqual(tools.float_compare(lead_tag_1.automated_probability, 33.69, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_2.automated_probability, 23.51, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_1_2.automated_probability, 28.05, 2), 0)

        # set email_state for each lead and update probabilities
        leads.filtered(lambda lead: lead.id % 2 == 0).email_state = 'correct'
        leads.filtered(lambda lead: lead.id % 2 == 1).email_state = 'incorrect'
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 4.21, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 0.23, 2), 0)

        # remove all pls fields
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_fields", False)
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 34.38, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 50.0, 2), 0)

        # check if the probabilities are the same with the old param
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_fields", "country_id,state_id,email_state,phone_state,source_id")
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 4.21, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 0.23, 2), 0)

        # remove tag_ids from the calculation
        self.assertEqual(tools.float_compare(lead_tag_1.automated_probability, 28.6, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_2.automated_probability, 28.6, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_1_2.automated_probability, 28.6, 2), 0)

        lead_tag_1.tag_ids = [(5, 0, 0)]  # remove all tags
        lead_tag_2.tag_ids = [(4, tag_ids[0])]  # add tag 1
        lead_tag_1_2.tag_ids = [(3, tag_ids[1], 0)]  # remove tag 2

        self.assertEqual(tools.float_compare(lead_tag_1.automated_probability, 28.6, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_2.automated_probability, 28.6, 2), 0)
        self.assertEqual(tools.float_compare(lead_tag_1_2.automated_probability, 28.6, 2), 0)

    def test_predictive_lead_scoring_always_won(self):
        """ The computation may lead scores close to 100% (or 0%), we check that pending
        leads are always in the ]0-100[ range."""
        Lead = self.env['crm.lead']
        LeadScoringFrequency = self.env['crm.lead.scoring.frequency']
        country_id = self.env['res.country'].search([], limit=1).id
        stage_id = self.env['crm.stage'].search([], limit=1).id
        team_id = self.env['crm.team'].create({'name': 'Team Test 1'}).id
        # create two leads
        leads = Lead.create([
            self._prepare_test_lead_values(team_id, 'edge pending', country_id, False, False, False, False, stage_id),
            self._prepare_test_lead_values(team_id, 'edge lost', country_id, False, False, False, False, stage_id),
            self._prepare_test_lead_values(team_id, 'edge won', country_id, False, False, False, False, stage_id),
        ])
        # set a new tag
        leads.tag_ids = self.env['crm.tag'].create({'name': 'lead scoring edge case'})

        # Set the PLS config
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_start_date", "2000-01-01")
        # tag_ids can be used in versions newer than v14
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_fields", "country_id")

        # set leads as won and lost
        leads[1].action_set_lost()
        leads[2].action_set_won()

        # recompute
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        # adapt the probability frequency to have high values
        # this way we are nearly sure it's going to be won
        freq_stage = LeadScoringFrequency.search([('variable', '=', 'stage_id'), ('value', '=', str(stage_id))])
        freq_tag = LeadScoringFrequency.search([('variable', '=', 'tag_id'), ('value', '=', str(leads.tag_ids.id))])
        freqs = freq_stage + freq_tag

        # check probabilities: won edge case
        freqs.write({'won_count': 10000000, 'lost_count': 1})
        leads._compute_probabilities()
        self.assertEqual(tools.float_compare(leads[2].probability, 100, 2), 0)
        self.assertEqual(tools.float_compare(leads[1].probability, 0, 2), 0)
        self.assertEqual(tools.float_compare(leads[0].probability, 99.99, 2), 0)

        # check probabilities: lost edge case
        freqs.write({'won_count': 1, 'lost_count': 10000000})
        leads._compute_probabilities()
        self.assertEqual(tools.float_compare(leads[2].probability, 100, 2), 0)
        self.assertEqual(tools.float_compare(leads[1].probability, 0, 2), 0)
        self.assertEqual(tools.float_compare(leads[0].probability, 0.01, 2), 0)

    def test_pls_no_share_stage(self):
        """ We test here the situation where all stages are team specific, as there is
            a current limitation (can be seen in _pls_get_won_lost_total_count) regarding
            the first stage (used to know how many lost and won there is) that requires
            to have no team assigned to it."""
        Lead = self.env['crm.lead']
        team_id = self.env['crm.team'].create([{'name': 'Team Test'}]).id
        self.env['crm.stage'].search([('team_ids', '=', False)]).write({'team_ids': [team_id]})
        lead = Lead.create({'name': 'team', 'team_id': team_id, 'probability': 41.23})
        Lead._cron_update_automated_probabilities()
        self.assertEqual(tools.float_compare(lead.probability, 41.23, 2), 0)
        self.assertEqual(tools.float_compare(lead.automated_probability, 0, 2), 0)

    def test_pls_tooltip_data(self):
        """ Assert that the method preparing tooltip data correctly returns (field, couple)
            values, in order of importance, of TOP 3 and LOW 3 criterions in PLS computation.
            See Table in docstring below for more details and a practical situation."""
        Lead = self.env['crm.lead']
        self.env['ir.config_parameter'].sudo().set_param(
            "crm.pls_fields",
            "country_id,state_id,email_state,phone_state,source_id"
        )
        country_ids = self.env['res.country'].search([], limit=2).ids
        source_ids = self.env['utm.source'].search([], limit=2).ids
        stage_ids = self.env['crm.stage'].search([], limit=3).ids
        state_ids = self.env['res.country.state'].search([], limit=2).ids
        team_id = self.env['crm.team'].create([{'name': 'Team Tooltip'}]).id
        leads = Lead.create([
            self._prepare_test_lead_values(team_id, 'lead Won A', country_ids[0], state_ids[0], False, False, source_ids[1], stage_ids[0]),
            self._prepare_test_lead_values(team_id, 'lead Won B', country_ids[1], state_ids[0], False, False, False, stage_ids[0]),
            self._prepare_test_lead_values(team_id, 'lead Lost C', False, False, False, False, source_ids[0], stage_ids[0]),
            self._prepare_test_lead_values(team_id, 'lead Lost D', country_ids[0], False, False, False, source_ids[0], stage_ids[0]),
            self._prepare_test_lead_values(team_id, 'lead Lost E', False, state_ids[1], False, False, False, stage_ids[2]),
            self._prepare_test_lead_values(team_id, 'lead Tooltip', country_ids[0], state_ids[0], False, False, source_ids[0], stage_ids[1]),
        ])

        # On creation, as phone and email are not set, these two fields will be set to False
        leads.email_state = 'correct'
        (leads[0] | leads[1] | leads[4] | leads[5]).phone_state = 'correct'
        (leads[2] | leads[3]).phone_state = 'incorrect'

        leads[:2].action_set_won()
        leads[2:5].action_set_lost()
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        # Values for leads[5]:
        # pW / pL is the probability that a won / lost lead has the lead value for a given field
        # [Score = pW / (pW + pL)] -> A score above .5 is a TOP, below .5 a LOW, equal to .5 ignored
        # Exception : for stage_id -> Score = 1 - P(current stage or lower for a lost lead)
        # ------------------------------------------------------------------------------------------
        # -- LOW 3 (lowest first, only 2 here)
        # source_id:   pW = 0.1/1.2  pL = 2.1/2.2            -> Score = 0.08
        # country_id:  pW = 1.1/2.2  pL = 1.1/1.2            -> Score = 0.353
        # -- Neither
        # email_state: pW = 2.1/2.1  pL = 3.1/3.1            -> Score = 0.5
        # -- TOP 3 (highest first)
        # state_id:    pW = 2.1/2.2  pL = 0.1/1.2            -> Score = 0.92
        # phone_state: pW = 2.1/2.2  pL = 1.1/3.2            -> Score = 0.735
        # stage_id:                  pL = 1.1/3.1            -> Score = 0.645
        expected_low_3 = ['source_id', 'country_id']
        expected_top_3 = ['state_id', 'phone_state', 'stage_id']

        tooltip_data = leads[5].prepare_pls_tooltip_data()
        self.assertEqual('Team Tooltip', tooltip_data['team_name'])
        self.assertEqual(tools.float_compare(tooltip_data['probability'], 74.30, 2), 0)

        self.assertListEqual([top_entry.get('field') for top_entry in tooltip_data['top_3_data']], expected_top_3)
        self.assertListEqual([low_entry.get('field') for low_entry in tooltip_data['low_3_data']], expected_low_3)

        # Assert scores for phone/email_state are excluded if absurd,
        # e.g. in top 3 when incorrect / not set or in low 3 if correct
        # Stage does not change and always has a score of 0.645
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_fields", "email_state,phone_state")

        leads[5].phone_state = False
        leads[5].email_state = 'incorrect'
        leads[:2].phone_state = False
        leads[:2].email_state = 'incorrect'
        leads[2:5].phone_state = 'correct'
        leads[2:5].email_state = 'correct'
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        # phone_state: pW = 2.1/2.2  pL = 0.1/3.2            -> Score = 0.968
        # email_state: pW = 2.1/2.2  pL = 0.1/3.2            -> Score = 0.968
        tooltip_data = leads[5].prepare_pls_tooltip_data()
        self.assertEqual(['stage_id'], [entry['field'] for entry in tooltip_data['top_3_data']])
        self.assertFalse(tooltip_data['low_3_data'])

        leads[5].email_state = 'correct'
        leads[5].phone_state = 'incorrect'
        leads[:2].phone_state = 'incorrect'
        Lead._cron_update_automated_probabilities()
        self.env.invalidate_all()

        # phone_state: pW = 2.1/2.2  pL = 0.1/3.2            -> Score = 0.968
        # email_state: pW = 0.1/2.2  pL = 3.1/3.2            -> Score = 0.045
        tooltip_data = leads[5].prepare_pls_tooltip_data()
        self.assertEqual(['stage_id'], [entry['field'] for entry in tooltip_data['top_3_data']])
        self.assertFalse(tooltip_data['low_3_data'])


@tagged('post_install', '-at_install', 'crm_lead_pls')
class TestCrmPlsSides(CrmPlsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.team = cls.env['crm.team'].create([{'name': 'Team Test'}])
        cls.stage_new, cls.stage_in_progress, cls.stage_won = cls.env['crm.stage'].create([
            {
                'name': 'New Stage',
                'sequence': 1,
                'team_ids': [cls.team.id],
            }, {
                'name': 'In Progress Stage',
                'sequence': 2,
                'team_ids': [cls.team.id],
            }, {
                'is_won': True,
                'name': 'Won Stage',
                'sequence': 3,
                'team_ids': [cls.team.id],
            },
        ])

    @users('user_sales_manager')
    def test_stage_update(self):
        """ Test side effects of changing stages """
        team_id = self.team.with_user(self.env.user).id
        stage_new, _stage_in_progress, stage_won = (self.stage_new + self.stage_in_progress + self.stage_won).with_user(self.env.user)
        leads = self.env['crm.lead'].create([
            {
                'name': 'Test Lead 1',
                'probability': 50,
                'stage_id': stage_new.id,
                'team_id': team_id,
            }, {
                'name': 'Test Lead 2',
                'probability': 50,
                'stage_id': stage_new.id,
                'team_id': team_id,
            }
        ])
        leads.action_set_lost()
        for lead in leads:
            self.assertFalse(lead.active)
            self.assertFalse(lead.probability)
        leads[0].active = True

        # putting in won state should reactivate
        leads.write({'stage_id': stage_won.id})
        for lead in leads:
            self.assertTrue(lead.active)
            self.assertEqual(lead.probability, 100)

    @users('user_sales_manager')
    def test_won_lost_validity(self):
        team_id = self.team.with_user(self.env.user).id
        stage_new, stage_in_progress, stage_won = (self.stage_new + self.stage_in_progress + self.stage_won).with_user(self.env.user)
        lead = self.env['crm.lead'].create([
            {
                'name': 'Test Lead',
                'probability': 50,
                'stage_id': stage_new.id,
                'team_id': team_id,
            }
        ])
        self.assertEqual(lead.won_status, 'pending')

        # Probability 100 is not a sufficient condition to win the lead
        lead.write({'probability': 100})
        self.assertEqual(lead.won_status, 'pending')

        # Test won validity
        lead.write({'probability': 90})
        self.assertEqual(lead.won_status, 'pending')
        lead.action_set_won()
        self.assertEqual(lead.probability, 100)
        self.assertTrue(lead.stage_id.is_won)
        self.assertEqual(lead.won_status, 'won')
        with self.assertRaises(exceptions.ValidationError, msg='A won lead cannot be set as lost.'):
            lead.action_set_lost()

        # Won lead can be inactive
        lead.write({'active': False})
        self.assertEqual(lead.probability, 100)
        self.assertEqual(lead.won_status, 'won')
        with self.assertRaises(exceptions.ValidationError, msg='A won lead cannot have probability < 100'):
            lead.write({'probability': 75})

        # Restore the lead in a non won stage. won_count = lost_count = 0.1 in frequency table. P = 50%
        lead.write({'stage_id': stage_in_progress.id, 'active': True})
        self.assertFalse(lead.probability == 100)
        self.assertEqual(lead.won_status, 'pending')

        # Test lost validity
        lead.action_set_lost()
        self.assertFalse(lead.active)
        self.assertEqual(lead.probability, 0)
        self.assertEqual(lead.won_status, 'lost')

        # Test won validity reaching won stage
        lead.write({'stage_id': stage_won.id})
        self.assertTrue(lead.active)
        self.assertEqual(lead.probability, 100)
        self.assertEqual(lead.won_status, 'won')

        # Back to lost
        lead.write({'active': False, 'probability': 0, 'stage_id': stage_new.id})
        self.assertEqual(lead.won_status, 'lost')

        # Once active again, lead is not lost anymore
        lead.write({'active': True})
        self.assertEqual(lead.won_status, 'pending', "An active lead cannot be lost")

    @users('user_sales_manager')
    def test_team_unlink(self):
        """ Test that frequencies are sent to "no team" when unlinking a team
        in order to avoid losing too much informations. """
        pls_team = self.env["crm.team"].browse(self.pls_team.ids)

        # existing no-team data
        noteam_scoring_data = [
            ('stage_id', '1', 20, 10),
            ('stage_id', '2', 0.1, 0.1),
            ('stage_id', '3', 10, 0),
            ('country_id', '1', 10, 0.1),
        ]
        self.env["crm.lead.scoring.frequency"].sudo().create([
            {
                'lost_count': lost_count,
                'team_id': False,
                'value': value,
                'variable': variable,
                'won_count': won_count,
            } for variable, value, won_count, lost_count in noteam_scoring_data
        ])

        # add some frequencies to team to unlink
        team_scoring_data = [
            ('stage_id', '1', 20, 10),  # existing noteam
            ('country_id', '1', 0.1, 10),  # existing noteam
            ('country_id', '2', 0.1, 0),  # new but void
            ('country_id', '3', 30, 30),  # new
        ]
        existing_plsteam = self.env["crm.lead.scoring.frequency"].sudo().create([
            {
                'lost_count': lost_count,
                'team_id': pls_team.id,
                'value': value,
                'variable': variable,
                'won_count': won_count,
            } for variable, value, won_count, lost_count in team_scoring_data
        ])

        pls_team.unlink()

        final_noteam = [
            ('stage_id', '1', 40, 20),
            ('stage_id', '2', 0.1, 0.1),
            ('stage_id', '3', 10, 0),
            ('country_id', '1', 10, 10),
            ('country_id', '3', 30, 30),

        ]
        self.assertEqual(
            existing_plsteam.exists(), self.env["crm.lead.scoring.frequency"],
            'Frequencies of unlinked teams should be unlinked (cascade)')
        existing_noteam = self.env["crm.lead.scoring.frequency"].sudo().search([
            ('team_id', '=', False),
            ('variable', 'in', ['stage_id', 'country_id']),
        ])
        for frequency in existing_noteam:
            stat = next(item for item in final_noteam if item[0] == frequency.variable and item[1] == frequency.value)
            self.assertEqual(frequency.won_count, stat[2])
            self.assertEqual(frequency.lost_count, stat[3])
        self.assertEqual(len(existing_noteam), len(final_noteam))


@tagged('lead_manage', 'crm_lead_pls')
class TestLeadLost(TestCrmCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lost_reason = cls.env['crm.lost.reason'].create({
            'name': 'Test Reason'
        })

    @users('user_sales_salesman')
    def test_lead_lost(self):
        """ Test setting a lead as lost using the wizard. Also check that an
        'html editor' void content used as feedback is not logged on the lead. """
        # Initial data
        self.assertEqual(len(self.lead_1.message_ids), 1, 'Should contain creation message')
        creation_message = self.lead_1.message_ids[0]
        self.assertEqual(creation_message.subtype_id, self.env.ref('crm.mt_lead_create'))
        self.assertEqual(
            self.lead_1.message_partner_ids, self.user_sales_leads.partner_id,
            'Responsible should be follower')

        # Update responsible as ACLs is "own only" for user_sales_salesman
        with self.mock_mail_gateway():
            self.lead_1.with_user(self.user_sales_manager).write({
                'user_id': self.user_sales_salesman.id,
                'probability': 32,
            })
            self.flush_tracking()

        lead = self.env['crm.lead'].browse(self.lead_1.ids)
        self.assertFalse(lead.lost_reason_id)
        self.assertEqual(
            self.lead_1.message_partner_ids, self.user_sales_leads.partner_id + self.user_sales_salesman.partner_id,
            'New responsible should be follower')
        self.assertEqual(lead.probability, 32)
        # tracking message
        self.assertEqual(len(lead.message_ids), 2, 'Should have tracked new responsible')
        update_message = lead.message_ids[0]
        self.assertMessageFields(
            update_message,
            {
                'notified_partner_ids': self.env['res.partner'],
                'partner_ids': self.env['res.partner'],
                'subtype_id': self.env.ref('mail.mt_note'),
                'tracking_field_names': ['user_id'],
            }
        )

        # mark as lost using the wizard
        lost_wizard = self.env['crm.lead.lost'].create({
            'lead_ids': lead.ids,
            'lost_reason_id': self.lost_reason.id,
            'lost_feedback': '<p></p>',  # void content
        })
        lost_wizard.action_lost_reason_apply()
        self.flush_tracking()

        # check lead update
        self.assertFalse(lead.active)
        self.assertEqual(lead.automated_probability, 0)
        self.assertEqual(lead.lost_reason_id, self.lost_reason)  # TDE FIXME: should be called lost_reason_id non didjou
        self.assertEqual(lead.probability, 0)
        # check messages
        self.assertEqual(len(lead.message_ids), 3, 'Should have logged a tracking message for lost lead with reason')
        lost_message = lead.message_ids[0]
        self.assertMessageFields(
            lost_message,
            {
                'notified_partner_ids': self.env['res.partner'],
                'partner_ids': self.env['res.partner'],
                'subtype_id': self.env.ref('crm.mt_lead_lost'),
                'tracking_field_names': ['active', 'lost_reason_id', 'won_status'],
                'tracking_values': [
                    ('active', 'boolean', True, False),
                    ('lost_reason_id', 'many2one', False, self.lost_reason),
                    ('won_status', 'char', 'Pending', 'Lost'),
                ],
            }
        )

    @users('user_sales_leads')
    def test_lead_lost_batch_wfeedback(self):
        """ Test setting leads as lost in batch using the wizard, including a log
        message. """
        leads = self._create_leads_batch(lead_type='lead', count=10, probabilities=[10, 20, 30])
        self.assertEqual(len(leads), 10)
        self.flush_tracking()

        lost_wizard = self.env['crm.lead.lost'].create({
            'lead_ids': leads.ids,
            'lost_reason_id': self.lost_reason.id,
            'lost_feedback': '<p>I cannot find it. It was in my closet and pouf, disappeared.</p>',
        })
        lost_wizard.action_lost_reason_apply()
        self.flush_tracking()

        for lead in leads:
            # check content
            self.assertFalse(lead.active)
            self.assertEqual(lead.automated_probability, 0)
            self.assertEqual(lead.probability, 0)
            self.assertEqual(lead.lost_reason_id, self.lost_reason)
            # check messages
            self.assertEqual(len(lead.message_ids), 2, 'Should have 2 messages: creation, lost with log')
            lost_message = lead.message_ids.filtered(lambda msg: msg.subtype_id == self.env.ref('crm.mt_lead_lost'))
            self.assertTrue(lost_message)
            self.assertTracking(
                lost_message,
                [('active', 'boolean', True, False),
                 ('lost_reason_id', 'many2one', False, self.lost_reason)
                ]
            )
            self.assertIn('<p>I cannot find it. It was in my closet and pouf, disappeared.</p>', lost_message.body,
                          'Feedback should be included directly within tracking message')

    @users('user_sales_salesman')
    @mute_logger('odoo.addons.base.models')
    def test_lead_lost_crm_rights(self):
        """ Test ACLs of lost reasons management and usage """
        lead = self.lead_1.with_user(self.env.user)

        # nice try little salesman but only managers can create lost reason to avoid bloating the DB
        with self.assertRaises(exceptions.AccessError):
            lost_reason = self.env['crm.lost.reason'].create({
                'name': 'Test Reason'
            })

        with self.with_user('user_sales_manager'):
            lost_reason = self.env['crm.lost.reason'].create({
                'name': 'Test Reason'
            })

        # nice try little salesman, you cannot invoke a wizard to update other people leads
        with self.assertRaises(exceptions.AccessError):
            # wizard needs to be here due to cache clearing in assertRaises
            # (ORM does not load m2m records unavailable to the user from database)
            lost_wizard = self.env['crm.lead.lost'].create({
                'lead_ids': lead.ids,
                'lost_reason_id': lost_reason.id
            })
            lost_wizard.action_lost_reason_apply()
