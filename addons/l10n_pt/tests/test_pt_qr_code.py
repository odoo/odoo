# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from addons.account.tests.test_account_move_out_invoice import TestAccountMoveOutInvoiceOnchanges
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class PortugalQRCodeTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_pt.pt_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'city': 'Lisboa',
            'zip': '1234-789',
            'vat': 'PT123456789',
            'company_registry': '123456',
            'phone': '+47 11 11 11 11',
            'country_id': cls.env.ref('base.pt').id,
        })

        cls.tax23 = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id), ('name', '=', 'IVA23')])
        cls.tax13 = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id), ('name', '=', 'IVA13')])
        cls.tax6 = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id), ('name', '=', 'IVA6')])
        cls.tax0 = cls.env['account.tax'].search([('company_id', '=', cls.company_data['company'].id), ('name', '=', 'IVA0')])

        cls.product1 = cls.env['product.product'].create({'name': 'product1', 'standard_price': 100.0, 'lst_price': 100.0})
        cls.product2 = cls.env['product.product'].create({'name': 'product2', 'standard_price': 100.0, 'lst_price': 100.0})
        cls.product3 = cls.env['product.product'].create({'name': 'product3', 'standard_price': 100.0, 'lst_price': 100.0})
        cls.product4 = cls.env['product.product'].create({'name': 'product4', 'standard_price': 100.0, 'lst_price': 100.0})

        cls.partner_be = cls.env['res.partner'].create({
            'name': 'Partner BE',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })

        line_taxes = [{'taxes': []}, {'taxes': [cls.tax6]}, {'taxes': [cls.tax23, cls.tax13]}]
        # cls.inv1 = cls._post_invoice(line_taxes)

    def test_multiple_taxes(self):
        pass

    def test_different_currency(self):
        pass

    def test_credit_note(self):
        pass
