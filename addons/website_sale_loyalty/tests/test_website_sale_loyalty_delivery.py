# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import HttpCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestWebsiteSaleDelivery(HttpCase):

    def setUp(self):
        super().setUp()

        self.env['product.product'].create({
            'name': 'Acoustic Bloc Screens',
            'list_price': 2950.0,
            'website_published': True,
        })

        self.gift_card = self.env['product.product'].create({
            'name': 'TEST - Gift Card',
            'list_price': 50,
            'type': 'service',
            'is_published': True,
            'sale_ok': True,
            'taxes_id': False,
        })

        # Disable any other program
        self.env['loyalty.program'].search([]).write({'active': False})

        self.gift_card_program = self.env['loyalty.program'].create({
            'name': 'Gift Cards',
            'program_type': 'gift_card',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'reward_point_split': True,
                'product_ids': self.gift_card,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
                'description': 'PAY WITH GIFT CARD',
            })],
        })

        # Create a gift card to be used
        self.env['loyalty.card'].create({
            'program_id': self.gift_card_program.id,
            'points': 50000,
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
        # Get admin user and set his preferred shipping method to normal delivery
        # This test also tests that we can indeed pay delivery fees with gift cards/ewallet
        admin_user = self.env.ref('base.user_admin')
        admin_user.partner_id.write({'property_delivery_carrier_id': self.normal_delivery.id})

        self.start_tour("/", 'shop_sale_loyalty_delivery', login='admin')
