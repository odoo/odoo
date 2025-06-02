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
            product = line.product_id

            if not (product.is_storable and not product.allow_out_of_stock_order):
                continue

            available_qty = cart._get_free_qty(product) - float(cart._get_cart_qty(product.id))
            required_qty = line.product_uom_qty

            if available_qty == 0:
                unavailable_products.append((required_qty, product.name))
            elif available_qty < required_qty:
                partially_available_products.append((available_qty, product.name))

        def format_product_list(products):
            formatted_list = [f"{qty} {name}" for qty, name in products]
            if len(formatted_list) > 2:
                return ", ".join(formatted_list[:-1]) + " and " + formatted_list[-1]
            return " and ".join(formatted_list)

        messages = []

        if unavailable_products:
            product_list = format_product_list(unavailable_products)
            qty = unavailable_products[0][0]
            verb = "were" if len(unavailable_products) > 1 or qty > 1 else "was"
            pronoun = "they are" if len(unavailable_products) > 1 or qty > 1 else "it is"
            messages.append(f"{product_list} {verb} not added to your cart because {pronoun} currently unavailable.")

        if partially_available_products:
            product_list = format_product_list(partially_available_products)
            qty = partially_available_products[0][0]
            verb = "are" if len(partially_available_products) > 1 or qty > 1 else "is"
            pronoun = "They have" if len(partially_available_products) > 1 or qty > 1 else "It has"
            messages.append(f"Only {product_list} {verb} available. {pronoun} been added to your cart.")

        return "\n".join(messages) if messages else False
