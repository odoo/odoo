# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.sale.tests.common import SaleCommon
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery, PaymentPortalDelivery
from odoo.addons.website.tools import MockRequest

@tagged('post_install', '-at_install')
class TestWebsiteSaleDeliveryController(PaymentCommon, SaleCommon):
    def setUp(self):
        super().setUp()
        self.website = self.env.ref('website.default_website')
        self.Controller = WebsiteSaleDelivery()

    # test that changing the carrier while there is a pending transaction raises an error
    def test_controller_change_carrier_when_transaction(self):
        with MockRequest(self.env, website=self.website):
            order = self.website.sale_get_order(force_create=True)
            order.transaction_ids = self._create_transaction(flow='redirect', state='pending')
            with self.assertRaises(UserError):
                with patch(
                    'odoo.addons.website_sale.models.website.Website.sale_get_order',
                    return_value=order,
                ):  # Patch to retrieve the order even if it is linked to a pending transaction.
                    self.Controller.update_eshop_carrier(carrier_id=1)

    # test that changing the carrier while there is a draft transaction doesn't raise an error
    def test_controller_change_carrier_when_draft_transaction(self):
        with MockRequest(self.env, website=self.website):
            order = self.website.sale_get_order(force_create=True)
            order.transaction_ids = self._create_transaction(flow='redirect', state='draft')
            self.Controller.update_eshop_carrier(carrier_id=1)

    def test_address_states(self):
        US = self.env.ref('base.us')
        MX = self.env.ref('base.mx')

        # Set all carriers to mexico
        self.env['delivery.carrier'].sudo().search([('website_published', '=', True)]).country_ids = [(6, 0, [MX.id])]

        # Create a new carrier to only one state in mexico
        self.env['delivery.carrier'].create({
                'name': "One_state",
                'product_id': self.env['product.product'].create({'name': "delivery product"}).id,
                'website_published': True,
                'country_ids': [(6, 0, [MX.id])],
                'state_ids': [(6, 0, [MX.state_ids.ids[0]])]
        })

        country_info = self.Controller.country_infos(country=MX, mode="shipping")
        self.assertEqual(len(country_info['states']), len(MX.state_ids))

        country_info = self.Controller.country_infos(country=US, mode="shipping")
        self.assertEqual(len(country_info['states']), 0)

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

        self.assertEqual(self.empty_order._get_delivery_methods().mapped('name'), ['Under 300', 'Fixed'])

    def test_validate_payment_with_no_available_delivery_method(self):
        """
        An error should be raised if you try to validate an order with a storable
        product without any delivery method available
        """
        storable_product = self.env['product.product'].create({
            'name': 'Storable Product',
            'sale_ok': True,
            'type': 'product',
            'website_published': True,
        })
        carriers = self.env['delivery.carrier'].search([])
        carriers.write({'website_published': False})

        with MockRequest(self.env, website=self.website):
            self.website.sale_get_order(force_create=True)
            self.Controller.cart_update_json(product_id=storable_product.id, add_qty=1)
            with self.assertRaises(ValidationError):
                self.Controller.shop_payment_validate()

    def test_check_order_delivery_before_payment(self):
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
            'lst_price': 1000.0,
            'standard_price': 800.0,
        })
        website = self.website.with_user(self.public_user)
        with MockRequest(product.with_user(self.public_user).env, website=website):
            sale_order = self.env['sale.order'].create({
                'partner_id': self.public_user.id,
                'order_line': [Command.create({'product_id': product.id})],
                'access_token': 'test_token',
            })
            # Try processing payment with a storable product and no carrier_id
            with self.assertRaises(ValidationError):
                PaymentPortalDelivery().shop_payment_transaction(sale_order.id, sale_order.access_token)
