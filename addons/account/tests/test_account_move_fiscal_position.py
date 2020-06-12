# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMoveFiscalPosition(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        
        cls.tax_10_price_include = cls.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })
        cls.tax_20_price_include = cls.env['account.tax'].create({
            'name': '20% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'price_include': True,
            'include_base_amount': True,
        })
        cls.tax_15_price_exclude = cls.env['account.tax'].create({
            'name': '15% excl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
        })

        cls.account_revenue_1 = cls.env['account.account'].create({
            'code': 'testrevenue1',
            'name': 'Product Sales 1',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
        })
        cls.account_revenue_2 = cls.env['account.account'].create({
            'code': 'testrevenue2',
            'name': 'Product Sales 2',
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
        })

        cls.fiscal_position_exclude_to_include = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_position_exclude_to_include',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_15_price_exclude.id,
                    'tax_dest_id': cls.tax_10_price_include.id,
                }),
            ],
            'account_ids': [
                (0, None, {
                    'account_src_id': cls.account_revenue_1.id,
                    'account_dest_id': cls.account_revenue_2.id,
                }),
            ],
        })
        cls.fiscal_position_include_to_exclude = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_position_include_to_exclude',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_10_price_include.id,
                    'tax_dest_id': cls.tax_15_price_exclude.id,
                }),
            ],
            'account_ids': [
                (0, None, {
                    'account_src_id': cls.account_revenue_1.id,
                    'account_dest_id': cls.account_revenue_2.id,
                }),
            ],
        })
        cls.fiscal_position_include_to_include = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_position_include_to_include',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_10_price_include.id,
                    'tax_dest_id': cls.tax_20_price_include.id,
                }),
            ],
            'account_ids': [
                (0, None, {
                    'account_src_id': cls.account_revenue_1.id,
                    'account_dest_id': cls.account_revenue_2.id,
                }),
            ],
        })

        cls.product_tax_10_price_include = cls.env['product.product'].create({
            'name': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 110.0,
            'taxes_id': [(6, 0, cls.tax_10_price_include.ids)],
            'property_account_income_id': cls.account_revenue_1.id,
        })

        cls.product_tax_15_price_exclude = cls.env['product.product'].create({
            'name': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 200.0,
            'taxes_id': [(6, 0, cls.tax_15_price_exclude.ids)],
            'property_account_income_id': cls.account_revenue_1.id,
        })

    def _test_fiscal_position_price_included_to_price_excluded_tax(self, invoice):
        ''' Test the invoice when dealing with a fiscal position mapping a price-included tax set by default on a
        product. Indeed, mapping a price-included-tax to a price-excluded-tax must remove the tax amount from the
        price_unit set on the product.
        '''

        # The original price_unit is 110.0. The price-included tax should be subtracted as 110.0 / 1.1 = 100.0.
        # Then, the currency should be applied (x2 in 2019) making the price_unit becoming 100.0 x 2 = 200.0.

        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_tax_10_price_include.id,
                'account_id': self.account_revenue_2.id,
                'price_unit': 200.0,
                'price_subtotal': 200.0,
                'tax_ids': self.tax_15_price_exclude.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                'product_id': False,
                'account_id': self.account_revenue_2.id,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': self.tax_15_price_exclude.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                'product_id': False,
                'account_id': self.partner_a.property_account_receivable_id.id,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 230.0,
                'debit': 115.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'fiscal_position_id': self.fiscal_position_include_to_exclude.id,
            'amount_untaxed': 200.0,
            'amount_tax': 30.0,
            'amount_total': 230.0,
        })

    def test_create_fiscal_position_price_included_to_price_excluded_tax(self):
        self.partner_a.property_account_position_id = self.fiscal_position_include_to_exclude

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_tax_10_price_include.id,
                'tax_ids': [(6, 0, self.tax_15_price_exclude.ids)],
            })],
        })

        self._test_fiscal_position_price_included_to_price_excluded_tax(invoice)

    def test_onchange_fiscal_position_price_included_to_price_excluded_tax(self):
        self.partner_a.property_account_position_id = self.fiscal_position_include_to_exclude

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_tax_10_price_include
        invoice = move_form.save()

        self._test_fiscal_position_price_included_to_price_excluded_tax(invoice)

    def _test_fiscal_position_price_included_to_price_included_tax(self, invoice):
        ''' Test the invoice when dealing with a fiscal position mapping a price-included tax set by default on a
        product. Indeed, mapping a price-included-tax to a price-included-tax must remove the tax amount from the
        price_unit set on the product and then add the tax amount from the new price-included tax.
        '''

        # The original price_unit is 110.0. The price-included tax should be subtracted as 110.0 / 1.1 = 100.0.
        # Due to the fiscal position, the price_unit is set to 120.0 due to the 20% price-included tax.
        # Then, the currency should be applied (x2 in 2019) making the price_unit becoming 100.0 x 2 = 200.0.

        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_tax_10_price_include.id,
                'account_id': self.account_revenue_2.id,
                'price_unit': 240.0,
                'price_subtotal': 200.0,
                'tax_ids': self.tax_20_price_include.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                'product_id': False,
                'account_id': self.account_revenue_2.id,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': self.tax_20_price_include.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -40.0,
                'debit': 0.0,
                'credit': 20.0,
            },
            {
                'product_id': False,
                'account_id': self.partner_a.property_account_receivable_id.id,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 240.0,
                'debit': 120.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'fiscal_position_id': self.fiscal_position_include_to_include.id,
            'amount_untaxed': 200.0,
            'amount_tax': 40.0,
            'amount_total': 240.0,
        })

    def test_create_fiscal_position_price_included_to_price_included_tax(self):
        self.partner_a.property_account_position_id = self.fiscal_position_include_to_include

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_tax_10_price_include.id,
                'tax_ids': [(6, 0, self.tax_20_price_include.ids)],
            })],
        })

        self._test_fiscal_position_price_included_to_price_included_tax(invoice)

    def test_onchange_fiscal_position_price_included_to_price_included_tax(self):
        self.partner_a.property_account_position_id = self.fiscal_position_include_to_include

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_tax_10_price_include
        invoice = move_form.save()

        self._test_fiscal_position_price_included_to_price_included_tax(invoice)

    def _test_fiscal_position_price_excluded_to_price_included_tax(self, invoice):
        ''' This time, use a fiscal position mapping a price-excluded tax to a
        price-included tax.
        '''

        # The price_unit is set to 110.0 due to the 10% price-included tax.
        # Then, the currency should be applied (x2 in 2019) making the price_unit becoming 100.0 x 2 = 200.0.

        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_tax_15_price_exclude.id,
                'account_id': self.account_revenue_2.id,
                'price_unit': 440.0,
                'price_subtotal': 400.0,
                'tax_ids': self.tax_10_price_include.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -400.0,
                'debit': 0.0,
                'credit': 200.0,
            },
            {
                'product_id': False,
                'account_id': self.account_revenue_2.id,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': self.tax_10_price_include.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -40.0,
                'debit': 0.0,
                'credit': 20.0,
            },
            {
                'product_id': False,
                'account_id': self.partner_a.property_account_receivable_id.id,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 440.0,
                'debit': 220.0,
                'credit': 0.0,
            },
        ], {
            'fiscal_position_id': self.fiscal_position_exclude_to_include.id,
            'amount_untaxed': 400.0,
            'amount_tax': 40.0,
            'amount_total': 440.0,
        })

    def test_create_fiscal_position_price_excluded_to_price_included_tax(self):
        self.partner_a.property_account_position_id = self.fiscal_position_exclude_to_include

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_tax_15_price_exclude.id,
                'tax_ids': [(6, 0, self.tax_10_price_include.ids)],
            })],
        })

        self._test_fiscal_position_price_excluded_to_price_included_tax(invoice)

    def test_onchange_fiscal_position_price_excluded_to_price_included_tax(self):
        self.partner_a.property_account_position_id = self.fiscal_position_exclude_to_include

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_tax_15_price_exclude
        invoice = move_form.save()

        self._test_fiscal_position_price_excluded_to_price_included_tax(invoice)
