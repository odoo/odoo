# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.website_sale_stock.tests.test_website_sale_stock_abandoned_cart_email import TestWebsiteSaleCartAbandonedCommon
from odoo.tests.common import tagged

@tagged('post_install', '-at_install')

class TestWebsiteSaleStockRentingAbandonedCartEmail(TestWebsiteSaleCartAbandonedCommon):
    def test_website_sale_stock_renting_abandoned_cart_email(self):
        """Make sure the send_abandoned_cart_email method sends the correct emails."""

        website = self.env['website'].get_current_website()
        website.send_abandoned_cart_email = True

        renting_product_template = self.env['product.template'].create({
            'name': 'renting_product_template',
            'type': 'product',
            'rent_ok': True,
            'allow_out_of_stock_order': False
        })
        renting_product_product = renting_product_template.product_variant_id
        now = fields.Datetime.now()
        order_line = [[0, 0, {
            'product_id': renting_product_product.id,
            'product_uom_qty': 1,
        }]]
        customer = self.env['res.partner'].create({
            'name': 'a',
            'email': 'a@example.com',
        })
        order_vals = {
            'partner_id': customer.id,
            'website_id': website.id,
            'state': 'draft',
            'date_order': now - relativedelta(hours=website.cart_abandoned_delay, minutes=1),
            'order_line': order_line,
            'rental_start_date': now - relativedelta(hours=website.cart_abandoned_delay, minutes=1),
            'rental_return_date': now + relativedelta(days=1),
        }
        abandoned_sale_order_with_not_available_rental = self.env['sale.order'].create(order_vals)
        abandoned_sale_order_with_not_available_rental.order_line.update({'is_rental': True})

        self.assertFalse(self.send_mail_patched(abandoned_sale_order_with_not_available_rental.id))
        # Reset cart_recovery sent state
        abandoned_sale_order_with_not_available_rental.cart_recovery_email_sent = False


        # Replenish the stock of the product
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': renting_product_product.id,
            'inventory_quantity': 1.0,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
        }).action_apply_inventory()

        self.assertTrue(self.send_mail_patched(abandoned_sale_order_with_not_available_rental.id))

        # Test if the email is not sent if the rental is not available anymore

        sale_order = self.env['sale.order'].create(order_vals)
        sale_order.order_line.update({'is_rental': True})
        sale_order.state = 'sale'

        sale_order2 = self.env['sale.order'].create(order_vals)
        sale_order2.order_line.update({'is_rental': True})

        self.assertFalse(self.send_mail_patched(sale_order2.id))
