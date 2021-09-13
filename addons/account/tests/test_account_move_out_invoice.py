# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError

from unittest.mock import patch
from datetime import timedelta


@tagged('post_install', '-at_install')
class TestAccountMoveOutInvoiceOnchanges(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.init_invoice('out_invoice', products=cls.product_a+cls.product_b)

        cls.product_line_vals_1 = {
            'name': cls.product_a.name,
            'product_id': cls.product_a.id,
            'account_id': cls.product_a.property_account_income_id.id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': cls.product_a.uom_id.id,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 1000.0,
            'price_subtotal': 1000.0,
            'price_total': 1150.0,
            'tax_ids': cls.product_a.taxes_id.ids,
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -1000.0,
            'debit': 0.0,
            'credit': 1000.0,
            'date_maturity': False,
            'tax_exigible': True,
        }
        cls.product_line_vals_2 = {
            'name': cls.product_b.name,
            'product_id': cls.product_b.id,
            'account_id': cls.product_b.property_account_income_id.id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': cls.product_b.uom_id.id,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 200.0,
            'price_subtotal': 200.0,
            'price_total': 260.0,
            'tax_ids': cls.product_b.taxes_id.ids,
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -200.0,
            'debit': 0.0,
            'credit': 200.0,
            'date_maturity': False,
            'tax_exigible': True,
        }
        cls.tax_line_vals_1 = {
            'name': cls.tax_sale_a.name,
            'product_id': False,
            'account_id': cls.company_data['default_account_tax_sale'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 180.0,
            'price_subtotal': 180.0,
            'price_total': 180.0,
            'tax_ids': [],
            'tax_line_id': cls.tax_sale_a.id,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -180.0,
            'debit': 0.0,
            'credit': 180.0,
            'date_maturity': False,
            'tax_exigible': True,
        }
        cls.tax_line_vals_2 = {
            'name': cls.tax_sale_b.name,
            'product_id': False,
            'account_id': cls.company_data['default_account_tax_sale'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 30.0,
            'price_subtotal': 30.0,
            'price_total': 30.0,
            'tax_ids': [],
            'tax_line_id': cls.tax_sale_b.id,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -30.0,
            'debit': 0.0,
            'credit': 30.0,
            'date_maturity': False,
            'tax_exigible': True,
        }
        cls.term_line_vals_1 = {
            'name': '',
            'product_id': False,
            'account_id': cls.company_data['default_account_receivable'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': -1410.0,
            'price_subtotal': -1410.0,
            'price_total': -1410.0,
            'tax_ids': [],
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': 1410.0,
            'debit': 1410.0,
            'credit': 0.0,
            'date_maturity': fields.Date.from_string('2019-01-01'),
            'tax_exigible': True,
        }
        cls.move_vals = {
            'partner_id': cls.partner_a.id,
            'currency_id': cls.company_data['currency'].id,
            'journal_id': cls.company_data['default_journal_sale'].id,
            'date': fields.Date.from_string('2019-01-01'),
            'fiscal_position_id': False,
            'payment_reference': '',
            'invoice_payment_term_id': cls.pay_terms_a.id,
            'amount_untaxed': 1200.0,
            'amount_tax': 210.0,
            'amount_total': 1410.0,
        }

    def setUp(self):
        super(TestAccountMoveOutInvoiceOnchanges, self).setUp()
        self.assertInvoiceValues(self.invoice, [
            self.product_line_vals_1,
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            self.term_line_vals_1,
        ], self.move_vals)

    def test_out_invoice_onchange_invoice_date(self):
        for tax_date, invoice_date, accounting_date in [
            ('2019-03-31', '2019-05-12', '2019-05-12'),
            ('2019-03-31', '2019-02-10', '2019-04-1'),
            ('2019-05-31', '2019-06-15', '2019-06-15'),
        ]:
            self.invoice.company_id.tax_lock_date = tax_date
            with Form(self.invoice) as move_form:
                move_form.invoice_date = invoice_date
            self.assertEqual(self.invoice.date, fields.Date.to_date(accounting_date))

    def test_out_invoice_line_onchange_product_1(self):
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.product_id = self.product_b
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'name': self.product_b.name,
                'product_id': self.product_b.id,
                'product_uom_id': self.product_b.uom_id.id,
                'account_id': self.product_b.property_account_income_id.id,
                'price_unit': 200.0,
                'price_subtotal': 200.0,
                'price_total': 260.0,
                'tax_ids': self.product_b.taxes_id.ids,
                'amount_currency': -200.0,
                'credit': 200.0,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'price_unit': 60.0,
                'price_subtotal': 60.0,
                'price_total': 60.0,
                'amount_currency': -60.0,
                'credit': 60.0,
            },
            {
                **self.tax_line_vals_2,
                'price_unit': 60.0,
                'price_subtotal': 60.0,
                'price_total': 60.0,
                'amount_currency': -60.0,
                'credit': 60.0,
            },
            {
                **self.term_line_vals_1,
                'price_unit': -520.0,
                'price_subtotal': -520.0,
                'price_total': -520.0,
                'amount_currency': 520.0,
                'debit': 520.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 400.0,
            'amount_tax': 120.0,
            'amount_total': 520.0,
        })

    def test_out_invoice_line_onchange_product_2_with_fiscal_pos_1(self):
        ''' Test mapping a price-included tax (10%) with a price-excluded tax (20%) on a price_unit of 110.0.
        The price_unit should be 100.0 after applying the fiscal position.
        '''
        tax_price_include = self.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })
        tax_price_exclude = self.env['account.tax'].create({
            'name': '15% excl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
        })

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': tax_price_include.id,
                    'tax_dest_id': tax_price_exclude.id,
                }),
            ],
        })

        product = self.env['product.product'].create({
            'name': 'product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 110.0,
            'taxes_id': [(6, 0, tax_price_include.ids)],
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.currency_id = self.currency_data['currency']
        move_form.fiscal_position_id = fiscal_position
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
        invoice = move_form.save()

        self.assertInvoiceValues(invoice, [
            {
                'product_id': product.id,
                'price_unit': 200.0,
                'price_subtotal': 200.0,
                'price_total': 230.0,
                'tax_ids': tax_price_exclude.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                'product_id': False,
                'price_unit': 30.0,
                'price_subtotal': 30.0,
                'price_total': 30.0,
                'tax_ids': [],
                'tax_line_id': tax_price_exclude.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                'product_id': False,
                'price_unit': -230.0,
                'price_subtotal': -230.0,
                'price_total': -230.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 230.0,
                'debit': 115.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'fiscal_position_id': fiscal_position.id,
            'amount_untaxed': 200.0,
            'amount_tax': 30.0,
            'amount_total': 230.0,
        })

        uom_dozen = self.env.ref('uom.product_uom_dozen')
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.product_uom_id = uom_dozen

        self.assertInvoiceValues(invoice, [
            {
                'product_id': product.id,
                'product_uom_id': uom_dozen.id,
                'price_unit': 2400.0,
                'price_subtotal': 2400.0,
                'price_total': 2760.0,
                'tax_ids': tax_price_exclude.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2400.0,
                'debit': 0.0,
                'credit': 1200.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 360.0,
                'price_subtotal': 360.0,
                'price_total': 360.0,
                'tax_ids': [],
                'tax_line_id': tax_price_exclude.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -360.0,
                'debit': 0.0,
                'credit': 180.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': -2760.0,
                'price_subtotal': -2760.0,
                'price_total': -2760.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2760.0,
                'debit': 1380.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'fiscal_position_id': fiscal_position.id,
            'amount_untaxed': 2400.0,
            'amount_tax': 360.0,
            'amount_total': 2760.0,
        })

    def test_out_invoice_line_onchange_product_2_with_fiscal_pos_2(self):
        ''' Test mapping a price-included tax (10%) with another price-included tax (20%) on a price_unit of 110.0.
        The price_unit should be 120.0 after applying the fiscal position.
        '''
        tax_price_include_1 = self.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })
        tax_price_include_2 = self.env['account.tax'].create({
            'name': '20% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'price_include': True,
            'include_base_amount': True,
        })

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': tax_price_include_1.id,
                    'tax_dest_id': tax_price_include_2.id,
                }),
            ],
        })

        product = self.env['product.product'].create({
            'name': 'product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 110.0,
            'taxes_id': [(6, 0, tax_price_include_1.ids)],
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.currency_id = self.currency_data['currency']
        move_form.fiscal_position_id = fiscal_position
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
        invoice = move_form.save()

        self.assertInvoiceValues(invoice, [
            {
                'product_id': product.id,
                'price_unit': 240.0,
                'price_subtotal': 200.0,
                'price_total': 240.0,
                'tax_ids': tax_price_include_2.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                'product_id': False,
                'price_unit': 40.0,
                'price_subtotal': 40.0,
                'price_total': 40.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include_2.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -40.0,
                'debit': 0.0,
                'credit': 20.0,
            },
            {
                'product_id': False,
                'price_unit': -240.0,
                'price_subtotal': -240.0,
                'price_total': -240.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 240.0,
                'debit': 120.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'fiscal_position_id': fiscal_position.id,
            'amount_untaxed': 200.0,
            'amount_tax': 40.0,
            'amount_total': 240.0,
        })

        uom_dozen = self.env.ref('uom.product_uom_dozen')
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.product_uom_id = uom_dozen

        self.assertInvoiceValues(invoice, [
            {
                'product_id': product.id,
                'product_uom_id': uom_dozen.id,
                'price_unit': 2880.0,
                'price_subtotal': 2400.0,
                'price_total': 2880.0,
                'tax_ids': tax_price_include_2.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2400.0,
                'debit': 0.0,
                'credit': 1200.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 480.0,
                'price_subtotal': 480.0,
                'price_total': 480.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include_2.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -480.0,
                'debit': 0.0,
                'credit': 240.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': -2880.0,
                'price_subtotal': -2880.0,
                'price_total': -2880.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2880.0,
                'debit': 1440.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'fiscal_position_id': fiscal_position.id,
            'amount_untaxed': 2400.0,
            'amount_tax': 480.0,
            'amount_total': 2880.0,
        })

    def test_out_invoice_line_onchange_business_fields_1(self):
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            # Current price_unit is 1000.
            # We set quantity = 4, discount = 50%, price_unit = 400. The debit/credit fields don't change because (4 * 500) * 0.5 = 1000.
            line_form.quantity = 4
            line_form.discount = 50
            line_form.price_unit = 500
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'quantity': 4,
                'discount': 50.0,
                'price_unit': 500.0,
            },
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            self.term_line_vals_1,
        ], self.move_vals)

        move_form = Form(self.invoice)
        with move_form.line_ids.edit(2) as line_form:
            # Reset field except the discount that becomes 100%.
            # /!\ The modification is made on the accounting tab.
            line_form.quantity = 1
            line_form.discount = 100
            line_form.price_unit = 1000
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'discount': 100.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'amount_currency': 0.0,
                'credit': 0.0,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'price_unit': 30.0,
                'price_subtotal': 30.0,
                'price_total': 30.0,
                'amount_currency': -30.0,
                'credit': 30.0,
            },
            self.tax_line_vals_2,
            {
                **self.term_line_vals_1,
                'price_unit': -260.0,
                'price_subtotal': -260.0,
                'price_total': -260.0,
                'amount_currency': 260.0,
                'debit': 260.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 200.0,
            'amount_tax': 60.0,
            'amount_total': 260.0,
        })

    def test_out_invoice_line_onchange_accounting_fields_1(self):
        move_form = Form(self.invoice)
        with move_form.line_ids.edit(2) as line_form:
            # Custom credit on the first product line.
            line_form.credit = 3000
        with move_form.line_ids.edit(3) as line_form:
            # Custom debit on the second product line. Credit should be reset by onchange.
            # /!\ It's a negative line.
            line_form.debit = 500
        with move_form.line_ids.edit(0) as line_form:
            # Custom credit on the first tax line.
            line_form.credit = 800
        with move_form.line_ids.edit(4) as line_form:
            # Custom credit on the second tax line.
            line_form.credit = 250
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 3000.0,
                'price_subtotal': 3000.0,
                'price_total': 3450.0,
                'amount_currency': -3000.0,
                'credit': 3000.0,
            },
            {
                **self.product_line_vals_2,
                'price_unit': -500.0,
                'price_subtotal': -500.0,
                'price_total': -650.0,
                'amount_currency': 500.0,
                'debit': 500.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': 800.0,
                'price_subtotal': 800.0,
                'price_total': 800.0,
                'amount_currency': -800.0,
                'credit': 800.0,
            },
            {
                **self.tax_line_vals_2,
                'price_unit': 250.0,
                'price_subtotal': 250.0,
                'price_total': 250.0,
                'amount_currency': -250.0,
                'credit': 250.0,
            },
            {
                **self.term_line_vals_1,
                'price_unit': -3550.0,
                'price_subtotal': -3550.0,
                'price_total': -3550.0,
                'amount_currency': 3550.0,
                'debit': 3550.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 2500.0,
            'amount_tax': 1050.0,
            'amount_total': 3550.0,
        })

    def test_out_invoice_line_onchange_partner_1(self):
        move_form = Form(self.invoice)
        move_form.partner_id = self.partner_b
        move_form.payment_reference = 'turlututu'
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'partner_id': self.partner_b.id,
            },
            {
                **self.product_line_vals_2,
                'partner_id': self.partner_b.id,
            },
            {
                **self.tax_line_vals_1,
                'partner_id': self.partner_b.id,
            },
            {
                **self.tax_line_vals_2,
                'partner_id': self.partner_b.id,
            },
            {
                **self.term_line_vals_1,
                'name': 'turlututu',
                'account_id': self.partner_b.property_account_receivable_id.id,
                'partner_id': self.partner_b.id,
                'price_unit': -423.0,
                'price_subtotal': -423.0,
                'price_total': -423.0,
                'amount_currency': 423.0,
                'debit': 423.0,
            },
            {
                **self.term_line_vals_1,
                'name': 'turlututu',
                'account_id': self.partner_b.property_account_receivable_id.id,
                'partner_id': self.partner_b.id,
                'price_unit': -987.0,
                'price_subtotal': -987.0,
                'price_total': -987.0,
                'amount_currency': 987.0,
                'debit': 987.0,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            **self.move_vals,
            'partner_id': self.partner_b.id,
            'payment_reference': 'turlututu',
            'fiscal_position_id': self.fiscal_pos_a.id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'amount_untaxed': 1200.0,
            'amount_tax': 210.0,
            'amount_total': 1410.0,
        })

        # Remove lines and recreate them to apply the fiscal position.
        move_form = Form(self.invoice)
        move_form.invoice_line_ids.remove(0)
        move_form.invoice_line_ids.remove(0)
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_b
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'account_id': self.product_b.property_account_income_id.id,
                'partner_id': self.partner_b.id,
                'tax_ids': self.tax_sale_b.ids,
            },
            {
                **self.product_line_vals_2,
                'partner_id': self.partner_b.id,
                'price_total': 230.0,
                'tax_ids': self.tax_sale_b.ids,
            },
            {
                **self.tax_line_vals_1,
                'name': self.tax_sale_b.name,
                'partner_id': self.partner_b.id,
                'tax_line_id': self.tax_sale_b.id,
            },
            {
                **self.term_line_vals_1,
                'name': 'turlututu',
                'account_id': self.partner_b.property_account_receivable_id.id,
                'partner_id': self.partner_b.id,
                'price_unit': -414.0,
                'price_subtotal': -414.0,
                'price_total': -414.0,
                'amount_currency': 414.0,
                'debit': 414.0,
            },
            {
                **self.term_line_vals_1,
                'name': 'turlututu',
                'account_id': self.partner_b.property_account_receivable_id.id,
                'partner_id': self.partner_b.id,
                'price_unit': -966.0,
                'price_subtotal': -966.0,
                'price_total': -966.0,
                'amount_currency': 966.0,
                'debit': 966.0,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            **self.move_vals,
            'partner_id': self.partner_b.id,
            'payment_reference': 'turlututu',
            'fiscal_position_id': self.fiscal_pos_a.id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'amount_untaxed': 1200.0,
            'amount_tax': 180.0,
            'amount_total': 1380.0,
        })

    def test_out_invoice_line_onchange_taxes_1(self):
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 1200
            line_form.tax_ids.add(self.tax_armageddon)
        move_form.save()

        child_tax_1 = self.tax_armageddon.children_tax_ids[0]
        child_tax_2 = self.tax_armageddon.children_tax_ids[1]

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 1200.0,
                'price_subtotal': 1000.0,
                'price_total': 1470.0,
                'tax_ids': (self.tax_sale_a + self.tax_armageddon).ids,
                'tax_exigible': False,
            },
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            {
                'name': child_tax_1.name,
                'product_id': False,
                'account_id': self.company_data['default_account_revenue'].id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': 120.0,
                'price_subtotal': 120.0,
                'price_total': 132.0,
                'tax_ids': child_tax_2.ids,
                'tax_line_id': child_tax_1.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -120.0,
                'debit': 0.0,
                'credit': 120.0,
                'date_maturity': False,
                'tax_exigible': False,
            },
            {
                'name': child_tax_1.name,
                'product_id': False,
                'account_id': self.company_data['default_account_tax_sale'].id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': 80.0,
                'price_subtotal': 80.0,
                'price_total': 88.0,
                'tax_ids': child_tax_2.ids,
                'tax_line_id': child_tax_1.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -80.0,
                'debit': 0.0,
                'credit': 80.0,
                'date_maturity': False,
                'tax_exigible': False,
            },
            {
                'name': child_tax_2.name,
                'product_id': False,
                'account_id': child_tax_2.cash_basis_transition_account_id.id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': 120.0,
                'price_subtotal': 120.0,
                'price_total': 120.0,
                'tax_ids': [],
                'tax_line_id': child_tax_2.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -120.0,
                'debit': 0.0,
                'credit': 120.0,
                'date_maturity': False,
                'tax_exigible': False,
            },
            {
                **self.term_line_vals_1,
                'price_unit': -1730.0,
                'price_subtotal': -1730.0,
                'price_total': -1730.0,
                'amount_currency': 1730.0,
                'debit': 1730.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 1200.0,
            'amount_tax': 530.0,
            'amount_total': 1730.0,
        })

    def test_out_invoice_line_onchange_rounding_price_subtotal_1(self):
        ''' Seek for rounding issue on the price_subtotal when dealing with a price_unit having more digits than the
        foreign currency one.
        '''
        decimal_precision_name = self.env['account.move.line']._fields['price_unit']._digits
        decimal_precision = self.env['decimal.precision'].search([('name', '=', decimal_precision_name)])

        self.assertTrue(decimal_precision, "Decimal precision '%s' not found" % decimal_precision_name)

        self.currency_data['currency'].rounding = 0.01
        decimal_precision.digits = 4

        def check_invoice_values(invoice):
            self.assertInvoiceValues(invoice, [
                {
                    'quantity': 1.0,
                    'price_unit': 0.025,
                    'price_subtotal': 0.03,
                    'debit': 0.0,
                    'credit': 0.02,
                    'currency_id': self.currency_data['currency'].id,
                },
                {
                    'quantity': 1.0,
                    'price_unit': -0.03,
                    'price_subtotal': -0.03,
                    'debit': 0.02,
                    'credit': 0.0,
                    'currency_id': self.currency_data['currency'].id,
                },
            ], {
                'amount_untaxed': 0.03,
                'amount_tax': 0.0,
                'amount_total': 0.03,
            })

        # == Test at the creation of the invoice ==

        invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 0.025,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })

        check_invoice_values(invoice_1)

        # == Test when writing on the invoice ==

        invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
        })
        invoice_2.write({
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 0.025,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })

        check_invoice_values(invoice_2)

    def test_out_invoice_line_onchange_rounding_price_subtotal_2(self):
        """ Ensure the cyclic computations implemented using onchanges are not leading to rounding issues when using
        price-included taxes.
        For example:
        100 / 1.21 ~= 82.64 but 82.64 * 1.21 ~= 99.99 != 100.0.
        """

        def check_invoice_values(invoice):
            self.assertInvoiceValues(invoice, [
                {
                    'price_unit': 100.0,
                    'price_subtotal': 82.64,
                    'debit': 0.0,
                    'credit': 82.64,
                },
                {
                    'price_unit': 17.36,
                    'price_subtotal': 17.36,
                    'debit': 0.0,
                    'credit': 17.36,
                },
                {
                    'price_unit': -100.0,
                    'price_subtotal': -100.0,
                    'debit': 100.0,
                    'credit': 0.0,
                },
            ], {
                'amount_untaxed': 82.64,
                'amount_tax': 17.36,
                'amount_total': 100.0,
            })

        tax = self.env['account.tax'].create({
            'name': '21%',
            'amount': 21.0,
            'price_include': True,
            'include_base_amount': True,
        })

        # == Test assigning tax directly ==

        invoice_create = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 100.0,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [(6, 0, tax.ids)],
            })],
        })

        check_invoice_values(invoice_create)

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.name = 'test line'
            line_form.price_unit = 100.0
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.tax_ids.clear()
            line_form.tax_ids.add(tax)
        invoice_onchange = move_form.save()

        check_invoice_values(invoice_onchange)

        # == Test when the tax is set on a product ==

        product = self.env['product.product'].create({
            'name': 'product',
            'lst_price': 100.0,
            'property_account_income_id': self.company_data['default_account_revenue'].id,
            'taxes_id': [(6, 0, tax.ids)],
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        move_form.partner_id = self.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
        invoice_onchange = move_form.save()

        check_invoice_values(invoice_onchange)

        # == Test with a fiscal position ==

        fiscal_position = self.env['account.fiscal.position'].create({'name': 'fiscal_position'})

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        move_form.partner_id = self.partner_a
        move_form.fiscal_position_id = fiscal_position
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
        invoice_onchange = move_form.save()

        check_invoice_values(invoice_onchange)

    def test_out_invoice_line_onchange_taxes_2_price_unit_tax_included(self):
        ''' Seek for rounding issue in the price unit. Suppose a price_unit of 2300 with a 5.5% price-included tax
        applied on it.

        The computed balance will be computed as follow: 2300.0 / 1.055 = 2180.0948 ~ 2180.09.
        Since accounting / business fields are synchronized, the inverse computation will try to recompute the
        price_unit based on the balance: 2180.09 * 1.055 = 2299.99495 ~ 2299.99.

        This test ensures the price_unit is not overridden in such case.
        '''
        tax_price_include = self.env['account.tax'].create({
            'name': 'Tax 5.5% price included',
            'amount': 5.5,
            'amount_type': 'percent',
            'price_include': True,
        })

        # == Single-currency ==

        # price_unit=2300 with 15% tax (excluded) + 5.5% tax (included).
        move_form = Form(self.invoice)
        move_form.invoice_line_ids.remove(1)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 2300
            line_form.tax_ids.add(tax_price_include)
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 2300.0,
                'price_subtotal': 2180.09,
                'price_total': 2627.01,
                'tax_ids': (self.product_a.taxes_id + tax_price_include).ids,
                'amount_currency': -2180.09,
                'credit': 2180.09,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': 327.01,
                'price_subtotal': 327.01,
                'price_total': 327.01,
                'amount_currency': -327.01,
                'credit': 327.01,
            },
            {
                'name': tax_price_include.name,
                'product_id': False,
                'account_id': self.product_line_vals_1['account_id'],
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': 119.91,
                'price_subtotal': 119.91,
                'price_total': 119.91,
                'tax_ids': [],
                'tax_line_id': tax_price_include.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -119.91,
                'debit': 0.0,
                'credit': 119.91,
                'date_maturity': False,
                'tax_exigible': True,
            },
            {
                **self.term_line_vals_1,
                'price_unit': -2627.01,
                'price_subtotal': -2627.01,
                'price_total': -2627.01,
                'amount_currency': 2627.01,
                'debit': 2627.01,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 2180.09,
            'amount_tax': 446.92,
            'amount_total': 2627.01,
        })

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = -2300
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': -2300.0,
                'price_subtotal': -2180.09,
                'price_total': -2627.01,
                'tax_ids': (self.product_a.taxes_id + tax_price_include).ids,
                'amount_currency': 2180.09,
                'debit': 2180.09,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': -327.01,
                'price_subtotal': -327.01,
                'price_total': -327.01,
                'amount_currency': 327.01,
                'debit': 327.01,
                'credit': 0.0,
            },
            {
                'name': tax_price_include.name,
                'product_id': False,
                'account_id': self.product_line_vals_1['account_id'],
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': -119.91,
                'price_subtotal': -119.91,
                'price_total': -119.91,
                'tax_ids': [],
                'tax_line_id': tax_price_include.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 119.91,
                'debit': 119.91,
                'credit': 0.0,
                'date_maturity': False,
                'tax_exigible': True,
            },
            {
                **self.term_line_vals_1,
                'price_unit': 2627.01,
                'price_subtotal': 2627.01,
                'price_total': 2627.01,
                'amount_currency': -2627.01,
                'debit': 0.0,
                'credit': 2627.01,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': -2180.09,
            'amount_tax': -446.92,
            'amount_total': -2627.01,
        })

        # == Multi-currencies ==

        move_form = Form(self.invoice)
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 2300
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 2300.0,
                'price_subtotal': 2180.095,
                'price_total': 2627.014,
                'tax_ids': (self.product_a.taxes_id + tax_price_include).ids,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2180.095,
                'credit': 1090.05,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': 327.014,
                'price_subtotal': 327.014,
                'price_total': 327.014,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -327.014,
                'credit': 163.51,
            },
            {
                'name': tax_price_include.name,
                'product_id': False,
                'account_id': self.product_line_vals_1['account_id'],
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': 119.905,
                'price_subtotal': 119.905,
                'price_total': 119.905,
                'tax_ids': [],
                'tax_line_id': tax_price_include.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -119.905,
                'debit': 0.0,
                'credit': 59.95,
                'date_maturity': False,
                'tax_exigible': True,
            },
            {
                **self.term_line_vals_1,
                'price_unit': -2627.014,
                'price_subtotal': -2627.014,
                'price_total': -2627.014,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2627.014,
                'debit': 1313.51,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'amount_untaxed': 2180.095,
            'amount_tax': 446.919,
            'amount_total': 2627.014,
        })

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = -2300
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': -2300.0,
                'price_subtotal': -2180.095,
                'price_total': -2627.014,
                'tax_ids': (self.product_a.taxes_id + tax_price_include).ids,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2180.095,
                'debit': 1090.05,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': -327.014,
                'price_subtotal': -327.014,
                'price_total': -327.014,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 327.014,
                'debit': 163.51,
                'credit': 0.0,
            },
            {
                'name': tax_price_include.name,
                'product_id': False,
                'account_id': self.product_line_vals_1['account_id'],
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': -119.905,
                'price_subtotal': -119.905,
                'price_total': -119.905,
                'tax_ids': [],
                'tax_line_id': tax_price_include.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 119.905,
                'debit': 59.95,
                'credit': 0.0,
                'date_maturity': False,
                'tax_exigible': True,
            },
            {
                **self.term_line_vals_1,
                'price_unit': 2627.014,
                'price_subtotal': 2627.014,
                'price_total': 2627.014,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2627.014,
                'debit': 0.0,
                'credit': 1313.51,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'amount_untaxed': -2180.095,
            'amount_tax': -446.919,
            'amount_total': -2627.014,
        })

    def test_out_invoice_line_onchange_analytic(self):
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_tags')

        analytic_tag = self.env['account.analytic.tag'].create({
            'name': 'test_analytic_tag',
        })

        analytic_account = self.env['account.analytic.account'].create({
            'name': 'test_analytic_account',
            'partner_id': self.invoice.partner_id.id,
            'code': 'TEST'
        })

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.analytic_account_id = analytic_account
            line_form.analytic_tag_ids.add(analytic_tag)
        move_form.save()

        # The tax is not flagged as an analytic one. It should change nothing on the taxes.
        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'analytic_account_id': analytic_account.id,
                'analytic_tag_ids': analytic_tag.ids,
            },
            {
                **self.product_line_vals_2,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.tax_line_vals_1,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.tax_line_vals_2,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.term_line_vals_1,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
        ], self.move_vals)

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.analytic_account_id = self.env['account.analytic.account']
            line_form.analytic_tag_ids.clear()
        move_form.save()

        # Enable the analytic
        self.tax_sale_a.analytic = True

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.analytic_account_id = analytic_account
            line_form.analytic_tag_ids.add(analytic_tag)
        move_form.save()

        # The tax is flagged as an analytic one.
        # A new tax line must be generated.
        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'analytic_account_id': analytic_account.id,
                'analytic_tag_ids': analytic_tag.ids,
            },
            {
                **self.product_line_vals_2,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.tax_line_vals_1,
                'price_unit': 150.0,
                'price_subtotal': 150.0,
                'price_total': 150.0,
                'amount_currency': -150.0,
                'credit': 150.0,
                'analytic_account_id': analytic_account.id,
                'analytic_tag_ids': analytic_tag.ids,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': 30.0,
                'price_subtotal': 30.0,
                'price_total': 30.0,
                'amount_currency': -30.0,
                'credit': 30.0,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.tax_line_vals_2,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.term_line_vals_1,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
        ], self.move_vals)

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.analytic_account_id = self.env['account.analytic.account']
            line_form.analytic_tag_ids.clear()
        move_form.save()

        # The tax line has been removed.
        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.product_line_vals_2,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.tax_line_vals_1,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.tax_line_vals_2,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                **self.term_line_vals_1,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
        ], self.move_vals)

    def test_out_invoice_line_onchange_analytic_2(self):
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        analytic_account = self.env['account.analytic.account'].create({
            'name': 'test_analytic_account1',
            'code': 'TEST1'
        })

        self.invoice.write({'invoice_line_ids': [(1, self.invoice.invoice_line_ids.ids[0], {
            'analytic_account_id': analytic_account.id,
        })]})

        self.assertRecordValues(self.invoice.invoice_line_ids, [
            {'analytic_account_id': analytic_account.id},
            {'analytic_account_id': False},
        ])

        # We can remove the analytic account, it is not recomputed by an invalidation
        self.invoice.write({'invoice_line_ids': [(1, self.invoice.invoice_line_ids.ids[0], {
            'analytic_account_id': False,
        })]})

        self.assertRecordValues(self.invoice.invoice_line_ids, [
            {'analytic_account_id': False},
            {'analytic_account_id': False},
        ])

    def test_out_invoice_line_onchange_cash_rounding_1(self):
        move_form = Form(self.invoice)
        # Add a cash rounding having 'add_invoice_line'.
        move_form.invoice_cash_rounding_id = self.cash_rounding_a
        move_form.save()

        # The cash rounding does nothing as the total is already rounded.
        self.assertInvoiceValues(self.invoice, [
            self.product_line_vals_1,
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            self.term_line_vals_1,
        ], self.move_vals)

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 999.99
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                'name': 'add_invoice_line',
                'product_id': False,
                'account_id': self.cash_rounding_a.profit_account_id.id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': 0.01,
                'price_subtotal': 0.01,
                'price_total': 0.01,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -0.01,
                'debit': 0.0,
                'credit': 0.01,
                'date_maturity': False,
                'tax_exigible': True,
            },
            {
                **self.product_line_vals_1,
                'price_unit': 999.99,
                'price_subtotal': 999.99,
                'price_total': 1149.99,
                'amount_currency': -999.99,
                'credit': 999.99,
            },
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            self.term_line_vals_1,
        ], self.move_vals)

        move_form = Form(self.invoice)
        # Change the cash rounding to one having 'biggest_tax'.
        move_form.invoice_cash_rounding_id = self.cash_rounding_b
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 999.99,
                'price_subtotal': 999.99,
                'price_total': 1149.99,
                'amount_currency': -999.99,
                'credit': 999.99,
            },
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            {
                'name': '%s (rounding)' % self.tax_sale_a.name,
                'product_id': False,
                'account_id': self.company_data['default_account_tax_sale'].id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': -0.04,
                'price_subtotal': -0.04,
                'price_total': -0.04,
                'tax_ids': [],
                'tax_line_id': self.tax_sale_a.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 0.04,
                'debit': 0.04,
                'credit': 0.0,
                'date_maturity': False,
                'tax_exigible': True,
            },
            {
                **self.term_line_vals_1,
                'price_unit': -1409.95,
                'price_subtotal': -1409.95,
                'price_total': -1409.95,
                'amount_currency': 1409.95,
                'debit': 1409.95,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 1199.99,
            'amount_tax': 209.96,
            'amount_total': 1409.95,
        })

    def test_out_invoice_line_onchange_currency_1(self):
        move_form = Form(self.invoice.with_context(dudu=True))
        move_form.currency_id = self.currency_data['currency']
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1000.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -180.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1410.0,
                'debit': 705.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
        })

        move_form = Form(self.invoice)
        # Change the date to get another rate: 1/3 instead of 1/2.
        move_form.date = fields.Date.from_string('2016-01-01')
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1000.0,
                'credit': 333.33,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'credit': 66.67,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -180.0,
                'credit': 60.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'credit': 10.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1410.0,
                'debit': 470.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2016-01-01'),
        })

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            # 0.045 * 0.1 = 0.0045. As the foreign currency has a 0.001 rounding,
            # the result should be 0.005 after rounding.
            line_form.quantity = 0.1
            line_form.price_unit = 0.045
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'quantity': 0.1,
                'price_unit': 0.05,
                'price_subtotal': 0.005,
                'price_total': 0.006,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -0.005,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'credit': 66.67,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': 30.0,
                'price_subtotal': 30.001,
                'price_total': 30.001,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.001,
                'credit': 10.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'credit': 10.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'price_unit': -260.01,
                'price_subtotal': -260.006,
                'price_total': -260.006,
                'amount_currency': 260.006,
                'debit': 86.67,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2016-01-01'),
            'amount_untaxed': 200.005,
            'amount_tax': 60.001,
            'amount_total': 260.006,
        })

        # Exit the multi-currencies.
        move_form = Form(self.invoice)
        move_form.currency_id = self.company_data['currency']
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'quantity': 0.1,
                'price_unit': 0.05,
                'price_subtotal': 0.01,
                'price_total': 0.01,
                'amount_currency': -0.01,
                'credit': 0.01,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'price_unit': 30.0,
                'price_subtotal': 30.0,
                'price_total': 30.0,
                'amount_currency': -30.0,
                'credit': 30.0,
            },
            self.tax_line_vals_2,
            {
                **self.term_line_vals_1,
                'price_unit': -260.01,
                'price_subtotal': -260.01,
                'price_total': -260.01,
                'amount_currency': 260.01,
                'debit': 260.01,
            },
        ], {
            **self.move_vals,
            'currency_id': self.company_data['currency'].id,
            'date': fields.Date.from_string('2016-01-01'),
            'amount_untaxed': 200.01,
            'amount_tax': 60.0,
            'amount_total': 260.01,
        })

    def test_out_invoice_create_refund(self):
        self.invoice.action_post()

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason',
            'refund_method': 'refund',
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'not_paid', "Refunding with a draft credit note should keep the invoice 'not_paid'.")
        self.assertInvoiceValues(reverse_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': 1000.0,
                'debit': 1000.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': 200.0,
                'debit': 200.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': 180.0,
                'debit': 180.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 30.0,
                'debit': 30.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': -1410.0,
                'debit': 0.0,
                'credit': 1410.0,
                'date_maturity': move_reversal.date,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': None,
            'name': 'RINV/2019/02/0001',
            'date': move_reversal.date,
            'state': 'draft',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'payment_state': 'not_paid',
        })

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason',
            'refund_method': 'cancel',
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'reversed', "After cancelling it with a reverse invoice, an invoice should be in 'reversed' state.")
        self.assertInvoiceValues(reverse_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': 1000.0,
                'debit': 1000.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': 200.0,
                'debit': 200.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': 180.0,
                'debit': 180.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 30.0,
                'debit': 30.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': -1410.0,
                'debit': 0.0,
                'credit': 1410.0,
                'date_maturity': move_reversal.date,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': None,
            'date': move_reversal.date,
            'state': 'posted',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'payment_state': 'paid',
        })

    def test_out_invoice_create_refund_multi_currency(self):
        ''' Test the account.move.reversal takes care about the currency rates when setting
        a custom reversal date.
        '''
        move_form = Form(self.invoice)
        move_form.date = '2016-01-01'
        move_form.currency_id = self.currency_data['currency']
        move_form.save()

        self.invoice.action_post()

        # The currency rate changed from 1/3 to 1/2.
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2017-01-01'),
            'reason': 'no reason',
            'refund_method': 'refund',
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'not_paid', "Refunding with a draft credit note should keep the invoice 'not_paid'.")
        self.assertInvoiceValues(reverse_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': 1000.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 500.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': 200.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 100.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': 180.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 90.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 30.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 15.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': -1410.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 0.0,
                'credit': 705.0,
                'date_maturity': move_reversal.date,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': None,
            'currency_id': self.currency_data['currency'].id,
            'date': move_reversal.date,
            'state': 'draft',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'payment_state': 'not_paid',
        })

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2017-01-01'),
            'reason': 'no reason',
            'refund_method': 'cancel',
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'reversed', "After cancelling it with a reverse invoice, an invoice should be in 'reversed' state.")
        self.assertInvoiceValues(reverse_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': 1000.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 500.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': 200.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 100.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': 180.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 90.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 30.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 15.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': -1410.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 0.0,
                'credit': 705.0,
                'date_maturity': move_reversal.date,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': None,
            'currency_id': self.currency_data['currency'].id,
            'date': move_reversal.date,
            'state': 'posted',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'payment_state': 'paid',
        })

    def test_out_invoice_create_refund_auto_post(self):
        self.invoice.action_post()

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.today() + timedelta(days=7),
            'reason': 'no reason',
            'refund_method': 'modify',
        })
        move_reversal.reverse_moves()
        refund = self.env['account.move'].search([('move_type', '=', 'out_refund'), ('company_id', '=', self.invoice.company_id.id)])

        self.assertRecordValues(refund, [{
            'state': 'draft',
            'auto_post': True,
        }])

    def test_out_invoice_create_1(self):
        # Test creating an account_move with the least information.
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, {
                    'product_id': self.product_a.id,
                    'product_uom_id': self.product_a.uom_id.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
                }),
                (0, None, {
                    'product_id': self.product_b.id,
                    'product_uom_id': self.product_b.uom_id.id,
                    'quantity': 1.0,
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, self.product_b.taxes_id.ids)],
                }),
            ]
        })

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1000.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -180.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1410.0,
                'debit': 705.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
        })

    def test_out_invoice_create_child_partner(self):
        # Test creating an account_move on a child partner.
        # This needs to attach the lines to the parent partner id.
        partner_a_child = self.env['res.partner'].create({
            'name': 'partner_a_child',
            'parent_id': self.partner_a.id
        })
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner_a_child.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, self.product_line_vals_1),
                (0, None, self.product_line_vals_2),
            ]
        })

        self.assertEqual(partner_a_child.id, move.partner_id.id, 'Keep child partner on the account move record')
        self.assertEqual(self.partner_a.id, move.line_ids[0].partner_id.id, 'Set parent partner on the account move line records')

    def test_out_invoice_write_1(self):
        # Test creating an account_move with the least information.
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, self.product_line_vals_1),
            ]
        })
        move.write({
            'invoice_line_ids': [
                (0, None, self.product_line_vals_2),
            ]
        })

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1000.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -180.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1410.0,
                'debit': 705.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
        })

    def test_out_invoice_write_2(self):
        ''' Ensure to not messing the invoice when writing a bad account type. '''
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, None, {
                    'name': 'test_out_invoice_write_2',
                    'quantity': 1.0,
                    'price_unit': 2000,
                }),
            ]
        })

        receivable_lines = move.line_ids.filtered(lambda line: line.account_id.user_type_id.type == 'receivable')
        not_receivable_lines = move.line_ids - receivable_lines

        # Write a receivable account on a not-receivable line.
        with self.assertRaises(UserError), self.cr.savepoint():
            not_receivable_lines.write({'account_id': receivable_lines[0].account_id.copy().id})

        # Write a not-receivable account on a receivable line.
        with self.assertRaises(UserError), self.cr.savepoint():
            receivable_lines.write({'account_id': not_receivable_lines[0].account_id.copy().id})

        # Write another receivable account on a receivable line.
        receivable_lines.write({'account_id': receivable_lines[0].account_id.copy().id})

    def test_out_invoice_post_1(self):
        ''' Check the invoice_date will be set automatically at the post date. '''
        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):
            # Create an invoice with rate 1/3.
            move = self.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_date': fields.Date.from_string('2016-01-01'),
                'currency_id': self.currency_data['currency'].id,
                'invoice_payment_term_id': self.pay_terms_a.id,
                'invoice_line_ids': [
                    (0, None, self.product_line_vals_1),
                    (0, None, self.product_line_vals_2),
                ]
            })

            # Remove the invoice_date to check:
            # - The invoice_date must be set automatically at today during the post.
            # - As the invoice_date changed, date did too so the currency rate has changed (1/3 => 1/2).
            # - A different invoice_date implies also a new date_maturity.
            # Add a manual edition of a tax line:
            # - The modification must be preserved in the business fields.
            # - The journal entry must be balanced before / after the post.
            move.write({
                'invoice_date': False,
                'line_ids': [
                    (1, move.line_ids.filtered(lambda line: line.tax_line_id.id == self.tax_line_vals_1['tax_line_id']).id, {
                        'amount_currency': -200.0,
                    }),
                    (1, move.line_ids.filtered(lambda line: line.date_maturity).id, {
                        'amount_currency': 1430.0,
                    }),
                ],
            })

            move.action_post()

            self.assertInvoiceValues(move, [
                {
                    **self.product_line_vals_1,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -1000.0,
                    'credit': 500.0,
                },
                {
                    **self.product_line_vals_2,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -200.0,
                    'credit': 100.0,
                },
                {
                    **self.tax_line_vals_1,
                    'currency_id': self.currency_data['currency'].id,
                    'price_unit': 200.0,
                    'price_subtotal': 200.0,
                    'price_total': 200.0,
                    'amount_currency': -200.0,
                    'credit': 100.0,
                },
                {
                    **self.tax_line_vals_2,
                    'currency_id': self.currency_data['currency'].id,
                    'amount_currency': -30.0,
                    'credit': 15.0,
                },
                {
                    **self.term_line_vals_1,
                    'name': move.name,
                    'currency_id': self.currency_data['currency'].id,
                    'price_unit': -1430.0,
                    'price_subtotal': -1430.0,
                    'price_total': -1430.0,
                    'amount_currency': 1430.0,
                    'debit': 715.0,
                    'date_maturity': frozen_today,
                },
            ], {
                **self.move_vals,
                'payment_reference': move.name,
                'currency_id': self.currency_data['currency'].id,
                'date': frozen_today,
                'invoice_date': frozen_today,
                'invoice_date_due': frozen_today,
                'amount_tax': 230.0,
                'amount_total': 1430.0,
            })

    def test_out_invoice_post_2(self):
        ''' Check the date will be set automatically at the next available post date due to the tax lock date. '''
        # Create an invoice with rate 1/3.
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2016-01-01'),
            'date': fields.Date.from_string('2015-01-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, {
                    'name': self.product_line_vals_1['name'],
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'quantity': self.product_line_vals_1['quantity'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'tax_ids': self.product_line_vals_1['tax_ids'],
                }),
                (0, None, {
                    'name': self.product_line_vals_2['name'],
                    'product_id': self.product_line_vals_2['product_id'],
                    'product_uom_id': self.product_line_vals_2['product_uom_id'],
                    'quantity': self.product_line_vals_2['quantity'],
                    'price_unit': self.product_line_vals_2['price_unit'],
                    'tax_ids': self.product_line_vals_2['tax_ids'],
                }),
            ],
        })

        # Add a manual edition of a tax line:
        # - The modification must be preserved in the business fields.
        # - The journal entry must be balanced before / after the post.
        move.write({
            'line_ids': [
                (1, move.line_ids.filtered(lambda line: line.tax_line_id.id == self.tax_line_vals_1['tax_line_id']).id, {
                    'amount_currency': -200.0,
                }),
                (1, move.line_ids.filtered(lambda line: line.date_maturity).id, {
                    'amount_currency': 1430.0,
                }),
            ],
        })

        # Set the tax lock date:
        # - The date must be set automatically at the date after the tax_lock_date.
        # - As the date changed, the currency rate has changed (1/3 => 1/2).
        move.company_id.tax_lock_date = fields.Date.from_string('2016-12-31')

        move.action_post()

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1000.0,
                'debit': 0.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'price_unit': 200.0,
                'price_subtotal': 200.0,
                'price_total': 200.0,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'name': move.name,
                'currency_id': self.currency_data['currency'].id,
                'price_unit': -1430.0,
                'price_subtotal': -1430.0,
                'price_total': -1430.0,
                'amount_currency': 1430.0,
                'debit': 715.0,
                'credit': 0.0,
                'date_maturity': fields.Date.from_string('2016-01-01'),
            },
        ], {
            **self.move_vals,
            'payment_reference': move.name,
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2017-01-01'),
            'amount_untaxed': 1200.0,
            'amount_tax': 230.0,
            'amount_total': 1430.0,
        })

    def test_out_invoice_switch_out_refund_1(self):
        # Test creating an account_move with an out_invoice_type and switch it in an out_refund.
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, self.product_line_vals_1),
                (0, None, self.product_line_vals_2),
            ]
        })
        move.action_switch_invoice_into_refund_credit_note()

        self.assertRecordValues(move, [{'move_type': 'out_refund'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1000.0,
                'debit': 500.0,
                'credit': 0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'debit': 100.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 180.0,
                'debit': 90.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 30.0,
                'debit': 15.0,
                'credit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1410.0,
                'credit': 705.0,
                'debit': 0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
        })

    def test_out_invoice_switch_out_refund_2(self):
        # Test creating an account_move with an out_invoice_type and switch it in an out_refund and a negative quantity.
        modified_product_line_vals_1 = self.product_line_vals_1.copy()
        modified_product_line_vals_1.update({'quantity': -modified_product_line_vals_1['quantity']})
        modified_product_line_vals_2 = self.product_line_vals_2.copy()
        modified_product_line_vals_2.update({'quantity': -modified_product_line_vals_2['quantity']})
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, modified_product_line_vals_1),
                (0, None, modified_product_line_vals_2),
            ]
        })

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1000.0,
                'price_subtotal': -1000.0,
                'price_total': -1150.0,
                'debit': 500.0,
                'credit': 0,
                'quantity': -1.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'price_subtotal': -200.0,
                'price_total': -260.0,
                'debit': 100.0,
                'credit': 0,
                'quantity': -1.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 180.0,
                'price_subtotal': -180.0,
                'price_total': -180.0,
                'price_unit': -180.0,
                'debit': 90.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 30.0,
                'price_subtotal': -30.0,
                'price_total': -30.0,
                'price_unit': -30.0,
                'debit': 15.0,
                'credit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1410.0,
                'price_subtotal': 1410.0,
                'price_total': 1410.0,
                'price_unit': 1410.0,
                'credit': 705.0,
                'debit': 0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'amount_tax' : -self.move_vals['amount_tax'],
            'amount_total' : -self.move_vals['amount_total'],
            'amount_untaxed' : -self.move_vals['amount_untaxed'],
        })

        move.action_switch_invoice_into_refund_credit_note()

        self.assertRecordValues(move, [{'move_type': 'out_refund'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1000.0,
                'debit': 500.0,
                'credit': 0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'debit': 100.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 180.0,
                'debit': 90.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 30.0,
                'debit': 15.0,
                'credit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1410.0,
                'credit': 705.0,
                'debit': 0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'amount_tax' : self.move_vals['amount_tax'],
            'amount_total' : self.move_vals['amount_total'],
            'amount_untaxed' : self.move_vals['amount_untaxed'],
        })

    def test_out_invoice_reverse_move_tags(self):
        country = self.env.ref('base.us')
        tags = self.env['account.account.tag'].create([{
            'name': "Test tag %s" % i,
            'applicability': 'taxes',
            'country_id': country.id,
        } for i in range(8)])

        taxes = self.env['account.tax'].create([{
            'name': "Test tax include_base_amount = %s" % include_base_amount,
            'amount': 10.0,
            'include_base_amount': include_base_amount,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tags[(i * 4)].ids)],
                }),
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, tags[(i * 4) + 1].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tags[(i * 4) + 2].ids)],
                }),
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, tags[(i * 4) + 3].ids)],
                }),
            ],
        } for i, include_base_amount in enumerate((True, False))])

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, taxes.ids)],
                }),
            ]
        })
        invoice.action_post()

        self.assertRecordValues(invoice.line_ids.sorted('tax_line_id'), [
            # Product line
            {'tax_line_id': False,          'tax_ids': taxes.ids,       'tax_tag_ids': (tags[0] + tags[4]).ids},
            # Receivable line
            {'tax_line_id': False,          'tax_ids': [],              'tax_tag_ids': []},
            # Tax lines
            {'tax_line_id': taxes[0].id,    'tax_ids': taxes[1].ids,    'tax_tag_ids': (tags[1] + tags[4]).ids},
            {'tax_line_id': taxes[1].id,    'tax_ids': [],              'tax_tag_ids': tags[5].ids},
        ])

        refund = invoice._reverse_moves(cancel=True)

        self.assertRecordValues(refund.line_ids.sorted('tax_line_id'), [
            # Product line
            {'tax_line_id': False,          'tax_ids': taxes.ids,       'tax_tag_ids': (tags[2] + tags[6]).ids},
            # Receivable line
            {'tax_line_id': False,          'tax_ids': [],              'tax_tag_ids': []},
            # Tax lines
            {'tax_line_id': taxes[0].id,    'tax_ids': taxes[1].ids,    'tax_tag_ids': (tags[3] + tags[6]).ids},
            {'tax_line_id': taxes[1].id,    'tax_ids': [],              'tax_tag_ids': tags[7].ids},
        ])

    def test_out_invoice_change_period_accrual_1(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2017-01-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, {
                    'name': self.product_line_vals_1['name'],
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'quantity': self.product_line_vals_1['quantity'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'tax_ids': self.product_line_vals_1['tax_ids'],
                }),
                (0, None, {
                    'name': self.product_line_vals_2['name'],
                    'product_id': self.product_line_vals_2['product_id'],
                    'product_uom_id': self.product_line_vals_2['product_uom_id'],
                    'quantity': self.product_line_vals_2['quantity'],
                    'price_unit': self.product_line_vals_2['price_unit'],
                    'tax_ids': self.product_line_vals_2['tax_ids'],
                }),
            ]
        })
        move.action_post()

        wizard = self.env['account.automatic.entry.wizard']\
            .with_context(active_model='account.move.line', active_ids=move.invoice_line_ids.ids).create({
            'action': 'change_period',
            'date': '2018-01-01',
            'percentage': 60,
            'journal_id': self.company_data['default_journal_misc'].id,
            'expense_accrual_account': self.env['account.account'].create({
                'name': 'Accrual Expense Account',
                'code': '234567',
                'user_type_id': self.env.ref('account.data_account_type_expenses').id,
                'reconcile': True,
            }).id,
            'revenue_accrual_account': self.env['account.account'].create({
                'name': 'Accrual Revenue Account',
                'code': '765432',
                'user_type_id': self.env.ref('account.data_account_type_expenses').id,
                'reconcile': True,
            }).id,
        })
        wizard_res = wizard.do_action()

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1000.0,
                'debit': 0.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -180.0,
                'debit': 0.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'name': 'INV/2017/01/0001',
                'amount_currency': 1410.0,
                'debit': 705.0,
                'credit': 0.0,
                'date_maturity': fields.Date.from_string('2017-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2017-01-01'),
            'payment_reference': 'INV/2017/01/0001',
        })

        accrual_lines = self.env['account.move'].browse(wizard_res['domain'][0][2]).line_ids.sorted('date')
        self.assertRecordValues(accrual_lines, [
            {'amount_currency': 600.0,  'debit': 300.0, 'credit': 0.0,      'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': -600.0, 'debit': 0.0,   'credit': 300.0,    'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': 120.0,  'debit': 60.0,  'credit': 0.0,      'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': -120.0, 'debit': 0.0,   'credit': 60.0,     'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': -600.0, 'debit': 0.0,   'credit': 300.0,    'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': 600.0,  'debit': 300.0, 'credit': 0.0,      'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': -120.0, 'debit': 0.0,   'credit': 60.0,     'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': 120.0,  'debit': 60.0,  'credit': 0.0,      'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
        ])

    def test_out_invoice_filter_zero_balance_lines(self):
        zero_balance_payment_term = self.env['account.payment.term'].create({
            'name': 'zero_balance_payment_term',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'sequence': 10,
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
                (0, 0, {
                    'value': 'balance',
                    'value_amount': 0.0,
                    'sequence': 20,
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
            ],
        })

        zero_balance_tax = self.env['account.tax'].create({
            'name': 'zero_balance_tax',
            'amount_type': 'percent',
            'amount': 0.0,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'invoice_payment_term_id': zero_balance_payment_term.id,
            'invoice_line_ids': [(0, None, {
                'name': 'whatever',
                'quantity': 1.0,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, zero_balance_tax.ids)],
            })]
        })

        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(len(invoice.line_ids), 2)

    def test_out_invoice_recomputation_receivable_lines(self):
        ''' Test a tricky specific case caused by some framework limitations. Indeed, when
        saving a record, some fields are written to the records even if the value is the same
        as the previous one. It could lead to an unbalanced journal entry when the recomputed
        line is the receivable/payable one.

        For example, the computed price_subtotal are the following:
        1471.95 / 0.14 = 10513.93
        906468.18 / 0.14 = 6474772.71
        1730.84 / 0.14 = 12363.14
        17.99 / 0.14 = 128.50
        SUM = 6497778.28

        But when recomputing the receivable line:
        909688.96 / 0.14 = 6497778.285714286 => 6497778.29

        This recomputation was made because the framework was writing the same 'price_unit'
        as the previous value leading to a recomputation of the debit/credit.
        '''
        self.env['decimal.precision'].search([
            ('name', '=', self.env['account.move.line']._fields['price_unit']._digits),
        ]).digits = 5

        self.env['res.currency.rate'].create({
            'name': '2019-01-01',
            'rate': 0.14,
            'currency_id': self.currency_data['currency'].id,
            'company_id': self.company_data['company'].id,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 38.73553, 'quantity': 38.0}),
                (0, 0, {'name': 'line2', 'price_unit': 4083.19000, 'quantity': 222.0}),
                (0, 0, {'name': 'line3', 'price_unit': 49.45257, 'quantity': 35.0}),
                (0, 0, {'name': 'line4', 'price_unit': 17.99000, 'quantity': 1.0}),
            ],
        })

        # assertNotUnbalancedEntryWhenSaving
        with Form(invoice) as move_form:
            move_form.invoice_payment_term_id = self.env.ref('account.account_payment_term_30days')

    def test_out_invoice_rounding_recomputation_receivable_lines(self):
        ''' Test rounding error due to the fact that subtracting then rounding is different from
        rounding then subtracting.
        '''
        self.env['decimal.precision'].search([
            ('name', '=', self.env['account.move.line']._fields['price_unit']._digits),
        ]).digits = 5

        self.env['res.currency.rate'].search([]).unlink()

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
        })

        # assertNotUnbalancedEntryWhenSaving
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.name = 'line1'
                line_form.account_id = self.company_data['default_account_revenue']
                line_form.tax_ids.clear()
                line_form.price_unit = 0.89500
        move_form.save()

    def test_out_invoice_multi_company(self):
        ''' Ensure the properties are found on the right company.
        '''

        product = self.env['product.product'].create({
            'name': 'product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'company_id': False,
        })

        partner = self.env['res.partner'].create({
            'name': 'partner',
            'company_id': False,
        })

        journal = self.env['account.journal'].create({
            'name': 'test_out_invoice_multi_company',
            'code': 'XXXXX',
            'type': 'sale',
            'company_id': self.company_data_2['company'].id,
        })

        product.with_company(self.company_data['company']).write({
            'property_account_income_id': self.company_data['default_account_revenue'].id,
        })

        partner.with_company(self.company_data['company']).write({
            'property_account_receivable_id': self.company_data['default_account_receivable'].id,
        })

        product.with_company(self.company_data_2['company']).write({
            'property_account_income_id': self.company_data_2['default_account_revenue'].id,
        })

        partner.with_company(self.company_data_2['company']).write({
            'property_account_receivable_id': self.company_data_2['default_account_receivable'].id,
        })

        def _check_invoice_values(invoice):
            self.assertInvoiceValues(invoice, [
                {
                    'product_id': product.id,
                    'account_id': self.company_data_2['default_account_revenue'].id,
                    'debit': 0.0,
                    'credit': 1000.0,
                },
                {
                    'product_id': False,
                    'account_id': self.company_data_2['default_account_receivable'].id,
                    'debit': 1000.0,
                    'credit': 0.0,
                },
            ], {
                'amount_untaxed': 1000.0,
                'amount_total': 1000.0,
            })

        invoice_create = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': partner.id,
            'journal_id': journal.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'price_unit': 1000.0,
            })],
        })

        _check_invoice_values(invoice_create)

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.journal_id = journal
        move_form.partner_id = partner
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = product
            line_form.tax_ids.clear()
        invoice_onchange = move_form.save()

        _check_invoice_values(invoice_onchange)

    def test_out_invoice_multiple_switch_payment_terms(self):
        ''' When switching immediate payment term to 30% advance then back to immediate payment term, ensure the
        receivable line is back to its previous value. If some business fields are not well updated, it could lead to a
        recomputation of debit/credit when writing and then, an unbalanced journal entry.
        '''
        # assertNotUnbalancedEntryWhenSaving
        with Form(self.invoice) as move_form:
            move_form.invoice_payment_term_id = self.pay_terms_b    # Switch to 30% in advance payment terms
            move_form.invoice_payment_term_id = self.pay_terms_a    # Back to immediate payment term

    def test_out_invoice_copy_custom_date(self):
        """ When creating a refund for a given invoice, the invoice is copied first. This test ensures the payment
        terms are well recomputed in order to take the new date into account.
        """
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'invoice_date_due': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [
                (0, None, {
                    'product_id': self.product_a.id,
                    'product_uom_id': self.product_a.uom_id.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
                }),
            ]
        })

        copy_invoice = invoice.copy(default={'invoice_date_due': '2018-01-01'})
        self.assertRecordValues(copy_invoice, [
            {'invoice_date_due': fields.Date.from_string('2018-01-01')},
        ])
        self.assertRecordValues(copy_invoice.line_ids.filtered('date_maturity'), [
            {'date_maturity': fields.Date.from_string('2018-01-01')},
        ])
