# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged

from odoo.addons.website_sale.tests.test_website_sale_cart_abandoned import TestWebsiteSaleCartAbandonedCommon
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockAbandonedCartEmail(
    TestWebsiteSaleCartAbandonedCommon, WebsiteSaleStockCommon
):
    def test_website_sale_stock_abandoned_cart_email(self):
        """Make sure the send_abandoned_cart_email method sends the correct emails."""

        website = self.env['website'].get_current_website()
        website.send_abandoned_cart_email = True
        website.write(
            {
                "send_abandoned_cart_email_activation_time": (
                    datetime.utcnow() - relativedelta(hours=website.cart_abandoned_delay)
                )
                - relativedelta(minutes=10)
            }
        )

        storable_product_product = self._create_product()
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
        self._add_product_qty_to_wh(
            storable_product_product.id,
            10,
            self.env.user._get_default_warehouse_id().lot_stock_id.id,
        )

        self.assertTrue(self.send_mail_patched(sale_order.id))
