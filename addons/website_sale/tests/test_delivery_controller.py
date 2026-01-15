# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleDeliveryController(PaymentCommon, WebsiteSaleCommon):
    def setUp(self):
        super().setUp()
        self.Controller = Delivery()

    # test that changing the carrier while there is a pending transaction raises an error
    def test_controller_change_carrier_when_transaction(self):
        website = self.website.with_env(self.env)
        self.empty_cart.transaction_ids = self._create_transaction(flow='redirect', state='pending')
        with MockRequest(website.env, website=website, sale_order_id=self.empty_cart.id) as request, self.assertRaises(UserError):
            request.cart = self.empty_cart
            self.Controller.shop_set_delivery_method(dm_id=self.free_delivery.id)

    # test that changing the carrier while there is a draft transaction doesn't raise an error
    def test_controller_change_carrier_when_draft_transaction(self):
        website = self.website.with_env(self.env)
        self.empty_cart.transaction_ids = self._create_transaction(flow='redirect', state='draft')
        with MockRequest(website.env, website=website, sale_order_id=self.empty_cart.id):
            self.Controller.shop_set_delivery_method(dm_id=self.free_delivery.id)

    def test_available_methods(self):
        self.env['delivery.carrier'].search([]).action_archive()
        self.product_delivery_poste = self.env['product.product'].create({
            'name': 'The Poste',
            'type': 'service',
            'categ_id': self.env.ref('delivery.product_category_deliveries').id,
            'sale_ok': False,
            'purchase_ok': False,
            'list_price': 20.0,
        })
        self.env['delivery.carrier'].create([
            {
                'name': 'Over 300',
                'delivery_type': 'base_on_rule',
                'product_id': self.product_delivery_poste.id,
                'website_published': True,
                'price_rule_ids': [
                    Command.create({
                        'operator': '>=',
                        'max_value': 300,
                        'variable': 'price',
                    }),
                ],
            }, {
                'name': 'Under 300',
                'delivery_type': 'base_on_rule',
                'product_id': self.product_delivery_poste.id,
                'website_published': True,
                'price_rule_ids': [
                    Command.create({
                        'operator': '<',
                        'max_value': 300,
                        'variable': 'price',
                    }),
                ],
            }, {
                'name': 'No rules',
                'delivery_type': 'base_on_rule',
                'product_id': self.product_delivery_poste.id,
                'website_published': True,
            }, {
                'name': 'Fixed',
                'product_id': self.product_delivery_poste.id,
                'website_published': True,
            },
        ])

        self.assertEqual(
            self.empty_cart._get_delivery_methods().mapped('name'), ['Under 300', 'Fixed']
        )
