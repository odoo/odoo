# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo import fields
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class PortugalQRCodeTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_pt.pt_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.tax23 = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id), ('name', '=', 'IVA23')])
        cls.tax13 = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id), ('name', '=', 'IVA13')])
        cls.tax6 = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id), ('name', '=', 'IVA6')])
        cls.tax0 = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id), ('name', '=', 'IVA0')])

        cls.company_data['company'].write({
            'city': 'Lisboa',
            'zip': '1234-789',
            'vat': 'PT123456789',
            'company_registry': '123456',
            'phone': '+47 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id
        })

        cls.partner_a['country_id'] = cls.env.ref('base.be').id
        
        cls.invoice = cls.env['account.move'].create({
            'type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'date': fields.Date.from_string('2022-01-01'),
            'name': 'INV/2022/0001',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'Name 0',
                    'product_id': cls.product_a.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [cls.tax23.id],
                }),
                (0, 0, {
                    'name': 'Name 1',
                    'product_id': cls.product_a.id,
                    'quantity': 1,
                    'price_unit': 200,
                    'tax_ids': [cls.tax23.id],
                }),
                (0, 0, {
                    'name': 'Name 2',
                    'product_id': cls.product_b.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [cls.tax13.id],
                }),
                (0, 0, {
                    'name': 'Name 3',
                    'product_id': cls.product_a.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [cls.tax6.id],
                }),
                (0, 0, {
                    'name': 'Name 4',
                    'product_id': cls.product_b.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [cls.tax0.id],
                })
            ]
        })

    def test_pt_qr_code_multiple_taxes(self):
        """Ensures that all possible taxes are correctly computed and exported"""
        self.invoice.preview_invoice()  # Triggers the _compute_qr_code_str method
        self.assertEqual(self.invoice.l10n_pt_qr_code_str,
                         'A:123456789*B:999999990*C:BE*D:FT*E:N*F:20220101*G:out_invoice INV/2022/0001*H:0'
                         '*I1:PT*I2:100.00*I3:100.00*I4:6.00*I5:100.00*I6:13.00*I7:300.00*I8:69.00'
                         '*N:88.00*O:688.00*Q:TODO*R:TODO')

    def test_pt_qr_code_different_currency(self):
        """Ensures that any foreign currency is correctly converted to EUR"""
        self.env['res.currency.rate'].create({
            'name': '2022-01-01',
            'rate': 1.25,
            'currency_id': self.env.ref('base.USD').id,
            'company_id': self.company_data['company'].id,
        })

        move_form = Form(self.invoice)
        move_form.date = '2022-01-01'
        move_form.currency_id = self.env.ref('base.USD')
        move_form.save()

        self.invoice.preview_invoice()
        self.assertEqual(self.invoice.l10n_pt_qr_code_str,
                         'A:123456789*B:999999990*C:BE*D:FT*E:N*F:20220101*G:out_invoice INV/2022/0001*H:0'
                         '*I1:PT*I2:80.00*I3:80.00*I4:4.80*I5:80.00*I6:10.40*I7:240.00*I8:55.20'
                         '*N:70.40*O:550.40*Q:TODO*R:TODO')


    def test_pt_qr_code_credit_note(self):
        """Test different types of moves, e.g. a credit note"""
        move_reversal = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2022-01-01'),
            'reason': 'no reason',
            'refund_method': 'refund',
        })
        reversal = move_reversal.reverse_moves()
        credit_note = self.env['account.move'].browse(reversal['res_id'])
        credit_note['name'] = 'RINV/2022/0001'
        credit_note.preview_invoice()
        self.assertEqual(credit_note.l10n_pt_qr_code_str,
                         'A:123456789*B:999999990*C:BE*D:NC*E:N*F:20220101*G:out_refund RINV/2022/0001*H:0'
                         '*I1:PT*I2:100.00*I3:100.00*I4:6.00*I5:100.00*I6:13.00*I7:300.00*I8:69.00'
                         '*N:88.00*O:688.00*Q:TODO*R:TODO')
