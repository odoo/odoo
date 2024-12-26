# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.website_sale_loyalty.controllers.delivery import WebsiteSaleLoyaltyDelivery


@tagged('post_install', '-at_install')
class TestWebsiteSaleDelivery(HttpCase, WebsiteSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Controller = WebsiteSaleLoyaltyDelivery()

        # Disable mail logic
        cls.env = cls.env['base'].with_context(**DISABLED_MAIL_CONTEXT).env
        # Disable existing pricelists
        cls.env['product.pricelist'].with_context(active_test=False).search([]).unlink()
        # Disable existing reward programs
        cls.env['loyalty.program'].search([]).active = False
        # Remove taxes completely during the following tests.
        cls.env.companies.account_sale_tax_id = False

        cls.partner_admin = cls.env.ref('base.partner_admin')
        cls.partner_admin.write(cls.dummy_partner_address_values)

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

        cls.env['loyalty.card'].create({
            'program_id': ewallet_program.id,
            'partner_id': cls.partner_admin.id,
            'points': 1000000,
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
        self.partner_admin.property_delivery_carrier_id = self.normal_delivery
        self.start_tour("/", 'shop_sale_loyalty_delivery', login='admin')

    def test_shipping_discount(self):
        """
        Check display of shipping discount promotion on checkout,
        combined with another reward (eWallet).
        """
        self.env['loyalty.program'].create({
            'name': "Buy 3, get up to $6 discount on shipping!",
            'program_type': 'promotion',
            'applies_on': 'current',
            'trigger': 'auto',
            'rule_ids': [Command.create({
                'minimum_qty': 3.0,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'shipping',
                'discount_max_amount': 6.0,
            })],
        })
        self.start_tour("/", 'check_shipping_discount', login="admin")

    def test_update_shipping_after_discount(self):
        """
        Verify that after applying a discount code, any `free_over` shipping gets recalculated.
        """
        self.normal_delivery.write({'free_over': True, 'amount': 75.0})
        self.start_tour("/shop", 'update_shipping_after_discount', login="admin")

    def test_express_checkout_shipping_discount(self):
        """
        Check display of shipping discount promotion in express checkout form by ensuring is present
        in the values returned to the form.
        """
        # Create a discount code
        program = self.env['loyalty.program'].sudo().create({
            'name': 'Free Shipping',
            'program_type': 'promo_code',
            'rule_ids': [
                Command.create({
                    'code': "FREE",
                    'minimum_amount': 0,
                })
            ],
            'reward_ids': [
                Command.create({
                    'reward_type': 'shipping',
                    'discount_max_amount': 6.0,
                })
            ]
        })

        # Apply discount
        self.cart._try_apply_code("FREE")
        self.cart._apply_program_reward(program.reward_ids, program.coupon_ids)

        with MockRequest(self.env, sale_order_id=self.cart.id, website=self.website):
            result = self.Controller.shop_set_delivery_method(self.normal_delivery2.id)
        self.assertEqual(result['delivery_discount_minor_amount'], -600)
