# -*- coding: utf-8 -*-
from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestSaleTaxes(AccountTestInvoicingCommon):

    def test_taxes_round_globally(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'

        tax_10_1 = self.env['account.tax'].create({
            'name': 'tax_10_1',
            'amount_type': 'percent',
            'amount': 10,
        })
        tax_10_2 = self.env['account.tax'].create({
            'name': 'tax_10_2',
            'amount_type': 'percent',
            'amount': 10,
        })

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        so_form.date_order = fields.Date.from_string('2019-01-01')
        with so_form.order_line.new() as line:
            line.product_id = self.product_a
            line.price_unit = 0.05
            line.tax_id.clear()
            line.tax_id.add(tax_10_1)
            line.tax_id.add(tax_10_2)
        so = so_form.save()

        self.assertRecordValues(so, [{
            'amount_untaxed': 0.05,
            'amount_tax': 0.02,
            'amount_total': 0.07,
        }])
