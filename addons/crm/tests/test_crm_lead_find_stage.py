# -*- coding: utf-8 -*-

from .common import TestCrmCases


class TestCrmLeadFindStage(TestCrmCases):

    def test_crm_lead_find_stage(self):
        """ Tests for Test Crm Lead Find Stage """

        # I create a new lead.
        lead = self.env['crm.lead'].create({
            'type': "lead",
            'name': "Test lead new",
            'partner_id': self.env.ref("base.res_partner_1").id,
            'description': "This is the description of the test new lead.",
            'team_id': self.env.ref("sales_team.team_sales_department").id
        })

        # I change type from lead to opportunity.
        lead.convert_opportunity(self.env.ref("base.res_partner_2").id)

        # I check default stage of opportunity.
        self.assertTrue(lead.stage_id.sequence <= 1, 'Default stage of opportunity is incorrect!')

        # Now I change the stage of opportunity to won.
        lead.action_set_won()

        # I check stage of opp should won, after change stage.
        stage_id = lead.stage_find(lead.team_id.id, [('probability', '=', 100.0)])
        self.assertEqual(stage_id, lead.stage_id.id, 'Stage of opportunity is incorrect!')
