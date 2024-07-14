# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_taxcloud.tests.common import TestAccountTaxcloudCommon
from odoo.tests.common import HttpCase
from odoo.tests import tagged

@tagged("external")
class TestWebsiteSaleGiftCard(TestAccountTaxcloudCommon, HttpCase):

    def setUp(self):
        super().setUp()

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

        self.product_delivery_normal = self.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
            'list_price': 10.0,
        })

        self.normal_delivery = self.env['delivery.carrier'].create({
            'name': 'Normal Delivery Charges',
            'fixed_price': 5,
            'delivery_type': 'fixed',
            'website_published': True,
            'product_id': self.product_delivery_normal.id,
        })

    def test_01_gift_card_with_taxcloud(self):
        #get admin user
        self.admin_user = self.env.ref('base.user_admin')
        self.admin_user.city = 'Zanesville'
        self.admin_user.state_id = self.env.ref("base.state_us_30").id
        self.admin_user.country_id = self.env.ref('base.us')
        self.admin_user.zip = '43071'
        self.admin_user.street = '226 Adair Ave'
        self.admin_user.property_account_position_id = self.fiscal_position

        self.start_tour("/", 'shop_sale_giftcard', login='admin')
