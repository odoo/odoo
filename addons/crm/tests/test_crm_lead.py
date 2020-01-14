# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.common import TestCrmCommon, INCOMING_EMAIL
from odoo.tests.common import users


class TestCRMLead(TestCrmCommon):

    @users('user_sales_manager')
    def test_crm_lead_creation_partner(self):
        lead = self.env['crm.lead'].create({
            'name': 'TestLead',
            'contact_name': 'Raoulette TestContact',
            'email_from': '"Raoulette TestContact" <raoulette@test.example.com>',
        })
        self.assertEqual(lead.type, 'lead')
        self.assertEqual(lead.user_id, self.user_sales_manager)
        self.assertEqual(lead.team_id, self.sales_team_1)
        self.assertEqual(lead.stage_id, self.stage_team1_1)
        self.assertEqual(lead.contact_name, 'Raoulette TestContact')
        self.assertEqual(lead.email_from, '"Raoulette TestContact" <raoulette@test.example.com>')

        # update to a partner, should udpate address
        lead.write({'partner_id': self.contact_1.id})
        # self.assertEqual(lead.partner_name, self.contact_company_1.name)
        # self.assertEqual(lead.contact_name, self.contact_1.name)
        # self.assertEqual(lead.email_from, self.contact_1.email)
        # self.assertEqual(lead.street, self.contact_1.street)
        # self.assertEqual(lead.city, self.contact_1.city)
        # self.assertEqual(lead.zip, self.contact_1.zip)
        # self.assertEqual(lead.country_id, self.contact_1.country_id)

    @users('user_sales_manager')
    def test_crm_lead_stages(self):
        lead = self.lead_1.with_user(self.env.user)
        self.assertEqual(lead.team_id, self.sales_team_1)

        lead.convert_opportunity(self.contact_1.id)
        self.assertEqual(lead.team_id, self.sales_team_1)

        lead.action_set_won()
        self.assertEqual(lead.probability, 100.0)
        self.assertEqual(lead.stage_id, self.stage_gen_won)  # generic won stage has lower sequence than team won stage

    @users('user_sales_manager')
    def test_crm_team_alias(self):
        new_team = self.env['crm.team'].create({
            'name': 'TestAlias',
            'use_leads': True,
            'use_opportunities': True,
            'alias_name': 'test.alias'
        })
        self.assertEqual(new_team.alias_id.alias_name, 'test.alias')
        self.assertEqual(new_team.alias_name, 'test.alias')

        new_team.write({
            'use_leads': False,
            'use_opportunities': False,
        })
        # self.assertFalse(new_team.alias_id.alias_name)
        # self.assertFalse(new_team.alias_name)

    def test_mailgateway(self):
        new_lead = self.format_and_process(
            INCOMING_EMAIL,
            'unknown.sender@test.example.com',
            '%s@%s' % (self.sales_team_1.alias_name, self.alias_domain),
            subject='Delivery cost inquiry',
            target_model='crm.lead',
        )
        self.assertEqual(new_lead.email_from, 'unknown.sender@test.example.com')
        self.assertFalse(new_lead.partner_id)
        self.assertEqual(new_lead.name, 'Delivery cost inquiry')

        message = new_lead.with_user(self.user_sales_manager).message_post(
            body='Here is my offer !',
            subtype_xmlid='mail.mt_comment')
        self.assertEqual(message.author_id, self.user_sales_manager.partner_id)

        new_partner_id = new_lead.handle_partner_assignation(action='create')[new_lead.id]
        new_partner = self.env['res.partner'].with_user(self.user_sales_manager).browse(new_partner_id)
        self.assertEqual(new_partner.email, 'unknown.sender@test.example.com')
        self.assertEqual(new_partner.team_id, self.sales_team_1)

    def test_crm_lead_merge(self):
        # During a mixed merge (involving leads and opps), data should be handled a certain way following their type
        # (m2o, m2m, text, ...)  Start by creating two leads and an opp and giving the rights of Sales manager.
        default_stage_id = self.stage_team1_1.id
        LeadSalesmanager = self.env['crm.lead'].with_user(self.user_sales_manager)

        # TEST CASE 1
        test_crm_opp_01 = LeadSalesmanager.create({
            'type': 'opportunity',
            'name': 'Test opportunity 1',
            'partner_id': self.contact_2.id,
            'stage_id': default_stage_id,
            'description': 'This is the description of the test opp 1.'
        })

        test_crm_lead_01 = LeadSalesmanager.create({
            'type': 'lead',
            'name': 'Test lead first',
            'partner_id': self.contact_1.id,
            'stage_id': default_stage_id,
            'description': 'This is the description of the test lead first.'
        })

        test_crm_lead_02 = LeadSalesmanager.create({
            'type': 'lead',
            'name': 'Test lead second',
            'partner_id': self.contact_1.id,
            'stage_id': default_stage_id,
            'description': 'This is the description of the test lead second.'
        })

        lead_ids = [test_crm_opp_01.id, test_crm_lead_01.id, test_crm_lead_02.id]
        additionnal_context = {'active_model': 'crm.lead', 'active_ids': lead_ids, 'active_id': lead_ids[0]}

        # I create a merge wizard and merge the leads and opp together in the first item of the list.
        merge_opp_wizard_01 = self.env['crm.merge.opportunity'].with_user(self.user_sales_manager).with_context(**additionnal_context).create({})
        merge_opp_wizard_01.action_merge()

        # I check for the resulting merged opp (based on name and partner)
        merged_lead = self.env['crm.lead'].search([('name', '=', 'Test opportunity 1'), ('partner_id', '=', self.contact_2.id)], limit=1)
        self.assertTrue(merged_lead, 'Fail to create merge opportunity wizard')
        self.assertEqual(merged_lead.description, 'This is the description of the test opp 1.\n\nThis is the description of the test lead first.\n\nThis is the description of the test lead second.', 'Description mismatch: when merging leads/opps with different text values, these values should get concatenated and separated with line returns')
        self.assertEqual(merged_lead.type, 'opportunity', 'Type mismatch: when at least one opp in involved in the merge, the result should be a new opp (instead of %s)' % merged_lead.type)

        # The other (tailing) leads/opps shouldn't exist anymore
        self.assertFalse(test_crm_lead_01.exists(), 'This tailing lead (id %s) should not exist anymore' % test_crm_lead_02.id)
        self.assertFalse(test_crm_lead_02.exists(), 'This tailing opp (id %s) should not exist anymore' % test_crm_opp_01.id)

        # TEST CASE 2
        # I want to test leads merge.  Start by creating two leads (with the same partner)
        test_crm_lead_03 = LeadSalesmanager.create({
            'type': 'lead',
            'name': 'Test lead 3',
            'partner_id': self.contact_1.id,
            'stage_id': default_stage_id
        })

        test_crm_lead_04 = LeadSalesmanager.create({
            'type': 'lead',
            'name': 'Test lead 4',
            'partner_id': self.contact_1.id,
            'stage_id': default_stage_id
        })

        lead_ids = [test_crm_lead_03.id, test_crm_lead_04.id]
        additionnal_context = {'active_model': 'crm.lead', 'active_ids': lead_ids, 'active_id': lead_ids[0]}

        # I create a merge wizard and merge the leads together.
        merge_opp_wizard_02 = self.env['crm.merge.opportunity'].with_user(self.user_sales_manager).with_context(**additionnal_context).create({})
        merge_opp_wizard_02.action_merge()

        # I check for the resulting merged lead (based on name and partner)
        merged_lead = self.env['crm.lead'].search([('name', '=', 'Test lead 3'), ('partner_id', '=', self.contact_1.id)], limit=1)
        self.assertTrue(merged_lead, 'Fail to create merge opportunity wizard')
        self.assertEqual(merged_lead.partner_id.id, self.contact_1.id, 'Partner mismatch')
        self.assertEqual(merged_lead.type, 'lead', 'Type mismatch: when leads get merged together, the result should be a new lead (instead of %s)' % merged_lead.type)
        self.assertFalse(test_crm_lead_04.exists(), 'This tailing lead (id %s) should not exist anymore' % test_crm_lead_04.id)

        # TEST CASE 3
        # I want to test opps merge.  Start by creating two opportunities (with the same partner).
        test_crm_opp_02 = LeadSalesmanager.create({
            'type': 'opportunity',
            'name': 'Test opportunity 2',
            'partner_id': self.contact_2.id,
            'stage_id': default_stage_id
        })

        test_crm_opp_03 = LeadSalesmanager.create({
            'type': 'opportunity',
            'name': 'Test opportunity 3',
            'partner_id': self.contact_2.id,
            'stage_id': default_stage_id
        })

        opportunity_ids = [test_crm_opp_02.id, test_crm_opp_03.id]
        additionnal_context = {'active_model': 'crm.lead', 'active_ids': opportunity_ids, 'active_id': opportunity_ids[0]}

        # I create a merge wizard and merge the opps together.
        merge_opp_wizard_03 = self.env['crm.merge.opportunity'].with_user(self.user_sales_manager).with_context(**additionnal_context).create({})
        merge_opp_wizard_03.action_merge()

        merged_opportunity = self.env['crm.lead'].search([('name', '=', 'Test opportunity 2'), ('partner_id', '=', self.contact_2.id)], limit=1)
        self.assertTrue(merged_opportunity, 'Fail to create merge opportunity wizard')
        self.assertEqual(merged_opportunity.partner_id.id, self.contact_2.id, 'Partner mismatch')
        self.assertEqual(merged_opportunity.type, 'opportunity', 'Type mismatch: when opps get merged together, the result should be a new opp (instead of %s)' % merged_opportunity.type)
        self.assertFalse(test_crm_opp_03.exists(), 'This tailing opp (id %s) should not exist anymore' % test_crm_opp_03.id)
