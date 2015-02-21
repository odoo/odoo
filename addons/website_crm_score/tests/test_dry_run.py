# -*- coding: utf-8 -*-
from openerp.addons.website_crm_score.tests.common import TestScoring
from openerp.tools import mute_logger


class test_dry_run(TestScoring):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_dry_run(self):
        cr, uid = self.cr, self.uid

        # scoring
        self.website_crm_score.assign_scores_to_leads(cr, uid)

        l0 = self.crm_lead.read(cr, uid, self.lead0, ['score'], None)
        l1 = self.crm_lead.read(cr, uid, self.lead1, ['score'], None)
        l2 = self.crm_lead.read(cr, uid, self.lead2, ['score'], None)

        self.assertEqual(l0['score'], 1000, 'scoring failed')
        self.assertEqual(l1['score'], 900, 'scoring failed')
        self.assertEqual(l2['score'], 0, 'scoring failed')

        # dry run
        self.team.dry_assign_leads(cr, uid, None)

        fields = ['team_id', 'user_id', 'lead_id']

        dr0_sect = self.crm_leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead0), ('user_id', '=', False)], fields)[0]
        dr0_user = self.crm_leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead0), ('user_id', '!=', False)], fields)[0]

        dr1_sect = self.crm_leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead1), ('user_id', '=', False)], fields)[0]
        dr1_user = self.crm_leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead1), ('user_id', '!=', False)], fields)[0]

        dr2 = self.crm_leads_dry_run.search_read(cr, uid, [('lead_id', '=', self.lead2)], fields)

        self.assertEqual(dr0_sect['team_id'][0], self.team0, 'dry run failed')
        self.assertEqual(dr0_user['team_id'][0], self.team0, 'dry run failed')
        self.assertEqual(dr0_user['user_id'][0], self.salesmen0, 'dry run failed')

        self.assertEqual(dr1_sect['team_id'][0], self.team1, 'dry run failed')
        self.assertEqual(dr1_user['team_id'][0], self.team1, 'dry run failed')
        self.assertEqual(dr1_user['user_id'][0], self.salesmen1, 'dry run failed')

        self.assertEqual(dr2, [], 'dry run failed')

        ldr = self.crm_leads_dry_run.search_count(cr, uid, [], None)
        self.assertEqual(ldr, 4, 'wrong number of dry run created')

        # assignement after dry run
        self.crm_leads_dry_run.assign_leads(cr, uid, None)

        l0 = self.crm_lead.read(cr, uid, self.lead0, ['team_id', 'user_id'], None)
        l1 = self.crm_lead.read(cr, uid, self.lead1, ['team_id', 'user_id'], None)
        l2 = self.crm_lead.read(cr, uid, self.lead2, ['team_id', 'user_id'], None)

        self.assertEqual(l0['team_id'][0], self.team0, 'assignation failed')
        self.assertEqual(l1['team_id'][0], self.team1, 'assignation failed')
        self.assertEqual(l2['team_id'], False, 'assignation failed')

        self.assertEqual(l0['user_id'][0], self.salesmen0, 'assignation failed')
        self.assertEqual(l1['user_id'][0], self.salesmen1, 'assignation failed')
        self.assertEqual(l2['user_id'], False, 'assignation failed')

        ldr = self.crm_leads_dry_run.search_count(cr, uid, [], None)

        self.assertEqual(ldr, 0, 'dry run not removed correctly')
