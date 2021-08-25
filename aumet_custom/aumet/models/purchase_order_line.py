from ..marketplace_apis.cart import CartAPI
from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    bonus = fields.Integer("Bonus")
    payment_method = fields.Many2one("aumet.payment_method", string="payment method")

    price_unit = fields.Float(
        'Unit Price', compute='_compute_standard_price', store=False)

    @api.depends()
    def _compute_standard_price(self):
        try:
            self.price_unit = self.product_id.marketplace_product.unit_price
        except Exception as exc1:
            print(exc1)

    @api.depends("product_id")
    def calculate_possible_payment_methods(self):
        payment_methods = self.env["aumet.payment_method"].search([])

        return [(i.marketplace_payment_method_id, i.name) for i in payment_methods]

    def onchange(self, values, field_name, field_onchange):
        try:
            product = self.env["product.product"].search([("id", "=", values["product_id"])])

            mpapi_response = CartAPI.get_product_details(product.marketplace_product.marketplace_id,
                                                         self.env.user.marketplace_token
                                                         )

            if (mpapi_response["data"]["data"]["payment_methods"]):
                pass
            else:
                seller_id = mpapi_response["data"]["data"]["entityId"]
                dist_data = CartAPI.get_disr_details(self.env.user.marketplace_token, seller_id)
                if  dist_data["data"]["payment_methods"]:
                    payment_methods_name = [method["name"] for method in dist_data["data"]["payment_methods"]]
                    print(payment_methods_name)
        except Exception as exc1:
            pass

        data = super(PurchaseOrderLine, self).onchange(values, field_name, field_onchange)

        return data
