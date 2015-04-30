# -*- coding: utf-8 -*-

from openerp.tools import ustr

from openerp.modules.module import get_module_resource
from openerp.tests.common import TransactionCase


class TestCrmClaim(TransactionCase):

    def setUp(self):
        super(TestCrmClaim, self).setUp()
        self.CrmClaim = self.env['crm.claim']
        self.MailThread = self.env['mail.thread']

    def test_01_email_message(self):
        msg = open(get_module_resource('crm_claim', 'tests', 'customer_claim.eml'), 'rb').read()
        self.MailThread.message_process('crm.claim', msg)

        domain = [
            ('name', '=', ustr("demande derèglement de votre produit.")),
            ('email_from', '=', 'Mr. John Right <info@customer.com>'),
            ('partner_id', '=', False),
            ('email_cc', '=', None),
        ]
        self.assertEqual(self.CrmClaim.search_count(domain), 1, msg="Unable to parse the Crm Claim from Email")
