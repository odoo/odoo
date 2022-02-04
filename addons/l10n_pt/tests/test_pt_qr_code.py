# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.tests import tagged


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

        cls.product = cls.env['product.product'].create({'name': 'Product :-)', 'standard_price': 100.0, 'lst_price': 100.0})

        cls.partner_a['country_id'] = cls.env.ref('base.be').id

        cls.invoice = cls.env['account.move'].create({
            'type': 'out_invoice',
            'partner_id': cls.partner_a.id,
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
        self.invoice.preview_invoice()
        self.assertEqual(self.invoice.l10n_pt_qr_code_str,
                         "A:123456789*B:999999990*C:BE*D:FT*E:N*F:20220204*G:out_invoice /*H:0"
                         "*I1:PT*I2:100.00*I3:100.00*I4:6.00*I5:100.00*I6:13.00*I7:300.00*I8:69.00"
                         "*N:88.00*O:600.00*Q:TODO*R:TODO")

    def test_pt_qr_code_different_currency(self):
        pass

    def test_pt_qr_code_credit_note(self):
        pass
