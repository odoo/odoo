# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockDeliveryController(PaymentCommon, WebsiteSaleCommon):

    def test_validate_payment_with_no_available_delivery_method(self):
        """
        An error should be raised if you try to validate an order with a storable
        product without any delivery method available
        """
        storable_product = self.env['product.product'].create([{
            'name': 'Storable Product',
            'sale_ok': True,
            'is_storable': True,
            'website_published': True,
        }])
        carriers = self.env['delivery.carrier'].search([])
        carriers.write({'website_published': False})

        DeliveryController = Delivery()
        with MockRequest(self.env, website=self.website, sale_order_id=self.empty_cart.id):
            DeliveryController.cart_update_json(product_id=storable_product.id, add_qty=1)
            with self.assertRaises(ValidationError):
                DeliveryController.shop_payment_validate()
