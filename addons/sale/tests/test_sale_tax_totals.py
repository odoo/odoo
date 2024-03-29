# -*- coding: utf-8 -*-
from odoo.addons.account.tests.test_invoice_tax_totals import TestTaxTotals
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class SaleTestTaxTotals(TestTaxTotals):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.so_product = cls.env['product.product'].create({
            'name': 'Odoo course',
            'type': 'service',
        })

    def _create_document_for_tax_totals_test(self, lines_data):
        # Overridden in order to run the inherited tests with sale.order's
        # tax_totals field instead of account.move's

        lines_vals = [
            (0, 0, {
                'name': 'test',
                'product_id': self.so_product.id,
                'price_unit': amount,
                'product_uom_qty': 1,
                'tax_id': [(6, 0, taxes.ids)],
            })
        for amount, taxes in lines_data]

        return self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': lines_vals,
        })
