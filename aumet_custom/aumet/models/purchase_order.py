from odoo import models
from odoo.exceptions import ValidationError
from ..marketplace_apis import cart
from ..response_mapping.errors import ErrorHelper


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def write(self, vals):

        for i in self.order_line:
            if (i.product_id.is_marketplace_item):
                item_add_line_result = cart.CartAPI.add_item_to_cart(
                    self.env.user.marketplace_token,
                    self.env.user.marketplace_pharmacy_id,
                    i.product_id.marketplace_product.marketplace_id,
                    i.product_uom_qty,
                    i.bonus,
                    i.payment_method.marketplace_payment_method_id
                )

                if ErrorHelper.get_status_code(item_add_line_result.json()["message"]) == 409:
                    raise ValidationError(f'Invalid Payment method for order line {i.product_id.name}')

        return super(PurchaseOrder, self).write(vals)
