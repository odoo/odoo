# -*- coding: utf-8 -*-
from odoo.addons.account.tests.invoice_test_common import InvoiceTestCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMoveOutInvoiceOnchanges(InvoiceTestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestAccountMoveOutInvoiceOnchanges, cls).setUpClass()

        cls.invoice = cls.init_invoice('out_invoice')

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
            'currency_id': False,
            'amount_currency': 0.0,
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
            'currency_id': False,
            'amount_currency': 0.0,
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
            'currency_id': False,
            'amount_currency': 0.0,
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
            'currency_id': False,
            'amount_currency': 0.0,
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
            'currency_id': False,
            'amount_currency': 0.0,
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
            'invoice_payment_ref': '',
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
                'credit': 200.0,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'price_unit': 60.0,
                'price_subtotal': 60.0,
                'price_total': 60.0,
                'credit': 60.0,
            },
            {
                **self.tax_line_vals_2,
                'price_unit': 60.0,
                'price_subtotal': 60.0,
                'price_total': 60.0,
                'credit': 60.0,
            },
            {
                **self.term_line_vals_1,
                'price_unit': -520.0,
                'price_subtotal': -520.0,
                'price_total': -520.0,
                'debit': 520.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 400.0,
            'amount_tax': 120.0,
            'amount_total': 520.0,
        })

    def test_out_invoice_line_onchange_business_fields_1(self):
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            # Current price_unit is 1000.
            # We set quantity = 4, discount = 50%, price_unit = 500 because (4 * 500) * 0.5 = 1000.
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
                'credit': 0.0,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'price_unit': 30.0,
                'price_subtotal': 30.0,
                'price_total': 30.0,
                'credit': 30.0,
            },
            self.tax_line_vals_2,
            {
                **self.term_line_vals_1,
                'price_unit': -260.0,
                'price_subtotal': -260.0,
                'price_total': -260.0,
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
                'credit': 3000.0,
            },
            {
                **self.product_line_vals_2,
                'price_unit': -500.0,
                'price_subtotal': -500.0,
                'price_total': -650.0,
                'debit': 500.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': 800.0,
                'price_subtotal': 800.0,
                'price_total': 800.0,
                'credit': 800.0,
            },
            {
                **self.tax_line_vals_2,
                'price_unit': 250.0,
                'price_subtotal': 250.0,
                'price_total': 250.0,
                'credit': 250.0,
            },
            {
                **self.term_line_vals_1,
                'price_unit': -3550.0,
                'price_subtotal': -3550.0,
                'price_total': -3550.0,
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
        move_form.invoice_payment_ref = 'turlututu'
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
                'partner_id': self.partner_b.id,
                'price_unit': -423.0,
                'price_subtotal': -423.0,
                'price_total': -423.0,
                'debit': 423.0,
            },
            {
                **self.term_line_vals_1,
                'name': 'turlututu',
                'partner_id': self.partner_b.id,
                'price_unit': -987.0,
                'price_subtotal': -987.0,
                'price_total': -987.0,
                'debit': 987.0,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            **self.move_vals,
            'partner_id': self.partner_b.id,
            'invoice_payment_ref': 'turlututu',
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
                'debit': 966.0,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            **self.move_vals,
            'partner_id': self.partner_b.id,
            'invoice_payment_ref': 'turlututu',
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
                'currency_id': False,
                'amount_currency': 0.0,
                'debit': 0.0,
                'credit': 120.0,
                'date_maturity': False,
                'tax_exigible': True,
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
                'currency_id': False,
                'amount_currency': 0.0,
                'debit': 0.0,
                'credit': 80.0,
                'date_maturity': False,
                'tax_exigible': True,
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
                'currency_id': False,
                'amount_currency': 0.0,
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
                'debit': 1730.0,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 1200.0,
            'amount_tax': 530.0,
            'amount_total': 1730.0,
        })

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
                'account_id': self.cash_rounding_a.account_id.id,
                'partner_id': self.partner_a.id,
                'product_uom_id': False,
                'quantity': 1.0,
                'discount': 0.0,
                'price_unit': 0.01,
                'price_subtotal': 0.01,
                'price_total': 0.01,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': False,
                'amount_currency': 0.0,
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
                'currency_id': False,
                'amount_currency': 0.0,
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
                'debit': 1409.95,
            },
        ], {
            **self.move_vals,
            'amount_untaxed': 1199.99,
            'amount_tax': 209.96,
            'amount_total': 1409.95,
        })

    def test_out_invoice_line_onchange_currency_1(self):
        # New journal having a foreign currency set.
        journal = self.company_data['default_journal_sale'].copy()
        journal.currency_id = self.currency_data['currency']

        move_form = Form(self.invoice)
        move_form.journal_id = journal
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'currency_id': journal.currency_id.id,
                'amount_currency': -1000.0,
                'credit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': journal.currency_id.id,
                'amount_currency': -200.0,
                'credit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': journal.currency_id.id,
                'amount_currency': -180.0,
                'credit': 90.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': journal.currency_id.id,
                'amount_currency': -30.0,
                'credit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': journal.currency_id.id,
                'amount_currency': 1410.0,
                'debit': 705.0,
            },
        ], {
            **self.move_vals,
            'currency_id': journal.currency_id.id,
            'journal_id': journal.id,
        })

        move_form = Form(self.invoice)
        # Change the date to get another rate: 1/3 instead of 1/2.
        move_form.date = fields.Date.from_string('2016-01-01')
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'currency_id': journal.currency_id.id,
                'amount_currency': -1000.0,
                'credit': 333.33,
            },
            {
                **self.product_line_vals_2,
                'currency_id': journal.currency_id.id,
                'amount_currency': -200.0,
                'credit': 66.67,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': journal.currency_id.id,
                'amount_currency': -180.0,
                'credit': 60.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': journal.currency_id.id,
                'amount_currency': -30.0,
                'credit': 10.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': journal.currency_id.id,
                'amount_currency': 1410.0,
                'debit': 470.0,
            },
        ], {
            **self.move_vals,
            'currency_id': journal.currency_id.id,
            'journal_id': journal.id,
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
                'currency_id': journal.currency_id.id,
                'amount_currency': -0.005,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': journal.currency_id.id,
                'amount_currency': -200.0,
                'credit': 66.67,
            },
            {
                **self.tax_line_vals_1,
                'price_unit': 30.0,
                'price_subtotal': 30.001,
                'price_total': 30.001,
                'currency_id': journal.currency_id.id,
                'amount_currency': -30.001,
                'credit': 10.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': journal.currency_id.id,
                'amount_currency': -30.0,
                'credit': 10.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': journal.currency_id.id,
                'price_unit': -260.01,
                'price_subtotal': -260.006,
                'price_total': -260.006,
                'amount_currency': 260.006,
                'debit': 86.67,
            },
        ], {
            **self.move_vals,
            'currency_id': journal.currency_id.id,
            'journal_id': journal.id,
            'date': fields.Date.from_string('2016-01-01'),
            'amount_untaxed': 200.005,
            'amount_tax': 60.001,
            'amount_total': 260.006,
        })

        move_form = Form(self.invoice)
        move_form.currency_id = self.company_data['currency']
        move_form.save()

        self.assertInvoiceValues(self.invoice, [
            {
                **self.product_line_vals_1,
                'quantity': 0.1,
                'price_unit': 0.1,
                'price_subtotal': 0.01,
                'price_total': 0.01,
                'credit': 0.01,
            },
            self.product_line_vals_2,
            {
                **self.tax_line_vals_1,
                'price_unit': 30.0,
                'price_subtotal': 30.0,
                'price_total': 30.0,
                'credit': 30.0,
            },
            self.tax_line_vals_2,
            {
                **self.term_line_vals_1,
                'price_unit': -260.01,
                'price_subtotal': -260.01,
                'price_total': -260.01,
                'debit': 260.01,
            },
        ], {
            **self.move_vals,
            'currency_id': self.company_data['currency'].id,
            'journal_id': journal.id,
            'date': fields.Date.from_string('2016-01-01'),
            'amount_untaxed': 200.01,
            'amount_tax': 60.0,
            'amount_total': 260.01,
        })

    def test_out_invoice_onchange_sequence_number_1(self):
        self.assertRecordValues(self.invoice, [{
            'invoice_sequence_number_next': '0001',
            'invoice_sequence_number_next_prefix': 'INV/2019/',
        }])

        move_form = Form(self.invoice)
        move_form.invoice_sequence_number_next = '0042'
        move_form.save()

        self.assertRecordValues(self.invoice, [{
            'invoice_sequence_number_next': '0042',
            'invoice_sequence_number_next_prefix': 'INV/2019/',
        }])

        self.invoice.post()

        self.assertRecordValues(self.invoice, [{'name': 'INV/2019/0042'}])

        invoice_copy = self.invoice.copy()
        invoice_copy.post()

        self.assertRecordValues(invoice_copy, [{'name': 'INV/2019/0043'}])

    def test_out_invoice_create_draft_refund(self):
        self.invoice.post()

        move_reversal = self.env['account.move.reversal'].with_context(active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason',
            'refund_method': 'refund',
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertInvoiceValues(reverse_move, [
            {
                **self.product_line_vals_1,
                'debit': 1000.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'debit': 200.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'debit': 180.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'debit': 30.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'name': self.invoice.name,
                'debit': 0.0,
                'credit': 1410.0,
            },
        ], {
            **self.move_vals,
            'date': move_reversal.date,
            'state': 'draft',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'invoice_payment_state': 'not_paid',
        })

        move_reversal = self.env['account.move.reversal'].with_context(active_ids=self.invoice.ids).create({
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason',
            'refund_method': 'cancel',
        })
        reversal = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertInvoiceValues(reverse_move, [
            {
                **self.product_line_vals_1,
                'debit': 1000.0,
                'credit': 0.0,
            },
            {
                **self.product_line_vals_2,
                'debit': 200.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_1,
                'debit': 180.0,
                'credit': 0.0,
            },
            {
                **self.tax_line_vals_2,
                'debit': 30.0,
                'credit': 0.0,
            },
            {
                **self.term_line_vals_1,
                'name': self.invoice.name,
                'debit': 0.0,
                'credit': 1410.0,
            },
        ], {
            **self.move_vals,
            'date': move_reversal.date,
            'state': 'posted',
            'ref': 'Reversal of: %s, %s' % (self.invoice.name, move_reversal.reason),
            'invoice_payment_state': 'paid',
        })

    def test_out_invoice_create_1(self):
        # Test creating an account_move with the least information.
        move = self.env['account.move'].create({
            'type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-01-01'),
            'currency_id': self.currency_data['currency'].id,
            'invoice_payment_term_id': self.pay_terms_a.id,
            'invoice_line_ids': [
                (0, None, self.product_line_vals_1),
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

    def test_out_invoice_write_1(self):
        # Test creating an account_move with the least information.
        move = self.env['account.move'].create({
            'type': 'out_invoice',
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

    def test_out_invoice_post_1(self):
        frozen_today = fields.Date.today()
        with patch.object(fields.Date, 'today', lambda *args, **kwargs: frozen_today), patch.object(fields.Date, 'context_today', lambda *args, **kwargs: frozen_today):
            # Create an invoice with rate 1/3.
            move = self.env['account.move'].create({
                'type': 'out_invoice',
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

            move.post()

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
                'invoice_payment_ref': move.name,
                'currency_id': self.currency_data['currency'].id,
                'date': frozen_today,
                'invoice_date': frozen_today,
                'invoice_date_due': frozen_today,
                'amount_tax': 230.0,
                'amount_total': 1430.0,
            })

    def test_out_invoice_switch_out_refund_1(self):
        # Test creating an account_move with an out_invoice_type and switch it in an out_refund.
        move = self.env['account.move'].create({
            'type': 'out_invoice',
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

        self.assertRecordValues(move, [{'type': 'out_refund'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1000.0,
                'debit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'debit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'debit': 100.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 30.0,
                'debit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1430.0,
                'credit': 715.0,
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
            'type': 'out_invoice',
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
                'amount_currency': -1000.0,
                'debit': 500.0,
                'quantity': -1.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'debit': 100.0,
                'quantity': -1.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -200.0,
                'debit': 100.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -30.0,
                'debit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1430.0,
                'credit': 715.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'amount_tax' : -self.move_vals['amount_tax'],
            'amount_total' : -self.move_vals['amount_total'],
            'amount_untaxed' : -self.move_vals['amount_untaxed'],
        })

        move.action_switch_invoice_into_refund_credit_note()

        self.assertRecordValues(move, [{'type': 'out_refund'}])
        self.assertInvoiceValues(move, [
            {
                **self.product_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1000.0,
                'debit': 500.0,
            },
            {
                **self.product_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'debit': 100.0,
            },
            {
                **self.tax_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 200.0,
                'debit': 100.0,
            },
            {
                **self.tax_line_vals_2,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 30.0,
                'debit': 15.0,
            },
            {
                **self.term_line_vals_1,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -1430.0,
                'credit': 715.0,
            },
        ], {
            **self.move_vals,
            'currency_id': self.currency_data['currency'].id,
            'amount_tax' : self.move_vals['amount_tax'],
            'amount_total' : self.move_vals['amount_total'],
            'amount_untaxed' : self.move_vals['amount_untaxed'],
        })