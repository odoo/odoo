# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo.http import request, route
from odoo.tools import groupby

from odoo.addons.website_sale.controllers import reorder


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
        cart_sudo = request.cart or request.website._create_cart()
        unavailable_products, partially_available_products = [], []

        SaleOrderLine = order_sudo.env['sale.order.line']
        requested_quantities = defaultdict(int)
        for product, lines in groupby(
            order_sudo.order_line.with_user(request.env.user).sudo(),
            lambda sol: sol.product_id,
        ):

            lines_to_reorder = SaleOrderLine.concat(
                *[line for line in lines if line._is_reorder_allowed()]
            )
            if product.type == 'combo':
                for linked_line in lines_to_reorder.linked_line_ids:
                    combo_product = linked_line.product_id
                    if(
                        combo_product.is_storable
                        and not combo_product.allow_out_of_stock_order
                    ):
                        requested_quantities[combo_product] += linked_line.product_uom_qty
            elif(
                product.is_storable
                and not product.allow_out_of_stock_order
            ):
                for sol in lines_to_reorder:
                    requested_quantities[product] += sol.product_uom_qty

        for product, requested_quantity in requested_quantities.items():
            available_qty = (
                request.website._get_product_available_qty(product)
                - float(cart_sudo._get_cart_qty(product.id))
            )

            if available_qty == 0:
                unavailable_products.append((requested_quantity, product.name))
            elif available_qty < requested_quantity:
                partially_available_products.append((available_qty, product.name))

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
