# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestMailFetched(TransactionCase):

    def test_01_mail_fetched(self):
        # Mail script will be fetched him request from mail server.
        # so I process that mail after read EML file
        Helpdesk = self.env['crm.helpdesk']
        request_message = open(openerp.modules.module.get_module_resource('crm_helpdesk','test', 'customer_question.eml'),'rb').read()
        self.env['mail.thread'].message_process(Helpdesk, request_message)

        #After getting the mail,
        # I check details of new question of that customer.
        question = Helpdesk.search([('email_from','=', 'Mr. John Right <info@customer.com>')], limit=1)
        self.assertFalse(question and len(question), "Question is not created after getting request")
        self.assertEqual(question.name == tools.ustr("Where is download link of user manual of your product ? "), "Subject does not match")

        # Now I Update message according to provide services.
        try:
          Helpdesk.message_update(question, {'subject': 'Link of product', 'body': 'www.openerp.com'})
        except:
          pass
