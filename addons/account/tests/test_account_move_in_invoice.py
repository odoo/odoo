# -*- coding: utf-8 -*-
# pylint: disable=bad-whitespace
from freezegun import freeze_time
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields, Command
from odoo.osv import expression
from odoo.exceptions import ValidationError
from datetime import date

from collections import defaultdict

@tagged('post_install', '-at_install')
class TestAccountMoveInInvoiceOnchanges(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.init_invoice('in_invoice', products=cls.product_a+cls.product_b)

        cls.product_line_vals_1 = {
            'name': cls.product_a.name,
            'product_id': cls.product_a.id,
            'account_id': cls.product_a.property_account_expense_id.id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': cls.product_a.uom_id.id,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 800.0,
            'price_subtotal': 800.0,
            'price_total': 920.0,
            'tax_ids': cls.product_a.supplier_taxes_id.ids,
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': 800.0,
            'debit': 800.0,
            'credit': 0.0,
            'date_maturity': False,
        }
        cls.product_line_vals_2 = {
            'name': cls.product_b.name,
            'product_id': cls.product_b.id,
            'account_id': cls.product_b.property_account_expense_id.id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': cls.product_b.uom_id.id,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 160.0,
            'price_subtotal': 160.0,
            'price_total': 208.0,
            'tax_ids': cls.product_b.supplier_taxes_id.ids,
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': 160.0,
            'debit': 160.0,
            'credit': 0.0,
            'date_maturity': False,
        }
        cls.tax_line_vals_1 = {
            'name': cls.tax_purchase_a.name,
            'product_id': False,
            'account_id': cls.company_data['default_account_tax_purchase'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': False,
            'discount': 0.0,
            'price_unit': 0.0,
            'price_subtotal': 0.0,
            'price_total': 0.0,
            'tax_ids': [],
            'tax_line_id': cls.tax_purchase_a.id,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': 144.0,
            'debit': 144.0,
            'credit': 0.0,
            'date_maturity': False,
        }
        cls.tax_line_vals_2 = {
            'name': cls.tax_purchase_b.name,
            'product_id': False,
            'account_id': cls.company_data['default_account_tax_purchase'].id,
            'partner_id': cls.partner_a.id,
            'product_uom_id': False,
            'quantity': False,
            'discount': 0.0,
            'price_unit': 0.0,
            'price_subtotal': 0.0,
            'price_total': 0.0,
            'tax_ids': [],
            'tax_line_id': cls.tax_purchase_b.id,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': 24.0,
            'debit': 24.0,
            'credit': 0.0,
            'date_maturity': False,
        }
        cls.term_line_vals_1 = {
            'name': '',
            'product_id': False,
            'account_id': cls.company_data['default_account_payable'].id,
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
            'amount_currency': -1128.0,
            'debit': 0.0,
            'credit': 1128.0,
            'date_maturity': fields.Date.from_string('2019-01-01'),
        }
        cls.move_vals = {
            'partner_id': cls.partner_a.id,
            'currency_id': cls.company_data['currency'].id,
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'date': fields.Date.from_string('2019-01-01'),
            'fiscal_position_id': False,
            'payment_reference': '',
            'invoice_payment_term_id': cls.pay_terms_a.id,
            'amount_untaxed': 960.0,
            'amount_tax': 168.0,
            'amount_total': 1128.0,
        }
        cls.env.user.groups_id += cls.env.ref('uom.group_uom')
        (cls.tax_armageddon + cls.tax_armageddon.children_tax_ids).write({'type_tax_use': 'purchase'})

    def setUp(self):
        super(TestAccountMoveInInvoiceOnchanges, self).setUp()
        self.assertInvoiceValues(self.invoice, [
            self.product_line_vals_1,
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            self.term_line_vals_1,
        ], self.move_vals)

    def test_in_invoice_onchange_invoice_date(self):
        for tax_date, invoice_date, accounting_date in [
            ('2019-03-31', '2019-05-12', '2019-05-31'),
            ('2019-03-31', '2019-02-10', '2019-04-30'),
            ('2019-05-31', '2019-06-15', '2019-06-30'),
        ]:
            self.invoice.company_id.tax_lock_date = tax_date
            with Form(self.invoice) as move_form:
                move_form.invoice_date = invoice_date
            self.assertEqual(self.invoice.date, fields.Date.to_date(accounting_date))

    @freeze_time('2021-09-16')
    def test_in_invoice_onchange_invoice_date_2(self):
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.partner_id = self.partner_a
        invoice_form.invoice_payment_term_id = self.env.ref('account.account_payment_term_30days')
        with invoice_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        invoice_form.invoice_date = fields.Date.from_string('2021-09-01')
        invoice = invoice_form.save()

        self.assertRecordValues(invoice, [{
            'date': fields.Date.from_string('2021-09-16'),
            'invoice_date': fields.Date.from_string('2021-09-01'),
            'invoice_date_due': fields.Date.from_string('2021-10-01'),
        }])

    def test_in_invoice_line_onchange_product_1(self):
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
                'account_id': self.product_b.property_account_expense_id.id,
                'price_unit': 160.0,
                'price_subtotal': 160.0,
                'price_total': 208.0,
                'tax_ids': self.product_b.supplier_taxes_id.ids,
                'amount_currency': 160.0,
                'debit': 160.0,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'amount_currency': 48.0,
                'debit': 48.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 48.0,
                'debit': 48.0,
            },
            {
                **self.term_line_vals_1,
                'amount_currency': -416.0,
                'credit': 416.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 320.0,
            'amount_tax': 96.0,
            'amount_total': 416.0,
        })

    def test_in_invoice_line_onchange_product_2_with_fiscal_pos(self):
        ''' Test mapping a price-included tax (10%) with a price-excluded tax (20%) on a price_unit of 110.0.
        The price_unit should be 100.0 after applying the fiscal position.
        '''
        tax_price_include = self.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })
        tax_price_exclude = self.env['account.tax'].create({
            'name': '15% excl',
            'type_tax_use': 'purchase',
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
            'standard_price': 110.0,
            'supplier_taxes_id': [(6, 0, tax_price_include.ids)],
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
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
                'amount_currency': 200.0,
                'debit': 100.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_exclude.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 30.0,
                'debit': 15.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -230.0,
                'debit': 0.0,
                'credit': 115.0,
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
                'amount_currency': 2400.0,
                'debit': 1200.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_exclude.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 360.0,
                'debit': 180.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2760.0,
                'debit': 0.0,
                'credit': 1380.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'fiscal_position_id': fiscal_position.id,
            'amount_untaxed': 2400.0,
            'amount_tax': 360.0,
            'amount_total': 2760.0,
        })

    def test_in_invoice_line_onchange_product_2_with_fiscal_pos_2(self):
        ''' Test mapping a price-included tax (10%) with another price-included tax (20%) on a price_unit of 110.0.
        The price_unit should be 120.0 after applying the fiscal position.
        '''
        tax_price_include_1 = self.env['account.tax'].create({
            'name': '10% incl',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
            'price_include': True,
            'include_base_amount': True,
        })
        tax_price_include_2 = self.env['account.tax'].create({
            'name': '20% incl',
            'type_tax_use': 'purchase',
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
            'standard_price': 110.0,
            'supplier_taxes_id': [(6, 0, tax_price_include_1.ids)],
        })

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
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
                'amount_currency': 200.0,
                'debit': 100.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include_2.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 40.0,
                'debit': 20.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -240.0,
                'debit': 0.0,
                'credit': 120.0,
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
                'amount_currency': 2400.0,
                'debit': 1200.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': tax_price_include_2.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 480.0,
                'debit': 240.0,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'product_uom_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2880.0,
                'debit': 0.0,
                'credit': 1440.0,
            },
        ], {
            'currency_id': self.currency_data['currency'].id,
            'fiscal_position_id': fiscal_position.id,
            'amount_untaxed': 2400.0,
            'amount_tax': 480.0,
            'amount_total': 2880.0,
        })

    def test_in_invoice_line_onchange_business_fields_1(self):
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            # Current price_unit is 800.
            # We set quantity = 4, discount = 50%, price_unit = 400. The debit/credit fields don't change because (4 * 400) * 0.5 = 800.
            line_form.quantity = 4
            line_form.discount = 50
            line_form.price_unit = 400
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'quantity': 4,
                'discount': 50.0,
                'price_unit': 400.0,
            },
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            self.term_line_vals_1,
        ], self.move_vals)

        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            # Reset field except the discount that becomes 100%.
            # /!\ The modification is made on the accounting tab.
            line_form.quantity = 1
            line_form.discount = 100
            line_form.price_unit = 800
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'discount': 100.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'amount_currency': 0.0,
                'debit': 0.0,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'amount_currency': 24.0,
                'debit': 24.0,
            },
            self.tax_line_vals_2,
            {
                **self.term_line_vals_1,
                'amount_currency': -208.0,
                'credit': 208.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 160.0,
            'amount_tax': 48.0,
            'amount_total': 208.0,
        })

    def test_in_invoice_line_onchange_partner_1(self):
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
                'name': 'turlututu installment #1',
                'partner_id': self.partner_b.id,
                'account_id': self.partner_b.property_account_payable_id.id,
                'amount_currency': -338.4,
                'credit': 338.4,
            },
            {
                **self.term_line_vals_1,
                'name': 'turlututu installment #2',
                'partner_id': self.partner_b.id,
                'account_id': self.partner_b.property_account_payable_id.id,
                'amount_currency': -789.6,
                'credit': 789.6,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            **self.move_vals,
            'partner_id': self.partner_b.id,
            'payment_reference': 'turlututu',
            'fiscal_position_id': self.fiscal_pos_a.id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'amount_untaxed': 960.0,
            'amount_tax': 168.0,
            'amount_total': 1128.0,
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
                'account_id': self.product_b.property_account_expense_id.id,
                'partner_id': self.partner_b.id,
                'tax_ids': self.tax_purchase_b.ids,
            },
            {
                **self.product_line_vals_2,
                'partner_id': self.partner_b.id,
                'price_total': 184.0,
                'tax_ids': self.tax_purchase_b.ids,
            },
            {
                **self.tax_line_vals_1,
                'name': self.tax_purchase_b.name,
                'partner_id': self.partner_b.id,
                'tax_line_id': self.tax_purchase_b.id,
            },
            {
                **self.term_line_vals_1,
                'name': 'turlututu installment #1',
                'account_id': self.partner_b.property_account_payable_id.id,
                'partner_id': self.partner_b.id,
                'amount_currency': -331.2,
                'credit': 331.2,
            },
            {
                **self.term_line_vals_1,
                'name': 'turlututu installment #2',
                'account_id': self.partner_b.property_account_payable_id.id,
                'partner_id': self.partner_b.id,
                'amount_currency': -772.8,
                'credit': 772.8,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            **self.move_vals,
            'partner_id': self.partner_b.id,
            'payment_reference': 'turlututu',
            'fiscal_position_id': self.fiscal_pos_a.id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'amount_untaxed': 960.0,
            'amount_tax': 144.0,
            'amount_total': 1104.0,
        })

    def test_in_invoice_line_onchange_taxes_1(self):
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 960
            line_form.tax_ids.add(self.tax_armageddon)
        move_form.save()

        child_tax_1 = self.tax_armageddon.children_tax_ids[0]
        child_tax_2 = self.tax_armageddon.children_tax_ids[1]

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 960.0,
                'price_subtotal': 800.0,
                'price_total': 1176.0,
                'tax_ids': (self.tax_purchase_a + self.tax_armageddon).ids,
            },
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
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
                'amount_currency': 64.0,
                'debit': 64.0,
                'credit': 0.0,
                'date_maturity': False,
            },
            {
                'name': child_tax_1.name,
                'product_id': False,
                'account_id': self.company_data['default_account_expense'].id,
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
                'amount_currency': 96.0,
                'debit': 96.0,
                'credit': 0.0,
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
                'amount_currency': 96.0,
                'debit': 96.0,
                'credit': 0.0,
                'date_maturity': False,
            },
            {
                **self.term_line_vals_1,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'amount_currency': -1384.0,
                'credit': 1384.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 960.0,
            'amount_tax': 424.0,
            'amount_total': 1384.0,
        })

    def test_compute_cash_rounding_lines(self):
        cash_rounding_add_invoice_line = self.env['account.cash.rounding'].create({
            'name': 'Add invoice line Rounding Down',
            'rounding': .1,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data['default_account_revenue'].id,
            'loss_account_id': self.company_data['default_account_expense'].id,
            'rounding_method': 'DOWN',
        })
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_cash_rounding_id': cash_rounding_add_invoice_line.id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'line',
                    'price_unit': 295,
                    'tax_ids': [],
                }),
                Command.create({
                    'name': 'cost',
                    'price_unit': 280.33,
                }),
                Command.create({
                    'name': 'cost neg',
                    'price_unit': -280.33,
                }),
            ],
        })
        self.assertFalse(move.line_ids.filtered(lambda line: line.display_type == 'rounding'))

    def test_in_invoice_line_onchange_cash_rounding_1(self):
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
            line_form.price_unit = 799.99
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 799.99,
                'price_subtotal': 799.99,
                'price_total': 919.99,
                'amount_currency': 799.99,
                'debit': 799.99,
            },
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            {
                'name': 'add_invoice_line',
                'product_id': False,
                'account_id': self.cash_rounding_a.loss_account_id.id,
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
                'amount_currency': 0.01,
                'debit': 0.01,
                'credit': 0.0,
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

        repartition_line = self.tax_purchase_a.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax')
        repartition_line.write({'tag_ids': [(4, tax_line_tag.id, 0)]})

        # Create the invoice
        biggest_tax_invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'invoice_cash_rounding_id': self.cash_rounding_b.id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'price_unit': 799.99,
                    'tax_ids': [(6, 0, self.product_a.supplier_taxes_id.ids)],
                    'product_uom_id':  self.product_a.uom_id.id,
                }),

                (0, 0, {
                    'product_id': self.product_b.id,
                    'price_unit': self.product_b.standard_price,
                    'tax_ids': [(6, 0, self.product_b.supplier_taxes_id.ids)],
                    'product_uom_id':  self.product_b.uom_id.id,
                }),
            ],
        })

        self.assertInvoiceValues(biggest_tax_invoice, [
            {
                **self.product_line_vals_1,
                'price_unit': 799.99,
                'price_subtotal': 799.99,
                'price_total': 919.99,
                'amount_currency': 799.99,
                'debit': 799.99,
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
                'tax_repartition_line_id': self.tax_purchase_b.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                'tax_tag_ids': [],
            },
            {
                'name': '%s (rounding)' % self.tax_purchase_a.name,
                'product_id': False,
                'account_id': self.company_data['default_account_tax_purchase'].id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': False,
                'discount': 0.0,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'tax_ids': [],
                'tax_line_id': self.tax_purchase_a.id,
                'tax_repartition_line_id': repartition_line.id,
                'tax_tag_ids': tax_line_tag.ids,
                'currency_id': self.company_data['currency'].id,
                'amount_currency': -0.04,
                'debit': 0.0,
                'credit': 0.04,
                'date_maturity': False,
            },
            {
                **self.term_line_vals_1,
                'amount_currency': -1127.95,
                'credit': 1127.95,
                'tax_repartition_line_id': None,
                'tax_tag_ids': [],
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 959.99,
            'amount_tax': 167.96,
            'amount_total': 1127.95,
        })

    def test_in_invoice_line_onchange_currency_1(self):
        move_form = Form(self.invoice)
        move_form.currency_id = self.currency_data['currency']
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'debit': 400.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 160.0,
                'debit': 80.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 144.0,
                'debit': 72.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.0,
                'debit': 12.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1128.0,
                'credit': 564.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
        })

        # Change the date to get another rate: 1/3 instead of 1/2.
        with Form(self.invoice) as move_form:
            move_form.invoice_date = fields.Date.from_string('2016-01-01')
            move_form.date = fields.Date.from_string('2016-01-01')

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'debit': 266.67,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 160.0,
                'debit': 53.33,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 144.0,
                'debit': 48.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.0,
                'debit': 8.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1128.0,
                'credit': 376.0,
                'date_maturity': fields.Date.from_string('2016-01-01'),
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
                'amount_currency': 0.005,
                'debit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 160.0,
                'debit': 53.33,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.001,
                'debit': 8.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.0,
                'debit': 8.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -208.006,
                'credit': 69.33,
                'date_maturity': fields.Date.from_string('2016-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2016-01-01'),
            'amount_untaxed': 160.005,
            'amount_tax': 48.001,
            'amount_total': 208.006,
        })

        # Exit the multi-currencies.
        with Form(self.invoice) as move_form:
            move_form.currency_id = self.company_data['currency']

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'quantity': 0.1,
                'price_unit': 0.05,
                'price_subtotal': 0.01,
                'price_total': 0.01,
                'amount_currency': 0.01,
                'debit': 0.01,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'amount_currency': 24.0,
                'debit': 24.0,
            },
            self.tax_line_vals_2,
            {
                **self.term_line_vals_1,
                'amount_currency': -208.01,
                'credit': 208.01,
                'date_maturity': fields.Date.from_string('2016-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.company_data['currency'].id,
            'date': fields.Date.from_string('2016-01-01'),
            'amount_untaxed': 160.01,
            'amount_tax': 48.0,
            'amount_total': 208.01,
        })

    def test_in_invoice_onchange_past_invoice_1(self):
        if self.env.ref('purchase.group_purchase_manager', raise_if_not_found=False):
            # `purchase` adds a view which makes `invoice_vendor_bill_id` invisible
            # for purchase users
            # https://github.com/odoo/odoo/blob/385884afd31f25d61e99d139ecd4c574d99a1863/addons/purchase/views/account_move_views.xml#L26
            self.env.user.groups_id -= self.env.ref('purchase.group_purchase_manager')
            self.env.user.groups_id -= self.env.ref('purchase.group_purchase_user')
        copy_invoice = self.invoice.copy()

        move_form = Form(self.invoice)
        move_form.invoice_line_ids.remove(0)
        move_form.invoice_line_ids.remove(0)
        move_form.invoice_vendor_bill_id = copy_invoice
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            self.product_line_vals_1,
            self.product_line_vals_2,
            self.tax_line_vals_1,
            self.tax_line_vals_2,
            self.term_line_vals_1,
        ], self.move_vals)

    def test_in_invoice_create_refund(self):
        self.invoice.action_post()

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
                'amount_currency': -800.0,
                'debit': 0.0,
                'credit': 800.0,
                'tax_tag_invert': True,
                'tax_base_amount': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': -160.0,
                'debit': 0.0,
                'credit': 160.0,
                'tax_tag_invert': True,
                'tax_base_amount': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': -144.0,
                'debit': 0.0,
                'credit': 144.0,
                'tax_tag_invert': True,
                'tax_base_amount': 960.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': -24.0,
                'debit': 0.0,
                'credit': 24.0,
                'tax_tag_invert': True,
                'tax_base_amount': 160.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': 1128.0,
                'debit': 1128.0,
                'credit': 0.0,
                'date_maturity': move_reversal.date,
                'tax_tag_invert': False,
                'tax_base_amount': 0.0,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': None,
            'date': move_reversal.date,
            'state': 'draft',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'payment_state': 'not_paid',
        })

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason again',
            'journal_id': self.invoice.journal_id.id,
        })
        reversal = move_reversal.modify_moves()
        new_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'reversed', "After cancelling it with a reverse invoice, an invoice should be in 'reversed' state.")
        self.assertInvoiceValues(new_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': 800.0,
                'debit': 800.0,
                'credit': 0.0,
                'tax_tag_invert': False,
                'tax_base_amount': 0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': 160.0,
                'debit': 160.0,
                'credit': 0.0,
                'tax_tag_invert': False,
                'tax_base_amount': 0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': 144.0,
                'debit': 144.0,
                'credit': 0.0,
                'tax_tag_invert': False,
                'tax_base_amount': 960.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 24.0,
                'debit': 24.0,
                'credit': 0.0,
                'tax_tag_invert': False,
                'tax_base_amount': 160.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': -1128.0,
                'debit': 0.0,
                'credit': 1128.0,
                'date_maturity': move_reversal.date,
                'tax_tag_invert': False,
                'tax_base_amount': 0,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'date': move_reversal.date,
            'state': 'draft',
            'ref': False,
            'payment_state': 'not_paid',
        })

    def test_in_invoice_create_refund_multi_currency(self):
        ''' Test the account.move.reversal takes care about the currency rates when setting
        a custom reversal date.
        '''
        with Form(self.invoice) as move_form:
            move_form.date = '2016-01-01'
            move_form.currency_id = self.currency_data['currency']

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
                'amount_currency': -800.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 0.0,
                'credit': 400.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': -160.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 0.0,
                'credit': 80.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': -144.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 0.0,
                'credit': 72.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': -24.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 0.0,
                'credit': 12.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': 1128.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 564.0,
                'credit': 0.0,
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
            'reason': 'no reason again',
            'journal_id': self.invoice.journal_id.id,
        })
        reversal = move_reversal.modify_moves()
        new_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(self.invoice.payment_state, 'reversed', "After cancelling it with a reverse invoice, an invoice should be in 'reversed' state.")
        self.assertInvoiceValues(new_move, [
            {
                **self.product_line_vals_1,
                'amount_currency': 800.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 400.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'amount_currency': 160.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 80.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'amount_currency': 144.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 72.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'amount_currency': 24.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 12.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'name': '',
                'amount_currency': -1128.0,
                'currency_id': self.currency_data['currency'].id,
                'debit': 0.0,
                'credit': 564.0,
                'date_maturity': move_reversal.date,
            },
        ], {
            **self.move_vals,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'currency_id': self.currency_data['currency'].id,
            'date': move_reversal.date,
            'state': 'draft',
            'ref': False,
            'payment_state': 'not_paid',
        })

    def test_in_invoice_create_1(self):
        # Test creating an account_move with the least information.
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
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

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'debit': 400.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 160.0,
                'debit': 80.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 144.0,
                'debit': 72.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.0,
                'debit': 12.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1128.0,
                'credit': 564.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2019-01-31'),
        })

    def test_in_invoice_write_1(self):
        # Test creating an account_move with the least information.
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
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
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'debit': 400.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 160.0,
                'debit': 80.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 144.0,
                'debit': 72.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.0,
                'debit': 12.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1128.0,
                'credit': 564.0,
            },
        ], {
            **self.move_vals,
            'date': fields.Date.from_string('2019-01-31'),
            'currency_id': self.currency_data['currency'].id,
        })

    def test_in_invoice_single_duplicate_supplier_reference(self):
        """ Ensure duplicated ref are computed correctly in this simple case """
        invoice_1 = self.invoice
        invoice_1.ref = 'a unique supplier reference that will be copied'
        invoice_2 = invoice_1.copy(default={'invoice_date': invoice_1.invoice_date})
        # ensure no Error is raised
        invoice_2.ref = invoice_1.ref
        self.assertRecordValues(invoice_2, [{'duplicated_ref_ids': invoice_1.ids}])

    def test_in_invoice_single_duplicate_supplier_reference_with_form(self):
        """ Ensure duplicated ref are computed correctly with UI's NEW_ID"""
        invoice_1 = self.invoice
        invoice_1.ref = 'a unique supplier reference that will be copied'
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = invoice_1.invoice_date
        move_form.ref = invoice_1.ref
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_b
        invoice_2 = move_form.save()
        self.assertRecordValues(invoice_2, [{'duplicated_ref_ids': invoice_1.ids}])

    def test_in_invoice_multiple_duplicate_supplier_reference_batch(self):
        """ Ensure duplicated ref are computed correctly even when updated in batch"""
        invoice_1 = self.invoice
        invoice_1.ref = 'a unique supplier reference that will be copied'
        invoice_2 = invoice_1.copy(default={'invoice_date': invoice_1.invoice_date})
        invoice_3 = invoice_1.copy(default={'invoice_date': invoice_1.invoice_date})

        # reassign to trigger the compute method
        invoices = invoice_1 + invoice_2 + invoice_3
        invoices.ref = invoice_1.ref
        self.assertRecordValues(invoices, [
            {'duplicated_ref_ids': (invoice_2 + invoice_3).ids},
            {'duplicated_ref_ids': (invoice_1 + invoice_3).ids},
            {'duplicated_ref_ids': (invoice_1 + invoice_2).ids},
        ])

    @freeze_time('2023-02-01')
    def test_in_invoice_payment_register_wizard(self):
        # Test creating an account_move with an in_invoice_type and check payment register wizard values
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2023-01-30'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_line_vals_1['product_id'],
                    'product_uom_id': self.product_line_vals_1['product_uom_id'],
                    'price_unit': self.product_line_vals_1['price_unit'],
                    'tax_ids': [Command.set(self.product_line_vals_1['tax_ids'])],
                }),
            ],
        })
        move.action_post()
        action_data = move.action_register_payment()
        with Form(self.env[action_data['res_model']].with_context(action_data['context'])) as wiz_form:
            self.assertEqual(wiz_form.payment_date.strftime('%Y-%m-%d'), '2023-02-01')
            self.assertEqual(wiz_form.amount, 920)
            self.assertTrue(wiz_form.group_payment)
            self.assertFalse(wiz_form._get_modifier('group_payment', 'invisible'))
            self.assertFalse(wiz_form._get_modifier('group_payment', 'readonly'))

    def test_in_invoice_switch_type_1(self):
        # Test creating an account_move with an in_invoice_type and switch it in an in_refund,
        # then switching it back to an in_invoice.
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
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
        move.action_switch_move_type()  # Switch to refund.

        self.assertRecordValues(move, [{'move_type': 'in_refund'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -800.0,
                'credit': 400.0,
                'debit': 0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -160.0,
                'credit': 80.0,
                'debit': 0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -144.0,
                'credit': 72.0,
                'debit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -24.0,
                'credit': 12.0,
                'debit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1128.0,
                'debit': 564.0,
                'credit': 0,
            },
        ], {
            **self.move_vals,
            'date': fields.Date.from_string('2019-01-31'),
            'currency_id': self.currency_data['currency'].id,
        })

        move.action_switch_move_type()  # Switch back to invoice.

        self.assertRecordValues(move, [{'move_type': 'in_invoice'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'credit': 0,
                'debit': 400.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 160.0,
                'credit': 0.0,
                'debit': 80,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 144.0,
                'credit': 0,
                'debit': 72,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.0,
                'credit': 0,
                'debit': 12,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1128.0,
                'debit': 0,
                'credit': 564,
            },
        ], {
            **self.move_vals,
            'date': fields.Date.from_string('2019-01-31'),
            'currency_id': self.currency_data['currency'].id,
        })

    def test_in_invoice_switch_type_2(self):
        # Test creating an account_move with an in_invoice_type and switch it in an in_refund and a negative quantity,
        # then switching it back to an in_invoice.
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
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
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -800.0,
                'price_subtotal': -800.0,
                'price_total': -920.0,
                'credit': 400.0,
                'debit': 0,
                'quantity': -1.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -160.0,
                'price_subtotal': -160.0,
                'price_total': -208.0,
                'credit': 80.0,
                'debit': 0,
                'quantity': -1.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -144.0,
                'credit': 72.0,
                'debit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -24.0,
                'credit': 12.0,
                'debit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1128.0,
                'debit': 564.0,
                'credit': 0,
            },
        ], {
            **self.move_vals,
            'date': fields.Date.from_string('2019-01-31'),
            'currency_id': self.currency_data['currency'].id,
            'amount_tax' : -self.move_vals['amount_tax'],
            'amount_total' : -self.move_vals['amount_total'],
            'amount_untaxed' : -self.move_vals['amount_untaxed'],
        })
        move.action_switch_move_type()  # Switch to refund

        self.assertRecordValues(move, [{'move_type': 'in_refund'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -800.0,
                'credit': 400.0,
                'debit': 0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -160.0,
                'credit': 80.0,
                'debit': 0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -144.0,
                'credit': 72.0,
                'debit': 0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -24.0,
                'credit': 12.0,
                'debit': 0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1128.0,
                'debit': 564.0,
                'credit': 0,
            },
        ], {
            **self.move_vals,
            'date': fields.Date.from_string('2019-01-31'),
            'currency_id': self.currency_data['currency'].id,
            'amount_tax' : self.move_vals['amount_tax'],
            'amount_total' : self.move_vals['amount_total'],
            'amount_untaxed' : self.move_vals['amount_untaxed'],
        })
        move.action_switch_move_type()  # Switch back to invoice

        self.assertRecordValues(move, [{'move_type': 'in_invoice'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'credit': 0,
                'debit': 400,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 160.0,
                'credit': 0,
                'debit': 80,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 144.0,
                'credit': 0,
                'debit': 72,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.0,
                'credit': 0,
                'debit': 12,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1128.0,
                'debit': 0,
                'credit': 564,
            },
        ], {
            **self.move_vals,
            'date': fields.Date.from_string('2019-01-31'),
            'currency_id': self.currency_data['currency'].id,
            'amount_tax': self.move_vals['amount_tax'],
            'amount_total': self.move_vals['amount_total'],
            'amount_untaxed': self.move_vals['amount_untaxed'],
        })

    def test_in_invoice_change_period_accrual_1(self):
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
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

        wizard = self.env['account.automatic.entry.wizard'].with_context(
            active_model='account.move.line',
            active_ids=move.invoice_line_ids.ids,
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

        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 800.0,
                'debit': 400.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 160.0,
                'debit': 80.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 144.0,
                'debit': 72.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 24.0,
                'debit': 12.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1128.0,
                'debit': 0.0,
                'credit': 564.0,
                'date_maturity': fields.Date.from_string('2017-01-01'),
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2017-01-01'),
        })

        accrual_lines = self.env['account.move'].browse(wizard_res['domain'][0][2]).line_ids.sorted('date')
        self.assertRecordValues(accrual_lines, [
            {'amount_currency': -480.0, 'debit': 0.0,   'credit': 240.0,    'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': 480.0,  'debit': 240.0, 'credit': 0.0,      'account_id': wizard.expense_accrual_account.id,        'reconciled': True},
            {'amount_currency': -96.0,  'debit': 0.0,   'credit': 48.0,     'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': 96.0,   'debit': 48.0,  'credit': 0.0,      'account_id': wizard.expense_accrual_account.id,        'reconciled': True},
            {'amount_currency': 480.0,  'debit': 240.0, 'credit': 0.0,      'account_id': self.product_line_vals_1['account_id'],   'reconciled': False},
            {'amount_currency': -480.0, 'debit': 0.0,   'credit': 240.0,    'account_id': wizard.expense_accrual_account.id,        'reconciled': True},
            {'amount_currency': 96.0,   'debit': 48.0,  'credit': 0.0,      'account_id': self.product_line_vals_2['account_id'],   'reconciled': False},
            {'amount_currency': -96.0,  'debit': 0.0,   'credit': 48.0,     'account_id': wizard.expense_accrual_account.id,        'reconciled': True},
        ])

    def test_in_invoice_reverse_caba(self):
        tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'account_type': 'liability_current',
            'reconcile': True,
            'company_id': self.company_data['company'].id,
        })
        tax_final_account = self.env['account.account'].create({
            'name': 'TAX_TO_DEDUCT',
            'code': 'TDEDUCT',
            'account_type': 'asset_current',
            'company_id': self.company_data['company'].id,
        })
        tax_base_amount_account = self.env['account.account'].create({
            'name': 'TAX_BASE',
            'code': 'TBASE',
            'account_type': 'asset_current',
            'company_id': self.company_data['company'].id,
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
            'type_tax_use': 'purchase',
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
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
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
        partial_rec = invoice.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])
        expected_values = [
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': tax_base_amount_account.id,
                'debit': 0.0,
                'credit': 800.0,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': tax.ids,
                'tax_tag_ids': tax_tags['invoice']['base'].ids,
                'account_id': tax_base_amount_account.id,
                'debit': 800.0,
                'credit': 0.0,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': tax_waiting_account.id,
                'debit': 0.0,
                'credit': 80.0,
            },
            {
                'tax_line_id': tax.id,
                'tax_repartition_line_id': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                'tax_ids': [],
                'tax_tag_ids': tax_tags['invoice']['tax'].ids,
                'account_id': tax_final_account.id,
                'debit': 80.0,
                'credit': 0.0,
            },
        ]
        self.assertRecordValues(caba_move.line_ids, expected_values)
        # unreconcile
        credit_aml = invoice.line_ids.filtered('credit')
        credit_aml.remove_move_reconcile()
        # check caba move reverse is same as caba move with only debit/credit inverted
        reversed_caba_move = self.env['account.move'].search([('reversed_entry_id', '=', caba_move.id)])
        for value in expected_values:
            value.update({
                'debit': value['credit'],
                'credit': value['debit'],
            })
        self.assertRecordValues(reversed_caba_move.line_ids, expected_values)

    def test_in_invoice_with_down_payment_caba(self):
        tax_waiting_account = self.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'account_type': 'liability_current',
            'reconcile': True,
            'company_id': self.company_data['company'].id,
        })
        tax_final_account = self.env['account.account'].create({
            'name': 'TAX_TO_DEDUCT',
            'code': 'TDEDUCT',
            'account_type': 'asset_current',
            'company_id': self.company_data['company'].id,
        })
        default_expense_account = self.company_data['default_account_expense']
        not_default_expense_account = self.env['account.account'].create({
            'name': 'NOT_DEFAULT_EXPENSE',
            'code': 'NDE',
            'account_type': 'expense',
            'company_id': self.company_data['company'].id,
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
            'type_tax_use': 'purchase',
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
        # create bill
        # one downpayment on default account and one product line on not default account, both with the caba tax
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2017-01-01'),
            'invoice_line_ids': [
                Command.create({
                    'account_id': not_default_expense_account.id,
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
        partial_rec = invoice.mapped('line_ids.matched_debit_ids')
        caba_move = self.env['account.move'].search([('tax_cash_basis_rec_id', '=', partial_rec.id)])
        # all amls with tax_tag should all have tax_tag_invert at False since the caba move comes from a bill
        expected_values = [
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': not_default_expense_account.id,
                'debit': 0.0,
                'credit': 800.0,
                'tax_tag_invert': False,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': tax.ids,
                'tax_tag_ids': tax_tags['invoice']['base'].ids,
                'account_id': not_default_expense_account.id,
                'debit': 800.0,
                'credit': 0.0,
                'tax_tag_invert': False,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': default_expense_account.id,
                'debit': 300.0,
                'credit': 0.0,
                'tax_tag_invert': False,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': tax.ids,
                'tax_tag_ids': tax_tags['invoice']['base'].ids,
                'account_id': default_expense_account.id,
                'debit': 0.0,
                'credit': 300.0,
                'tax_tag_invert': False,
            },
            {
                'tax_line_id': False,
                'tax_repartition_line_id': False,
                'tax_ids': [],
                'tax_tag_ids': [],
                'account_id': tax_waiting_account.id,
                'debit': 0.0,
                'credit': 50.0,
                'tax_tag_invert': False,
            },
            {
                'tax_line_id': tax.id,
                'tax_repartition_line_id': tax.invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax').id,
                'tax_ids': [],
                'tax_tag_ids': tax_tags['invoice']['tax'].ids,
                'account_id': tax_final_account.id,
                'debit': 50.0,
                'credit': 0.0,
                'tax_tag_invert': False,
            },
        ]
        self.assertRecordValues(caba_move.line_ids, expected_values)

    def test_in_invoice_line_tax_line_delete(self):
        with self.assertRaisesRegex(ValidationError, "You cannot delete a tax line"):
            with Form(self.invoice) as invoice_form:
                invoice_form.line_ids.remove(2)

    @freeze_time('2022-06-17')
    def test_fiduciary_mode_date_suggestion(self):
        """Test that the fiduciary mode invoice date suggestion is correct."""

        # Fiduciary mode not enabled, no date suggestion
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        self.assertFalse(move_form.invoice_date)

        # Fiduciary mode enabled, date suggestion
        self.env.company.quick_edit_mode = "out_and_in_invoices"

        # We are June 17th. No Lock date. Bill Date of the most recent Vendor Bill : March 15th
        # ==> Default New Vendor Bill date = March 31st (last day of March)
        self.init_invoice(move_type='in_invoice', invoice_date='2022-03-15', products=self.product_a, post=True)
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        self.assertEqual(move_form.invoice_date.strftime('%Y-%m-%d'), '2022-03-31')

        # We are June 17th. No Lock date. Bill Date of the most recent Vendor Bill : March 31st
        # ==> Default New Vendor Bill date = March 31st 2022 (last day of March)
        self.init_invoice(move_type='in_invoice', invoice_date='2022-03-31', products=self.product_b, post=True)
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        self.assertEqual(move_form.invoice_date.strftime('%Y-%m-%d'), '2022-03-31')

        # We are June 17th. No Lock date. Bill Date of the most recent Vendor Bill : June 16th
        # ==> Default New Vendor Bill date = June 17th (today is smaller than end of June)
        move = self.init_invoice(move_type='in_invoice', invoice_date='2022-06-16', products=self.product_b, post=True)
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        self.assertEqual(move_form.invoice_date, date.today())
        move.button_draft()
        move.unlink()

        # We are June 17th. Lock date : April 30th. Bill Date of the most recent Vendor Bill : April 30th
        # ==> Default New Vendor Bill date = May 31st (last day of the first month not locked)
        self.env['account.move'].search([('state', '!=', 'posted')]).unlink()
        move = self.init_invoice(move_type='in_invoice', invoice_date='2022-04-30', products=self.product_a, post=True)
        move.company_id.fiscalyear_lock_date = fields.Date.from_string('2022-04-30')
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        self.assertEqual(move_form.invoice_date.strftime('%Y-%m-%d'), '2022-05-31')

        # If the user changes the invoice date, we should not override it
        self.init_invoice(move_type='in_invoice', invoice_date='2022-05-01', products=self.product_b, post=True)
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        self.assertEqual(move_form.invoice_date.strftime('%Y-%m-%d'), '2022-05-31')
        move_form.invoice_date = fields.Date.from_string('2022-05-06')
        move = move_form.save()
        self.assertEqual(move.invoice_date.strftime('%Y-%m-%d'), '2022-05-06')

    def _assert_payment_move_state(self, move_type, amount, counterpart_values_list, payment_state):
        def assert_partial(line1, line2):
            partial = self.env['account.partial.reconcile'].search(expression.OR([
                [('debit_move_id', '=', line1.id), ('credit_move_id', '=', line2.id)],
                [('debit_move_id', '=', line2.id), ('credit_move_id', '=', line1.id)],
            ]), limit=1)
            self.assertTrue(partial)

        def create_move(move_type, amount, account=None):
            move_vals = {
                'move_type': move_type,
                'date': '2020-01-10',
            }
            if move_type in self.env['account.move'].get_sale_types(include_receipts=True) + self.env['account.move'].get_purchase_types(include_receipts=True):
                move_vals.update({
                    'partner_id': self.partner_a.id,
                    'invoice_date': '2020-01-10',
                    'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': amount, 'tax_ids': []})],
                })
            else:
                if amount > 0.0:
                    debit_account = account or self.company_data['default_account_receivable']
                    credit_account = self.company_data['default_account_revenue']
                    debit_balance = amount
                else:
                    credit_account = account or self.company_data['default_account_receivable']
                    debit_account = self.company_data['default_account_revenue']
                    debit_balance = -amount
                move_vals['line_ids'] = [
                    Command.create({
                        'name': "line1",
                        'account_id': debit_account.id,
                        'balance': debit_balance,
                    }),
                    Command.create({
                        'name': "line2",
                        'account_id': credit_account.id,
                        'balance': -debit_balance,
                    }),
                ]
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            return move

        def create_payment(move, amount):
            self.env['account.payment.register']\
                .with_context(active_ids=move.ids, active_model='account.move')\
                .create({
                    'amount': amount,
                })\
                ._create_payments()

        def create_reverse(move, amount):
            move_reversal = self.env['account.move.reversal']\
                .with_context(active_model='account.move', active_ids=move.ids)\
                .create({
                    'reason': 'no reason',
                    'journal_id': move.journal_id.id,
                })
            reversal = move_reversal.refund_moves()
            reverse_move = self.env['account.move'].browse(reversal['res_id'])
            if reverse_move.move_type in ('out_refund', 'in_refund'):
                reverse_move.write({
                    'invoice_line_ids': [
                        Command.update(reverse_move.invoice_line_ids.id, {'price_unit': amount}),
                    ],
                })
            else:
                line = move.line_ids.filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
                reverse_move.write({
                    'line_ids': [
                        Command.update(line.id, {'balance': amount}),
                    ],
                })
            if reverse_move.state == 'draft':
                reverse_move.action_post()

        def create_statement_line(move, amount):
            statement_line = self.env['account.bank.statement.line'].create({
                'payment_ref': 'ref',
                'journal_id': self.company_data['default_journal_bank'].id,
                'amount': amount,
                'date': '2020-01-10',
            })
            _st_liquidity_lines, st_suspense_lines, _st_other_lines = statement_line\
                .with_context(skip_account_move_synchronization=True)\
                ._seek_for_lines()
            line = move.line_ids.filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))

            st_suspense_lines.account_id = line.account_id
            (st_suspense_lines + line).reconcile()
            assert_partial(st_suspense_lines, line)

        move = create_move(move_type, amount)
        line = move.line_ids.filtered(lambda line: line.account_type in ('asset_receivable', 'liability_payable'))
        for counterpart_move_type, counterpart_amount in counterpart_values_list:
            if counterpart_move_type == 'payment':
                create_payment(move, counterpart_amount)
            elif counterpart_move_type == 'reverse':
                create_reverse(move, counterpart_amount)
            elif counterpart_move_type == 'statement_line':
                create_statement_line(move, counterpart_amount)
            else:
                counterpart_move = create_move(counterpart_move_type, counterpart_amount, account=line.account_id)
                counterpart_line = counterpart_move.line_ids.filtered(lambda x: x.account_id == line.account_id)
                (line + counterpart_line).reconcile()
                assert_partial(line, counterpart_line)

        if payment_state == 'in_payment' and move._get_invoice_in_payment_state() == 'paid':
            payment_state = 'paid'

        self.assertRecordValues(move, [{'payment_state': payment_state}])

    def test_payment_move_state(self):
        for move_type, amount, counterpart_values_list, payment_state in (
            ('out_invoice', 1000.0, [('out_refund', 1000.0)], 'reversed'),
            ('out_invoice', 1000.0, [('out_refund', 500.0), ('out_refund', 500.0)], 'reversed'),
            ('out_invoice', 1000.0, [('out_refund', 500.0), ('entry', -500.0)], 'reversed'),
            ('out_invoice', 1000.0, [('reverse', 1000.0)], 'reversed'),
            ('out_receipt', 1000.0, [('out_refund', 1000.0)], 'reversed'),
            ('out_receipt', 1000.0, [('out_refund', 500.0), ('out_refund', 500.0)], 'reversed'),
            ('out_receipt', 1000.0, [('reverse', 1000.0)], 'reversed'),
            ('out_refund', 1000.0, [('reverse', -1000.0)], 'reversed'),
            ('in_invoice', 1000.0, [('in_refund', 1000.0)], 'reversed'),
            ('in_invoice', 1000.0, [('in_refund', 500.0), ('in_refund', 500.0)], 'reversed'),
            ('in_invoice', 1000.0, [('in_refund', 500.0), ('entry', 500.0)], 'reversed'),
            ('in_invoice', 1000.0, [('reverse', 1000.0)], 'reversed'),
            ('in_receipt', 1000.0, [('in_refund', 1000.0)], 'reversed'),
            ('in_receipt', 1000.0, [('in_refund', 500.0), ('in_refund', 500.0)], 'reversed'),
            ('in_receipt', 1000.0, [('reverse', 1000.0)], 'reversed'),
            ('in_refund', 1000.0, [('reverse', 1000.0)], 'reversed'),
            ('entry', 1000.0, [('entry', -1000.0)], 'not_paid'),
            ('entry', 1000.0, [('reverse', 1000.0)], 'not_paid'),

            ('out_invoice', 1000.0, [('payment', 500.0)], 'partial'),
            ('out_invoice', 1000.0, [('payment', 1000.0)], 'in_payment'),
            ('out_invoice', 1000.0, [('statement_line', 500.0)], 'partial'),
            ('out_invoice', 1000.0, [('statement_line', 1000.0)], 'paid'),
            ('out_receipt', 1000.0, [('payment', 500.0)], 'partial'),
            ('out_receipt', 1000.0, [('payment', 1000.0)], 'in_payment'),
            ('out_receipt', 1000.0, [('statement_line', 500.0)], 'partial'),
            ('out_receipt', 1000.0, [('statement_line', 1000.0)], 'paid'),
            ('out_refund', 1000.0, [('payment', 500.0)], 'partial'),
            ('out_refund', 1000.0, [('payment', 1000.0)], 'in_payment'),
            ('out_refund', 1000.0, [('statement_line', -500.0)], 'partial'),
            ('out_refund', 1000.0, [('statement_line', -1000.0)], 'paid'),
            ('in_invoice', 1000.0, [('payment', 500.0)], 'partial'),
            ('in_invoice', 1000.0, [('payment', 1000.0)], 'in_payment'),
            ('in_invoice', 1000.0, [('statement_line', -500.0)], 'partial'),
            ('in_invoice', 1000.0, [('statement_line', -1000.0)], 'paid'),
            ('in_receipt', 1000.0, [('payment', 500.0)], 'partial'),
            ('in_receipt', 1000.0, [('payment', 1000.0)], 'in_payment'),
            ('in_receipt', 1000.0, [('statement_line', -500.0)], 'partial'),
            ('in_receipt', 1000.0, [('statement_line', -1000.0)], 'paid'),
            ('in_refund', 1000.0, [('payment', 500.0)], 'partial'),
            ('in_refund', 1000.0, [('payment', 1000.0)], 'in_payment'),
            ('in_refund', 1000.0, [('statement_line', 500.0)], 'partial'),
            ('in_refund', 1000.0, [('statement_line', 1000.0)], 'paid'),
            ('entry', 1000.0, [('payment', 500.0)], 'not_paid'),
            ('entry', 1000.0, [('payment', 1000.0)], 'not_paid'),
            ('entry', 1000.0, [('statement_line', 500.0)], 'not_paid'),
            ('entry', 1000.0, [('statement_line', 1000.0)], 'not_paid'),

            ('out_invoice', 1000.0, [('out_refund', 500.0), ('payment', 500.0)], 'in_payment'),
            ('out_invoice', 1000.0, [('out_refund', 500.0), ('payment', 400.0)], 'partial'),
            ('out_invoice', 1000.0, [('out_refund', 500.0), ('statement_line', 500.0)], 'paid'),
            ('out_invoice', 1000.0, [('out_refund', 500.0), ('statement_line', 400.0)], 'partial'),
            ('out_invoice', 1000.0, [('entry', -1000.0)], 'paid'),
            ('in_invoice', 1000.0, [('in_refund', 500.0), ('payment', 500.0)], 'in_payment'),
            ('in_invoice', 1000.0, [('in_refund', 500.0), ('payment', 400.0)], 'partial'),
            ('in_invoice', 1000.0, [('in_refund', 500.0), ('statement_line', -500.0)], 'paid'),
            ('in_invoice', 1000.0, [('in_refund', 500.0), ('statement_line', -400.0)], 'partial'),
            ('in_invoice', 1000.0, [('entry', 1000.0)], 'paid'),
        ):
            with self.subTest(
                move_type=move_type,
                amount=amount,
                counterpart_values_list=counterpart_values_list,
                payment_state=payment_state,
            ):
                self._assert_payment_move_state(move_type, amount, counterpart_values_list, payment_state)

    def test_onchange_journal_currency(self):
        """
        Ensure invoice currency changes on journal change, iff the journal
        has a currency_id set.
        """

        chf = self.env.ref('base.CHF')
        eur = self.env.ref('base.EUR')

        journal_gen_exp = self.env['account.journal'].create({
            'name': 'Expenses (generic)',
            'type': 'purchase',
            'code': 'EXPGEN',
        })
        journal_swiss_exp = self.env['account.journal'].create({
            'name': 'Expenses (CHF)',
            'type': 'purchase',
            'code': 'EXPCHF',
            'currency_id': chf.id,
        })

        self.invoice.currency_id = eur
        move_form = Form(self.invoice)
        invoice = move_form.save()
        self.assertEqual(invoice.currency_id, eur)

        # No change expected with generic journal
        move_form.journal_id = journal_gen_exp
        move_form.save()
        self.assertEqual(invoice.currency_id, eur,
                         "Changing to a journal without set currency shouldn't affect invoice currency")

        # Currency should change
        move_form.journal_id = journal_swiss_exp
        move_form.save()
        self.assertEqual(invoice.currency_id, chf,
                         "Changing to a journal with a set currency should change invoice currency")

    def test_onchange_payment_reference(self):
        """
        Ensure payment reference propagation from move to payment term
        line is done correctly
        """
        payment_term_line = self.invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term')
        with Form(self.invoice) as move_form:
            move_form.payment_reference = 'test'
        self.assertEqual(payment_term_line.name, 'test')
        with Form(self.invoice) as move_form:
            move_form.payment_reference = False
        self.assertEqual(payment_term_line.name, '', 'Payment term line was not changed')

    def test_taxes_onchange_product_uom_and_price_unit(self):
        """
        Ensure that taxes are recomputed correctly when product uom and
        price unit are changed for users without 'uom.group_uom' group
        """
        self.env.user.groups_id -= self.env.ref('uom.group_uom')
        tax = self.company_data['default_tax_purchase']
        product = self.env['product.product'].create({
            'name': 'product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'standard_price': 0.0,
            'supplier_taxes_id': [Command.set(tax.ids)],
        })
        expected_values = [
            {
                'tax_line_id': False,
                'debit': 100.0,
                'credit': 0.0,
            },
            {
                'tax_line_id': tax.id,
                'debit': 15.0,
                'credit': 0.0,
            },
            {
                'tax_line_id': False,
                'debit': 0.0,
                'credit': 115.0,
            },
        ]
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2024-03-01')
        # add a line (without product) with a price of 100.0 and a 15% tax
        with move_form.invoice_line_ids.new() as line_form:
            line_form.name = 'no product'
            line_form.price_unit = 100.0
            line_form.tax_ids.add(tax)
        invoice = move_form.save()
        self.assertRecordValues(invoice.line_ids, expected_values)

        move_form = Form(invoice)
        # edit line to add a product and set price to 100.0 manually
        # that should recompute the taxes
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.product_id = product
            line_form.price_unit = 100.0
        invoice = move_form.save()
        self.assertRecordValues(invoice.line_ids, expected_values)

    def test_in_invoice_line_product_taxes_on_branch(self):
        """ Check taxes populated on bill lines from product on branch company.
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
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'Tax B',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 15,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_x = self.env['account.tax'].create({
            'name': 'Tax X',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 20,
            'tax_group_id': tax_groups[1].id,
            'company_id': branch_x.id,
        })
        tax_xx = self.env['account.tax'].create({
            'name': 'Tax XX',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 25,
            'tax_group_id': tax_groups[2].id,
            'company_id': branch_xx.id,
        })
        # create several products with different taxes combination
        product_all_taxes = self.env['product.product'].create({
            'name': 'Product all taxes',
            'taxes_id': [Command.set((tax_a + tax_b + tax_x + tax_xx).ids)],
            'supplier_taxes_id': [Command.set((tax_a + tax_b + tax_x + tax_xx).ids)],
        })
        product_no_xx_tax = self.env['product.product'].create({
            'name': 'Product no tax from XX',
            'taxes_id': [Command.set((tax_a + tax_b + tax_x).ids)],
            'supplier_taxes_id': [Command.set((tax_a + tax_b + tax_x).ids)],
        })
        product_no_branch_tax = self.env['product.product'].create({
            'name': 'Product no tax from branch',
            'taxes_id': [Command.set((tax_a + tax_b).ids)],
            'supplier_taxes_id': [Command.set((tax_a + tax_b).ids)],
        })
        product_no_tax = self.env['product.product'].create({
            'name': 'Product no tax',
            'taxes_id': [],
            'supplier_taxes_id': [],
        })
        # create a bill from Branch XX with the different products:
        # - Product all taxes           => tax from Branch XX should be set
        # - Product no tax from XX      => tax from Branch X should be set
        # - Product no tax from branch  => 2 taxes from parent company should be set
        # - Product no tax              => no tax should be set
        bill = self.init_invoice(
            'in_invoice',
            products=product_all_taxes + product_no_xx_tax + product_no_branch_tax + product_no_tax,
            company=branch_xx
        )
        self.assertRecordValues(bill.invoice_line_ids, [
            {'product_id': product_all_taxes.id, 'tax_ids': tax_xx.ids},
            {'product_id': product_no_xx_tax.id, 'tax_ids': tax_x.ids},
            {'product_id': product_no_branch_tax.id, 'tax_ids': (tax_a + tax_b).ids},
            {'product_id': product_no_tax.id, 'tax_ids': []},
        ])

    def test_purchase_uom_on_vendor_bills(self):
        uom_gram = self.env.ref('uom.product_uom_gram')
        uom_kgm = self.env.ref('uom.product_uom_kgm')

        # product with different sale and purchase UOM
        product = self.env['product.product'].create({
            'name': 'product',
            'uom_id': uom_gram.id,
            'uom_po_id': uom_kgm.id,
            'standard_price': 110.0,
        })
        # customer invoice should have sale uom
        invoice = self.init_invoice(move_type='out_invoice', products=[product])
        invoice_uom = invoice.invoice_line_ids[0].product_uom_id
        self.assertEqual(invoice_uom, uom_gram)
        # vendor bill should have purchase uom
        bill = self.init_invoice(move_type='in_invoice', products=[product])
        bill_uom = bill.invoice_line_ids[0].product_uom_id
        self.assertEqual(bill_uom, uom_kgm)
