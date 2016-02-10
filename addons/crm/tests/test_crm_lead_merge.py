# -*- coding: utf-8 -*-

from .common import TestCrmCases


class TestCrmLeadMerge(TestCrmCases):

    def test_crm_lead_merge(self):
        """ Tests for Test Crm Lead Merge """
        CrmMergeOpportunity = self.env['crm.merge.opportunity']

        partner3_id = self.ref("base.res_partner_3")
        SalesmanLead = self.CrmLead.sudo(self.crm_salemanager_id)

        # During a mixed merge (involving leads and opps), data should be handled a certain way following their type (m2o, m2m, text, ...)  Start by creating two leads and an opp and giving the rights of Sales manager.
        test_crm_opp_01 = SalesmanLead.create({
            'type': 'opportunity',
            'name': 'Test opportunity 1',
            'partner_id': partner3_id,
            'stage_id': self.stage_lead1_id,
            'description': 'This is the description of the test opp 1.'
        })

        test_crm_lead_01 = SalesmanLead.create({
            'type': 'lead',
            'name': 'Test lead first',
            'partner_id': self.partner1_id,
            'stage_id': self.stage_lead1_id,
            'description': 'This is the description of the test lead first.'
        })

        test_crm_lead_02 = SalesmanLead.create({
            'type': 'lead',
            'name': 'Test lead second',
            'partner_id': self.partner1_id,
            'stage_id': self.stage_lead1_id,
            'description': 'This is the description of the test lead second.'
        })

        lead_ids = [test_crm_opp_01.id, test_crm_lead_01.id, test_crm_lead_02.id]
        context = {'active_model': 'crm.lead', 'active_ids': lead_ids, 'active_id': lead_ids[0]}

        # I create a merge wizard and merge the leads and opp together in the first item of the list.
        CrmMergeOpportunity.with_context(context).create({}).action_merge()

        # I check for the resulting merged opp (based on name and partner).
        merge = self.CrmLead.search([('name', '=', 'Test opportunity 1'), ('partner_id', '=', partner3_id)], limit=1)
        self.assertTrue(merge, 'Fail to create merge opportunity wizard')
        self.assertEqual(merge.description, 'This is the description of the test opp 1.\n\nThis is the description of the test lead first.\n\nThis is the description of the test lead second.', 'Description mismatch: when merging leads/opps with different text values, these values should get concatenated and separated with line returns')
        self.assertEqual(merge.type, 'opportunity', 'Type mismatch: when at least one opp in involved in the merge, the result should be a new opp (instead of %s)' % merge.type)

        # The other (tailing) leads/opps shouldn't exist anymore.
        self.assertFalse(test_crm_lead_01.exists(), 'This tailing lead (id %s) should not exist anymore' % test_crm_lead_02.id)

        self.assertFalse(test_crm_lead_02.exists(), 'This tailing opp (id %s) should not exist anymore' % test_crm_opp_01.id)

        # I want to test leads merge. Start by creating two leads (with the same partner).
        test_crm_lead_03 = SalesmanLead.create({
            'type': 'lead',
            'name':'Test lead 3',
            'partner_id': self.partner1_id,
            'stage_id': self.stage_lead1_id
        })

        test_crm_lead_04 = SalesmanLead.create({
            'type': 'lead',
            'name': 'Test lead 4',
            'partner_id': self.partner1_id,
            'stage_id': self.stage_lead1_id
        })

        lead_ids = [test_crm_lead_03.id, test_crm_lead_04.id]
        context = {'active_model': 'crm.lead', 'active_ids': lead_ids, 'active_id': lead_ids[0]}

        # I create a merge wizard and merge the leads together.
        CrmMergeOpportunity.with_context(context).create({}).action_merge()

        # I check for the resulting merged lead (based on name and partner).
        merge_lead = self.CrmLead.search([('name', '=', 'Test lead 3'), ('partner_id', '=', self.partner1_id)], limit=1)
        self.assertTrue(merge_lead, 'Fail to create merge opportunity wizard')
        self.assertEqual(merge_lead.partner_id.id, self.partner1_id, 'Partner mismatch')
        self.assertEqual(merge_lead.type, 'lead', 'Type mismatch: when leads get merged together, the result should be a new lead (instead of %s)' % merge.type)
        self.assertFalse(test_crm_lead_04.exists(), 'This tailing lead (id %s) should not exist anymore' % test_crm_lead_04.id)

        # I want to test opps merge.  Start by creating two opportunities (with the same partner).
        test_crm_opp_02 = SalesmanLead.create({
            'type': 'opportunity',
            'name': 'Test opportunity 2',
            'partner_id': partner3_id,
            'stage_id': self.stage_lead1_id
        })

        test_crm_opp_03 = SalesmanLead.create({
            'type': 'opportunity',
            'name': 'Test opportunity 3',
            'partner_id': partner3_id,
            'stage_id': self.stage_lead1_id
        })

        opp_ids = [test_crm_opp_02.id, test_crm_opp_03.id]
        context = {'active_model': 'crm.lead', 'active_ids': opp_ids, 'active_id': opp_ids[0]}

        # I create a merge wizard and merge the opps together.
        CrmMergeOpportunity.with_context(context).create({}).action_merge()

        merge_opp = self.CrmLead.search([('name', '=', 'Test opportunity 2'), ('partner_id', '=', partner3_id)], limit=1)
        self.assertTrue(merge_opp, 'Fail to create merge opportunity wizard')
        self.assertEqual(merge_opp.partner_id.id, partner3_id, 'Partner mismatch')
        self.assertEqual(merge_opp.type, 'opportunity', 'Type mismatch: when opps get merged together, the result should be a new opp (instead of %s)' % merge.type)
        self.assertFalse(test_crm_opp_03.exists(), 'This tailing opp (id %s) should not exist anymore' % test_crm_opp_03.id)
