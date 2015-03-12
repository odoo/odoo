# -*- coding: utf-8 -*-
from openerp.addons.website_crm_score.tests.common import TestScoring
from openerp.tools import mute_logger


class test_assign(TestScoring):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_assign(self):
        cr, uid = self.cr, self.uid
        # scoring
        self.website_crm_score.assign_scores_to_leads(cr, uid)

        l0 = self.crm_lead.read(cr, uid, self.lead0, ['score'], None)
        l1 = self.crm_lead.read(cr, uid, self.lead1, ['score'], None)
        l2 = self.crm_lead.read(cr, uid, self.lead2, ['score'], None)

        self.assertEqual(l0['score'], 1000, 'scoring failed')
        self.assertEqual(l1['score'], 900, 'scoring failed')
        self.assertEqual(l2['score'], 0, 'scoring failed')

        # assignation
        self.team.direct_assign_leads(cr, uid, None)

        l0 = self.crm_lead.read(cr, uid, self.lead0, ['team_id', 'user_id'], None)
        l1 = self.crm_lead.read(cr, uid, self.lead1, ['team_id', 'user_id'], None)
        l2 = self.crm_lead.read(cr, uid, self.lead2, ['team_id', 'user_id'], None)

        self.assertEqual(l0['team_id'][0], self.team0, 'assignation failed')
        self.assertEqual(l1['team_id'][0], self.team1, 'assignation failed')
        self.assertEqual(l2['team_id'], False, 'assignation failed')

        self.assertEqual(l0['user_id'][0], self.salesmen0, 'assignation failed')
        self.assertEqual(l1['user_id'][0], self.salesmen1, 'assignation failed')
        self.assertEqual(l2['user_id'], False, 'assignation failed')
