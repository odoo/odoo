# -*- coding: utf-8 -*-

from .common import TestCrmCases
from odoo.modules.module import get_module_resource


class TestCrmLeadMessage(TestCrmCases):

    def test_crm_lead_message(self):
        """ Tests for Test Crm Lead Message """
        CrmLead = self.env['crm.lead']
        MailThread = self.env['mail.thread']

        # Customer interested in our product, so he sends request by email to get more details.
        # Mail script will fetch his request from mail server. Then I process that mail after read EML file.
        request_file = open(get_module_resource('crm', 'tests', 'customer_request.eml'), 'rb')
        request_message = request_file.read()
        MailThread.message_process('crm.lead', request_message)

        # After getting the mail, I check details of new lead of that customer.
        lead = CrmLead.search([('email_from', '=', 'Mr. John Right <info@customer.com>')], limit=1)
        self.assertTrue(lead.ids, 'Fail to create merge opportunity wizard')
        self.assertFalse(lead.partner_id, 'Customer should be a new one')
        self.assertEqual(lead.name, 'Fournir votre devis avec le meilleur prix.', 'Subject does not match')

        # I reply his request with welcome message. TODO revert mail.mail to mail.compose.message (conversion to customer should be automatic).
        lead = CrmLead.search([('email_from', '=', 'Mr. John Right <info@customer.com>')], limit=1)
        context = {'active_model': 'crm.lead', 'active_id': lead.id}
        mail = self.env['mail.compose.message'].with_context(context).create({
            'body': "Merci de votre intérêt pour notre produit, nous vous contacterons bientôt. Bien à vous",
            'email_from': 'sales@mycompany.com'
        })
        # Give the access rights of Salesman to communicate with customer.
        mail.sudo(self.crm_salesman_id).send_mail()

        # Now, I convert him into customer and put him into regular customer list.
        CrmLead.search([('email_from', '=', 'Mr. John Right <info@customer.com>')]).with_context(context).handle_partner_assignation()
