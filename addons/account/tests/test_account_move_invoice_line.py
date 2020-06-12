# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged, new_test_user
from odoo import fields
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestAccountMoveInvoiceLine(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Run tests with precision of price_unit / quantity set to 5.
        cls.env['decimal.precision'].search([('name', 'in', (
            cls.env['account.move.line']._fields['quantity']._digits,
            cls.env['account.move.line']._fields['price_unit']._digits,
        ))]).digits = 5
        
        cls.tax_5_5_price_include = cls.env['account.tax'].create({
            'name': 'Tax 5.5% price included',
            'amount': 5.5,
            'amount_type': 'percent',
            'price_include': True,
        })
        
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_receipt',
            'date': '2016-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
            })],
        })
        cls.line = cls.invoice.invoice_line_ids
        
        cls.expected_line_vals = {
            'name': cls.product_a.name,
            'product_id': cls.product_a.id,
            'account_id': cls.product_a.property_account_income_id.id,
            'partner_id': False,
            'product_uom_id': cls.product_a.uom_id.id,
            'quantity': 1.0,
            'discount': 0.0,
            'price_unit': 1000.0,
            'price_subtotal': 1000.0,
            'tax_ids': [],
            'tax_line_id': False,
            'currency_id': cls.company_data['currency'].id,
            'amount_currency': -1000.0,
            'debit': 0.0,
            'credit': 1000.0,
            'tax_exigible': True,
        }
            
    def test_invoice_line_no_modification(self):
        self.assertRecordValues(self.line, [self.expected_line_vals])
        
    def test_invoice_line_write_product_uom_id(self):
        dozen_uom = self.env.ref('uom.product_uom_dozen')
        self.invoice.write({
            'invoice_line_ids': [(1, self.line.id, {'product_uom_id': dozen_uom.id})],
        })

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'product_uom_id': dozen_uom.id,
            'price_unit': 12000.0,
            'price_subtotal': 12000.0,
            'credit': 12000.0,
            'amount_currency': -12000.0,
        }])

    def test_invoice_line_onchange_product_uom_id(self):
        dozen_uom = self.env.ref('uom.product_uom_dozen')
        with Form(self.invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.product_uom_id = dozen_uom

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'product_uom_id': dozen_uom.id,
            'price_unit': 12000.0,
            'price_subtotal': 12000.0,
            'credit': 12000.0,
            'amount_currency': -12000.0,
        }])
        
    def test_invoice_line_write_quantity(self):
        self.invoice.write({
            'invoice_line_ids': [(1, self.line.id, {'quantity': 0.12345})],
        })

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'quantity': 0.12345,
            'price_subtotal': 123.45,
            'credit': 123.45,
            'amount_currency': -123.45,
        }])

    def test_invoice_line_onchange_quantity(self):
        with Form(self.invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.quantity = 0.12345

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'quantity': 0.12345,
            'price_subtotal': 123.45,
            'credit': 123.45,
            'amount_currency': -123.45,
        }])
        
    def test_invoice_line_write_price_unit(self):
        self.invoice.write({
            'invoice_line_ids': [(1, self.line.id, {'price_unit': 0.98765})],
        })

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'price_unit': 0.98765,
            'price_subtotal': 0.99,
            'credit': 0.99,
            'amount_currency': -0.99,
        }])

    def test_invoice_line_onchange_price_unit(self):
        with Form(self.invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 0.98765

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'price_unit': 0.98765,
            'price_subtotal': 0.99,
            'credit': 0.99,
            'amount_currency': -0.99,
        }])

    def test_invoice_line_write_discount(self):
        self.invoice.write({
            'invoice_line_ids': [(1, self.line.id, {'discount': 50.0})],
        })

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'discount': 50.0,
            'price_subtotal': 500.0,
            'credit': 500.0,
            'amount_currency': -500.0,
        }])

        self.invoice.write({
            'invoice_line_ids': [(1, self.line.id, {'discount': 100.0})],
        })

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'discount': 100.0,
            'price_subtotal': 0.0,
            'credit': 0.0,
            'amount_currency': 0.0,
        }])

    def test_invoice_line_onchange_discount(self):
        with Form(self.invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.discount = 50.0

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'discount': 50.0,
            'price_subtotal': 500.0,
            'credit': 500.0,
            'amount_currency': -500.0,
        }])

        with Form(self.invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.discount = 100.0

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'discount': 100.0,
            'price_subtotal': 0.0,
            'credit': 0.0,
            'amount_currency': 0.0,
        }])

    def test_invoice_line_write_debit(self):
        self.invoice.write({
            'invoice_line_ids': [(1, self.line.id, {
                'debit': 0.12,
                'credit': 0.0,
            })],
        })

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'price_unit': -0.12,
            'discount': 0.0,
            'price_subtotal': -0.12,
            'debit': 0.12,
            'credit': 0.0,
            'amount_currency': 0.12,
        }])

    def test_invoice_line_onchange_debit(self):
        with Form(self.invoice) as move_form:
            index = [move_form._values['line_ids'][1] == self.line.id][0]
            with move_form.line_ids.edit(index) as line_form:
                line_form.debit = 0.12

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'price_unit': -0.12,
            'discount': 0.0,
            'price_subtotal': -0.12,
            'debit': 0.12,
            'credit': 0.0,
            'amount_currency': 0.12,
        }])

    def test_invoice_line_write_tax_ids(self):
        self.invoice.write({
            'invoice_line_ids': [(1, self.line.id, {
                'tax_ids': [(6, 0, self.tax_armageddon.ids)],
            })],
        })

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'price_subtotal': 833.33,
            'tax_ids': self.tax_armageddon.ids,
            'credit': 833.33,
            'amount_currency': -833.33,
            'tax_exigible': False,
        }])

    def test_invoice_line_onchange_tax_ids(self):
        with Form(self.invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.tax_ids.add(self.tax_armageddon)

        self.assertRecordValues(self.line, [{
            **self.expected_line_vals,
            'price_subtotal': 833.33,
            'tax_ids': self.tax_armageddon.ids,
            'credit': 833.33,
            'amount_currency': -833.33,
            'tax_exigible': False,
        }])

    def _test_invoice_line_price_unit_rounding_issue_nb_decimals(self, invoice):
        ''' Seek for rounding issue on the price_subtotal when dealing with a price_unit having more digits (5) than the
        foreign currency one (3).
        '''
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 1.0025,
            'price_subtotal': 1.003,
            'currency_id': self.currency_data['currency'].id,
            'amount_currency': -1.003,
            'debit': 0.0,
            'credit': 0.33,
        }])

    def test_invoice_line_create_price_unit_rounding_issue_nb_decimals(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_receipt',
            'date': '2016-01-01',
            'currency_id': self.currency_data['currency'].id,   # 3 decimal places
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 1.0025,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        self._test_invoice_line_price_unit_rounding_issue_nb_decimals(invoice)

    def test_invoice_line_write_price_unit_rounding_issue_nb_decimals(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_receipt',
            'date': '2016-01-01',
            'currency_id': self.currency_data['currency'].id,   # 3 decimal places
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 0.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        invoice.write({'invoice_line_ids': [(1, invoice.invoice_line_ids.id, {
            'price_unit': 1.0025,
        })]})
        self._test_invoice_line_price_unit_rounding_issue_nb_decimals(invoice)

    def test_invoice_line_onchange_price_unit_rounding_issue_nb_decimals(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_receipt'))
        move_form.date = fields.Date.from_string('2016-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.tax_ids.clear()
            line_form.name = 'test line'
            line_form.price_unit = 1.0025
            line_form.account_id = self.company_data['default_account_revenue']
        invoice = move_form.save()
        self._test_invoice_line_price_unit_rounding_issue_nb_decimals(invoice)
    
    def _test_invoice_line_tax_ids_rounding_issue_single_currency(self, invoice):
        ''' Seek for rounding issue in the price unit. Suppose a price_unit of 2300 with a 5.5% price-included tax
        applied on it.

        The computed balance will be computed as follow: 2300.0 / 1.055 = 2180.0948 ~ 2180.09.
        Since accounting / business fields are synchronized, the inverse computation will try to recompute the
        price_unit based on the balance: 2180.09 * 1.055 = 2299.99495 ~ 2299.99.

        This test ensures the price_unit is not overridden in such case.
        '''
        self.assertRecordValues(invoice.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 2300.0,
            'price_subtotal': 2180.09,
            'debit': 0.0,
            'credit': 2180.09,
        }])

    def test_invoice_line_create_tax_ids_rounding_issue_single_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_receipt',
            'date': '2016-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 2300.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [(6, 0, self.tax_5_5_price_include.ids)],
            })],
        })
        self._test_invoice_line_tax_ids_rounding_issue_single_currency(invoice)

    def test_invoice_line_write_tax_ids_rounding_issue_single_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_receipt',
            'date': '2016-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 2300.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        invoice.write({'invoice_line_ids': [(1, invoice.invoice_line_ids.id, {
            'tax_ids': [(6, 0, self.tax_5_5_price_include.ids)],
        })]})
        self._test_invoice_line_tax_ids_rounding_issue_single_currency(invoice)

    def test_invoice_line_onchange_tax_ids_rounding_issue_single_currency(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_receipt'))
        move_form.date = fields.Date.from_string('2016-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.tax_ids.clear()
            line_form.name = 'test line'
            line_form.price_unit = 2300.0
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.tax_ids.add(self.tax_5_5_price_include)
        invoice = move_form.save()
        self._test_invoice_line_tax_ids_rounding_issue_single_currency(invoice)

    def _test_invoice_line_tax_ids_rounding_issue_foreign_currency(self, invoice):
        ''' Same as above in a multi-currencies environment.'''

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'quantity': 1.0,
            'price_unit': 2300.0,
            'price_subtotal': 2180.095,
            'amount_currency': -2180.095,
            'currency_id': self.currency_data['currency'].id,
            'debit': 0.0,
            'credit': 726.7,
        }])

    def test_invoice_line_create_tax_ids_rounding_issue_foreign_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_receipt',
            'date': '2016-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 2300.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [(6, 0, self.tax_5_5_price_include.ids)],
            })],
        })
        self._test_invoice_line_tax_ids_rounding_issue_foreign_currency(invoice)

    def test_invoice_line_write_tax_ids_rounding_issue_foreign_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_receipt',
            'date': '2016-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'price_unit': 2300.0,
                'quantity': 1,
                'account_id': self.company_data['default_account_revenue'].id,
            })],
        })
        invoice.write({'invoice_line_ids': [(1, invoice.invoice_line_ids.id, {
            'tax_ids': [(6, 0, self.tax_5_5_price_include.ids)],
        })]})
        self._test_invoice_line_tax_ids_rounding_issue_foreign_currency(invoice)

    def test_invoice_line_onchange_tax_ids_rounding_issue_foreign_currency(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_receipt'))
        move_form.date = fields.Date.from_string('2016-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.tax_ids.clear()
            line_form.name = 'test line'
            line_form.price_unit = 2300.0
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.tax_ids.add(self.tax_5_5_price_include)
        invoice = move_form.save()
        self._test_invoice_line_tax_ids_rounding_issue_foreign_currency(invoice)
