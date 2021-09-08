import logging

from ..marketplace_apis.cart import CartAPI
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    bonus = fields.Integer("Bonus")

    price_unit = fields.Float(
        'Unit Price', compute='_compute_standard_price', store=False)

    is_marketplace_order = fields.Boolean("Is in marketplace")

    def _compute_standard_price(self):
        self.product_id.with_prefetch()
        summation = 0.0
        for i in self.product_id:
            if i.is_marketplace_item:
                self.is_marketplace_order = True
                summation += i.marketplace_product.unit_price
            else:
                self.is_marketplace_order = False
                summation += i.standard_price

        self.price_unit = summation

    @api.depends("product_id")
    def calculate_possible_payment_methods(self):
        payment_methods = self.env["aumet.payment_method"].search([])

        return [(i.marketplace_payment_method_id, i.name) for i in payment_methods]

    def create(self, vals_list):
        result = super(PurchaseOrderLine, self).create(vals_list)
        preftech = (result.product_id.with_prefetch())
        if result.product_id.is_marketplace_item:
            _logger.info("About to place order in marketplace")
            item_add_line_result = CartAPI.add_item_to_cart(
                self.env.user.marketplace_token,
                self.env.user.marketplace_pharmacy_id,
                result.product_id.marketplace_product.id,
                result.product_uom_qty,
                result.bonus,
                preftech.payment_method.marketplace_payment_method_id)

            if item_add_line_result:
                self.order_id.with_prefetch()
                self.order_id.state = "in marketplace"

        return result

    def onchange(self, values, field_name, field_onchange):
        try:
            product = self.env["product.product"].search([("id", "=", values["product_id"])])

            mpapi_response = CartAPI.get_product_details(self.env.user.marketplace_token,
                                                         product.marketplace_product.marketplace_id)

            seller_id = mpapi_response["data"]["data"]["entityId"]
            dist_data = CartAPI.get_disr_details(self.env.user.marketplace_token, seller_id)
            if dist_data["data"]["payment_methods"]:
                payment_methods_name = [method["name"] for method in dist_data["data"]["payment_methods"]]
                print(payment_methods_name)

        except Exception as exc1:
            pass

        return super(PurchaseOrderLine, self).onchange(values, field_name, field_onchange)
