# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleDeliveryController(PaymentCommon, WebsiteSaleCommon):
    _test_user_groups = (
        'base.group_user',
        'product.group_product_manager',
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    def setUp(self):
        super().setUp()
        self.Controller = Delivery()
        self.empty_cart = self._create_so(order_line=[])

    # test that changing the delivery method while there is a pending transaction raises an error
    def test_controller_change_carrier_when_transaction(self):
        self.empty_cart.sudo().transaction_ids = self._create_transaction(flow="redirect", state="pending")
        with (
            self.mock_request(sale_order_id=self.empty_cart.id) as request,
            self.assertRaises(UserError),
        ):
            request.cart = self.empty_cart
            self.Controller.shop_set_delivery_method(dm_id=self.free_delivery.id)

    # test that changing the delivery method while there is a draft transaction is successful
    def test_controller_change_carrier_when_draft_transaction(self):
        self.empty_cart.sudo().transaction_ids = self._create_transaction(flow="redirect", state="draft")
        with self.mock_request(sale_order_id=self.empty_cart.id):
            self.Controller.shop_set_delivery_method(dm_id=self.free_delivery.id)

    def test_available_methods(self):
        self.env["delivery.carrier"].search([]).action_archive()
        self.product_delivery_poste = self.env["product.product"].create({
            "name": "The Poste",
            "type": "service",
            "categ_id": self.env.ref("delivery.product_category_deliveries").id,
            "sale_ok": False,
            "purchase_ok": False,
            "list_price": 20.0,
        })
        self.env["delivery.carrier"].create([
            {
                "name": "Over 300",
                "delivery_type": "base_on_rule",
                "product_id": self.product_delivery_poste.id,
                "website_published": True,
                "price_rule_ids": [
                    Command.create({"operator": ">=", "max_value": 300, "variable": "price"})
                ],
            },
            {
                "name": "Under 300",
                "delivery_type": "base_on_rule",
                "product_id": self.product_delivery_poste.id,
                "website_published": True,
                "price_rule_ids": [
                    Command.create({"operator": "<", "max_value": 300, "variable": "price"})
                ],
            },
            {
                "name": "No rules",
                "delivery_type": "base_on_rule",
                "product_id": self.product_delivery_poste.id,
                "website_published": True,
            },
            {
                "name": "Fixed",
                "product_id": self.product_delivery_poste.id,
                "website_published": True,
            },
        ])

        self.assertEqual(
            self.empty_cart._get_delivery_methods().mapped("name"), ["Under 300", "Fixed"]
        )

    def test_recompute_cart_recomputes_delivery_rate(self):
        delivery_product = self.env['product.product'].create({
            'name': 'Delivery Fee',
            'type': 'service',
            'sale_ok': False,
            'purchase_ok': False,
        })
        carrier = self.env['delivery.carrier'].create({
            'name': 'Free over 15',
            'delivery_type': 'base_on_rule',
            'product_id': delivery_product.id,
            'website_published': True,
            'price_rule_ids': [
                Command.create({
                    'operator': '>=',
                    'max_value': 15,
                    'variable': 'price',
                    'list_base_price': 0,
                }),
                Command.create({
                    'operator': '<',
                    'max_value': 15,
                    'variable': 'price',
                    'list_base_price': 10,
                }),
            ],
        })
        order = self.empty_cart
        order.order_line = [
            Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
            }),
        ]
        order.partner_id.write(self.dummy_partner_address_values)
        with self.mock_request(sale_order_id=order.id) as request:
            order = request.cart
            order._set_delivery_method(carrier)
            self.assertEqual(order.amount_delivery, 0.0)

            self.product.list_price = 10.0
            order._update_cart_taxes_and_prices()

        self.assertEqual(order.amount_delivery, 10.0)
