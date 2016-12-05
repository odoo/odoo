# -*- coding: utf-8 -*-
from odoo import tools, _
from odoo.tests import common

class TestUBL(common.TransactionCase):
    def test_ubl_invoice(self):
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
            return
        invoice_id = self.env['account.invoice'].create({
            'journal_id': journal_id.id,
            'company_id': self.env.ref('base.main_company').id,
            'partner_id': self.env.ref('base.res_partner_2').id,
            'type': 'out_invoice',
            'invoice_line_ids': [(6, 0, [invoice_line_id_1.id, invoice_line_id_2.id])],
            'payment_term_id': self.env.ref('account.account_payment_term').id
        })
        invoice_id.action_invoice_open()
        attachment_id = invoice_id.generate_edi_BE()
        assert attachment_id, _('Fail during the generation of the EDI document')

