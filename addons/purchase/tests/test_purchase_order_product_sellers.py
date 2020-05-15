# -*- coding: utf-8 -*-
from odoo.addons.account.tests.invoice_test_common import InvoiceTestCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestPurchaseOrderProductSellers(InvoiceTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product = cls.env['product.product'].create({
            'name': 'product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'standard_price': 100.0,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
        })

    def assertPoLineValues(self, seller_vals_list, expected_po_line_vals):
        ''' Helper to check the po line values with a specific setup of sellers set on the product.

        :param seller_vals_list:        The values to create the sellers (product.supplierinfo).
        :param expected_po_line_vals:   The expected values of the po line.
        '''

        self.product.write({
            'seller_ids': [(0, 0, seller_vals) for seller_vals in seller_vals_list],
        })

        with self.mocked_today('2019-01-01'):
            po_form = Form(self.env['purchase.order'])
            po_form.partner_id = self.partner_a
            po_form.date_order = fields.Date.from_string('2018-01-01')
            with po_form.order_line.new() as line_form:
                line_form.product_id = self.product
            purchase_order = po_form.save()

        self.assertRecordValues(purchase_order.order_line, [expected_po_line_vals])

    def test_no_matching_seller(self):
        self.assertPoLineValues([
            {
                'name': self.partner_b.id,
                'min_qty': 12.0,
            }
        ], {
            'product_qty': 0.0,
            'price_unit': 100.0,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'date_planned': fields.Datetime.from_string('2019-01-01 00:00:00'),
        })

    def test_seller_min_quantity_no_product(self):
        self.assertPoLineValues([
            {
                'name': self.partner_a.id,
                'product_id': False,
                'min_qty': 12.0,
                'price': 100.0,
            },
            {
                'name': self.partner_a.id,
                'product_id': False,
                'min_qty': 8.0,
                'price': 200.0,
            }
        ], {
            'product_qty': 8.0,
            'price_unit': 200.0,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'date_planned': fields.Datetime.from_string('2018-01-02 00:00:00'),
        })
