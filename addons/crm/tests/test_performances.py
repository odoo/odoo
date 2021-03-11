# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo.addons.crm.tests.test_crm_lead_assignment import TestLeadAssignCommon
from odoo.tests.common import tagged
from odoo.tools import mute_logger


@tagged('lead_assign')
class TestLeadAssignPerf(TestLeadAssignCommon):
    """ Test performances of lead assignment feature added in saas-14.2

    Assign process is a random process: randomizing teams leads to searching,
    assigning and de-duplicating leads in various order. As a lot of search
    are implied during assign process query counters may vary from run to run.
    "Heavy" performance test included here ranged from 6K to 6.3K queries. Either
    we set high counters maximum which makes those tests less useful. Either we
    avoid random if possible which is what we decided to do by setting the seed
    of random in tests.
    """

    @classmethod
    def setUpClass(cls):
        super(TestLeadAssignPerf, cls).setUpClass()
        random.seed(2042)

    @mute_logger('odoo.models.unlink', 'odoo.addons.crm.models.crm_team', 'odoo.addons.crm.models.crm_team_member')
    def test_assign_perf_duplicates(self):
        """ Test assign process with duplicates on partner. Allow to ensure notably
        that de duplication is effectively performed. """
        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            partner_ids=[self.contact_1.id, self.contact_2.id, False, False, False],
            count=50
        )
        self.assertInitialData()

        # assign probability to leads (bypass auto probability as purpose is not to test pls)
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        for idx in range(0, 5):
            sliced_leads = leads[idx:len(leads):5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)

        with self.with_user('user_sales_manager'):
            with self.assertQueryCount(user_sales_manager=477):  # crm only: 466
                self.env['crm.team'].browse(self.sales_teams.ids)._action_assign_leads(work_days=2)

        # teams assign
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        leads_st1 = leads.filtered_domain([('team_id', '=', self.sales_team_1.id)])
        leads_stc = leads.filtered_domain([('team_id', '=', self.sales_team_convert.id)])
        self.assertEqual(len(leads_st1), 10)  # 2 * 2 * 75 / 30.0
        self.assertEqual(len(leads_stc), 12)  # 2 * 2 * 90 / 30.0

        # salespersons assign
        self.members.invalidate_cache(fnames=['lead_month_count'])
        self.assertMemberAssign(self.sales_team_1_m1, 3)  # 45 max on 2 days
        self.assertMemberAssign(self.sales_team_1_m2, 1)  # 15 max on 2 days
        self.assertMemberAssign(self.sales_team_1_m3, 1)  # 15 max on 2 days
        self.assertMemberAssign(self.sales_team_convert_m1, 2)  # 30 max on 15
        self.assertMemberAssign(self.sales_team_convert_m2, 4)  # 60 max on 15

        # run a second round to finish leads
        with self.with_user('user_sales_manager'):
            with self.assertQueryCount(user_sales_manager=137):  # crm only: 128
                self.env['crm.team'].browse(self.sales_teams.ids)._action_assign_leads(work_days=2)

        # teams assign: everything should be done due to duplicates
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        self.assertTrue(len(leads.filtered_domain([('team_id', '=', False)])) == 0)

        # deduplicate should have removed all duplicated linked to contact_1 and contact_2
        new_assigned_leads_wpartner = self.env['crm.lead'].search([
            ('partner_id', 'in', (self.contact_1 | self.contact_2).ids),
            ('id', 'in', leads.ids)
        ])
        self.assertEqual(len(new_assigned_leads_wpartner), 2)

    @mute_logger('odoo.models.unlink', 'odoo.addons.crm.models.crm_team', 'odoo.addons.crm.models.crm_team_member')
    def test_assign_perf_no_duplicates(self):
        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            partner_ids=[False],
            count=50
        )
        self.assertInitialData()

        # assign probability to leads (bypass auto probability as purpose is not to test pls)
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        for idx in range(0, 5):
            sliced_leads = leads[idx:len(leads):5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)

        with self.with_user('user_sales_manager'):
            with self.assertQueryCount(user_sales_manager=211):  # crm only: 206
                self.env['crm.team'].browse(self.sales_teams.ids)._action_assign_leads(work_days=2)

        # teams assign
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        leads_st1 = leads.filtered_domain([('team_id', '=', self.sales_team_1.id)])
        leads_stc = leads.filtered_domain([('team_id', '=', self.sales_team_convert.id)])
        self.assertEqual(len(leads_st1), 10)  # 2 * 2 * 75 / 30.0
        self.assertEqual(len(leads_stc), 12)  # 2 * 2 * 90 / 30.0

        # salespersons assign
        self.members.invalidate_cache(fnames=['lead_month_count'])
        self.assertMemberAssign(self.sales_team_1_m1, 3)  # 45 max on 2 days
        self.assertMemberAssign(self.sales_team_1_m2, 1)  # 15 max on 2 days
        self.assertMemberAssign(self.sales_team_1_m3, 1)  # 15 max on 2 days
        self.assertMemberAssign(self.sales_team_convert_m1, 2)  # 30 max on 15
        self.assertMemberAssign(self.sales_team_convert_m2, 4)  # 60 max on 15

    @mute_logger('odoo.models.unlink', 'odoo.addons.crm.models.crm_team', 'odoo.addons.crm.models.crm_team_member')
    def test_assign_perf_populated(self):
        """ Test assignment on a more high volume oriented test set in order to
        have more insights on query counts. """
        # create leads enough to have interesting counters
        _lead_count, _email_dup_count, _partner_count = 500, 50, 150
        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            partner_count=_partner_count,
            country_ids=[self.env.ref('base.be').id, self.env.ref('base.fr').id, False],
            count=_lead_count,
            email_dup_count=_email_dup_count)
        self.assertInitialData()
        # assign for one month, aka a lot
        self.env.ref('crm.ir_cron_crm_lead_assign').write({'interval_type': 'days', 'interval_number': 30})
        self.env['ir.config_parameter'].set_param('crm.assignment.bundle', '20')
        # create a third team
        sales_team_3 = self.env['crm.team'].create({
            'name': 'Sales Team 3',
            'sequence': 15,
            'alias_name': False,
            'use_leads': True,
            'use_opportunities': True,
            'company_id': False,
            'user_id': False,
            'assignment_domain': [('country_id', '!=', False)],
        })
        sales_team_3_m1 = self.env['crm.team.member'].create({
            'user_id': self.user_sales_manager.id,
            'crm_team_id': sales_team_3.id,
            'assignment_max': 60,
            'assignment_domain': False,
        })
        sales_team_3_m2 = self.env['crm.team.member'].create({
            'user_id': self.user_sales_leads.id,
            'crm_team_id': sales_team_3.id,
            'assignment_max': 60,
            'assignment_domain': False,
        })
        sales_team_3_m3 = self.env['crm.team.member'].create({
            'user_id': self.user_sales_salesman.id,
            'crm_team_id': sales_team_3.id,
            'assignment_max': 15,
            'assignment_domain': [('probability', '>=', 10)],
        })
        sales_teams = self.sales_teams | sales_team_3
        self.assertEqual(sum(team.assignment_max for team in sales_teams), 300)
        self.assertEqual(len(leads), 550)

        # assign probability to leads (bypass auto probability as purpose is not to test pls)
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        for idx in range(0, 5):
            sliced_leads = leads[idx:len(leads):5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)

        with self.with_user('user_sales_manager'):
            with self.assertQueryCount(user_sales_manager=6250):  # crm only: 6237
                self.env['crm.team'].browse(sales_teams.ids)._action_assign_leads(work_days=30)

        self.members.invalidate_cache(fnames=['lead_month_count'])
        self.assertMemberAssign(self.sales_team_1_m1, 45)  # 45 max on one month
        self.assertMemberAssign(self.sales_team_1_m2, 15)  # 15 max on one month
        self.assertMemberAssign(self.sales_team_1_m3, 15)  # 15 max on one month
        self.assertMemberAssign(self.sales_team_convert_m1, 30)  # 30 max on one month
        self.assertMemberAssign(self.sales_team_convert_m2, 60)  # 60 max on one month
        self.assertMemberAssign(sales_team_3_m1, 60)  # 60 max on one month
        self.assertMemberAssign(sales_team_3_m2, 60)  # 60 max on one month
        self.assertMemberAssign(sales_team_3_m3, 15)  # 15 max on one month
