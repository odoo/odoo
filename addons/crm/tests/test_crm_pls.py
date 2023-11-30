# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import tools
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.fields import Date
from odoo.tests import Form, tagged, users, loaded_demo_data
from odoo.tests.common import TransactionCase


@tagged('crm_lead_pls')
class TestCRMPLS(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """ Keep a limited setup to ensure tests are not impacted by other
        records created in CRM common. """
        super(TestCRMPLS, cls).setUpClass()

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

    def _get_lead_values(self, team_id, name_suffix, country_id, state_id, email_state, phone_state, source_id, stage_id):
        return {
            'name': 'lead_' + name_suffix,
            'type': 'opportunity',
            'state_id': state_id,
            'email_state': email_state,
            'phone_state': phone_state,
            'source_id': source_id,
            'stage_id': stage_id,
            'country_id': country_id,
            'team_id': team_id
        }

    def generate_leads_with_tags(self, tag_ids):
        Lead = self.env['crm.lead']
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

        leads_with_tags = Lead.create(leads_to_create)

        return leads_with_tags

    def test_crm_lead_pls_update(self):
        """ We test here that the wizard for updating probabilities from settings
            is getting correct value from config params and after updating values
            from the wizard, the config params are correctly updated
        """
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
                self._get_lead_values(team_ids[0], 'team_1_%s' % str(i), country_ids[i], state_ids[i], state_values[i], state_values[i], source_ids[i], stage_ids[i]))
        leads_to_create.append(
            self._get_lead_values(team_ids[0], 'team_1_%s' % str(3), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[2], stage_ids[1]))
        leads_to_create.append(
            self._get_lead_values(team_ids[0], 'team_1_%s' % str(4), country_ids[1], state_ids[1], state_values[1], state_values[0], source_ids[1], stage_ids[0]))
        #   for team 2
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(5), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[1], stage_ids[2]))
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(6), country_ids[0], state_ids[1], state_values[0], state_values[1], source_ids[2], stage_ids[1]))
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(7), country_ids[0], state_ids[2], state_values[0], state_values[1], source_ids[2], stage_ids[0]))
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(8), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[2], stage_ids[1]))
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(9), country_ids[1], state_ids[0], state_values[1], state_values[0], source_ids[1], stage_ids[1]))

        #   for leads with no team
        leads_to_create.append(
            self._get_lead_values(False, 'no_team_%s' % str(10), country_ids[1], state_ids[1], state_values[2], state_values[0], source_ids[1], stage_ids[2]))
        leads_to_create.append(
            self._get_lead_values(False, 'no_team_%s' % str(11), country_ids[0], state_ids[1], state_values[1], state_values[1], source_ids[0], stage_ids[0]))
        leads_to_create.append(
            self._get_lead_values(False, 'no_team_%s' % str(12), country_ids[1], state_ids[2], state_values[0], state_values[1], source_ids[2], stage_ids[0]))
        leads_to_create.append(
            self._get_lead_values(False, 'no_team_%s' % str(13), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[2], stage_ids[1]))

        leads = Lead.create(leads_to_create)

        # assign team 3 to all leads with no teams (also take data into account).
        leads_with_no_team = self.env['crm.lead'].sudo().search([('team_id', '=', False)])
        leads_with_no_team.write({'team_id': team_ids[2]})

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
        # Proba should be different as "no team" is not considered as a separated team.
        leads_with_no_team.write({'team_id': False})
        Lead._cron_update_automated_probabilities()
        lead_13_no_team_proba = leads[13].automated_probability
        self.assertTrue(lead_13_team_3_proba != leads[13].automated_probability, "Probability for leads with no team should be different than if they where in their own team.")
        # Todo: Make this test fully independent from demo data
        if not loaded_demo_data(self.env):
            expected_proba = 35.19
        else:
            expected_proba = 36.65
        self.assertAlmostEqual(lead_13_no_team_proba, expected_proba, places=2)

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
        leads[4].toggle_active()
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
        self.assertEqual(lead_4_stage_0_freq.won_count, 2.1)  # + 1
        self.assertEqual(lead_4_stage_won_freq.won_count, 2.1)  # + 1
        self.assertEqual(lead_4_country_freq.won_count, 1.1)  # + 1
        self.assertEqual(lead_4_email_state_freq.won_count, 2.1)  # + 1
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.lost_count, 0.1)  # unchanged
        self.assertEqual(lead_4_country_freq.lost_count, 1.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.lost_count, 2.1)  # unchanged

        # Archive (was won, now lost) -> Should decrease won and increase lost
        leads[4].toggle_active()
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # - 1
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # - 1
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # - 1
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # - 1
        self.assertEqual(lead_4_stage_0_freq.lost_count, 3.1)  # + 1
        self.assertEqual(lead_4_stage_won_freq.lost_count, 1.1)  # consider stages with <= sequence when lostand as stage is won.. even won_stage lost_count is increased by 1
        self.assertEqual(lead_4_country_freq.lost_count, 2.1)  # + 1
        self.assertEqual(lead_4_email_state_freq.lost_count, 3.1)  # + 1

        # Move to original stage -> Should do nothing (as lead is still lost)
        leads[4].stage_id = stage_ids[0]
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_0_freq.lost_count, 3.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.lost_count, 1.1)  # unchanged
        self.assertEqual(lead_4_country_freq.lost_count, 2.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.lost_count, 3.1)  # unchanged

        # Restore -> Should decrease lost - at the end, frequencies should be like first frequencyes tests (except for 0.0 -> 0.1)
        leads[4].toggle_active()
        self.assertEqual(lead_4_stage_0_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_won_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_country_freq.won_count, 0.1)  # unchanged
        self.assertEqual(lead_4_email_state_freq.won_count, 1.1)  # unchanged
        self.assertEqual(lead_4_stage_0_freq.lost_count, 2.1)  # - 1
        self.assertEqual(lead_4_stage_won_freq.lost_count, 1.1)  # unchanged - consider stages with <= sequence when lost
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
        self.assertEqual(lead_4_stage_won_freq.lost_count, 1.1)  # unchanged
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
        leads_with_tags = self.generate_leads_with_tags(tag_ids)

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
            self._get_lead_values(team_id, 'edge pending', country_id, False, False, False, False, stage_id),
            self._get_lead_values(team_id, 'edge lost', country_id, False, False, False, False, stage_id),
            self._get_lead_values(team_id, 'edge won', country_id, False, False, False, False, stage_id),
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

    def test_settings_pls_start_date(self):
        # We test here that settings never crash due to ill-configured config param 'crm.pls_start_date'
        set_param = self.env['ir.config_parameter'].sudo().set_param
        str_date_8_days_ago = Date.to_string(Date.today() - timedelta(days=8))
        resConfig = self.env['res.config.settings']

        set_param("crm.pls_start_date", "2021-10-10")
        res_config_new = resConfig.new()
        self.assertEqual(Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            "2021-10-10", "If config param is a valid date, date in settings should match with config param")

        set_param("crm.pls_start_date", "")
        res_config_new = resConfig.new()
        self.assertEqual(Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            str_date_8_days_ago, "If config param is empty, date in settings should be set to 8 days before today")

        set_param("crm.pls_start_date", "One does not simply walk into system parameters to corrupt them")
        res_config_new = resConfig.new()
        self.assertEqual(Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            str_date_8_days_ago, "If config param is not a valid date, date in settings should be set to 8 days before today")

    def test_pls_no_share_stage(self):
        """ We test here the situation where all stages are team specific, as there is
            a current limitation (can be seen in _pls_get_won_lost_total_count) regarding
            the first stage (used to know how many lost and won there is) that requires
            to have no team assigned to it."""
        Lead = self.env['crm.lead']
        team_id = self.env['crm.team'].create([{'name': 'Team Test'}]).id
        self.env['crm.stage'].search([('team_id', '=', False)]).write({'team_id': team_id})
        lead = Lead.create({'name': 'team', 'team_id': team_id, 'probability': 41.23})
        Lead._cron_update_automated_probabilities()
        self.assertEqual(tools.float_compare(lead.probability, 41.23, 2), 0)
        self.assertEqual(tools.float_compare(lead.automated_probability, 0, 2), 0)

    @users('user_sales_manager')
    def test_team_unlink(self):
        """ Test that frequencies are sent to "no team" when unlinking a team
        in order to avoid losing too much informations. """
        pls_team = self.env["crm.team"].browse(self.pls_team.ids)

        # clean existing data
        self.env["crm.lead.scoring.frequency"].sudo().search([('team_id', '=', False)]).unlink()

        # existing no-team data
        no_team = [
            ('stage_id', '1', 20, 10),
            ('stage_id', '2', 0.1, 0.1),
            ('stage_id', '3', 10, 0),
            ('country_id', '1', 10, 0.1),
        ]
        self.env["crm.lead.scoring.frequency"].sudo().create([
            {'variable': variable, 'value': value,
             'won_count': won_count, 'lost_count': lost_count,
             'team_id': False,
            } for variable, value, won_count, lost_count in no_team
        ])

        # add some frequencies to team to unlink
        team = [
            ('stage_id', '1', 20, 10),  # existing noteam
            ('country_id', '1', 0.1, 10),  # existing noteam
            ('country_id', '2', 0.1, 0),  # new but void
            ('country_id', '3', 30, 30),  # new
        ]
        existing_plsteam = self.env["crm.lead.scoring.frequency"].sudo().create([
            {'variable': variable, 'value': value,
             'won_count': won_count, 'lost_count': lost_count,
             'team_id': pls_team.id,
            } for variable, value, won_count, lost_count in team
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
