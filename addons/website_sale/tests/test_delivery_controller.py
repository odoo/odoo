# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.fields import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.sale.tests.common import SaleCommon
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.controllers.delivery import Delivery



@tagged('post_install', '-at_install')
class TestWebsiteSaleDeliveryController(PaymentCommon, SaleCommon):
    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.Controller = Delivery()

    # test that changing the carrier while there is a pending transaction raises an error
    def test_controller_change_carrier_when_transaction(self):
        with MockRequest(self.env, website=self.website):
            order = self.website.sale_get_order(force_create=True)
            order.transaction_ids = self._create_transaction(flow='redirect', state='pending')
            with self.assertRaises(UserError), patch(
                'odoo.addons.website_sale.models.website.Website.sale_get_order',
                return_value=order,
            ):  # Patch to retrieve the order even if it is linked to a pending transaction.
                self.Controller.shop_set_delivery_method(dm_id='1')

    # test that changing the carrier while there is a draft transaction doesn't raise an error
    def test_controller_change_carrier_when_draft_transaction(self):
        with MockRequest(self.env, website=self.website):
            order = self.website.sale_get_order(force_create=True)
            order.transaction_ids = self._create_transaction(flow='redirect', state='draft')
            self.Controller.shop_set_delivery_method(dm_id='1')

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
            self.empty_order._get_delivery_methods().mapped('name'), ['Under 300', 'Fixed']
        )
