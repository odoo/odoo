# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_business_taxes_computation import AccountTestBusinessTaxesComputation
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestInvoiceTaxesComputation(AccountTestBusinessTaxesComputation):

    @classmethod
    def _create_business_object(self, line_vals):
        return self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-01 00:00:00',
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': vals['price_unit'],
                'tax_id': [(6, 0, vals['tax_ids'])],
            }) for vals in line_vals],
        })

    @classmethod
    def _get_totals(cls, business_object):
        return {
            'amount_untaxed': business_object.amount_untaxed,
            'amount_tax': business_object.amount_tax,
        }
