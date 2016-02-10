# -*- coding: utf-8 -*-

from .common import TestCrmCases

class TestCrmLeadOperations(TestCrmCases):

    def test_crm_lead_copy(self):
        """I make duplicate the Lead."""
        self.env.ref('crm.crm_case_4').copy()

    def test_crm_lead_cancel(self):
        lead = self.env.ref('crm.crm_case_1')

        """I set a new sale team giving access rights of salesmanager."""
        team_id = self.env['crm.team'].sudo(self.crm_salemanager_id).create({'name': "Phone Marketing"}).id
        lead.write({'team_id': team_id})

        # Salesmananger check unqualified lead.
        self.assertEqual(lead.stage_id.sequence, 1, 'Lead is in new stage')

    def test_crm_lead_unlink(self):
        """Only Sales manager Unlink the Lead so test with Manager's access rights'."""
        self.env.ref('crm.crm_case_4').unlink()
