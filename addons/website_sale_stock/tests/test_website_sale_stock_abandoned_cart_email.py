# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.website_sale.tests.test_website_sale_cart_abandoned import TestWebsiteSaleCartAbandonedCommon
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockAbandonedCartEmail(TestWebsiteSaleCartAbandonedCommon):
    def test_website_sale_stock_abandoned_cart_email(self):
        """Make sure the send_abandoned_cart_email method sends the correct emails."""

        website = self.env['website'].get_current_website()
        website.send_abandoned_cart_email = True

        storable_product_template = self.env['product.template'].create({
            'name': 'storable_product_template',
            'type': 'product',
            'allow_out_of_stock_order': False
        })
        storable_product_product = storable_product_template.product_variant_id
        order_line = [[0, 0, {
            'name': 'The Product',
            'product_id': storable_product_product.id,
            'product_uom_qty': 1,
        }]]
        customer = self.env['res.partner'].create({
            'name': 'a',
            'email': 'a@example.com',
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': customer.id,
            'website_id': website.id,
            'state': 'draft',
            'date_order': (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)) - relativedelta(
                minutes=1),
            'order_line': order_line
        })

        self.assertFalse(self.send_mail_patched(sale_order.id))
        # Reset cart_recovery sent state
        sale_order.cart_recovery_email_sent = False

        # Replenish the stock of the product
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': storable_product_product.id,
            'inventory_quantity': 10.0,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
        }).action_apply_inventory()

        self.assertTrue(self.send_mail_patched(sale_order.id))

        company = self.env['res.company'].create({'name': 'Company C'})
        self.env.user.company_id = company
        website_1 = self.env['website'].create({
            'name': 'Website Company C',
            'company_id': company.id,
            'send_abandoned_cart_email': True,
        })
        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', company.id)])
        product = self.env['product.product'].create({
            'name': 'Product',
            'allow_out_of_stock_order': False,
            'type': 'product',
            'default_code': 'E-COM1',
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create([{
            'product_id': product.id,
            'inventory_quantity': 25.0,
            'location_id': warehouse_1.lot_stock_id.id,
        }]).action_apply_inventory()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'website_id': website_1.id,
            'date_order': (datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)) - relativedelta(
                minutes=1),
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 5,
                }),
            ],
        })

        self.assertTrue(self.send_mail_patched(sale_order.id))
