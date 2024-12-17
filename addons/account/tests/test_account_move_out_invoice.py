# -*- coding: utf-8 -*-
# pylint: disable=bad-whitespace
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged
from odoo import fields, Command
from odoo.exceptions import UserError

from collections import defaultdict
from unittest.mock import patch
from datetime import timedelta
from freezegun import freeze_time



@tagged('post_install', '-at_install')
class TestAccountMoveOutInvoiceOnchanges(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('HRK', rounding=0.001)
        cls.company_data_2 = cls.setup_other_company()

        cls.invoice = cls.init_invoice('out_invoice', products=cls.product_a+cls.product_b)

        cls.product_line_vals_1 = {
            'name': 'product_a',
            'product_id': cls.product_a.id,
            'account_id': cls.product_a.property_account_income_id.id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': cls.product_a.uom_id.id,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 1000.0,
            'price_subtotal': 1000.0,
            'price_total': 1150.0,
            'tax_ids': cls.product_a.taxes_id.filtered(lambda t: t.company_id == cls.invoice.company_id).ids,
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -1000.0,
            'debit': 0.0,
            'credit': 1000.0,
            'date_maturity': False,
        }
        cls.product_line_vals_2 = {
            'name': 'product_b',
            'product_id': cls.product_b.id,
            'account_id': cls.product_b.property_account_income_id.id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': cls.product_b.uom_id.id,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 200.0,
            'price_subtotal': 200.0,
            'price_total': 260.0,
            'tax_ids': cls.product_b.taxes_id.filtered(lambda t: t.company_id == cls.invoice.company_id).ids,
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -200.0,
            'debit': 0.0,
            'credit': 200.0,
            'date_maturity': False,
        }
        cls.tax_line_vals_1 = {
            'name': cls.tax_sale_a.name,
            'product_id': False,
            'account_id': cls.company_data['default_account_tax_sale'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': False,
            'discount': 0.0,
            'price_unit': 0.0,
            'price_subtotal': 0.0,
            'price_total': 0.0,
            'tax_ids': [],
            'tax_line_id': cls.tax_sale_a.id,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -180.0,
            'debit': 0.0,
            'credit': 180.0,
            'date_maturity': False,
        }
        cls.tax_line_vals_2 = {
            'name': cls.tax_sale_b.name,
            'product_id': False,
            'account_id': cls.company_data['default_account_tax_sale'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': False,
            'discount': 0.0,
            'price_unit': 0.0,
            'price_subtotal': 0.0,
            'price_total': 0.0,
            'tax_ids': [],
            'tax_line_id': cls.tax_sale_b.id,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -30.0,
            'debit': 0.0,
            'credit': 30.0,
            'date_maturity': False,
        }
        cls.term_line_vals_1 = {
            'name': '',
            'product_id': False,
            'account_id': cls.company_data['default_account_receivable'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': False,
            'discount': 0.0,
            'price_unit': 0.0,
            'price_subtotal': 0.0,
            'price_total': 0.0,
            'tax_ids': [],
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': 1410.0,
            'debit': 1410.0,
            'credit': 0.0,
            'date_maturity': fields.Date.from_string('2019-01-01'),
        }
        cls.move_vals = {
            'partner_id': cls.partner_a.id,
            'currency_id': cls.company_data['currency'].id,
            'journal_id': cls.company_data['default_journal_sale'].id,
            'date': fields.Date.from_string('2019-01-01'),
            'fiscal_position_id': False,
            'payment_reference': False,
            'invoice_payment_term_id': cls.pay_terms_a.id,
            'amount_untaxed': 1200.0,
            'amount_tax': 210.0,
            'amount_total': 1410.0,
        }
        cls.env.user.groups_id += cls.env.ref('uom.group_uom')

    def setUp(self):
        super(TestAccountMoveOutInvoiceOnchanges, self).setUp()
        self.assertInvoiceValues(self.invoice, [
            self.product_line_vals_1,
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            self.term_line_vals_1,
        ], self.move_vals)

    @freeze_time('2020-01-15')
    def test_out_invoice_onchange_invoice_date(self):
        for tax_date, invoice_date, accounting_date in [
            ('2019-03-31', '2019-05-12', '2019-05-12'),
            ('2019-03-31', '2019-02-10', '2019-12-31'),
            ('2019-05-31', '2019-06-15', '2019-06-15'),
        ]:
            self.invoice.company_id.tax_lock_date = tax_date
            invoice = self.invoice.copy()
            with Form(invoice) as move_form:
                move_form.invoice_date = invoice_date
            invoice.action_post()
            self.assertEqual(invoice.date, fields.Date.to_date(accounting_date))

    def test_out_invoice_line_onchange_product_1(self):
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.product_id = self.product_b
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'name': 'product_b',
                'product_id': self.product_b.id,
                'product_uom_id': self.product_b.uom_id.id,
                'account_id': self.product_b.property_account_income_id.id,
                'price_unit': 200.0,
                'price_subtotal': 200.0,
                'price_total': 260.0,
                'tax_ids': self.product_b.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids,
                'amount_currency': -200.0,
                'credit': 200.0,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'amount_currency': -60.0,
                'credit': 60.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': -60.0,
                'credit': 60.0,
            },
            {
                **self.term_line_vals_1,
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
            'price_include_override': 'tax_included',
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
        move_form.currency_id = self.other_currency
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
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_exclude.id,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.other_currency.id,
                'amount_currency': 230.0,
                'debit': 115.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.other_currency.id,
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
                'currency_id': self.other_currency.id,
                'amount_currency': -2400.0,
                'debit': 0.0,
                'credit': 1200.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_exclude.id,
                'currency_id': self.other_currency.id,
                'amount_currency': -360.0,
                'debit': 0.0,
                'credit': 180.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.other_currency.id,
                'amount_currency': 2760.0,
                'debit': 1380.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.other_currency.id,
            'fiscal_position_id': fiscal_position.id,
            'amount_untaxed': 2400.0,
            'amount_tax': 360.0,
            'amount_total': 2760.0,
        })

        # Check rounding.
        decimal_precision_name = self.env['account.move.line']._fields['price_unit']._digits
        decimal_precision = self.env['decimal.precision'].search([('name', '=', decimal_precision_name)])
        decimal_precision.digits = 4

        product.lst_price = 90.0034
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'fiscal_position_id': fiscal_position.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'test line',
                    'product_id': product.id,
                }),
            ],
        })
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'price_unit': 163.6425, # 90.0034 / 1.10 * 2
            'tax_ids': tax_price_exclude.ids,
            'price_subtotal': 163.643,
            'price_total': 188.189,
        }])

    def test_out_invoice_line_onchange_product_2_with_fiscal_pos_2(self):
        ''' Test mapping a price-included tax (10%) with another price-included tax (20%) on a price_unit of 110.0.
        The price_unit should be 120.0 after applying the fiscal position.
        '''
        tax_price_include_1 = self.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        })
        tax_price_include_2 = self.env['account.tax'].create({
            'name': '20% incl',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'price_include_override': 'tax_included',
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
        move_form.currency_id = self.other_currency
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
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include_2.id,
                'currency_id': self.other_currency.id,
                'amount_currency': -40.0,
                'debit': 0.0,
                'credit': 20.0,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.other_currency.id,
                'amount_currency': 240.0,
                'debit': 120.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.other_currency.id,
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
                'currency_id': self.other_currency.id,
                'amount_currency': -2400.0,
                'debit': 0.0,
                'credit': 1200.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include_2.id,
                'currency_id': self.other_currency.id,
                'amount_currency': -480.0,
                'debit': 0.0,
                'credit': 240.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.other_currency.id,
                'amount_currency': 2880.0,
                'debit': 1440.0,
                'credit': 0.0,
            },
        ], {
            'currency_id': self.other_currency.id,
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
        with move_form.invoice_line_ids.edit(0) as line_form:
            # Reset field except the discount that becomes 100%.
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
                'amount_currency': -30.0,
                'credit': 30.0,
            },
            self.tax_line_vals_2,
            {
                **self.term_line_vals_1,
                'amount_currency': 260.0,
                'debit': 260.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 200.0,
            'amount_tax': 60.0,
            'amount_total': 260.0,
        })

    def test_out_invoice_line_onchange_partner_1(self):
        move_form = Form(self.invoice)
        move_form.partner_id = self.partner_b
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
                'name': 'installment #1',
                'account_id': self.partner_b.property_account_receivable_id.id,
                'partner_id': self.partner_b.id,
                'amount_currency': 423.0,
                'debit': 423.0,
            },
            {
                **self.term_line_vals_1,
                'name': 'installment #2',
                'account_id': self.partner_b.property_account_receivable_id.id,
                'partner_id': self.partner_b.id,
                'amount_currency': 987.0,
                'debit': 987.0,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            **self.move_vals,
            'partner_id': self.partner_b.id,
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
                'name': 'installment #1',
                'account_id': self.partner_b.property_account_receivable_id.id,
                'partner_id': self.partner_b.id,
                'amount_currency': 414.0,
                'debit': 414.0,
            },
            {
                **self.term_line_vals_1,
                'name': 'installment #2',
                'account_id': self.partner_b.property_account_receivable_id.id,
                'partner_id': self.partner_b.id,
                'amount_currency': 966.0,
                'debit': 966.0,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            **self.move_vals,
            'partner_id': self.partner_b.id,
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
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': child_tax_2.ids,
                'tax_line_id': child_tax_1.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -120.0,
                'debit': 0.0,
                'credit': 120.0,
                'date_maturity': False,
            },
            {
                'name': child_tax_1.name,
                'product_id': False,
                'account_id': self.company_data['default_account_tax_sale'].id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': child_tax_2.ids,
                'tax_line_id': child_tax_1.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -80.0,
                'debit': 0.0,
                'credit': 80.0,
                'date_maturity': False,
            },
            {
                'name': child_tax_2.name,
                'product_id': False,
                'account_id': child_tax_2.cash_basis_transition_account_id.id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': child_tax_2.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -120.0,
                'debit': 0.0,
                'credit': 120.0,
                'date_maturity': False,
            },
            {
                **self.term_line_vals_1,
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

        self.other_currency.rounding = 0.01
        decimal_precision.digits = 4

        def check_invoice_values(invoice):
            self.assertInvoiceValues(invoice, [
                {
                    'quantity': 1.0,
                    'price_unit': 0.025,
                    'price_subtotal': 0.03,
                    'debit': 0.0,
                    'credit': 0.02,
                    'currency_id': self.other_currency.id,
                },
                {
                    'quantity': False,
                    'price_unit': 0.0,
                    'price_subtotal': 0.0,
                    'debit': 0.02,
                    'credit': 0.0,
                    'currency_id': self.other_currency.id,
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
            'currency_id': self.other_currency.id,
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
            'currency_id': self.other_currency.id,
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
                    'price_unit': 0.0,
                    'price_subtotal': 0.0,
                    'debit': 0.0,
                    'credit': 17.36,
                },
                {
                    'price_unit': 0.0,
                    'price_subtotal': 0.0,
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
            'price_include_override': 'tax_included',
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
            'price_include_override': 'tax_included',
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
                'tax_ids': (self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company) + tax_price_include).ids,
                'amount_currency': -2180.09,
                'credit': 2180.09,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': -327.01,
                'credit': 327.01,
            },
            {
                'name': tax_price_include.name,
                'product_id': False,
                'account_id': self.product_line_vals_1['account_id'],
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -119.91,
                'debit': 0.0,
                'credit': 119.91,
                'date_maturity': False,
            },
            {
                **self.term_line_vals_1,
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
                'tax_ids': (self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company) + tax_price_include).ids,
                'amount_currency': 2180.09,
                'debit': 2180.09,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
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
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include.id,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 119.91,
                'debit': 119.91,
                'credit': 0.0,
                'date_maturity': False,
            },
            {
                **self.term_line_vals_1,
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
        move_form.currency_id = self.other_currency
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 2300
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 2300.0,
                'price_subtotal': 2180.095,
                'price_total': 2627.014,
                'tax_ids': (self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company) + tax_price_include).ids,
                'currency_id': self.other_currency.id,
                'amount_currency': -2180.095,
                'credit': 1090.05,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -327.014,
                'credit': 163.51,
            },
            {
                'name': tax_price_include.name,
                'product_id': False,
                'account_id': self.product_line_vals_1['account_id'],
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include.id,
                'currency_id': self.other_currency.id,
                'amount_currency': -119.905,
                'debit': 0.0,
                'credit': 59.95,
                'date_maturity': False,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 2627.014,
                'debit': 1313.51,
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
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
                'tax_ids': (self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company) + tax_price_include).ids,
                'currency_id': self.other_currency.id,
                'amount_currency': 2180.095,
                'debit': 1090.05,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
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
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include.id,
                'currency_id': self.other_currency.id,
                'amount_currency': 119.905,
                'debit': 59.95,
                'credit': 0.0,
                'date_maturity': False,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -2627.014,
                'debit': 0.0,
                'credit': 1313.51,
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
            'amount_untaxed': -2180.095,
            'amount_tax': -446.919,
            'amount_total': -2627.014,
        })

    def test_payment_term_line_fiscal_position(self):
        """Test the mapping of payment term line accounts with fiscal position."""
        account_revenue_copy = self.company_data['default_account_revenue'].copy()
        account_receivable_copy = self.company_data['default_account_receivable'].copy()
        fp = self.env['account.fiscal.position'].create({
            'name': 'Test FP',
            'account_ids': [
                Command.create({
                    'account_src_id': self.company_data['default_account_revenue'].id,
                    'account_dest_id': account_revenue_copy.id,
                }),
                Command.create({
                    'account_src_id': self.company_data['default_account_receivable'].id,
                    'account_dest_id': account_receivable_copy.id,
                }),
            ],
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'fiscal_position_id': fp.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 295.0,
                    'tax_ids': [(6, 0, self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                }),
            ],
        })
        invoice.action_post()

        self.assertIn(account_receivable_copy, invoice.line_ids.account_id)
        self.assertIn(account_revenue_copy, invoice.line_ids.account_id)

    def test_out_invoice_line_onchange_analytic(self):
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'test_analytic_account',
            'partner_id': self.invoice.partner_id.id,
            'plan_id': analytic_plan.id,
            'code': 'TEST'
        })

        analytic_distribution = {str(analytic_account.id): 100.00}

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.analytic_distribution = analytic_distribution
        move_form.save()

        # The tax is not flagged as an analytic one. It should change nothing on the taxes.
        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'analytic_distribution': analytic_distribution,
            },
            {
                **self.product_line_vals_2,
                'analytic_distribution': False,
            },
            {
                **self.tax_line_vals_1,
                'analytic_distribution': False,
            },
            {
                **self.tax_line_vals_2,
                'analytic_distribution': False,
            },
            {
                **self.term_line_vals_1,
                'analytic_distribution': False,
            },
        ], self.move_vals)

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.analytic_distribution = {}
        move_form.save()

        # Enable the analytic
        self.tax_sale_a.analytic = True

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.analytic_distribution = analytic_distribution
        move_form.save()

        # The tax is flagged as an analytic one.
        # A new tax line must be generated.
        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'analytic_distribution': analytic_distribution,
            },
            {
                **self.product_line_vals_2,
                'analytic_distribution': False,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': -150.0,
                'credit': 150.0,
                'analytic_distribution': analytic_distribution,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': -30.0,
                'credit': 30.0,
                'analytic_distribution': False,
            },
            {
                **self.tax_line_vals_2,
                'analytic_distribution': False,
            },
            {
                **self.term_line_vals_1,
                'analytic_distribution': False,
            },
        ], self.move_vals)

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.analytic_distribution = {}
        with move_form.invoice_line_ids.edit(1) as line_form:
            line_form.analytic_distribution = {}
        move_form.save()

        # The tax line has been removed.
        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'analytic_distribution': False,
            },
            {
                **self.product_line_vals_2,
                'analytic_distribution': False,
            },
            {
                **self.tax_line_vals_1,
                'analytic_distribution': False,
            },
            {
                **self.tax_line_vals_2,
                'analytic_distribution': False,
            },
            {
                **self.term_line_vals_1,
                'analytic_distribution': False,
            },
        ], self.move_vals)

    def test_out_invoice_line_onchange_analytic_2(self):
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')

        analytic_plan = self.env['account.analytic.plan'].create({'name': 'Plan Test'})
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'test_analytic_account1',
            'plan_id': analytic_plan.id,
            'code': 'TEST1'
        })

        analytic_distribution = {str(analytic_account.id): 100.00}

        self.invoice.write({'invoice_line_ids': [(1, self.invoice.invoice_line_ids.ids[0], {
            'analytic_distribution': analytic_distribution,
        })]})

        self.assertRecordValues(self.invoice.invoice_line_ids, [
            {'analytic_distribution': analytic_distribution},
            {'analytic_distribution': False},
        ])

        # We can remove the analytic account, it is not recomputed by an invalidation
        self.invoice.write({'invoice_line_ids': [(1, self.invoice.invoice_line_ids.ids[0], {
            'analytic_distribution': False,
        })]})

        self.assertRecordValues(self.invoice.invoice_line_ids, [
            {'analytic_distribution': False},
            {'analytic_distribution': False},
        ])

    def test_out_invoice_line_onchange_cash_rounding_1(self):
        # Required for `invoice_cash_rounding_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('account.group_cash_rounding')
        # Test 'add_invoice_line' rounding
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
                'name': 'add_invoice_line',
                'product_id': False,
                'account_id': self.cash_rounding_a.profit_account_id.id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -0.01,
                'debit': 0.0,
                'credit': 0.01,
                'date_maturity': False,
            },
            self.term_line_vals_1,
        ], self.move_vals)

        # Test 'biggest_tax' rounding

        self.company_data['company'].country_id = self.env.ref('base.us')

        # Add a tag to product_a's default tax
        tax_line_tag = self.env['account.account.tag'].create({
            'name': "Tax tag",
            'applicability': 'taxes',
            'country_id': self.company_data['company'].country_id.id,
        })

        repartition_line = self.tax_sale_a.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
        repartition_line.write({'tag_ids': [(4, tax_line_tag.id, 0)]})

        # Create the invoice
        biggest_tax_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'invoice_cash_rounding_id': self.cash_rounding_b.id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 999.99,
                    'tax_ids': [(6, 0, self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                    'product_uom_id':  self.product_a.uom_id.id,
                }),

                (0, 0, {
                    'product_id': self.product_b.id,
                    'price_unit': self.product_b.lst_price,
                    'tax_ids': [(6, 0, self.product_b.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                    'product_uom_id':  self.product_b.uom_id.id,
                }),
            ],
        })

        self.assertInvoiceValues(biggest_tax_invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 999.99,
                'price_subtotal': 999.99,
                'price_total': 1149.99,
                'amount_currency': -999.99,
                'credit': 999.99,
                'tax_repartition_line_id': None,
                'tax_tag_ids': [],
            },
            {
                **self.product_line_vals_2,
                'tax_repartition_line_id': None,
                'tax_tag_ids': [],
            },
            {
                **self.tax_line_vals_1,
                'tax_repartition_line_id': repartition_line.id,
                'tax_tag_ids': tax_line_tag.ids,
            },
            {
                **self.tax_line_vals_2,
                'tax_repartition_line_id': self.tax_sale_b.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                'tax_tag_ids': [],
            },
            {
                'name': '%s (rounding)' % self.tax_sale_a.name,
                'product_id': False,
                'account_id': self.company_data['default_account_tax_sale'].id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': self.tax_sale_a.id,
                'tax_repartition_line_id': repartition_line.id,
                'tax_tag_ids': tax_line_tag.ids,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': 0.04,
                'debit': 0.04,
                'credit': 0.0,
                'date_maturity': False,
            },
            {
                **self.term_line_vals_1,
                'amount_currency': 1409.95,
                'debit': 1409.95,
                'tax_repartition_line_id': None,
                'tax_tag_ids': [],
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 1199.99,
            'amount_tax': 209.96,
            'amount_total': 1409.95,
        })

    def test_out_invoice_line_onchange_currency_1(self):
        move_form = Form(self.invoice)
        move_form.currency_id = self.other_currency
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -180.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 1410.0,
                'debit': 705.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
        })

        # Change the date to get another rate: 1/3 instead of 1/2.
        with Form(self.invoice) as move_form:
            move_form.invoice_date = fields.Date.from_string('2016-01-01')

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
                'credit': 333.33,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'credit': 66.67,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -180.0,
                'credit': 60.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'credit': 10.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 1410.0,
                'debit': 470.0,
                'date_maturity': fields.Date.from_string('2016-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
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
                'currency_id': self.other_currency.id,
                'amount_currency': -0.005,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'credit': 66.67,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.001,
                'credit': 10.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'credit': 10.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 260.006,
                'debit': 86.67,
                'date_maturity': fields.Date.from_string('2016-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
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
                'amount_currency': -30.0,
                'credit': 30.0,
            },
            self.tax_line_vals_2,
            {
                **self.term_line_vals_1,
                'amount_currency': 260.01,
                'debit': 260.01,
                'date_maturity': fields.Date.from_string('2016-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.company_data['currency'].id,
            'date': fields.Date.from_string('2016-01-01'),
            'amount_untaxed': 200.01,
            'amount_tax': 60.0,
            'amount_total': 260.01,
        })

    def test_out_invoice_line_tax_fixed_price_include_free_product(self):
        ''' Check that fixed tax include are correctly computed while the price_unit is 0
        '''
        fixed_tax_price_include = self.env['account.tax'].create({
            'name': 'BEBAT 0.05',
            'type_tax_use': 'sale',
            'amount_type': 'fixed',
            'amount': 0.05,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-03',
            'date': '2022-03-03',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Free product',
                'price_unit': 0.0,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [(6, 0, fixed_tax_price_include.ids)],
            })],
        })
        self.assertInvoiceValues(invoice, [
            {   'display_type': 'product',
                'balance': 0.05,
                'price_subtotal': -0.05,
                'price_total': 0.0,
            }, {
                'display_type': 'tax',
                'balance': -0.05,
                'price_subtotal': 0.0,
                'price_total': 0.0,
            }, {
                'display_type': 'payment_term',
                'balance': 0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
            },
        ], {
            'amount_untaxed': -0.05,
            'amount_tax': 0.05,
            'amount_total': 0.0,
        })

    def test_out_invoice_line_taxes_fixed_price_include_free_product(self):
        ''' Check that fixed tax include are correctly computed while the price_unit is 0
        '''
        # please ensure this test remains consistent with
        # test_free_product_and_price_include_fixed_tax in the sale module
        fixed_tax_price_include_1 = self.env['account.tax'].create({
            'name': 'BEBAT 0.05',
            'type_tax_use': 'sale',
            'amount_type': 'fixed',
            'amount': 0.05,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        })
        fixed_tax_price_include_2 = self.env['account.tax'].create({
            'name': 'Recupel 0.25',
            'type_tax_use': 'sale',
            'amount_type': 'fixed',
            'amount': 0.25,
            'price_include_override': 'tax_included',
            'include_base_amount': True,
        })
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2022-03-03',
            'date': '2022-03-03',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Free product',
                'price_unit': 0.0,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [(6, 0, (fixed_tax_price_include_1 + fixed_tax_price_include_2).ids)],
            })],
        })

        self.assertRecordValues(invoice, [{
            'amount_untaxed': -0.30,
            'amount_tax': 0.30,
            'amount_total': 0.0,
        }])

    def test_out_invoice_create_refund(self):
        self.invoice.action_post()

        bank1 = self.env['res.partner.bank'].create({
            'acc_number': 'BE43798822936101',
            'partner_id': self.partner_a.id,
        })

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason',
            'journal_id': self.invoice.journal_id.id,
        })
        reversal = move_reversal.refund_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'not_paid', "Refunding with a draft credit note should keep the invoice 'not_paid'.")
        self.assertInvoiceValues(reverse_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': 1000.0,
                'debit': 1000.0,
                'credit': 0.0,
                'tax_tag_invert': False,
                'tax_base_amount': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': 200.0,
                'debit': 200.0,
                'credit': 0.0,
                'tax_tag_invert': False,
                'tax_base_amount': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': 180.0,
                'debit': 180.0,
                'credit': 0.0,
                'tax_tag_invert': False,
                'tax_base_amount': 1200.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 30.0,
                'debit': 30.0,
                'credit': 0.0,
                'tax_tag_invert': False,
                'tax_base_amount': 200.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': -1410.0,
                'debit': 0.0,
                'credit': 1410.0,
                'date_maturity': move_reversal.date,
                'tax_tag_invert': False,
                'tax_base_amount': 0.0,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': None,
            'name_placeholder': 'RINV/2019/00001',
            'date': move_reversal.date,
            'state': 'draft',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'payment_state': 'not_paid',
            'partner_bank_id': bank1.id,
        })

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason',
            'journal_id': self.invoice.journal_id.id,
        })
        reversal = move_reversal.modify_moves()
        new_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'reversed', "After cancelling it with a reverse invoice, an invoice should be in 'reversed' state.")
        self.assertInvoiceValues(new_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': -1000.0,
                'debit': 0.0,
                'credit': 1000.0,
                'tax_tag_invert': True,
                'tax_base_amount': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 200.0,
                'tax_tag_invert': True,
                'tax_base_amount': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': -180.0,
                'debit': 0.0,
                'credit': 180.0,
                'tax_tag_invert': True,
                'tax_base_amount': 1200.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 30.0,
                'tax_tag_invert': True,
                'tax_base_amount': 200.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': 1410.0,
                'debit': 1410.0,
                'credit': 0.0,
                'date_maturity': move_reversal.date,
                'tax_tag_invert': False,
                'tax_base_amount': 0.0,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'date': move_reversal.date,
            'state': 'draft',
            'ref': False,
            'payment_state': 'not_paid',
        })

    def test_out_invoice_create_refund_multi_currency(self):
        ''' Test the account.move.reversal takes care about the currency rates when setting
        a custom reversal date.
        '''
        with Form(self.invoice) as move_form:
            move_form.invoice_date = '2016-01-01'
            move_form.currency_id = self.other_currency

        self.invoice.action_post()

        # The currency rate changed from 1/3 to 1/2.
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2017-01-01'),
            'reason': 'no reason',
            'journal_id': self.invoice.journal_id.id,
        })
        reversal = move_reversal.refund_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'not_paid', "Refunding with a draft credit note should keep the invoice 'not_paid'.")
        self.assertInvoiceValues(reverse_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': 1000.0,
                'currency_id': self.other_currency.id,
                'debit': 500.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': 200.0,
                'currency_id': self.other_currency.id,
                'debit': 100.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': 180.0,
                'currency_id': self.other_currency.id,
                'debit': 90.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 30.0,
                'currency_id': self.other_currency.id,
                'debit': 15.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': -1410.0,
                'currency_id': self.other_currency.id,
                'debit': 0.0,
                'credit': 705.0,
                'date_maturity': move_reversal.date,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': None,
            'currency_id': self.other_currency.id,
            'date': move_reversal.date,
            'state': 'draft',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'payment_state': 'not_paid',
        })

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2017-01-01'),
            'reason': 'no reason',
            'journal_id': self.invoice.journal_id.id,
        })
        reversal = move_reversal.modify_moves()
        new_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'reversed', "After cancelling it with a reverse invoice, an invoice should be in 'reversed' state.")
        self.assertInvoiceValues(new_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': -1000.0,
                'currency_id': self.other_currency.id,
                'debit': 0.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': -200.0,
                'currency_id': self.other_currency.id,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': -180.0,
                'currency_id': self.other_currency.id,
                'debit': 0.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': -30.0,
                'currency_id': self.other_currency.id,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': 1410.0,
                'currency_id': self.other_currency.id,
                'debit': 705.0,
                'credit': 0.0,
                'date_maturity': move_reversal.date,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'currency_id': self.other_currency.id,
            'date': move_reversal.date,
            'state': 'draft',
            'ref': False,
            'payment_state': 'not_paid',
        })

    def test_out_invoice_create_refund_auto_post(self):
        self.invoice.action_post()

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.today() + timedelta(days=7),
            'reason': 'no reason',
            'journal_id': self.invoice.journal_id.id,
        })
        move_reversal.modify_moves()
        refund = self.env['account.move'].search([('move_type', '=', 'out_refund'), ('company_id', '=', self.invoice.company_id.id)])

        self.assertRecordValues(refund, [{
            'state': 'draft',
            'auto_post': 'at_date',
        }])

    def test_out_invoice_create_1(self):
        # Test creating an account_move with the least information.
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, {
                    'product_id': self.product_a.id,
                    'product_uom_id': self.product_a.uom_id.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                }),
                (0, None, {
                    'product_id': self.product_b.id,
                    'product_uom_id': self.product_b.uom_id.id,
                    'quantity': 1.0,
                    'price_unit': 200.0,
                    'tax_ids': [(6, 0, self.product_b.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                }),
            ]
        })

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -180.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 1410.0,
                'debit': 705.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
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
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_1['tax_ids'])],
                }),
                Command.create({
                    'product_id': self.product_line_vals_2['product_id'],
                    'product_uom_id': self.product_line_vals_2['product_uom_id'],
                    'price_unit': self.product_line_vals_2['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_2['tax_ids'])],
                }),
            ],
        })

        self.assertEqual(partner_a_child.id, move.partner_id.id, 'Keep child partner on the account move record')
        self.assertEqual(self.partner_a.id, move.line_ids[0].partner_id.id, 'Set parent partner on the account move line records')

    def test_out_invoice_write_1(self):
        # Test creating an account_move with the least information.
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_1['tax_ids'])],
                }),
            ],
        })
        move.write({
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_line_vals_2['product_id'],
                    'product_uom_id': self.product_line_vals_2['product_uom_id'],
                    'price_unit': self.product_line_vals_2['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_2['tax_ids'])],
                }),
            ],
        })

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -180.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 1410.0,
                'debit': 705.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
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

        receivable_lines = move.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')
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
                'currency_id': self.other_currency.id,
                'invoice_payment_term_id': self.pay_terms_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_line_vals_1['product_id'],
                        'product_uom_id': self.product_line_vals_1['product_uom_id'],
                        'price_unit': self.product_line_vals_1['price_unit'],
                        'tax_ids': [Command.set(self.product_line_vals_1['tax_ids'])],
                    }),
                    Command.create({
                        'product_id': self.product_line_vals_2['product_id'],
                        'product_uom_id': self.product_line_vals_2['product_uom_id'],
                        'price_unit': self.product_line_vals_2['price_unit'],
                        'tax_ids': [Command.set(self.product_line_vals_2['tax_ids'])],
                    }),
                ],
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
                    'currency_id': self.other_currency.id,
                    'amount_currency': -1000.0,
                    'credit': 500.0,
                },
                {
                    **self.product_line_vals_2,
                    'currency_id': self.other_currency.id,
                    'amount_currency': -200.0,
                    'credit': 100.0,
                },
                {
                    **self.tax_line_vals_1,
                    'currency_id': self.other_currency.id,
                    'amount_currency': -200.0,
                    'credit': 100.0,
                },
                {
                    **self.tax_line_vals_2,
                    'currency_id': self.other_currency.id,
                    'amount_currency': -30.0,
                    'credit': 15.0,
                },
                {
                    **self.term_line_vals_1,
                    'name': move.name,
                    'currency_id': self.other_currency.id,
                    'amount_currency': 1430.0,
                    'debit': 715.0,
                    'date_maturity': frozen_today,
                    'account_id': self.company_data['default_account_receivable'].id,
                },
            ], {
                **self.move_vals,
                'payment_reference': move.name,
                'currency_id': self.other_currency.id,
                'date': frozen_today,
                'invoice_date': frozen_today,
                'invoice_date_due': frozen_today,
                'amount_tax': 230.0,
                'amount_total': 1430.0,
            })

    @freeze_time('2017-01-15')
    def test_out_invoice_post_2(self):
        ''' Check the date will be set automatically at today due to the tax lock date. '''
        # Create an invoice with rate 1/3.
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2017-01-15'),
            'date': fields.Date.from_string('2015-01-01'),
            'currency_id': self.other_currency.id,
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
        # - The date must be set automatically at the date of today (2017-01-15).
        # - As the date changed, the currency rate has changed (1/3 => 1/2).
        move.company_id.tax_lock_date = fields.Date.from_string('2016-12-31')

        move.action_post()

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
                'debit': 0.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'name': move.name,
                'currency_id': self.other_currency.id,
                'amount_currency': 1430.0,
                'debit': 715.0,
                'credit': 0.0,
                'date_maturity': fields.Date.from_string('2017-01-15'),
            },
        ], {
            **self.move_vals,
            'payment_reference': move.name,
            'currency_id': self.other_currency.id,
            'date': fields.Date.from_string('2017-01-15'),
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
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_1['tax_ids'])],
                }),
                Command.create({
                    'product_id': self.product_line_vals_2['product_id'],
                    'product_uom_id': self.product_line_vals_2['product_uom_id'],
                    'price_unit': self.product_line_vals_2['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_2['tax_ids'])],
                }),
            ],
        })
        move.action_switch_move_type()

        self.assertRecordValues(move, [{'move_type': 'out_refund'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 1000.0,
                'debit': 500.0,
                'credit': 0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': 200.0,
                'debit': 100.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 180.0,
                'debit': 90.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': 30.0,
                'debit': 15.0,
                'credit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1410.0,
                'credit': 705.0,
                'debit': 0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
        })

    def test_out_invoice_switch_out_refund_2(self):
        # Test creating an account_move with an out_invoice_type and switch it in an out_refund and a negative quantity.
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'quantity': -self.product_line_vals_1['quantity'],
                    'tax_ids': [Command.set(self.product_line_vals_1['tax_ids'])],
                }),
                Command.create({
                    'product_id': self.product_line_vals_2['product_id'],
                    'product_uom_id': self.product_line_vals_2['product_uom_id'],
                    'price_unit': self.product_line_vals_2['price_unit'],
                    'quantity': -self.product_line_vals_2['quantity'],
                    'tax_ids': [Command.set(self.product_line_vals_2['tax_ids'])],
                }),
            ],
        })

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 1000.0,
                'price_subtotal': -1000.0,
                'price_total': -1150.0,
                'debit': 500.0,
                'credit': 0,
                'quantity': -1.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': 200.0,
                'price_subtotal': -200.0,
                'price_total': -260.0,
                'debit': 100.0,
                'credit': 0,
                'quantity': -1.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 180.0,
                'debit': 90.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': 30.0,
                'debit': 15.0,
                'credit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1410.0,
                'credit': 705.0,
                'debit': 0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
            'amount_tax' : -self.move_vals['amount_tax'],
            'amount_total' : -self.move_vals['amount_total'],
            'amount_untaxed' : -self.move_vals['amount_untaxed'],
        })

        move.action_switch_move_type()

        self.assertRecordValues(move, [{'move_type': 'out_refund'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 1000.0,
                'debit': 500.0,
                'credit': 0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': 200.0,
                'debit': 100.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': 180.0,
                'debit': 90.0,
                'credit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': 30.0,
                'debit': 15.0,
                'credit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1410.0,
                'credit': 705.0,
                'debit': 0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
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
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tags[(i * 4)].ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'tag_ids': [(6, 0, tags[(i * 4) + 1].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tags[(i * 4) + 2].ids)],
                }),
                (0, 0, {
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
            'currency_id': self.other_currency.id,
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
                'account_type': 'expense',
                'reconcile': True,
            }).id,
            'revenue_accrual_account': self.env['account.account'].create({
                'name': 'Accrual Revenue Account',
                'code': '765432',
                'account_type': 'expense',
                'reconcile': True,
            }).id,
        })
        wizard_res = wizard.do_action()

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
                'debit': 0.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -180.0,
                'debit': 0.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'name': 'INV/2017/00001',
                'amount_currency': 1410.0,
                'debit': 705.0,
                'credit': 0.0,
                'date_maturity': fields.Date.from_string('2017-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
            'date': fields.Date.from_string('2017-01-01'),
            'payment_reference': 'INV/2017/00001',
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

    @freeze_time('2019-01-16')
    def test_out_invoice_change_period_past_move_date(self):
        move = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_a,
            invoice_date=fields.Date.from_string('2019-01-01'),
            amounts=[1000.0],
            post=True,
        )

        context = {
            'default_move_type': 'out_invoice',
            'active_model': 'account.move.line',
            'active_ids': move.mapped('invoice_line_ids').ids
        }
        wizard = self.env['account.automatic.entry.wizard'] \
            .with_context(context) \
            .create({
                'action': 'change_period',
                'journal_id': self.company_data['default_journal_misc'],
                'revenue_accrual_account': self.company_data['default_account_assets'].id,
            })
        wizard_res = wizard.do_action()

        accrual_moves = self.env['account.move'].browse(wizard_res['domain'][0][2])
        self.assertRecordValues(accrual_moves, [
            {'state': 'posted', 'date': fields.Date.from_string('2019-01-16')},
            {'state': 'posted', 'date': fields.Date.from_string('2019-01-16')},
        ])

    @freeze_time("2017-01-01")
    def test_out_invoice_change_to_future_period_accrual_1(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2017-01-01'),
            'currency_id': self.other_currency.id,
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
                'account_type': 'expense',
                'reconcile': True,
            }).id,
            'revenue_accrual_account': self.env['account.account'].create({
                'name': 'Accrual Revenue Account',
                'code': '765432',
                'account_type': 'expense',
                'reconcile': True,
            }).id,
        })
        wizard_res = wizard.do_action()

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -1000.0,
                'debit': 0.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -200.0,
                'debit': 0.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.other_currency.id,
                'amount_currency': -180.0,
                'debit': 0.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.other_currency.id,
                'amount_currency': -30.0,
                'debit': 0.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.other_currency.id,
                'name': 'INV/2017/00001',
                'amount_currency': 1410.0,
                'debit': 705.0,
                'credit': 0.0,
                'date_maturity': fields.Date.from_string('2017-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.other_currency.id,
            'date': fields.Date.from_string('2017-01-01'),
            'payment_reference': 'INV/2017/00001',
        })

        accrual_lines = self.env['account.move'].browse(wizard_res['domain'][0][2]).line_ids.sorted('date')
        self.assertRecordValues(accrual_lines, [
            {
                'amount_currency': 600.0,
                'debit': 300.0,
                'credit': 0.0,
                'account_id': self.product_line_vals_1['account_id'],
                'reconciled': False
            },
            {
                'amount_currency': -600.0,
                'debit': 0.0,
                'credit': 300.0,
                'account_id': wizard.revenue_accrual_account.id,
                'reconciled': False
            },
            {
                'amount_currency': 120.0,
                'debit': 60.0,
                'credit': 0.0,
                'account_id': self.product_line_vals_2['account_id'],
                'reconciled': False
            },
            {
                'amount_currency': -120.0,
                'debit': 0.0,
                'credit': 60.0,
                'account_id': wizard.revenue_accrual_account.id,
                'reconciled': False
            },
            {
                'amount_currency': -600.0,
                'debit': 0.0,
                'credit': 300.0,
                'account_id': self.product_line_vals_1['account_id'],
                'reconciled': False
            },
            {
                'amount_currency': 600.0,
                'debit': 300.0,
                'credit': 0.0,
                'account_id': wizard.revenue_accrual_account.id,
                'reconciled': False
            },
            {
                'amount_currency': -120.0,
                'debit': 0.0,
                'credit': 60.0,
                'account_id': self.product_line_vals_2['account_id'],
                'reconciled': False
            },
            {
                'amount_currency': 120.0,
                'debit': 60.0,
                'credit': 0.0,
                'account_id': wizard.revenue_accrual_account.id,
                'reconciled': False
            },
        ])

    def test_out_invoice_multi_date_change_period_accrual(self):
        dates = ['2017-01-01', '2017-01-01', '2017-02-01']
        values = []
        for date in dates:
            values.append({
                'move_type': 'out_invoice',
                'date': date,
                'partner_id': self.partner_a.id,
                'invoice_date': fields.Date.from_string(date),
                'currency_id': self.other_currency.id,
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

        moves = self.env['account.move'].create(values)
        moves.action_post()

        wizard = self.env['account.automatic.entry.wizard'].with_context(
            active_model='account.move.line',
            active_ids=moves.invoice_line_ids.ids,
        ).create({
            'action': 'change_period',
            'date': '2018-01-01',
            'percentage': 60,
            'journal_id': self.company_data['default_journal_misc'].id,
            'expense_accrual_account': self.env['account.account'].create({
                'name': 'Accrual Expense Account',
                'code': '234567',
                'account_type': 'expense',
                'reconcile': True,
            }).id,
            'revenue_accrual_account': self.env['account.account'].create({
                'name': 'Accrual Revenue Account',
                'code': '765432',
                'account_type': 'expense',
                'reconcile': True,
            }).id,
        })
        wizard_res = wizard.do_action()

        for date, move, ref in zip(dates, moves, ['INV/2017/00001', 'INV/2017/00002', 'INV/2017/00003']):
            self.assertInvoiceValues(move, [
                {
                    **self.product_line_vals_1,
                    'currency_id': self.other_currency.id,
                    'amount_currency': -1000.0,
                    'debit': 0.0,
                    'credit': 500.0,
                },
                {
                    **self.product_line_vals_2,
                    'currency_id': self.other_currency.id,
                    'amount_currency': -200.0,
                    'debit': 0.0,
                    'credit': 100.0,
                },
                {
                    **self.tax_line_vals_1,
                    'currency_id': self.other_currency.id,
                    'amount_currency': -180.0,
                    'debit': 0.0,
                    'credit': 90.0,
                },
                {
                    **self.tax_line_vals_2,
                    'currency_id': self.other_currency.id,
                    'amount_currency': -30.0,
                    'debit': 0.0,
                    'credit': 15.0,
                },
                {
                    **self.term_line_vals_1,
                    'currency_id': self.other_currency.id,
                    'name': ref,
                    'amount_currency': 1410.0,
                    'debit': 705.0,
                    'credit': 0.0,
                    'date_maturity': fields.Date.from_string(date),
                },
            ], {
                **self.move_vals,
                'currency_id': self.other_currency.id,
                'date': fields.Date.from_string(date),
                'payment_reference': ref,
            })

        moves = self.env['account.move'].browse(wizard_res['domain'][0][2])

        accrual_lines = moves.line_ids.sorted('date')
        self.assertRecordValues(accrual_lines, [
            {'amount_currency': 600.0,  'debit': 300.0, 'credit': 0.0,      'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': -600.0, 'debit': 0.0,   'credit': 300.0,    'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': 120.0,  'debit': 60.0,  'credit': 0.0,      'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': -120.0, 'debit': 0.0,   'credit': 60.0,     'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': 600.0,  'debit': 300.0, 'credit': 0.0,      'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': -600.0, 'debit': 0.0,   'credit': 300.0,    'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': 120.0,  'debit': 60.0,  'credit': 0.0,      'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': -120.0, 'debit': 0.0,   'credit': 60.0,     'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': 600.0,  'debit': 300.0, 'credit': 0.0,      'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': -600.0, 'debit': 0.0,   'credit': 300.0,    'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': 120.0,  'debit': 60.0,  'credit': 0.0,      'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': -120.0, 'debit': 0.0,   'credit': 60.0,     'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},

            {'amount_currency': -600.0, 'debit': 0.0,   'credit': 300.0,    'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': 600.0,  'debit': 300.0, 'credit': 0.0,      'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': -120.0, 'debit': 0.0,   'credit': 60.0,     'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': 120.0,  'debit': 60.0,  'credit': 0.0,      'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': -600.0, 'debit': 0.0,   'credit': 300.0,    'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': 600.0,  'debit': 300.0, 'credit': 0.0,      'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
            {'amount_currency': -120.0, 'debit': 0.0,   'credit': 60.0,     'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': 120.0,  'debit': 60.0,  'credit': 0.0,      'account_id': wizard.revenue_accrual_account.id,        'reconciled': True},
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
                    'nb_days': 0,
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
            'currency_id': self.other_currency.id,
            'company_id': self.company_data['company'].id,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
            'invoice_line_ids': [
                Command.create({'name': 'line1', 'price_unit': 38.73553, 'quantity': 38.0, 'tax_ids': []}),
                Command.create({'name': 'line2', 'price_unit': 4083.19000, 'quantity': 222.0, 'tax_ids': []}),
                Command.create({'name': 'line3', 'price_unit': 49.45257, 'quantity': 35.0, 'tax_ids': []}),
                Command.create({'name': 'line4', 'price_unit': 17.99000, 'quantity': 1.0, 'tax_ids': []}),
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
                'tax_ids': [],
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
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [
                (0, None, {
                    'product_id': self.product_a.id,
                    'product_uom_id': self.product_a.uom_id.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [(6, 0, self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                }),
            ]
        })

        copy_invoice = invoice.copy(default={
            'invoice_date_due': '2018-01-01',
            'invoice_payment_term_id': False,
        })
        self.assertRecordValues(copy_invoice, [
            {'invoice_date_due': fields.Date.from_string('2018-01-01')},
        ])
        self.assertRecordValues(copy_invoice.line_ids.filtered('date_maturity'), [
            {'date_maturity': fields.Date.from_string('2018-01-01')},
        ])

    def test_out_invoice_note_and_tax_partner_is_set(self):
        # Make sure that, when creating an invoice by giving a list of lines with the last one being a note,
        # the partner_id of the tax line is properly set.
        invoice_vals_list = [{
            'move_type': 'out_invoice',
            'currency_id': self.other_currency.id,
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'My super product.',
                    'quantity': 1.0,
                    'price_unit': 750.0,
                    'tax_ids': [(6, 0, self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                }),
                (0, 0, {
                    'display_type': 'line_note',
                    'name': 'This is a note',
                    'account_id': False,
                }),
            ],
        }]
        moves = self.env['account.move'].create(invoice_vals_list)
        tax_line = moves.line_ids.filtered('tax_line_id')
        self.assertEqual(tax_line.partner_id.id, self.partner_a.id)

    def test_out_invoice_reverse_caba(self):
        tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'account_type': 'liability_current',
            'reconcile': True,
        })
        tax_final_account = self.env['account.account'].create({
            'name': 'TAX_TO_DEDUCT',
            'code': 'TDEDUCT',
            'account_type': 'asset_current',
        })
        tax_base_amount_account = self.env['account.account'].create({
            'name': 'TAX_BASE',
            'code': 'TBASE',
            'account_type': 'asset_current',
        })
        self.env.company.account_cash_basis_base_account_id = tax_base_amount_account
        self.env.company.tax_exigibility = True
        tax_tags = defaultdict(dict)
        for line_type, repartition_type in [(l, r) for l in ('invoice', 'refund') for r in ('base', 'tax')]:
            tax_tags[line_type][repartition_type] = self.env['account.account.tag'].create({
                'name': '%s %s tag' % (line_type, repartition_type),
                'applicability': 'taxes',
                'country_id': self.env.ref('base.us').id,
            })
        tax = self.env['account.tax'].create({
            'name': 'cash basis 10%',
            'type_tax_use': 'sale',
            'amount': 10,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': tax_waiting_account.id,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tax_tags['invoice']['base'].ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_final_account.id,
                    'tag_ids': [(6, 0, tax_tags['invoice']['tax'].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'tag_ids': [(6, 0, tax_tags['refund']['base'].ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_final_account.id,
                    'tag_ids': [(6, 0, tax_tags['refund']['tax'].ids)],
                }),
            ],
        })
        # create invoice
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(tax)
        invoice = move_form.save()
        invoice.action_post()
        # make payment
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()
        # check caba move
        partial_rec = invoice.mapped('line_ids.matched_credit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])
        expected_values = [
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': tax_base_amount_account.id,
                'debit': 1000.0,
                'credit': 0.0,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': tax.ids,
                'tax_tag_ids': tax_tags['invoice']['base'].ids,
                'account_id': tax_base_amount_account.id,
                'debit': 0.0,
                'credit': 1000.0,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': tax_waiting_account.id,
                'debit': 100.0,
                'credit': 0.0,
            },
            {
                'tax_line_id': tax.id,
                'tax_repartition_line_id': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                'tax_ids': [],
                'tax_tag_ids': tax_tags['invoice']['tax'].ids,
                'account_id': tax_final_account.id,
                'debit': 0.0,
                'credit': 100.0,
            },
        ]
        self.assertRecordValues(caba_move.line_ids, expected_values)
        # unreconcile
        debit_aml = invoice.line_ids.filtered('debit')
        debit_aml.remove_move_reconcile()
        # check caba move reverse is same as caba move with only debit/credit inverted
        reversed_caba_move = self.env['account.move'].search([('reversed_entry_id', '=', caba_move.id)])
        for value in expected_values:
            value.update({
                'debit': value['credit'],
                'credit': value['debit'],
            })
        self.assertRecordValues(reversed_caba_move.line_ids, expected_values)

    def test_out_invoice_with_down_payment_caba(self):
        tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'account_type': 'liability_current',
            'reconcile': True,
        })
        tax_final_account = self.env['account.account'].create({
            'name': 'TAX_TO_DEDUCT',
            'code': 'TDEDUCT',
            'account_type': 'asset_current',
        })
        default_income_account = self.company_data['default_account_revenue']
        not_default_income_account = self.env['account.account'].create({
            'name': 'NOT_DEFAULT_INCOME',
            'code': 'NDI',
            'account_type': 'income',
        })
        self.env.company.tax_exigibility = True
        tax_tags = defaultdict(dict)
        for line_type, repartition_type in [(l, r) for l in ('invoice', 'refund') for r in ('base', 'tax')]:
            tax_tags[line_type][repartition_type] = self.env['account.account.tag'].create({
                'name': '%s %s tag' % (line_type, repartition_type),
                'applicability': 'taxes',
                'country_id': self.env.ref('base.us').id,
            })
        tax = self.env['account.tax'].create({
            'name': 'cash basis 10%',
            'type_tax_use': 'sale',
            'amount': 10,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': tax_waiting_account.id,
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(tax_tags['invoice']['base'].ids)],
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'account_id': tax_final_account.id,
                    'tag_ids': [Command.set(tax_tags['invoice']['tax'].ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(tax_tags['refund']['base'].ids)],
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'account_id': tax_final_account.id,
                    'tag_ids': [Command.set(tax_tags['refund']['tax'].ids)],
                }),
            ],
        })
        # create invoice
        # one downpayment on default account and one product line on not default account, both with the caba tax
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2017-01-01'),
            'invoice_line_ids': [
                Command.create({
                    'account_id': not_default_income_account.id,
                    'product_id': self.product_a.id,
                    'tax_ids': [Command.set(tax.ids)],
                }),
                Command.create({
                    'name': 'Down payment',
                    'price_unit': 300,
                    'quantity': -1,
                    'tax_ids': [Command.set(tax.ids)],
                }),
            ]
        })
        invoice.action_post()
        # make payment
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_date': invoice.date,
        })._create_payments()
        # check caba move
        partial_rec = invoice.mapped('line_ids.matched_credit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])
        # all amls with tax_tag should all have tax_tag_invert at True since the caba move comes from an invoice
        expected_values = [
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': not_default_income_account.id,
                'debit': 1000.0,
                'credit': 0.0,
                'tax_tag_invert': False,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': tax.ids,
                'tax_tag_ids': tax_tags['invoice']['base'].ids,
                'account_id': not_default_income_account.id,
                'debit': 0.0,
                'credit': 1000.0,
                'tax_tag_invert': True,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': default_income_account.id,
                'debit': 0.0,
                'credit': 300.0,
                'tax_tag_invert': False,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': tax.ids,
                'tax_tag_ids': tax_tags['invoice']['base'].ids,
                'account_id': default_income_account.id,
                'debit': 300.0,
                'credit': 0.0,
                'tax_tag_invert': True,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': tax_waiting_account.id,
                'debit': 70.0,
                'credit': 0.0,
                'tax_tag_invert': False,
            },
            {
                'tax_line_id': tax.id,
                'tax_repartition_line_id': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                'tax_ids': [],
                'tax_tag_ids': tax_tags['invoice']['tax'].ids,
                'account_id': tax_final_account.id,
                'debit': 0.0,
                'credit': 70.0,
                'tax_tag_invert': True,
            },
        ]
        self.assertRecordValues(caba_move.line_ids, expected_values)

    def test_tax_grid_remove_tax(self):
        # Add a tag to tax_sale_a
        tax_line_tag = self.env['account.account.tag'].create({
            'name': "Tax tag",
            'applicability': 'taxes',
            'country_id': self.company_data['company'].country_id.id,
        })

        repartition_line = self.tax_sale_a.invoice_repartition_line_ids\
            .filtered(lambda x: x.repartition_type == 'tax')
        repartition_line.tag_ids |= tax_line_tag

        # Create the invoice
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.from_string('2022-02-20'),
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 999.99,
                    'tax_ids': [Command.set(self.product_a.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                }),
            ],
        })

        with Form(invoice) as form:
            with form.invoice_line_ids.edit(0) as line_form:
                line_form.tax_ids.clear()

        # Tags should be empty since the tax has been removed from the invoice line
        self.assertRecordValues(invoice.line_ids, [{'tax_tag_ids': []}, {'tax_tag_ids': []}])

    def test_quick_edit_total_amount(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.invoice_date = fields.Date.from_string('2022-01-01')
        move_form.partner_id = self.partner_a

        # Quick edit total amount not activated yet
        # As quick edit total is not yet activated, it's invisible by default in the view
        move_form._view['modifiers']['quick_edit_total_amount']['invisible'] = 'False'
        move_form.quick_edit_total_amount = 100.0
        invoice = move_form.save()
        self.assertEqual(invoice.amount_total, 0.0)
        self.assertEqual(len(invoice.invoice_line_ids), 0)

        # Quick edit total amount activated
        self.env.company.quick_edit_mode = "out_and_in_invoices"
        self.env.company.account_sale_tax_id = self.env['account.tax'].create({
            'name': '21%',
            'amount': 21,
            'type_tax_use': 'sale',
        })  # 21% tax of a total amount may create a rounding error (99.99 or 100.01)

        # Let's make sure it does not (the rounding cent should be on the tax)
        with Form(invoice) as move_form:
            move_form.quick_edit_total_amount = 100.0
        self.assertEqual(invoice.amount_total, 100)
        self.assertEqual(invoice.amount_untaxed, 82.64)
        self.assertEqual(invoice.amount_tax, 17.36)
        self.assertEqual(len(invoice.invoice_line_ids), 1)

        # Modify one invoice line
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 50
        self.assertEqual(invoice.amount_total, 60.5)
        self.assertEqual(invoice.amount_untaxed, 50)
        self.assertEqual(invoice.amount_tax, 10.5)
        self.assertEqual(len(invoice.invoice_line_ids), 1)

        # Suggest the new amount such that the total is equal to the quick amount
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                self.assertEqual(line_form.price_unit, 32.64)
        self.assertEqual(invoice.amount_total, 100)
        self.assertEqual(invoice.amount_untaxed, 82.64)
        self.assertEqual(invoice.amount_tax, 17.36)
        self.assertEqual(len(invoice.invoice_line_ids), 2)

    def test_quick_edit_total_amount_with_mixed_epd(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.invoice_date = fields.Date.from_string('2022-01-01')

        # Quick edit total amount activated
        self.env.company.quick_edit_mode = "out_and_in_invoices"
        # 21% sale tax
        self.env.company.account_sale_tax_id = self.env['account.tax'].create({
            'name': '21%',
            'amount': 21,
            'type_tax_use': 'sale',
        })
        # Create a payment term with early payment discount of 2%  and computation set to mixed (Always (upon invoice))
        epd_payment_term = self.env['account.payment.term'].create({
            'name': "2/7 Term",
            'discount_days': 7,
            'discount_percentage': 2,
            'early_discount': True,
            'early_pay_discount_computation': 'mixed',
        })
        # Set the payment term to the one we just created
        move_form.invoice_payment_term_id = epd_payment_term

        invoice = move_form.save()

        # Invoice of one item of price 100, discount 2% and tax 21%:
        # 21% tax = 100 * (1 - 0.2) * 0.21 = 20.58
        # total_amount = 100 + 20.58 = 120.58

        # Make sure the quick edit added one line with the correct values
        with Form(invoice) as move_form:
            move_form.quick_edit_total_amount = 120.58
        self.assertRecordValues(invoice, [{'amount_total': 120.58, 'amount_untaxed': 100, 'amount_tax': 20.58}])
        self.assertEqual(len(invoice.invoice_line_ids), 1)

        # Modify one invoice line
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 70
        self.assertRecordValues(invoice, [{'amount_total': 84.41, 'amount_untaxed': 70, 'amount_tax': 14.41}])
        self.assertEqual(len(invoice.invoice_line_ids), 1)

        # Suggest the new amount such that the total is equal to the quick amount
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.new() as line_form:
                self.assertEqual(line_form.price_unit, 30)
        self.assertRecordValues(invoice, [{'amount_total': 120.58, 'amount_untaxed': 100, 'amount_tax': 20.58}])
        self.assertEqual(len(invoice.invoice_line_ids), 2)

    def test_out_invoice_depreciated_account(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'currency_id': self.other_currency.id,
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'My super product.',
                    'quantity': 1.0,
                    'price_unit': 750.0,
                    'account_id': self.product_a.property_account_income_id.id,
                })
            ],
        })
        self.product_a.property_account_income_id.deprecated = True
        with self.assertRaises(UserError), self.cr.savepoint():
            move.action_post()

    def test_change_currency_id(self):
        """
        Test that we are able to change currency on invoice,
        even when a default currency is set on journal
        """
        self.company_data['default_journal_sale'].currency_id = self.company_data['currency']
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'My super product.',
                    'quantity': 1.0,
                    'price_unit': 750.0,
                    'account_id': self.product_a.property_account_income_id.id,
                    'tax_ids': False,
                })
            ],
        })

        self.assertEqual(move.currency_id, self.company_data['currency'])
        move.currency_id = self.other_currency
        self.assertEqual(move.currency_id, self.other_currency)
        self.assertRecordValues(move.line_ids, [
            {
                'display_type': 'product',
                'currency_id': self.other_currency.id,
                'debit': 0.0,
                'credit': 375.0,
            },
            {
                'display_type': 'payment_term',
                'currency_id': self.other_currency.id,
                'debit': 375.0,
                'credit': 0.0,
            },
        ])

        move.currency_id = self.company_data['currency']
        with Form(move) as move_form:
            move_form.currency_id = self.other_currency
        self.assertEqual(move.currency_id, self.other_currency)
        self.assertEqual(move.line_ids.currency_id, self.other_currency)

        with Form(self.env['account.move'].with_context(default_move_type='out_invoice')) as move_form:
            move_form.journal_id = self.company_data['default_journal_sale']
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_a
                line_form.tax_ids.clear()
            move_form.currency_id = self.other_currency
            self.assertEqual(move_form.currency_id, self.other_currency)
        move = move_form.save()
        self.assertEqual(move.currency_id, self.other_currency)
        self.assertEqual(move.line_ids.currency_id, self.other_currency)

    def test_change_journal_currency(self):
        second_journal = self.company_data['default_journal_sale'].copy({
            'currency_id': self.other_currency.id,
        })
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'My super product.',
                    'quantity': 1.0,
                    'price_unit': 750.0,
                    'account_id': self.product_a.property_account_income_id.id,
                    'tax_ids': False,
                })
            ],
        })

        self.assertEqual(move.currency_id, self.company_data['currency'])
        move.journal_id = second_journal
        self.assertEqual(move.currency_id, self.other_currency)

    @freeze_time('2019-01-01')
    def test_date_reversal_exchange_move(self):
        """
        Test the date of the reversal of an exchange move created when unreconciling a payment made in the past, when no lock date is set.
        It should be the last day of the month of the exchange move date if sequence is incremented by month,
        and the last day of the year of the exchange move date if sequence is incremented by year.
        """
        for format_incrementor, expected_date in (('month', '2017-01-31'), ('year', '2017-12-31')):
            with self.subTest(format_incrementor=format_incrementor, expected_date=expected_date):
                invoice = self.init_invoice(move_type='out_invoice', partner=self.partner_a, invoice_date='2016-01-20', post=True, amounts=[750.0], currency=self.other_currency)

                new_exchange_journal = self.env['account.journal'].create({
                    'name': f'Exchange Journal for {invoice.name}',
                    'code': f'EXCH{invoice.sequence_number}',
                    'type': 'general',
                    'company_id': self.env.company.id,
                })

                # Need a first move in the new journal to initiate the sequence with a right incrementor, depending on the wanted format
                self.env['account.move'].create({
                    'journal_id': new_exchange_journal.id,
                    'name': 'EXCH/2019/00001' if format_incrementor == 'year' else 'EXCH/2019/01/0001',
                    'line_ids': [
                        (0, 0, {
                            'account_id': self.company_data['default_account_receivable'].id,
                            'debit': 125.0,
                            'credit': 0.0,
                        }),
                        (0, 0, {
                            'account_id': self.company_data['default_account_revenue'].id,
                            'debit': 0.0,
                            'credit': 125.0,
                        })
                    ]
                })

                self.env.company.currency_exchange_journal_id = new_exchange_journal

                self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
                    'payment_date': '2017-01-20',
                })._create_payments()

                line_receivable = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')

                exchange_move = line_receivable.full_reconcile_id.partial_reconcile_ids.exchange_move_id

                # Date of the exchange move should be the end of the month/year of the payment
                self.assertEqual(exchange_move.date, fields.Date.to_date(expected_date))

                line_receivable.remove_move_reconcile()

                exchange_move_reversal = exchange_move.reversal_move_ids

                # Date of the reversal of the exchange move should be the last day of the month/year of the payment depending on the sequence format
                self.assertEqual(exchange_move_reversal.date, fields.Date.to_date(expected_date))

    @freeze_time('2023-01-01')
    def test_change_first_journal_move_sequence(self):
        """Invoice name should not be reset when posting the invoice"""
        new_sale_journal = self.company_data['default_journal_sale'].copy()
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'journal_id': new_sale_journal.id,
            'partner_id': self.partner_a.id,
            'name': 'INV1/2023/00010',
            'invoice_line_ids': [
                Command.create({
                    'name': 'My super product.',
                    'quantity': 1.0,
                    'price_unit': 750.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                })
            ]
        })
        invoice.action_post()
        self.assertEqual(invoice.name, 'INV1/2023/00010')

    def test_invoice_mass_posting(self):
        """
        With some particular setup (in this case, rounding issue), partner get mixed up in the
        invoice lines after mass posting.
        """
        currency = self.company_data['currency']
        currency.rounding = 0.0001
        invoice1 = self.init_invoice(move_type='out_invoice', partner=self.partner_a, invoice_date='2016-01-20', products=self.product_a)
        invoice1.invoice_line_ids.price_unit = 12.36
        invoice2 = self.init_invoice(move_type='out_invoice', partner=self.partner_b, invoice_date='2016-01-20', products=self.product_a)

        self.env["validate.account.move"].create({
            "force_post": True,
            "move_ids": [Command.set((invoice1 + invoice2).ids)]
        }).validate_move()

        for aml in invoice1.line_ids:
            self.assertEqual(aml.partner_id, self.partner_a)
        for aml in invoice2.line_ids:
            self.assertEqual(aml.partner_id, self.partner_b)

    @freeze_time('2023-01-01')
    def test_post_valid_invoices_when_auto_post(self):
        valid_invoice = self.init_invoice(move_type='out_invoice', products=self.product_a, invoice_date='2023-01-01')

        # missing partner
        invalid_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-01-01',
            'date': '2023-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 10,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })

        # missing invoice lines
        invalid_invoice_2 = self.init_invoice(move_type='out_invoice', invoice_date='2023-01-01')

        (valid_invoice + invalid_invoice_1 + invalid_invoice_2).auto_post = 'at_date'

        self.env['account.move']._autopost_draft_entries()
        self.assertEqual(valid_invoice.state, 'posted')
        self.assertEqual(invalid_invoice_1.state, 'draft')

        self.assertTrue(any(
            message.body == "<p>The move could not be posted for the following reason: The field 'Customer' is required, please complete it to validate the Customer Invoice.</p>"
            for message in invalid_invoice_1.message_ids))

        self.assertEqual(invalid_invoice_2.state, 'draft')
        self.assertTrue(any(
            message.body == "<p>The move could not be posted for the following reason: You need to add a line before posting.</p>"
            for message in invalid_invoice_2.message_ids))

    def test_no_taxes_on_payment_term_line(self):
        ''' No tax should be set on payment_term lines'''

        receivable_account = self.partner_a.property_account_receivable_id
        receivable_account.tax_ids = [Command.set(self.company_data['default_tax_sale'].ids)]

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'test line',
                    'quantity': 1,
                    'price_unit': 100,
                })
            ],
        })

        self.assertRecordValues(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term'), [
            {'account_id': receivable_account.id, 'tax_ids': []},
        ])

    def test_invoice_journal_account_check_constraints(self):
        """
        Test account-journal constraint check is working as expected in a complex write operation
        Setup:
          - journal_a accepts account_a but not account_b
          - journal_b accepts account_b but not account_a
        We expect that constraints are checked as usual when creating/writing records, and in particular
        changing account and journal at the same time should work
        """

        account_a = self.company_data['default_account_revenue'].copy()
        journal_a = self.company_data['default_journal_sale'].copy({'default_account_id': account_a.id})
        account_b = account_a.copy()
        journal_b = journal_a.copy({'default_account_id': account_b.id})
        journal_a.account_control_ids = account_a | self.company_data['default_account_tax_sale'] | self.company_data['default_account_receivable']
        journal_b.account_control_ids = account_b | self.company_data['default_account_tax_sale'] | self.company_data['default_account_receivable']

        # Should not raise
        invoice = self.env['account.move'].with_context(default_move_type='out_invoice').create({
            'journal_id': journal_a.id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'My super product.',
                    'quantity': 1.0,
                    'price_unit': 750.0,
                    'account_id': account_a.id,
                })
            ]
        })

        # Should not raise
        invoice.write({'journal_id': journal_b.id, 'invoice_line_ids': [Command.update(invoice.invoice_line_ids.id, {'account_id': account_b.id})]})

        with self.assertRaises(UserError), self.cr.savepoint():
            invoice.write({'journal_id': journal_a.id})
        with self.assertRaises(UserError), self.cr.savepoint():
            # we want to test the update of both records in the same write operation
            invoice.write({'invoice_line_ids': [Command.update(invoice.invoice_line_ids.id, {'account_id': account_a.id})]})

    def test_discount_allocation_account_on_invoice(self):
        # Ensure two aml of display_type 'discount' are correctly created when setting an account for discounts in the settings
        discount_account = self.company_data['default_account_expense'].copy()
        self.company_data['company'].account_discount_expense_allocation_id = discount_account

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'discount': 5,
                })
            ],
        })
        product_line_account = invoice.line_ids.filtered(lambda x: x.product_id).account_id
        self.assertRecordValues(invoice.line_ids.filtered(lambda l: l.display_type == 'discount'), [
            {
                'account_id': product_line_account.id,
                'tax_ids': [],
                'amount_currency': -50.0,
                'debit': 0.0,
                'credit': 50.0,
            },
            {
                'account_id': discount_account.id,
                'tax_ids': [],
                'amount_currency': 50.0,
                'debit': 50.0,
                'credit': 0.0,
            },
        ])

    def test_keep_receivable(self):
        """Duplicating an invoice with a different receivable account should keep the account."""
        receivable_account = self.partner_a.property_account_receivable_id
        other_receivable_account = receivable_account.copy()

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'test line',
                    'quantity': 1,
                    'price_unit': 100,
                })
            ],
        })

        invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').account_id = other_receivable_account
        duplicate_invoice = invoice.copy()

        self.assertEqual(
            duplicate_invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').account_id,
            other_receivable_account
        )

    def test_account_on_invoice_line_product_removal(self):
        """Removing a product from an invoice line should preserve that line's account."""
        other_income_account = self.product_a.property_account_income_id.copy()

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                }),
            ]
        })
        invoice.invoice_line_ids.account_id = other_income_account
        invoice.invoice_line_ids.product_id = False

        self.assertEqual(
            invoice.invoice_line_ids.account_id,
            other_income_account,
            "Removing a product from an invoice line should no change the account."
        )

    def test_compute_name_payment_reference(self):
        """
        Test that the label of the payment_term line is consistent with the payment reference
        Also tests that it won't affect the hash inalterability report
        """
        self.company_data['default_journal_sale'].restrict_mode_hash_table = True

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_b
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        invoice = move_form.save()
        payment_term_lines = invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')

        self.assertRecordValues(payment_term_lines, [
            {'name': 'installment #1'},
            {'name': 'installment #2'},
        ])

        move_form.save()

        self.assertRecordValues(payment_term_lines, [
            {'name': 'installment #1'},
            {'name': 'installment #2'},
        ])

        invoice = move_form.save()

        self.assertRecordValues(payment_term_lines, [
            {'name': 'installment #1'},
            {'name': 'installment #2'},
        ])

        invoice.action_post()
        invoice._generate_and_send(allow_fallback_pdf=False)
        move_form.save()

        # The integrity check should work
        integrity_check = invoice.company_id._check_hash_integrity()['results'][0]
        self.assertEqual(integrity_check['msg_cover'], 'Entries are correctly hashed')

    def test_out_invoice_create_cross_branch_refund(self):
        """You should not be able to reverse moves from different branches."""

        # create a new branch
        self.env.company.write({
            'child_ids': [
                Command.create({'name': 'Branch A'}),
            ],
        })
        self.cr.precommit.run()  # load the CoA

        # create an invoice on the new branch
        branch_a = self.env.company.child_ids
        branch_invoice = self.init_invoice('out_invoice', products=self.product_a, company=branch_a)

        branch_invoice.action_post()
        self.invoice.action_post()

        with self.assertRaises(UserError) as error_catcher:
            # attempt to reverse both the parent's and the branch's move at once
            move_reversal = self.env['account.move.reversal'].with_context(
                active_model="account.move",
                active_ids=(branch_invoice + self.invoice).ids,
            ).create({})

            move_reversal.refund_moves()

        self.assertEqual(error_catcher.exception.args[0], "All selected moves for reversal must belong to the same company.")

    def test_update_lines_date_when_invoice_date_changes(self):
        move = self.init_invoice(
            move_type='in_invoice',
            partner=self.partner_a,
            amounts=[1000.0],
        )

        move.invoice_date = fields.Date.from_string('2024-01-01')
        self.env.flush_all()

        for line in move.line_ids:
            self.assertEqual(line.date, move.date)

    def test_invoice_copy_data(self):
        """User should be able to duplicate invoices with different journals"""

        new_sale_journal = self.company_data['default_journal_sale'].copy()

        invoice_1, invoice_2 = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': self.company_data['default_journal_sale'].id,
        }, {
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': new_sale_journal.id,
        }])

        invoices_duplicate = (invoice_1 + invoice_2).copy_data()

        self.assertEqual(invoice_1.journal_id.id, invoices_duplicate[0]['journal_id'])
        self.assertEqual(invoice_2.journal_id.id, invoices_duplicate[1]['journal_id'])

    def test_on_quick_encoding_non_accounting_lines(self):
        """ Ensure that quick encoding values are only applied to accounting lines) """

        self.env.company.quick_edit_mode = "out_and_in_invoices"
        move_form = Form(
            self.env['account.move'].with_context(default_move_type='out_invoice')
        )
        move_form.quick_edit_total_amount = 100.0
        with move_form.invoice_line_ids.new() as invoice_line_form:
            invoice_line_form.display_type = 'line_section'
        move_form.save()

    def test_out_invoice_line_product_taxes_on_branch(self):
        """ Check taxes populated on invoice lines from product on branch company.
            Taxes from the branch company should be taken with a fallback on parent company.
        """
        # create the following branch hierarchy:
        #     Parent company
        #         |----> Branch X
        #                   |----> Branch XX
        company = self.env.company
        branch_x = self.env['res.company'].create({
            'name': 'Branch X',
            'country_id': company.country_id.id,
            'parent_id': company.id,
        })
        branch_xx = self.env['res.company'].create({
            'name': 'Branch XX',
            'country_id': company.country_id.id,
            'parent_id': branch_x.id,
        })
        self.cr.precommit.run()  # load the CoA
        # create taxes for the parent company and its branches
        tax_groups = self.env['account.tax.group'].create([{
            'name': 'Tax Group',
            'company_id': company.id,
        }, {
            'name': 'Tax Group X',
            'company_id': branch_x.id,
        }, {
            'name': 'Tax Group XX',
            'company_id': branch_xx.id,
        }])
        tax_a = self.env['account.tax'].create({
            'name': 'Tax A',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'Tax B',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_x = self.env['account.tax'].create({
            'name': 'Tax X',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 20,
            'tax_group_id': tax_groups[1].id,
            'company_id': branch_x.id,
        })
        tax_xx = self.env['account.tax'].create({
            'name': 'Tax XX',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 25,
            'tax_group_id': tax_groups[2].id,
            'company_id': branch_xx.id,
        })
        # create several products with different taxes combination
        product_all_taxes = self.env['product.product'].create({
            'name': 'Product all taxes',
            'taxes_id': [Command.set((tax_a + tax_b + tax_x + tax_xx).ids)],
        })
        product_no_xx_tax = self.env['product.product'].create({
            'name': 'Product no tax from XX',
            'taxes_id': [Command.set((tax_a + tax_b + tax_x).ids)],
        })
        product_no_branch_tax = self.env['product.product'].create({
            'name': 'Product no tax from branch',
            'taxes_id': [Command.set((tax_a + tax_b).ids)],
        })
        product_no_tax = self.env['product.product'].create({
            'name': 'Product no tax',
            'taxes_id': [],
        })
        # create an invoice from Branch XX with the different products:
        # - Product all taxes           => tax from Branch XX should be set
        # - Product no tax from XX      => tax from Branch X should be set
        # - Product no tax from branch  => 2 taxes from parent company should be set
        # - Product no tax              => no tax should be set
        invoice = self.init_invoice(
            'out_invoice',
            products=product_all_taxes + product_no_xx_tax + product_no_branch_tax + product_no_tax,
            company=branch_xx
        )
        self.assertRecordValues(invoice.invoice_line_ids, [
            {'product_id': product_all_taxes.id, 'tax_ids': tax_xx.ids},
            {'product_id': product_no_xx_tax.id, 'tax_ids': tax_x.ids},
            {'product_id': product_no_branch_tax.id, 'tax_ids': (tax_a + tax_b).ids},
            {'product_id': product_no_tax.id, 'tax_ids': []},
        ])

    def test_discount_allocation_account_on_invoice_currency_change(self):
        # Ensure aml of 'discount' display_type is correctly recomputed when changing the currency
        discount_account = self.company_data['default_account_expense'].copy()
        self.company_data['company'].account_discount_expense_allocation_id = discount_account
        self.env['res.currency.rate'].create({
            'name': '2024-01-01',
            'rate': 0.20,
            'currency_id': self.other_currency.id,
            'company_id': self.company_data['company'].id,
        })
        # create an invoice in a foreign currency and a 5% discount
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'quantity': 1,
                    'discount': 5,
                })
            ],
        })
        product_line_account = invoice.line_ids.filtered(lambda x: x.product_id).account_id
        self.assertRecordValues(invoice.line_ids.filtered(lambda l: l.display_type == 'discount'), [
            {
                'account_id': product_line_account.id,
                'tax_ids': [],
                'amount_currency': -50.0,
                'debit': 0.0,
                'credit': 250.0,
            },
            {
                'account_id': discount_account.id,
                'tax_ids': [],
                'amount_currency': 50.0,
                'debit': 250.0,
                'credit': 0.0,
            },
        ])
        move_form = Form(invoice)
        # change the currency of the invoice to the currency of the company
        invoice.currency_id = self.company_data['currency'].id
        move_form.save()
        self.assertRecordValues(invoice.line_ids.filtered(lambda l: l.display_type == 'discount'), [
            {
                'account_id': product_line_account.id,
                'tax_ids': [],
                'amount_currency': -50.0,    # amount_currency should not change
                'debit': 0.0,
                'credit': 50.0,
            },
            {
                'account_id': discount_account.id,
                'tax_ids': [],
                'amount_currency': 50.0,    # amount_currency should not change
                'debit': 50.0,
                'credit': 0.0,
            },
        ])

    def test_invoice_with_empty_currency(self):

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'invoice_line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        })
        move_form = Form(move)
        move_form.currency_id = self.env['res.currency']
        self.assertTrue(move.currency_id)
