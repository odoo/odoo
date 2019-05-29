# -*- coding: utf-8 -*-
from odoo import tools, _
from odoo.tests import common
import base64
from odoo.modules.module import get_module_resource

class TestUBL(common.TransactionCase):
    def setUp(self):
        super(TestUBL, self).setUp()
        # Force user Belgium country.
        self.env.user.company_id = self.env['res.company'].create({'name': 'MyCompany'})
        self.env.user.company_id.country = self.env.ref('base.be')
        self.env.ref('l10n_be.l10nbe_chart_template').load_for_current_company(False, False)
        self.partner_id = self.env['res.partner'].create({'name': 'TestUser', 'vat': 'BE0123456789'})

    def test_ubl_invoice_import(self):
        xml_file_path = get_module_resource('l10n_be_edi', 'test_xml_file', 'efff_test.xml')
        xml_file = open(xml_file_path, 'rb').read()
        invoice = self.env['account.move'].with_context(default_type='in_invoice').create({})

        attachment_id = self.env['ir.attachment'].create({
            'name': 'efff_test.xml',
            'datas': base64.encodestring(xml_file),
            'res_id': invoice.id,
            'res_model': 'account.move',
        })

        invoice.message_post(attachment_ids=[attachment_id.id])

        self.assertEqual(invoice.amount_total, 666.50)
        self.assertEqual(invoice.amount_tax, 115.67)
        self.assertEqual(invoice.partner_id, self.partner_id)
