import logging

from odoo import models, fields
from odoo.exceptions import ValidationError
from ..marketplace_apis import cart
from ..marketplace_apis.cart import CartAPI
from ..response_mapping.errors import ErrorHelper

_logger = logging.getLogger(__name__)
class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('in marketplace', 'In Marketplace'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False,  tracking=True)

    standard_price = fields.Char(
        compute='_compute', store=False, string="test")

    def button_marketplace(self, force=False):
        pass

    def write(self, vals):
        _logger.error("#!@#!@#!@#!@#!@#!@")
        state_of_po = vals.get('state', False)
        if state_of_po != "cancel":

            for i in self.order_line:
                if not self.env.user.marketplace_token:
                    raise ValidationError(f'Make sure to have your Marketplace token in your user settings')
                _logger.error(i.product_id.is_marketplace_item)
                if i.product_id.is_marketplace_item:
                    item_add_line_result = cart.CartAPI.add_item_to_cart(
                        self.env.user.marketplace_token,
                        self.env.user.marketplace_pharmacy_id,
                        i.product_id.marketplace_product.marketplace_id,
                        i.product_uom_qty,
                        i.bonus,
                        i.payment_method.marketplace_payment_method_id
                    )
                    print("@!#!@#!@#!")
                    print(item_add_line_result.json()["message"])
                    error_code = ErrorHelper.get_status_code(item_add_line_result.json()["message"])

                    if error_code == 409:
                        valid_methods = self.get_payment_methods(i.product_id.marketplace_product.marketplace_id)
                        raise ValidationError(
                            f'Invalid Payment method for order line {i.product_id.name}, valid methods are {valid_methods}')
                    elif error_code == 408:
                        raise ValidationError(
                            f'your Marketplace cart seems to be full, please try emptying it before placing order')

        return super(PurchaseOrder, self).write(vals)

    def get_payment_methods(self, marketplace_id):
        mpapi_response = CartAPI.get_product_details(marketplace_id,
                                                     self.env.user.marketplace_token
                                                     )
        allowed_methods = []
        if (mpapi_response["data"]["data"]["payment_methods"]):

            return (mpapi_response["data"]["data"]["payment_methods"])

        else:
            seller_id = mpapi_response["data"]["data"]["entityId"]
            try:
                dist_data = CartAPI.get_disr_details(self.env.user.marketplace_token, seller_id)
                if dist_data["data"]["payment_methods"]:
                    allowed_methods = [method["name"] for method in dist_data["data"]["payment_methods"]]
                    return allowed_methods

            except Exception:
                pass
            if allowed_methods:
                return allowed_methods

            return (["CASH", "Cheque"])
