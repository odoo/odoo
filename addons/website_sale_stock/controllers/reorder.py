# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers import reorder
from odoo.http import request, route


class CustomerPortal(reorder.CustomerPortal):

    def _sale_reorder_get_line_context(self):
        return {
            **super()._sale_reorder_get_line_context(),
            'website_sale_stock_get_quantity': True,
        }

    @route()
    def my_orders_reorder(self, order_id, access_token):
        shop_warning = self._get_reorder_shop_warning(order_id)
        result = super().my_orders_reorder(order_id, access_token)
        request.cart.shop_warning = shop_warning

        return result

    def _get_reorder_shop_warning(self, order_id):
        order_sudo = request.env['sale.order'].sudo().browse(order_id)
        cart = request.cart or request.website._create_cart()
        unavailable_products, partially_available_products = [], []

        for line in order_sudo.order_line:
            if line.with_user(request.env.user).sudo()._is_reorder_allowed():
                lines_to_consider = line.linked_line_ids if line.product_id.type == 'combo' else line

                if all((
                    not line_to_consider.product_id.is_storable
                    or line_to_consider.product_id.product_tmpl_id.allow_out_of_stock_order
                ) for line_to_consider in lines_to_consider):
                    continue

                available_qty = min(
                    request.website._get_product_available_qty(line_to_consider.product_id)
                    - float(cart._get_cart_qty(line_to_consider.product_id.id))
                for line_to_consider in lines_to_consider)

                required_qty = line.product_uom_qty

                if available_qty == 0:
                    unavailable_products.append((required_qty, line.product_id.name))
                elif available_qty < required_qty:
                    partially_available_products.append((available_qty, line.product_id.name))

        messages = []

        if unavailable_products:
            messages.append(
                self.env._(
                    "\"%(product_string)s\" couldn't be added to your cart because it's currently unavailable.",
                    product_string=", ".join(
                        f"{qty} {name}" for qty, name in unavailable_products
                    ),
                ),
            )

        if partially_available_products:
            messages.append(
                self.env._(
                    'Only "%(product_string)s" available and added to your cart.',
                    product_string=", ".join(
                        f"{qty} {name}" for qty, name in partially_available_products
                    ),
                ),
            )

        return "\n".join(messages) if messages else False
