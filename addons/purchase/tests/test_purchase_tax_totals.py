# -*- coding: utf-8 -*-
from odoo.addons.account.tests.test_invoice_tax_totals import TestTaxTotals
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class PurchaseTestTaxTotals(TestTaxTotals):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.po_product = cls.env['product.product'].create({
            'name': 'Odoo course',
            'type': 'service',
        })

    def _create_document_for_tax_totals_test(self, lines_data):
        # Overridden in order to run the inherited tests with purchase.order's
        # tax_totals_json field instead of account.move's

        lines_vals = [
            (0, 0, {
                'name': 'test',
                'product_id': self.po_product.id,
                'product_qty': 1,
                'product_uom': self.po_product.uom_po_id.id,
                'price_unit': amount,
                'taxes_id': [(6, 0, taxes.ids)],
            })
        for amount, taxes in lines_data]

        return self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': lines_vals,
        })
