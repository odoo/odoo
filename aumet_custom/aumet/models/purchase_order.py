import logging

from odoo import models, fields, api
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

    def button_marketplace(self):
        pass

    @api.depends('order_line.product_id','order_line.product_id.marketplace_product.marketplace_id')
    def create1(self, vals_list):
        print("#$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        print(vals_list)
        print(dir(self))
        print(self.id)
        print(self.order_line)
        print("&&&&&&&&&&&&&&&&&&&&&&&")
        print(self.order_line.product_id)
        # if self.order_line.product_id.is_marketplace_item:
        result =  super(PurchaseOrder, self).create(vals_list)

        print("^^^^^^^^^^^^^^^^")
        print(result.product_id)
        # created_product = self.env['purchase.order'].search([('id', '=',result.id )])

        created_lines = self.env['purchase.order.line'].search([('order_id', '=', result.id)])
        print(len(created_lines))
        print(result.id,
        self.env.user.marketplace_token,
        self.env.user.marketplace_pharmacy_id,
        result.order_line.product_id.marketplace_product.marketplace_id,
        result.order_line.product_uom_qty,
        result.order_line.bonus,
        result.order_line.payment_method.marketplace_payment_method_id)
        item_add_line_result = cart.CartAPI.add_item_to_cart(
            self.env.user.marketplace_token,
            self.env.user.marketplace_pharmacy_id,
            result.order_line.product_id.marketplace_product.marketplace_id,
            result.order_line.product_uom_qty,
            result.order_line.bonus,
            result.order_line.payment_method.marketplace_payment_method_id
        )
        print(self.env.user.marketplace_token)
        print(self.env.user.marketplace_token)

        raise Exception()
        return result

    def write1(self, vals):

        state_of_po = vals.get('state')
        if state_of_po == "cancel":
            return super(PurchaseOrder, self).write(vals)

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

                error_code = ErrorHelper.get_status_code(item_add_line_result.json()["message"])

                if error_code == 409:
                    valid_methods = self.get_payment_methods(i.product_id.marketplace_product.marketplace_id)
                    raise ValidationError(
                        f'Invalid Payment method for order line {i.product_id.name}, valid methods are {valid_methods}')
                elif error_code == 408:
                    raise ValidationError(
                        f'your Marketplace cart seems to be full, please try emptying it before placing order')

        return super(PurchaseOrder, self).write(vals)


