# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMoveAnalytic(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.user.groups_id += cls.env.ref('analytic.group_analytic_accounting')
        cls.env.user.groups_id += cls.env.ref('analytic.group_analytic_tags')

        cls.analytic_tag = cls.env['account.analytic.tag'].create({
            'name': 'test_analytic_tag',
        })

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'test_analytic_account',
            'partner_id': cls.partner_a.id,
            'code': 'TEST'
        })

    def _test_analytic_on_base_not_on_tax(self, invoice):
        # The tax is not flagged as an analytic one. It should change nothing on the taxes.
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'tax_ids': self.product_a.taxes_id.ids,
                'tax_line_id': False,
                'debit': 0.0,
                'credit': 1000.0,
                'analytic_account_id': self.analytic_account.id,
                'analytic_tag_ids': self.analytic_tag.ids,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'debit': 0.0,
                'credit': 150.0,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': False,
                'debit': 1150.0,
                'credit': 0.0,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
        ], {
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        })

    def _test_analytic_on_base_and_on_tax(self, invoice):
        # The tax is flagged as an analytic one.
        # A new tax line must be generated.
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'tax_ids': self.product_a.taxes_id.ids,
                'tax_line_id': False,
                'debit': 0.0,
                'credit': 2000.0,
                'analytic_account_id': self.analytic_account.id,
                'analytic_tag_ids': self.analytic_tag.ids,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'debit': 0.0,
                'credit': 300.0,
                'analytic_account_id': self.analytic_account.id,
                'analytic_tag_ids': self.analytic_tag.ids,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': False,
                'debit': 2300.0,
                'credit': 0.0,
                'analytic_account_id': False,
                'analytic_tag_ids': [],
            },
        ], {
            'amount_untaxed': 2000.0,
            'amount_tax': 300.0,
            'amount_total': 2300.0,
        })

    def test_create_analytic_flow(self):
        self.product_a.taxes_id.analytic = False

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
                'analytic_account_id': self.analytic_account.id,
                'analytic_tag_ids': self.analytic_tag.ids,
            })],
        })

        self._test_analytic_on_base_not_on_tax(invoice)

        self.product_a.taxes_id.analytic = True

        # Trigger the recomputation of taxes.
        invoice.write({'invoice_line_ids': [(1, invoice.invoice_line_ids.id, {'price_unit': 2000.0})]})

        self._test_analytic_on_base_and_on_tax(invoice)

    def test_onchange_analytic_flow(self):
        self.product_a.taxes_id.analytic = False

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.analytic_account_id = self.analytic_account
            line_form.analytic_tag_ids.add(self.analytic_tag)
        invoice = move_form.save()

        self._test_analytic_on_base_not_on_tax(invoice)

        self.product_a.taxes_id.analytic = True

        # Trigger the recomputation of taxes.
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 2000.0

        self._test_analytic_on_base_and_on_tax(invoice)
