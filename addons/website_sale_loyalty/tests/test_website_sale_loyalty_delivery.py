# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import HttpCase
from odoo.tests import tagged

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged('post_install', '-at_install')
class TestWebsiteSaleDelivery(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.ref('base.user_admin').write({
            'name': 'Mitchell Admin',
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_39').id,
        })

        # Disable mail logic
        cls.env = cls.env['base'].with_context(**DISABLED_MAIL_CONTEXT).env
        # Disable existing reward programs
        cls.env['loyalty.program'].search([]).active = False
        # Remove taxes completely during the following tests.
        cls.env.companies.account_sale_tax_id = False

        cls.env['product.product'].create({
            'name': "Plumbus",
            'list_price': 100.0,
            'website_published': True,
        })

        product_gift_card = cls.env['product.product'].create({
            'name': 'TEST - Gift Card',
            'list_price': 50,
            'type': 'service',
            'is_published': True,
            'sale_ok': True,
        })

        gift_card_program = cls.env['loyalty.program'].create({
            'name': 'Gift Cards',
            'program_type': 'gift_card',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [Command.create({
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'reward_point_split': True,
                'product_ids': product_gift_card.ids,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
                'description': 'PAY WITH GIFT CARD',
            })],
        })

        # Create a gift card to be used
        cls.env['loyalty.card'].create({
            'program_id': gift_card_program.id,
            'points': 50000,
            'code': '123456',
        })

        # Create a 50% discount on order code
        cls.env['loyalty.program'].create({
            'name': "50% discount code",
            'program_type': 'promo_code',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'code': "test-50pc",
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 50.0,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })

        ewallet_program = cls.env['loyalty.program'].create({
            'name': "eWallet",
            'program_type': 'ewallet',
            'applies_on': 'future',
            'trigger': 'auto',
            'reward_ids': [Command.create({
                'description': "Pay with eWallet",
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
            })],
        })

        cls.ewallet = cls.env['loyalty.card'].create({
            'program_id': ewallet_program.id,
            'points': 6e66,
            'code': 'infinite-money-glitch',
        })

        delivery_product1, delivery_product2 = cls.env['product.product'].create([{
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
        }, {
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
        }])

        cls.normal_delivery, cls.normal_delivery2 = cls.env['delivery.carrier'].create([{
            'name': 'delivery1',
            'fixed_price': 5,
            'delivery_type': 'fixed',
            'website_published': True,
            'product_id': delivery_product1.id,
        }, {
            'name': 'delivery2',
            'fixed_price': 10,
            'delivery_type': 'fixed',
            'website_published': True,
            'product_id': delivery_product2.id,
        }])

    def test_shop_sale_gift_card_keep_delivery(self):
        # Get admin user and set his preferred shipping method to normal delivery
        # This test also tests that we can indeed pay delivery fees with gift cards/ewallet
        admin_user = self.env.ref('base.user_admin')
        admin_user.partner_id.write({'property_delivery_carrier_id': self.normal_delivery.id})

        self.start_tour("/", 'shop_sale_loyalty_delivery', login='admin')

    def test_shipping_discount(self):
        """
        Check display of shipping discount promotion on checkout,
        combined with another reward (eWallet).
        """
        self.env['loyalty.program'].create({
            'name': "Buy 3, get up to $75 discount on shipping",
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_qty': 3.0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'shipping',
                'discount_max_amount': 75.0,
            })],
        })
        self.normal_delivery.fixed_price = 100
        self.start_tour("/", 'check_shipping_discount', login="admin")

    def test_update_shipping_after_discount(self):
        """
        Verify that after applying a discount code, any `free_over` shipping gets recalculated.
        """
        self.normal_delivery.write({'free_over': True, 'amount': 75.0})
        self.start_tour("/shop", 'update_shipping_after_discount', login="admin")
