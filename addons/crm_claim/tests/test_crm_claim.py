# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.tools import ustr
from odoo.modules.module import get_module_resource


class TestCrmClaim(TransactionCase):

    def test_01_email_message(self):
        # Customer requests a claim after the sale of our product. He sends claim request by email.
        # Mail script will be fetched him request from mail server. so I process that mail after read EML file
        msg = open(get_module_resource('crm_claim', 'tests', 'customer_claim.eml'), 'rb').read()
        self.env['mail.thread'].message_process('crm.claim', msg)
        # After getting the mail, I check details of new claim of that customer.
        claims = self.env['crm.claim'].search([('email_from', '=', 'Mr. John Right <info@customer.com>')])
        self.assertTrue(claims, "Claim is not created after getting request")
        self.assertEqual(claims[0].name, ustr("demande de règlement de votre produit."), "Subject does not match.")
