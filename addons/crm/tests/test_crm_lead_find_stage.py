# -*- coding: utf-8 -*-

from openerp.tests import common

class TestCrmLeadFindStage(common.TransactionCase):

    def test_crm_lead_find_stage(self):
        """ Tests for Test Crm Lead Find Stage """
        CrmLead = self.env['crm.lead']
        CrmStage = self.env['crm.stage']

        # I create a new lead.
        test_crm_lead_new = CrmLead.create(
            dict(
                lead_type="lead",
                name="Test lead new",
                partner_id=self.env.ref("base.res_partner_1").id,
                description="This is the description of the test new lead.",
                team_id=self.env.ref("sales_team.team_sales_department").id,
            ))

        # I check default stage of lead.
        stage = CrmStage.search_read([('sequence', '=', '1')], ['id'])[0]
        stage_id = test_crm_lead_new.stage_find(test_crm_lead_new.team_id.id or False, [])
        self.assertEqual(stage_id, stage['id'], 'Default stage of lead is incorrect!')

        # I change type from lead to opportunity.
        test_crm_lead_new.convert_opportunity(self.env.ref("base.res_partner_2").id)

        # Now I check default stage after change type.
        stage = CrmStage.search_read([('sequence', '=', '1')], ['id'])[0]
        stage_id = test_crm_lead_new.stage_find(test_crm_lead_new.team_id.id or False, [])
        self.assertEqual(stage_id, stage['id'], 'Default stage of opportunity is incorrect!')

        # Now I change the stage of opportunity to won.
        test_crm_lead_new.case_mark_won()

        # I check statge of opp should won, after change stage.
        stage_id = test_crm_lead_new.stage_find(test_crm_lead_new.team_id.id or False, [('probability', '=', '100.0')])
        self.assertEqual(stage_id, test_crm_lead_new.stage_id.id, 'Stage of opportunity is incorrect!')
