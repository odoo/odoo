# -*- coding: utf-8 -*-

from odoo.tests import common


class TestCrmLeadFindStage(common.TransactionCase):

    def test_crm_lead_find_stage(self):
        """ Tests for Test Crm Lead Find Stage """
        CrmLead = self.env['crm.lead']
        CrmStage = self.env['crm.stage']

        # I create a new lead.
        test_crm_lead_new = CrmLead.create({
            'type': "lead",
            'name': "Test lead new",
            'partner_id': self.ref("base.res_partner_1"),
            'description': "This is the description of the test new lead.",
            'team_id': self.ref("sales_team.team_sales_department")
        })

        # I change type from lead to opportunity.
        test_crm_lead_new.convert_opportunity(self.env.ref("base.res_partner_2"))

        # I check default stage of opportunity.
        self.assertTrue(test_crm_lead_new.stage_id.sequence <= 1, 'Default stage of opportunity is incorrect!')

        # Now I change the stage of opportunity to won.
        test_crm_lead_new.action_set_won()

        # I check stage of opp should won, after change stage.
        stage_id = test_crm_lead_new.stage_find(test_crm_lead_new.team_id.id, [('probability', '=', 100.0)])
        self.assertEqual(stage_id, test_crm_lead_new.stage_id.id, 'Stage of opportunity is incorrect!')
