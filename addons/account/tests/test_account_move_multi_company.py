# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMoveMultiCompany(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.product = cls.env['product.product'].create({
            'name': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'company_id': False,
        })

        cls.partner = cls.env['res.partner'].create({
            'name': 'partner',
            'company_id': False,
        })

        cls.product.with_company(cls.company_data['company']).write({
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
        })

        cls.partner.with_company(cls.company_data['company']).write({
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
        })

        cls.product.with_company(cls.company_data_2['company']).write({
            'property_account_income_id': cls.company_data_2['default_account_revenue'].id,
        })

        cls.partner.with_company(cls.company_data_2['company']).write({
            'property_account_receivable_id': cls.company_data_2['default_account_receivable'].id,
        })

    def _test_invoice_multi_company(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product.id,
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
            'journal_id': self.company_data_2['default_journal_sale'].id,
            'company_id': self.company_data_2['company'].id,
            'amount_untaxed': 1000.0,
            'amount_total': 1000.0,
        })

    def test_invoice_create_multi_company(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company_data_2['company'].id,
            'invoice_date': '2017-01-01',
            'partner_id': self.partner.id,
            'invoice_line_ids': [(0, 0, {'product_id': self.product.id})],
        })
        self._test_invoice_multi_company(invoice)

    def test_invoice_onchange_multi_company(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.journal_id = self.company_data_2['default_journal_sale']
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product
            line_form.tax_ids.clear()
        invoice = move_form.save()
        self._test_invoice_multi_company(invoice)
