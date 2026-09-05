# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.tests import Form, tagged

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale.controllers.cart import Cart
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockDeliveryController(PaymentCommon, WebsiteSaleCommon):
    def test_validate_payment_with_no_available_delivery_method(self):
        """
        Raise an error if order is being validated with a storable
        product without any delivery method available.
        """
        storable_product = self.env["product.product"].create([
            {
                "name": "Storable Product",
                "sale_ok": True,
                "is_storable": True,
                "website_published": True,
            }
        ])
        carriers = self.env["delivery.carrier"].search([])
        carriers.write({"website_published": False})

        WebsiteSaleCartController = Cart()
        WebsiteSaleController = WebsiteSale()
        with self.mock_request():
            WebsiteSaleCartController.add_to_cart(
                product_template_id=storable_product.product_tmpl_id,
                product_id=storable_product.id,
                quantity=1,
            )
            with self.assertRaises(ValidationError):
                WebsiteSaleController.shop_payment_validate()

    def test_validate_order_out_of_stock_zero_price(self):
        """Raise error if order is being validated for an out of stock product with 0 price."""
        WebsiteSaleController = WebsiteSale()
        storable_product = self.env["product.product"].create({
            "name": "Storable Product",
            "sale_ok": True,
            "is_storable": True,
            "website_published": True,
            "allow_out_of_stock_order": False,
            "lst_price": 0,
        })
        sale_order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [
                Command.create({"product_id": storable_product.id, "product_uom_qty": 12.0})
            ],
            "carrier_id": self.free_delivery.id,
        })
        self.free_delivery.write({"website_published": True})
        self.env["stock.quant"].with_context(inventory_mode=True).create({
            "product_id": storable_product.id,
            "inventory_quantity": 10.0,
            "location_id": self.env.user._get_default_warehouse_id().lot_stock_id.id,
        }).action_apply_inventory()

        with self.mock_request():
            request.cart = sale_order
            with self.assertRaises(ValidationError):
                WebsiteSaleController.shop_payment_validate()


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockDelivery(DeliveryCommon):
    def test_rule_delivery_price_uses_manually_entered_weight(self):
        "Test that the delivery price is computed using the manually entered weight in the wizard."
        self.product.weight = 0
        sale_order = self.sale_order
        delivery = self._prepare_carrier(product=self._prepare_carrier_product(), delivery_type="base_on_rule")
        delivery.price_rule_ids = [Command.create({
            "variable": "quantity",
            "operator": ">=",
            "max_value": 0,
            "variable_factor": "weight",
            "list_price": 2,
        })]
        with Form(self.env["choose.delivery.carrier"].with_context(default_order_id=sale_order, default_carrier_id=delivery)) as delivery_wizard:
            delivery_wizard.total_weight = 10
            wizard = delivery_wizard.save()
        wizard.button_confirm()
        delivery_line = sale_order.order_line.filtered("is_delivery")
        self.assertRecordValues(delivery_line, [{"product_id": delivery.product_id.id, "product_uom_qty": 1, "price_unit": 20}])
