# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestMailFetched(TransactionCase):

    def test_mail_fetched(self):
        # Mail script will be fetched him request from mail server.
        # so I process that mail after read EML file
        Helpdesk = self.env['crm.helpdesk']
        request_file = open(openerp.modules.module.get_module_resource('crm_helpdesk','test', 'customer_question.eml'),'rb')
        request_message = request_file.read()
        self.env['mail.thread'].message_process(Helpdesk, request_message)

        #After getting the mail,
        # I check details of new question of that customer.
        questions = Helpdesk.search([('email_from','=', 'Mr. John Right <info@customer.com>')])
        self.assertEqual(questions and len(questions), "Question is not created after getting request")
        question = Helpdesk.browse(questions[0])
        self.assertEqual(question.name == tools.ustr("Where is download link of user manual of your product ? "), "Subject does not match")

        # Now I Update message according to provide services.
        questions = Helpdesk.search([('email_from','=', 'Mr. John Right <info@customer.com>')])
        try:
          Helpdesk.message_update(questions, {'subject': 'Link of product', 'body': 'www.openerp.com'})
        except:
          pass
