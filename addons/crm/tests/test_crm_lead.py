# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestCrmCases
from odoo.modules.module import get_module_resource


class TestCRMLead(TestCrmCases):

    def test_crm_lead_cancel(self):
        # I set a new sales team giving access rights of salesman.
        team = self.env['crm.team'].with_user(self.crm_salemanager).create({'name': "Phone Marketing"})
        lead = self.env.ref('crm.crm_case_1')
        lead.with_user(self.crm_salemanager).write({'team_id': team.id})
        # Salesmananger check unqualified lead
        self.assertEqual(lead.stage_id.sequence, 1, 'Lead is in new stage')

    def test_crm_lead_copy(self):
        # I make duplicate the Lead
        self.env.ref('crm.crm_case_4').copy()

    def test_crm_lead_unlink(self):
        # Only Sales manager Unlink the Lead so test with Manager's access rights
        self.env.ref('crm.crm_case_4').with_user(self.crm_salemanager).unlink()

    def test_find_stage(self):
        # I create a new lead
        lead = self.env['crm.lead'].create({
            'type': "lead",
            'name': "Test lead new",
            'partner_id': self.env.ref("base.res_partner_1").id,
            'description': "This is the description of the test new lead.",
            'team_id': self.env.ref("sales_team.team_sales_department").id
        })
        # I change type from lead to opportunity
        lead.convert_opportunity(self.env.ref("base.res_partner_2").id)
        # I check default stage of opportunity
        self.assertLessEqual(lead.stage_id.sequence, 1, "Default stage of lead is incorrect!")

        # Now I change the stage of opportunity to won.
        lead.action_set_won()
        # I check stage of opp should won, after change stage.
        stage_id = lead._stage_find(domain=[('is_won', '=', True)])
        self.assertEqual(stage_id, lead.stage_id, "Stage of opportunity is incorrect!")

    def test_crm_lead_message(self):
        # Give the access rights of Salesman to communicate with customer
        # Customer interested in our product, so he sends request by email to get more details.
        # Mail script will fetch his request from mail server. Then I process that mail after read EML file.
        request_file = open(get_module_resource('crm', 'tests', 'customer_request.eml'), 'rb')
        request_message = request_file.read()
        self.env['mail.thread'].with_user(self.crm_salesman).message_process('crm.lead', request_message)

        # After getting the mail, I check details of new lead of that customer
        lead = self.env['crm.lead'].with_user(self.crm_salesman).search([('email_normalized', '=', 'info@customer.com')], limit=1)
        self.assertTrue(lead.ids, 'Fail to create merge opportunity wizard')
        self.assertFalse(lead.partner_id, 'Customer should be a new one')
        self.assertEqual(lead.name, 'Fournir votre devis avec le meilleur prix.', 'Subject does not match')

        # I reply his request with welcome message.
        # TODO revert mail.mail to mail.compose.message (conversion to customer should be automatic).
        lead = self.env['crm.lead'].search([('email_normalized', '=', 'info@customer.com')], limit=1)
        mail = self.env['mail.compose.message'].with_context(active_model='crm.lead', active_id=lead.id).create({
            'body': "Merci de votre intérêt pour notre produit, nous vous contacterons bientôt. Bien à vous",
            'email_from': 'sales@mycompany.com'
        })
        try:
            mail.send_mail()
        except:
            pass

        # Now, I convert him into customer and put him into regular customer list
        lead = self.env['crm.lead'].search([('email_normalized', '=', 'info@customer.com')], limit=1)
        lead.handle_partner_assignation()

    def test_crm_lead_merge(self):
        # During a mixed merge (involving leads and opps), data should be handled a certain way following their type (m2o, m2m, text, ...)  Start by creating two leads and an opp and giving the rights of Sales manager.
        default_stage_id = self.ref("crm.stage_lead1")
        LeadSalesmanager = self.env['crm.lead'].with_user(self.crm_salemanager)

        # TEST CASE 1
        test_crm_opp_01 = LeadSalesmanager.create({
            'type': 'opportunity',
            'name': 'Test opportunity 1',
            'partner_id': self.env.ref("base.res_partner_3").id,
            'stage_id': default_stage_id,
            'description': 'This is the description of the test opp 1.'
        })

        test_crm_lead_01 = LeadSalesmanager.create({
            'type': 'lead',
            'name': 'Test lead first',
            'partner_id': self.env.ref("base.res_partner_1").id,
            'stage_id': default_stage_id,
            'description': 'This is the description of the test lead first.'
        })

        test_crm_lead_02 = LeadSalesmanager.create({
            'type': 'lead',
            'name': 'Test lead second',
            'partner_id': self.env.ref("base.res_partner_1").id,
            'stage_id': default_stage_id,
            'description': 'This is the description of the test lead second.'
        })

        lead_ids = [test_crm_opp_01.id, test_crm_lead_01.id, test_crm_lead_02.id]
        additionnal_context = {'active_model': 'crm.lead', 'active_ids': lead_ids, 'active_id': lead_ids[0]}

        # I create a merge wizard and merge the leads and opp together in the first item of the list.
        merge_opp_wizard_01 = self.env['crm.merge.opportunity'].with_user(self.crm_salemanager).with_context(**additionnal_context).create({})
        merge_opp_wizard_01.action_merge()

        # I check for the resulting merged opp (based on name and partner)
        merged_lead = self.env['crm.lead'].search([('name', '=', 'Test opportunity 1'), ('partner_id', '=', self.env.ref("base.res_partner_3").id)], limit=1)
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
            'partner_id': self.env.ref("base.res_partner_1").id,
            'stage_id': default_stage_id
        })

        test_crm_lead_04 = LeadSalesmanager.create({
            'type': 'lead',
            'name': 'Test lead 4',
            'partner_id': self.env.ref("base.res_partner_1").id,
            'stage_id': default_stage_id
        })

        lead_ids = [test_crm_lead_03.id, test_crm_lead_04.id]
        additionnal_context = {'active_model': 'crm.lead', 'active_ids': lead_ids, 'active_id': lead_ids[0]}

        # I create a merge wizard and merge the leads together.
        merge_opp_wizard_02 = self.env['crm.merge.opportunity'].with_user(self.crm_salemanager).with_context(**additionnal_context).create({})
        merge_opp_wizard_02.action_merge()

        # I check for the resulting merged lead (based on name and partner)
        merged_lead = self.env['crm.lead'].search([('name', '=', 'Test lead 3'), ('partner_id', '=', self.env.ref("base.res_partner_1").id)], limit=1)
        self.assertTrue(merged_lead, 'Fail to create merge opportunity wizard')
        self.assertEqual(merged_lead.partner_id.id, self.env.ref("base.res_partner_1").id, 'Partner mismatch')
        self.assertEqual(merged_lead.type, 'lead', 'Type mismatch: when leads get merged together, the result should be a new lead (instead of %s)' % merged_lead.type)
        self.assertFalse(test_crm_lead_04.exists(), 'This tailing lead (id %s) should not exist anymore' % test_crm_lead_04.id)

        # TEST CASE 3
        # I want to test opps merge.  Start by creating two opportunities (with the same partner).
        test_crm_opp_02 = LeadSalesmanager.create({
            'type': 'opportunity',
            'name': 'Test opportunity 2',
            'partner_id': self.env.ref("base.res_partner_3").id,
            'stage_id': default_stage_id
        })

        test_crm_opp_03 = LeadSalesmanager.create({
            'type': 'opportunity',
            'name': 'Test opportunity 3',
            'partner_id': self.env.ref("base.res_partner_3").id,
            'stage_id': default_stage_id
        })

        opportunity_ids = [test_crm_opp_02.id, test_crm_opp_03.id]
        additionnal_context = {'active_model': 'crm.lead', 'active_ids': opportunity_ids, 'active_id': opportunity_ids[0]}

        # I create a merge wizard and merge the opps together.
        merge_opp_wizard_03 = self.env['crm.merge.opportunity'].with_user(self.crm_salemanager).with_context(**additionnal_context).create({})
        merge_opp_wizard_03.action_merge()

        merged_opportunity = self.env['crm.lead'].search([('name', '=', 'Test opportunity 2'), ('partner_id', '=', self.env.ref("base.res_partner_3").id)], limit=1)
        self.assertTrue(merged_opportunity, 'Fail to create merge opportunity wizard')
        self.assertEqual(merged_opportunity.partner_id.id, self.env.ref("base.res_partner_3").id, 'Partner mismatch')
        self.assertEqual(merged_opportunity.type, 'opportunity', 'Type mismatch: when opps get merged together, the result should be a new opp (instead of %s)' % merged_opportunity.type)
        self.assertFalse(test_crm_opp_03.exists(), 'This tailing opp (id %s) should not exist anymore' % test_crm_opp_03.id)

    def test_lead_won(self):
        """
        As there are multiple ways to set a lead as won (by action_set_won or moving the lead to a won stage)
        The logic behind the set as won is now in the write override to be executed
        each time the new stage is a won stage.
        """
        # Create leads at different stage
        leads_to_create = []
        for i in range(3):
            for x in range(3):
                leads_to_create.append({
                    'type': "lead",
                    'name': "Test lead new " + str(x),
                    'partner_id': self.env.ref("base.res_partner_1").id,
                    'description': "This is the description of the test new lead.",
                    'team_id': self.env.ref("sales_team.team_sales_department").id,
                    'stage_id': self.env.ref("crm.stage_lead%s" % (str(i + 1))).id,
                })
        leads = self.env['crm.lead'].create(leads_to_create)
        # Set leads as won (stage = won)
        leads[:4].write({'stage_id': self.env.ref("crm.stage_lead4").id})
        # Mark leads as won (via action)
        leads[4:].action_set_won()
        # Check if every single lead has the correct probability + correct stage
        index = 0
        for lead in leads:
            self.assertEqual(lead.stage_id.id, self.env.ref("crm.stage_lead4").id, 'Stage must be "Won"')
            self.assertEqual(lead.probability, 100, 'Probability of a won lead must be = 100%')
            index += 1
