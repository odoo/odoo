# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_savepoint import AccountingSavepointCase
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from odoo import fields

import logging

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class InvoiceTestCommon(AccountingSavepointCase):

    @classmethod
    def setUpClass(cls):
        super(InvoiceTestCommon, cls).setUpClass()

        # ==== Taxes ====
        cls.tax_sale_a = cls.company_data['default_tax_sale']
        cls.tax_sale_b = cls.company_data['default_tax_sale'].copy()
        cls.tax_purchase_a = cls.company_data['default_tax_purchase']
        cls.tax_purchase_b = cls.company_data['default_tax_purchase'].copy()
        cls.tax_armageddon = cls.setup_armageddon_tax('complex_tax', cls.company_data)

        # ==== Products ====
        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
            'supplier_taxes_id': [(6, 0, cls.tax_purchase_a.ids)],
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'product_b',
            'uom_id': cls.env.ref('uom.product_uom_dozen').id,
            'lst_price': 200.0,
            'standard_price': 160.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].copy().id,
            'property_account_expense_id': cls.company_data['default_account_expense'].copy().id,
            'taxes_id': [(6, 0, (cls.tax_sale_a + cls.tax_sale_b).ids)],
            'supplier_taxes_id': [(6, 0, (cls.tax_purchase_a + cls.tax_purchase_b).ids)],
        })

        # ==== Fiscal positions ====
        cls.fiscal_pos_a = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_sale_a.id,
                    'tax_dest_id': cls.tax_sale_b.id,
                }),
                (0, None, {
                    'tax_src_id': cls.tax_purchase_a.id,
                    'tax_dest_id': cls.tax_purchase_b.id,
                }),
            ],
            'account_ids': [
                (0, None, {
                    'account_src_id': cls.product_a.property_account_income_id.id,
                    'account_dest_id': cls.product_b.property_account_income_id.id,
                }),
                (0, None, {
                    'account_src_id': cls.product_a.property_account_expense_id.id,
                    'account_dest_id': cls.product_b.property_account_expense_id.id,
                }),
            ],
        })

        # ==== Payment terms ====
        cls.pay_terms_a = cls.env.ref('account.account_payment_term_immediate')
        cls.pay_terms_b = cls.env['account.payment.term'].create({
            'name': '30% Advance End of Following Month',
            'note': 'Payment terms: 30% Advance End of Following Month',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 30.0,
                    'sequence': 400,
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
                (0, 0, {
                    'value': 'balance',
                    'value_amount': 0.0,
                    'sequence': 500,
                    'days': 31,
                    'option': 'day_following_month',
                }),
            ],
        })

        # ==== Partners ====
        cls.partner_a = cls.env['res.partner'].create({
            'name': 'partner_a',
            'property_payment_term_id': cls.pay_terms_a.id,
            'property_supplier_payment_term_id': cls.pay_terms_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': False,
        })
        cls.partner_b = cls.env['res.partner'].create({
            'name': 'partner_b',
            'property_payment_term_id': cls.pay_terms_b.id,
            'property_supplier_payment_term_id': cls.pay_terms_b.id,
            'property_account_position_id': cls.fiscal_pos_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].copy().id,
            'property_account_payable_id': cls.company_data['default_account_payable'].copy().id,
            'company_id': False,
        })

        # ==== Cash rounding ====
        cls.cash_rounding_a = cls.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'account_id': cls.company_data['default_account_revenue'].copy().id,
            'rounding_method': 'UP',
        })
        cls.cash_rounding_b = cls.env['account.cash.rounding'].create({
            'name': 'biggest_tax',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'DOWN',
        })

    @classmethod
    def init_invoice(cls, move_type):
        move_form = Form(cls.env['account.move'].with_context(default_type=move_type))
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.partner_id = cls.partner_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = cls.product_a
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = cls.product_b
        return move_form.save()

    def assertInvoiceValues(self, move, expected_lines_values, expected_move_values):
        def sort_lines(lines):
            return lines.sorted(lambda line: (line.exclude_from_invoice_tab, not bool(line.tax_line_id), line.name or '', line.balance))
        self.assertRecordValues(sort_lines(move.line_ids), expected_lines_values)
        self.assertRecordValues(sort_lines(move.invoice_line_ids), expected_lines_values[:len(move.invoice_line_ids)])
        self.assertRecordValues(move, [expected_move_values])
