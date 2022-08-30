# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import HttpCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestWebsiteSaleDelivery(HttpCase):

    def setUp(self):
        super().setUp()

        self.gift_card = self.env['gift.card'].create({
            'initial_amount': 10000,
            'code': '123456',
        })

        self.product_delivery_normal1 = self.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
        })

        self.product_delivery_normal2 = self.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
        })

        self.normal_delivery = self.env['delivery.carrier'].create({
            'name': 'delivery1',
            'fixed_price': 5,
            'delivery_type': 'fixed',
            'website_published': True,
            'product_id': self.product_delivery_normal1.id,
        })

        self.normal_delivery2 = self.env['delivery.carrier'].create({
            'name': 'delivery2',
            'fixed_price': 10,
            'delivery_type': 'fixed',
            'website_published': True,
            'product_id': self.product_delivery_normal2.id,
        })

    def test_shop_sale_gift_card_keep_delivery(self):

        #get admin user and set his preferred shipping method to normal delivery
        admin_user = self.env.ref('base.user_admin')
        admin_user.partner_id.write({'property_delivery_carrier_id': self.normal_delivery.id})

        self.start_tour("/", 'shop_sale_giftcard_delivery', login='admin')
