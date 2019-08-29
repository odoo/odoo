# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import fields
from odoo.tests import common, tagged, Form


@tagged('post_install', '-at_install')
class TestSaleExpectedDate(common.TransactionCase):

    def test_sale_order_expected_date(self):
        """ Test expected date and effective date of Sales Orders """
        Product = self.env['product.product']

        product_A = Product.create({
            'name': 'Product A',
            'type': 'product',
            'sale_delay': 5,
            'uom_id': 1,
        })
        product_B = Product.create({
            'name': 'Product B',
            'type': 'product',
            'sale_delay': 10,
            'uom_id': 1,
        })
        product_C = Product.create({
            'name': 'Product C',
            'type': 'product',
            'sale_delay': 15,
            'uom_id': 1,
        })

        self.env['stock.quant']._update_available_quantity(product_A, self.env.ref('stock.stock_location_stock'), 10)
        self.env['stock.quant']._update_available_quantity(product_B, self.env.ref('stock.stock_location_stock'), 10)
        self.env['stock.quant']._update_available_quantity(product_C, self.env.ref('stock.stock_location_stock'), 10)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.ref('base.res_partner_3'),
            'picking_policy': 'direct',
            'order_line': [
                (0, 0, {'name': product_A.name, 'product_id': product_A.id, 'customer_lead': product_A.sale_delay, 'product_uom_qty': 5}),
                (0, 0, {'name': product_B.name, 'product_id': product_B.id, 'customer_lead': product_B.sale_delay, 'product_uom_qty': 5}),
                (0, 0, {'name': product_C.name, 'product_id': product_C.id, 'customer_lead': product_C.sale_delay, 'product_uom_qty': 5})
            ],
        })

        # if Shipping Policy is set to `direct`(when SO is in draft state) then expected date should be
        # current date + shortest lead time from all of it's order lines
        expected_date = fields.Datetime.now() + timedelta(days=5)
        self.assertAlmostEqual(expected_date, sale_order.expected_date,
            msg="Wrong expected date on sale order!", delta=timedelta(seconds=1))

        # if Shipping Policy is set to `one`(when SO is in draft state) then expected date should be
        # current date + longest lead time from all of it's order lines
        sale_order.write({'picking_policy': 'one'})
        expected_date = fields.Datetime.now() + timedelta(days=15)
        self.assertAlmostEquals(expected_date, sale_order.expected_date,
            msg="Wrong expected date on sale order!", delta=timedelta(seconds=1))

        sale_order.action_confirm()

        # Setting confirmation date of SO to 5 days from today so that the expected/effective date could be checked
        # against real confirmation date
        confirm_date = fields.Datetime.now() + timedelta(days=5)
        sale_order.write({'date_order': confirm_date})

        # if Shipping Policy is set to `one`(when SO is confirmed) then expected date should be
        # SO confirmation date + longest lead time from all of it's order lines
        expected_date = confirm_date + timedelta(days=15)
        self.assertAlmostEqual(expected_date, sale_order.expected_date,
            msg="Wrong expected date on sale order!", delta=timedelta(seconds=1))

        # if Shipping Policy is set to `direct`(when SO is confirmed) then expected date should be
        # SO confirmation date + shortest lead time from all of it's order lines
        sale_order.write({'picking_policy': 'direct'})
        expected_date = confirm_date + timedelta(days=5)
        self.assertAlmostEqual(expected_date, sale_order.expected_date,
            msg="Wrong expected date on sale order!", delta=timedelta(seconds=1))

        # Check effective date, it should be date on which the first shipment successfully delivered to customer
        picking = sale_order.picking_ids[0]
        for ml in picking.move_line_ids:
            ml.qty_done = ml.product_uom_qty
        picking.action_done()
        self.assertEquals(picking.state, 'done', "Picking not processed correctly!")

def test_sale_order_expected_date_manual(self):
        """ Check the behaviour of the field expected date
        """

        # Create a partner
        partner_a = self.env['res.partner'].create({'name': 'Moi'})

        # Create 2 products with stock available
        product_a = self.env['product.product'].create({'name': 'Des grosses Houppes'})
        product_b = self.env['product.product'].create({'name': 'Des petites Houppes'})

        # Sell those 2 products
        so = self.env['sale.order'].create({
            'partner_id': partner_a.id,
            'order_line': [
                (0, 0, {'name': product_a.name, 'product_id': product_a.id, 'product_uom_qty': 1, 'customer_lead': 1}),
                (0, 0, {'name': product_b.name, 'product_id': product_b.id, 'product_uom_qty': 1, 'customer_lead': 2}),
            ],
        })
        # The so should not be set as manual expected date by default
        self.assertFalse(so.is_expected_date_manual)

        # Change the expected date of the sale order
        new_date = fields.Datetime.now() + timedelta(days=2)
        f = Form(so)
        f.expected_date = new_date
        so = f.save()

        # Check the so is now set as manual expected date
        self.assertTrue(so.is_expected_date_manual)

        # Force recompute to cancel the manual expected date
        so.action_refresh_expected_date()

        # Make sure the date was recomputed
        self.assertFalse(so.expected_date_manual)

        # Change the expected date of the sale order
        new_date = fields.Datetime.now() + timedelta(days=7)
        f = Form(so)
        f.expected_date = new_date
        so = f.save()

        # The so's expected date should now bet set as manual again
        self.assertEquals(so.expected_date_manual, new_date)
        self.assertTrue(so.is_expected_date_manual)

        # Change the picking policy
        f = Form(so)
        f.picking_policy = 'one'
        so = f.save()

        # The SO should not be set as manual expected date anymore
        self.assertFalse(so.is_expected_date_manual)

        so.action_confirm()

        # Try to change the expected date of the sale order again, should raise
        # an error as once confirmed the SO's expected date should be readonly
        new_date = fields.Datetime.now() + timedelta(weeks=1)
        with self.assertRaises(AssertionError):
            f = Form(so)
            f.expected_date = new_date
            so = f.save()