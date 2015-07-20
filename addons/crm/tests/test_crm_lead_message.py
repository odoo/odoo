# -*- coding: utf-8 -*-

from openerp.tests import common
import openerp

class TestCrmLeadMessage(common.TransactionCase):

    def test_crm_lead_message(self):
        """ Tests for Test Crm Lead Message """
        CrmLead = self.env['crm.lead']
        MailThread = self.env['mail.thread']
        MainCompose = self.env['mail.compose.message']
        
        # Give the access rights of Salesman to communicate with customer.
        # self.env.ref('crm.lead').with_context({'uid': self.crm_res_users_salesman.id})  #APA FIX
        
        # Customer interested in our product, so he sends request by email to get more details.
        # Mail script will fetch his request from mail server. Then I process that mail after read EML file.
        request_file = open(openerp.modules.module.get_module_resource('crm','tests', 'customer_request.eml'),'rb')
        request_message = request_file.read()
        MailThread.message_process('crm.lead', request_message)
        
        # After getting the mail, I check details of new lead of that customer.
        leads = CrmLead.search([('email_from','=', 'Mr. John Right <info@customer.com>')])
        self.assertTrue(leads.ids and len(leads.ids), 'Fail to create merge opportunity wizard')
        self.assertFalse(leads[0].partner_id, 'Customer should be a new one')
        self.assertEqual(leads[0].name, 'Fournir votre devis avec le meilleur prix.', 'Subject does not match')

        # I reply his request with welcome message. TODO revert mail.mail to mail.compose.message (conversion to customer should be automatic).
        leads = CrmLead.search([('email_from','=', 'Mr. John Right <info@customer.com>')], limit=1)
        context = {'active_model': 'crm.lead','active_id': leads.id}
        mail = MainCompose.with_context(context).create(
            dict(
                body = "Merci de votre intérêt pour notre produit, nous vous contacterons bientôt. Bien à vous",
                email_from = 'sales@mycompany.com',
            ))
        mail.send_mail()

        # Now, I convert him into customer and put him into regular customer list.
        leads = CrmLead.search([('email_from','=', 'Mr. John Right <info@customer.com>')])
        leads.handle_partner_assignation()
