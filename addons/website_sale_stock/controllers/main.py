# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers import main as website_sale_controller

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError


class WebsiteSale(website_sale_controller.WebsiteSale):

    @http.route()
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True, **kwargs):
        product = request.env['product.product'].browse(product_id)

        if not product.allow_out_of_stock_order and add_qty and product.type == 'product' and product.free_qty - product.cart_qty - add_qty < 0:
            return {
                "warning": _("Unfortunately, this product is out of stock, you cannot add it to your cart anymore")
            }
        return super().cart_update_json(product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty,
                                        display=display, **kwargs)



class PaymentPortal(website_sale_controller.PaymentPortal):

    @http.route()
    def shop_payment_transaction(self, *args, **kwargs):
        """ Payment transaction override to double check cart quantities before
        placing the order
        """
        order = request.website.sale_get_order()
        values = []
        for line in order.order_line:
            if line.product_id.type == 'product' and not line.product_id.allow_out_of_stock_order:
                cart_qty = sum(order.order_line.filtered(lambda p: p.product_id.id == line.product_id.id).mapped('product_uom_qty'))
                avl_qty = line.product_id.with_context(warehouse=order.warehouse_id.id).free_qty
                if cart_qty > avl_qty:
                    values.append(_(
                        'You ask for %(quantity)s products but only %(available_qty)s is available',
                        quantity=cart_qty,
                        available_qty=avl_qty if avl_qty > 0 else 0
                    ))
        if values:
            raise ValidationError('. '.join(values) + '.')
        return super().shop_payment_transaction(*args, **kwargs)
