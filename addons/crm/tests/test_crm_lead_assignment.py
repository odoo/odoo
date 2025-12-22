# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from datetime import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.crm.tests.common import TestLeadConvertCommon
from odoo.tests.common import tagged
from odoo.tools import mute_logger


class TestLeadAssignCommon(TestLeadConvertCommon):

    @classmethod
    def setUpClass(cls):
        super(TestLeadAssignCommon, cls).setUpClass()
        cls._switch_to_multi_membership()
        cls._switch_to_auto_assign()

        # don't mess with existing teams, deactivate them to make tests repeatable
        cls.sales_teams = cls.sales_team_1 + cls.sales_team_convert
        cls.members = cls.sales_team_1_m1 + cls.sales_team_1_m2 + cls.sales_team_1_m3 + cls.sales_team_convert_m1 + cls.sales_team_convert_m2
        cls.env['crm.team'].search([('id', 'not in', cls.sales_teams.ids)]).write({'active': False})

        # don't mess with existing leads, unlink those assigned to users used here to make tests
        # repeatable (archive is not sufficient because of lost leads)

        with mute_logger('odoo.models.unlink'):
            cls.env['crm.lead'].with_context(active_test=False).search(['|', ('team_id', '=', False), ('user_id', 'in', cls.sales_teams.member_ids.ids)]).unlink()
        cls.bundle_size = 50
        cls.env['ir.config_parameter'].set_param('crm.assignment.commit.bundle', '%s' % cls.bundle_size)
        cls.env['ir.config_parameter'].set_param('crm.assignment.delay', '0')

    def assertInitialData(self):
        self.assertEqual(self.sales_team_1.assignment_max, 75)
        self.assertEqual(self.sales_team_convert.assignment_max, 90)

        # ensure domains
        self.assertEqual(self.sales_team_1.assignment_domain, False)
        self.assertEqual(self.sales_team_1_m1.assignment_domain, False)
        self.assertEqual(self.sales_team_1_m2.assignment_domain, "[('probability', '>=', 10)]")
        self.assertEqual(self.sales_team_1_m3.assignment_domain, "[('probability', '>=', 20)]")

        self.assertEqual(self.sales_team_convert.assignment_domain, "[('priority', 'in', ['1', '2', '3'])]")
        self.assertEqual(self.sales_team_convert_m1.assignment_domain, "[('probability', '>=', 20)]")
        self.assertEqual(self.sales_team_convert_m2.assignment_domain, False)

        # start afresh
        self.assertEqual(self.sales_team_1_m1.lead_month_count, 0)
        self.assertEqual(self.sales_team_1_m2.lead_month_count, 0)
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 0)
        self.assertEqual(self.sales_team_convert_m1.lead_month_count, 0)
        self.assertEqual(self.sales_team_convert_m2.lead_month_count, 0)


@tagged('lead_assign')
class TestLeadAssign(TestLeadAssignCommon):
    """ Test lead assignment feature added in saas-14.2 """

    def test_assign_configuration(self):
        now_patch = datetime(2020, 11, 2, 10, 0, 0)

        with patch.object(fields.Datetime, 'now', return_value=now_patch):
            config = self.env['res.config.settings'].create({
                'crm_use_auto_assignment': True,
                'crm_auto_assignment_action': 'auto',
                'crm_auto_assignment_interval_number': 19,
                'crm_auto_assignment_interval_type': 'hours'
            })
            config._onchange_crm_auto_assignment_run_datetime()
            config.execute()
            self.assertTrue(self.assign_cron.active)
            self.assertEqual(self.assign_cron.nextcall, datetime(2020, 11, 2, 10, 0, 0) + relativedelta(hours=19))

            config.write({
                'crm_auto_assignment_interval_number': 2,
                'crm_auto_assignment_interval_type': 'days'
            })
            config._onchange_crm_auto_assignment_run_datetime()
            config.execute()
            self.assertTrue(self.assign_cron.active)
            self.assertEqual(self.assign_cron.nextcall, datetime(2020, 11, 2, 10, 0, 0) + relativedelta(days=2))

            config.write({
                'crm_auto_assignment_run_datetime': fields.Datetime.to_string(datetime(2020, 11, 1, 10, 0, 0)),
            })
            config.execute()
            self.assertTrue(self.assign_cron.active)
            self.assertEqual(self.assign_cron.nextcall, datetime(2020, 11, 1, 10, 0, 0))

            config.write({
                'crm_auto_assignment_action': 'manual',
            })
            config.execute()
            self.assertFalse(self.assign_cron.active)
            self.assertEqual(self.assign_cron.nextcall, datetime(2020, 11, 1, 10, 0, 0))

            config.write({
                'crm_use_auto_assignment': False,
                'crm_auto_assignment_action': 'auto',
            })
            config.execute()
            self.assertFalse(self.assign_cron.active)
            self.assertEqual(self.assign_cron.nextcall, datetime(2020, 11, 1, 10, 0, 0))

    def test_assign_count(self):
        """ Test number of assigned leads when dealing with some existing data (leads
        or opportunities) as well as with opt-out management. """
        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            partner_ids=[False, False, False, self.contact_1.id],
            probabilities=[30],
            count=8,
            suffix='Initial',
        )
        # commit probability and related fields
        leads.flush_recordset()
        self.assertInitialData()

        # archived members should not be taken into account
        self.sales_team_1_m1.action_archive()
        # assignment_max = 0 means opt_out
        self.sales_team_1_m2.assignment_max = 0

        # assign probability to leads (bypass auto probability as purpose is not to test pls)
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        for idx, lead in enumerate(leads):
            lead.probability = idx * 10
        # commit probability and related fields
        leads.flush_recordset()
        self.assertEqual(leads[0].probability, 0)

        # create exiting leads for user_sales_salesman (sales_team_1_m3, sales_team_convert_m1)
        existing_leads = self._create_leads_batch(
            lead_type='lead', user_ids=[self.user_sales_salesman.id],
            probabilities=[10],
            count=14,
            suffix='Existing')
        self.assertEqual(existing_leads.team_id, self.sales_team_1, "Team should have lower sequence")
        existing_leads[0].active = False  # lost
        existing_leads[1].probability = 100  # not won
        existing_leads[2].probability = 0  # not lost
        existing_leads.flush_recordset()

        self.members.invalidate_model(['lead_month_count'])
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 14)
        self.assertEqual(self.sales_team_convert_m1.lead_month_count, 0)

        # re-assign existing leads, check monthly count is updated
        existing_leads[-2:]._handle_salesmen_assignment(user_ids=self.user_sales_manager.ids)
        # commit probability and related fields
        leads.flush_recordset()
        self.members.invalidate_model(['lead_month_count'])
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 12)

        # sales_team_1_m2 is opt-out (new field in 14.3) -> even with max, no lead assigned
        self.sales_team_1_m2.update({'assignment_max': 45, 'assignment_optout': True})
        self.sales_team_1_m3.update({'assignment_max': 45})
        with self.with_user('user_sales_manager'):
            teams_data, members_data = self.sales_team_1._action_assign_leads(force_quota=True)

        Leads = self.env['crm.lead']

        self.assertEqual(
            sorted(Leads.browse(teams_data[self.sales_team_1]['assigned']).mapped('name')),
            ['TestLeadInitial_0000', 'TestLeadInitial_0001', 'TestLeadInitial_0002',
             'TestLeadInitial_0004', 'TestLeadInitial_0005', 'TestLeadInitial_0006']
        )
        self.assertEqual(
            Leads.browse(teams_data[self.sales_team_1]['merged']).mapped('name'),
            ['TestLeadInitial_0003']
        )

        self.assertEqual(len(teams_data[self.sales_team_1]['duplicates']), 1)

        self.assertEqual(
            sorted(members_data[self.sales_team_1_m3]['assigned'].mapped('name')),
            ['TestLeadInitial_0000', 'TestLeadInitial_0005']
        )

        # salespersons assign
        self.members.invalidate_model(['lead_month_count'])
        self.assertEqual(self.sales_team_1_m1.lead_month_count, 0)  # archived do not get leads
        self.assertEqual(self.sales_team_1_m2.lead_month_count, 0)  # opt-out through assignment_max = 0
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 14)  # ignore actual quota (round(45/30) => +2) + existing 12

        with self.with_user('user_sales_manager'):
            self.env['crm.team'].browse(self.sales_team_1.ids)._action_assign_leads(force_quota=True)

        # salespersons assign
        self.members.invalidate_model(['lead_month_count'])
        self.assertEqual(self.sales_team_1_m1.lead_month_count, 0)  # archived do not get leads
        self.assertEqual(self.sales_team_1_m2.lead_month_count, 0)  # opt-out through assignment_max = 0
        self.assertEqual(self.sales_team_1_m3.lead_month_count, 16)  # ignore actual quota (round(45/30) => +2) + existing 14 and not capped anymore

    @mute_logger('odoo.models.unlink')
    def test_assign_duplicates(self):
        """ Test assign process with duplicates on partner. Allow to ensure notably
        that de duplication is effectively performed. """
        # fix the seed and avoid randomness
        random.seed(1940)

        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            partner_ids=[self.contact_1.id, self.contact_2.id, False, False, False],
            count=200
        )
        # commit probability and related fields
        leads.flush_recordset()
        self.assertInitialData()

        # assign probability to leads (bypass auto probability as purpose is not to test pls)
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        for idx in range(0, 5):
            sliced_leads = leads[idx:len(leads):5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)
        # commit probability and related fields
        leads.flush_recordset()

        with self.with_user('user_sales_manager'):
            self.env['crm.team'].browse(self.sales_teams.ids)._action_assign_leads()

        # teams assign
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        self.assertEqual(len(leads), 122)
        leads_st1 = leads.filtered_domain([('team_id', '=', self.sales_team_1.id)])
        leads_stc = leads.filtered_domain([('team_id', '=', self.sales_team_convert.id)])

        # check random globally assigned enough leads to team
        self.assertEqual(len(leads_st1), 76)
        self.assertEqual(len(leads_stc), 46)
        self.assertEqual(len(leads_st1) + len(leads_stc), len(leads))  # Make sure all lead are assigned

        # salespersons assign
        self.members.invalidate_model(['lead_month_count', 'lead_day_count'])
        self.assertMemberAssign(self.sales_team_1_m1, 2)  # 45 max on one month -> 2 daily
        self.assertMemberAssign(self.sales_team_1_m2, 1)  # 15 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_1_m3, 1)  # 15 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_convert_m1, 1)  # 30 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_convert_m2, 2)  # 60 max on one month -> 2 daily

        # teams assign: everything should be done due to duplicates
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        self.assertEqual(len(leads.filtered_domain([('team_id', '=', False)])), 0)

        # deduplicate should have removed all duplicated linked to contact_1 and contact_2
        new_assigned_leads_wpartner = self.env['crm.lead'].search([
            ('partner_id', 'in', (self.contact_1 | self.contact_2).ids),
            ('id', 'in', leads.ids)
        ])
        self.assertEqual(len(new_assigned_leads_wpartner), 2)

    @mute_logger('odoo.models.unlink')
    def test_assign_no_duplicates(self):
        # fix the seed and avoid randomness
        random.seed(1945)

        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            partner_ids=[False],
            count=150
        )
        # commit probability and related fields
        leads.flush_recordset()
        self.assertInitialData()

        # assign probability to leads (bypass auto probability as purpose is not to test pls)
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        for idx in range(0, 5):
            sliced_leads = leads[idx:len(leads):5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)
        # commit probability and related fields
        leads.flush_recordset()

        with self.with_user('user_sales_manager'):
            self.env['crm.team'].browse(self.sales_teams.ids)._action_assign_leads()

        # teams assign
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        leads_st1 = leads.filtered_domain([('team_id', '=', self.sales_team_1.id)])
        leads_stc = leads.filtered_domain([('team_id', '=', self.sales_team_convert.id)])
        self.assertEqual(len(leads), 150)

        # check random globally assigned enough leads to team
        self.assertEqual(len(leads_st1), 104)
        self.assertEqual(len(leads_stc), 46)
        self.assertEqual(len(leads_st1) + len(leads_stc), len(leads))  # Make sure all lead are assigned

        # salespersons assign
        self.members.invalidate_model(['lead_month_count', 'lead_day_count'])
        self.assertMemberAssign(self.sales_team_1_m1, 2)  # 45 max on one month -> 2 daily
        self.assertMemberAssign(self.sales_team_1_m2, 1)  # 15 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_1_m3, 1)  # 15 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_convert_m1, 1)  # 30 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_convert_m2, 2)  # 60 max on one month -> 2 daily

    @mute_logger('odoo.models.unlink')
    def test_assign_populated(self):
        """ Test assignment on a more high volume oriented test set in order to
        test more real life use cases. """
        # fix the seed and avoid randomness (funny: try 1870)
        random.seed(1871)

        # create leads enough to assign one month of work
        _lead_count, _email_dup_count, _partner_count = 600, 50, 150
        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            partner_count=_partner_count,
            country_ids=[self.env.ref('base.be').id, self.env.ref('base.fr').id, False],
            count=_lead_count,
            email_dup_count=_email_dup_count)
        # commit probability and related fields
        leads.flush_recordset()
        self.assertInitialData()

        # assign for one month, aka a lot
        self.env.ref('crm.ir_cron_crm_lead_assign').write({'interval_type': 'days', 'interval_number': 30})
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
        sales_teams = self.sales_teams + sales_team_3
        self.assertEqual(sum(team.assignment_max for team in sales_teams), 300)
        self.assertEqual(len(leads), 650)

        # assign probability to leads (bypass auto probability as purpose is not to test pls)
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])  # ensure order
        for idx in range(0, 5):
            sliced_leads = leads[idx:len(leads):5]
            for lead in sliced_leads:
                lead.probability = (idx + 1) * 10 * ((int(lead.priority) + 1) / 2)
        # commit probability and related fields
        leads.flush_recordset()

        with self.with_user('user_sales_manager'):
            self.env['crm.team'].browse(sales_teams.ids)._action_assign_leads()

        # teams assign
        leads = self.env['crm.lead'].search([('id', 'in', leads.ids)])
        self.assertEqual(leads.team_id, sales_teams)
        self.assertEqual(leads.user_id, sales_teams.member_ids)
        self.assertEqual(len(leads), 600)

        # check random globally assigned enough leads to team
        leads_st1 = leads.filtered_domain([('team_id', '=', self.sales_team_1.id)])
        leads_st2 = leads.filtered_domain([('team_id', '=', self.sales_team_convert.id)])
        leads_st3 = leads.filtered_domain([('team_id', '=', sales_team_3.id)])
        self.assertEqual(len(leads_st1), 165)
        self.assertEqual(len(leads_st2), 126)
        self.assertEqual(len(leads_st3), 309)

        # salespersons assign
        self.members.invalidate_model(['lead_month_count', 'lead_day_count'])
        self.assertMemberAssign(self.sales_team_1_m1, 2)  # 45 max on one month -> 2 daily
        self.assertMemberAssign(self.sales_team_1_m2, 1)  # 15 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_1_m3, 1)  # 15 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_convert_m1, 1)  # 30 max on one month -> 1 daily
        self.assertMemberAssign(self.sales_team_convert_m2, 2)  # 60 max on one month -> 2 daily
        self.assertMemberAssign(sales_team_3_m1, 2)  # 60 max on one month -> 2 daily
        self.assertMemberAssign(sales_team_3_m2, 2)  # 60 max on one month -> 2 daily
        self.assertMemberAssign(sales_team_3_m3, 1)  # 15 max on one month -> 1 daily

    def test_assign_quota(self):
        """ Test quota computation """
        self.assertInitialData()

        # quota computation without existing leads
        self.assertEqual(
            self.sales_team_1_m1._get_assignment_quota(),
            2,
            "Assignment quota: 45 max -> 2 daily (round(45/30))"
        )

        # create exiting leads for user_sales_leads (sales_team_1_m1)
        existing_leads = self._create_leads_batch(
            lead_type='lead', user_ids=[self.user_sales_leads.id],
            probabilities=[10],
            count=30)
        self.assertEqual(existing_leads.team_id, self.sales_team_1, "Team should have lower sequence")
        existing_leads.flush_recordset()

        self.sales_team_1_m1.invalidate_model(['lead_month_count', 'lead_day_count'])
        self.assertEqual(self.sales_team_1_m1.lead_month_count, 30)
        self.assertEqual(self.sales_team_1_m1.lead_day_count, 30)

        # quota computation with existing leads
        self.assertEqual(
            self.sales_team_1_m1._get_assignment_quota(),
            -28,
            "Assignment quota: 45 max -> 2 daily ; 30 daily lead already assign -> 2 - 30 -> -28"
        )
        self.assertEqual(
            self.sales_team_1_m1._get_assignment_quota(True),
            2,
            "Assignment quota: 45 max ignoring existing daily lead -> 2"
        )

    def test_assign_specific_won_lost(self):
        """ Test leads taken into account in assign process: won, lost, stage
        configuration. """
        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            partner_ids=[False, False, False, self.contact_1.id],
            probabilities=[30],
            count=6
        )
        leads[0].stage_id = self.stage_gen_won.id  # is won -> should not be taken into account
        leads[1].stage_id = False
        leads[2].update({'stage_id': False, 'probability': 0})
        leads[3].update({'stage_id': False, 'probability': False})
        leads[4].active = False  # is lost -> should not be taken into account
        leads[5].update({'team_id': self.sales_team_convert.id, 'user_id': self.user_sales_manager.id})  # assigned lead should not be re-assigned

        # commit probability and related fields
        leads.flush_recordset()

        self.sales_team_1.crm_team_member_ids.write({'assignment_max': 45})
        with self.with_user('user_sales_manager'):
            self.env['crm.team'].browse(self.sales_team_1.ids)._action_assign_leads()

        self.assertEqual(leads[0].team_id, self.env['crm.team'], 'Won lead should not be assigned')
        self.assertEqual(leads[0].user_id, self.env['res.users'], 'Won lead should not be assigned')
        for lead in leads[1:4]:
            self.assertIn(lead.user_id, self.sales_team_1.member_ids)
            self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(leads[4].team_id, self.env['crm.team'], 'Lost lead should not be assigned')
        self.assertEqual(leads[4].user_id, self.env['res.users'], 'Lost lead should not be assigned')
        self.assertEqual(leads[5].team_id, self.sales_team_convert, 'Assigned lead should not be reassigned')
        self.assertEqual(leads[5].user_id, self.user_sales_manager, 'Assigned lead should not be reassigned')

    def test_assign_team_and_salesperson_on_duplicate_lead(self):
        """Ensure leads duplicated from an existing lead are assigned correctly."""
        duplicate_lead = self.env['crm.lead'].create({
            'name': 'Test Lead',
            'type': 'opportunity',
            'probability': 15,
            'partner_id': self.contact_1.id,
            'team_id': False,
            'user_id': False,
        }).copy()
        self.assertFalse(duplicate_lead.date_open)

        sales_team = self.sales_team_1
        sales_team.assignment_domain = [('user_id', '=', False)]
        with self.with_user('user_sales_manager'):
            sales_team._action_assign_leads()

        self.assertEqual(duplicate_lead.team_id, sales_team)
        self.assertTrue(duplicate_lead.user_id)

    @mute_logger('odoo.models.unlink')
    def test_merge_assign_keep_master_team(self):
        """ Check existing opportunity keep its team and salesman when merged with a new lead """
        sales_team_dupe = self.env['crm.team'].create({
            'name': 'Sales Team Dupe',
            'sequence': 15,
            'alias_name': False,
            'use_leads': True,
            'use_opportunities': True,
            'company_id': False,
            'user_id': False,
            'assignment_domain': "[]",
        })
        self.env['crm.team.member'].create({
            'user_id': self.user_sales_salesman.id,
            'crm_team_id': sales_team_dupe.id,
            'assignment_max': 10,
            'assignment_domain': "[]",
        })

        master_opp = self.env['crm.lead'].create({
            'name': 'Master',
            'type': 'opportunity',
            'probability': 50,
            'partner_id': self.contact_1.id,
            'team_id': self.sales_team_1.id,
            'user_id': self.user_sales_manager.id,
        })
        dupe_lead = self.env['crm.lead'].create({
            'name': 'Dupe',
            'type': 'lead',
            'email_from': 'Duplicate Email <%s>' % master_opp.email_normalized,
            'probability': 10,
            'team_id': False,
            'user_id': False,
        })

        sales_team_dupe._action_assign_leads()
        self.assertFalse(dupe_lead.exists())
        self.assertEqual(master_opp.team_id, self.sales_team_1, 'Opportunity: should keep its sales team')
        self.assertEqual(master_opp.user_id, self.user_sales_manager, 'Opportunity: should keep its salesman')

    def test_no_assign_if_exceed_max_assign(self):
        """ Test no leads being assigned to any team member if weights list sums to 0"""

        leads = self._create_leads_batch(
            lead_type='lead',
            user_ids=[False],
            count=1
        )

        sales_team_4 = self.env['crm.team'].create({
            'name': 'Sales Team 4',
            'sequence': 15,
            'use_leads': True,
        })
        sales_team_4_m1 = self.env['crm.team.member'].create({
            'user_id': self.user_sales_salesman.id,
            'crm_team_id': sales_team_4.id,
            'assignment_max': 30,
        })

        sales_team_4_m1.lead_month_count = 30
        sales_team_4_m1.lead_day_count = 2
        leads.team_id = sales_team_4.id

        members_data = sales_team_4._assign_and_convert_leads()
        self.assertFalse(members_data,
            "If team member has lead count greater than max assign,then do not assign any more")
