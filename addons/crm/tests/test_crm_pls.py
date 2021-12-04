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
        state_values = ['correct', 'incorrect', None]
        source_ids = self.env['utm.source'].search([], limit=3).ids
        state_ids = self.env['res.country.state'].search([], limit=3).ids
        country_ids = self.env['res.country'].search([], limit=3).ids
        stage_ids = self.env['crm.stage'].search([], limit=3).ids
        team_ids = self.env['crm.team'].create([{'name': 'Team Test 1'}, {'name': 'Team Test 2'}]).ids
        # create bunch of lost and won crm_lead
        leads_to_create = []
        #   for team 1
        for i in range(3):
            leads_to_create.append(self._get_lead_values(team_ids[0], 'team_1_%s' % str(i), country_ids[i], state_ids[i], state_values[i], state_values[i], source_ids[i], stage_ids[i]))
        leads_to_create.append(
            self._get_lead_values(team_ids[0], 'team_1_%s' % str(3), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[2], stage_ids[1]))
        #   for team 2
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(0), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[1], stage_ids[2]))
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(1), country_ids[0], state_ids[1], state_values[0], state_values[1], source_ids[2], stage_ids[1]))
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(2), country_ids[0], state_ids[2], state_values[0], state_values[1], source_ids[2], stage_ids[0]))
        leads_to_create.append(
            self._get_lead_values(team_ids[1], 'team_2_%s' % str(3), country_ids[0], state_ids[1], state_values[2], state_values[0], source_ids[2], stage_ids[1]))

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
        leads[4].action_set_lost()
        leads[5].action_set_lost()
        leads[6].action_set_won()

        # rebuild frequencies table and recompute automated_probability for all leads.
        Lead._cron_update_automated_probabilities()

        # As the cron is computing and writing in SQL queries, we need to invalidate the cache
        leads.invalidate_cache()

        self.assertEquals(tools.float_compare(leads[3].automated_probability, 33.49, 2), 0)
        self.assertEquals(tools.float_compare(leads[7].automated_probability, 7.74, 2), 0)

    def test_settings_pls_start_date(self):
        # We test here that settings never crash due to ill-configured config param 'crm.pls_start_date'
        set_param = self.env['ir.config_parameter'].sudo().set_param
        str_date_8_days_ago = fields.Date.to_string(fields.Date.today() - timedelta(days=8))
        resConfig = self.env['res.config.settings']

        set_param("crm.pls_start_date", "2021-10-10")
        res_config_new = resConfig.new()
        self.assertEqual(fields.Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            "2021-10-10", "If config param is a valid date, date in settings it should match with config param")

        set_param("crm.pls_start_date", "")
        res_config_new = resConfig.new()
        self.assertEqual(fields.Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            str_date_8_days_ago, "If config param is empty, date in settings should be set to 8 days before today")

        set_param("crm.pls_start_date", "One does not simply walk into system parameters to corrupt them")
        res_config_new = resConfig.new()
        self.assertEqual(fields.Date.to_string(res_config_new.predictive_lead_scoring_start_date),
            str_date_8_days_ago, "If config param is not a valid date, date in settings should be set to 8 days before today")
