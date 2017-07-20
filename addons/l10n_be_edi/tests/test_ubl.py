# -*- coding: utf-8 -*-
from odoo import tools, _
from odoo.tests import common

class TestUBL(common.TransactionCase):
    def setUp(self):
        super(TestUBL, self).setUp()
        # Force user Belgium country.
        self.env.user.company_id.country = self.env.ref('base.be')

    def test_ubl_invoice(self):
        # Create
        invoice_line_id_1 = self.env['account.invoice.line'].create({
            'name': self.env.ref('product.consu_delivery_01').name,
            'product_id': self.env.ref('product.consu_delivery_01').id,
            'price_unit': 90.0,
            'quantity': 5,
            'account_id': self.env.ref('account.data_account_type_liquidity').id,
        })
        invoice_line_id_2 = self.env['account.invoice.line'].create({
            'name': self.env.ref('product.consu_delivery_03').name,
            'product_id': self.env.ref('product.consu_delivery_03').id,
            'price_unit': 15.0,
            'quantity': 5,
            'account_id': self.env.ref('account.data_account_type_liquidity').id,
       })
        journal_id = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        # No journal found
        if not journal_id:
            self.skipTest("No bank journal found")
        invoice_id = self.env['account.invoice'].create({
            'journal_id': journal_id.id,
            'company_id': self.env.ref('base.main_company').id,
            'partner_id': self.env.ref('base.res_partner_2').id,
            'type': 'out_invoice',
            'invoice_line_ids': [(6, 0, [invoice_line_id_1.id, invoice_line_id_2.id])],
            'payment_term_id': self.env.ref('account.account_payment_term').id
        })
        invoice_id.action_invoice_open()
        # Generate the attachment
        invoice_id.l10n_be_edi_generate_xml()
        attachment_id = self.env['ir.attachment'].search([
            ('datas_fname', '=', invoice_id.l10n_be_edi_attachment_name()),
            ('res_model', '=', 'account.invoice'),
            ('res_id', '=', invoice_id.id)
        ], limit=1)
        self.assertTrue(attachment_id, msg='Fail during the generation of the Belgium e-invoice.')
