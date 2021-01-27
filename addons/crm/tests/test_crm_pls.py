# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields, tools
from odoo.tests.common import TransactionCase


class TestCRMPLS(TransactionCase):

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
        team_ids = self.env['crm.team'].create([{'name': 'Team Test 1'}, {'name': 'Team Test 2'}]).ids
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

        leads = Lead.create(leads_to_create)

        # Set the PLS config
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_start_date", "2000-01-01")
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_fields", "country_id,state_id,email_state,phone_state,source_id")

        # set leads as won and lost
        # for Team 1
        leads[0].action_set_lost()
        leads[1].action_set_lost()
        leads[2].action_set_won()
        # for Team 2
        leads[5].action_set_lost()
        leads[6].action_set_lost()
        leads[7].action_set_won()

        # A. Test Full Rebuild
        # rebuild frequencies table and recompute automated_probability for all leads.
        Lead._cron_update_automated_probabilities()

        # As the cron is computing and writing in SQL queries, we need to invalidate the cache
        leads.invalidate_cache()

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 33.49, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 7.74, 2), 0)

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
        leads_with_tags.invalidate_cache()

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
        leads_with_tags.invalidate_cache()

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 4.21, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 0.23, 2), 0)

        # remove all pls fields
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_fields", False)
        Lead._cron_update_automated_probabilities()
        leads_with_tags.invalidate_cache()

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 34.38, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 50.0, 2), 0)

        # check if the probabilities are the same with the old param
        self.env['ir.config_parameter'].sudo().set_param("crm.pls_fields", "country_id,state_id,email_state,phone_state,source_id")
        Lead._cron_update_automated_probabilities()
        leads_with_tags.invalidate_cache()

        self.assertEqual(tools.float_compare(leads[3].automated_probability, 4.21, 2), 0)
        self.assertEqual(tools.float_compare(leads[8].automated_probability, 0.23, 2), 0)

    def test_settings_pls_start_date(self):
        # We test here that settings never crash due to ill-configured config param 'crm.pls_start_date'
        set_param = self.env['ir.config_parameter'].sudo().set_param
        str_date_8_days_ago = fields.Date.to_string(fields.Date.today() - timedelta(days=8))
        resConfig = self.env['res.config.settings']

        set_param("crm.pls_start_date", "2021-10-10")
        res_config_new = resConfig.new()
        self.assertEqual(fields.Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            "2021-10-10", "If config param is a valid date, date in settings should match with config param")

        set_param("crm.pls_start_date", "")
        res_config_new = resConfig.new()
        self.assertEqual(fields.Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            str_date_8_days_ago, "If config param is empty, date in settings should be set to 8 days before today")

        set_param("crm.pls_start_date", "One does not simply walk into system parameters to corrupt them")
        res_config_new = resConfig.new()
        self.assertEqual(fields.Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            str_date_8_days_ago, "If config param is not a valid date, date in settings should be set to 8 days before today")
