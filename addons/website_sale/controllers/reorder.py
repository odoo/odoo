# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):

    def _sale_reorder_get_line_context(self):
        return {}

    @route(
        '/my/orders/reorder',
        type='jsonrpc',
        auth='public',
        website=True,
    )
    def my_orders_reorder(self, order_id, access_token):
        """Retrieve reorder content and automatically add products to the cart."""
        try:
            sale_order = self._document_check_access(
                'sale.order', order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')

        order_sudo = (
            request.cart or request.website._create_cart()
        )  # Get or create cart

        products = []

        for line in sale_order.order_line:
            if line.display_type or line._is_delivery():
                continue  # Skip section headers and delivery products

            product = line.product_id
            combination = (
                product.product_template_attribute_value_ids
                | line.product_no_variant_attribute_value_ids
            )
            res = {
                'product_id': product.id,
                'name': line.name_short,
                'qty': line.product_uom_qty,
                'add_to_cart_allowed': line.with_user(request.env.user).sudo()._is_reorder_allowed(),
            }
            if res['add_to_cart_allowed']:
                res['combination_info'] = product.product_tmpl_id.with_context(
                    **self._sale_reorder_get_line_context()
                )._get_combination_info(combination, res['product_id'], res['qty'])

                # This condition will be useful only when website_sale_stock is installed.
                # We are sending only possible quantities to _add_cart function because
                # we are handling notifications ourself, so we don't need default warning
                # shown by sale_order model

                allow_out_of_stock = res['combination_info'].get(
                    'allow_out_of_stock_order', True
                )
                free_qty = res['combination_info'].get('free_qty', line.product_uom_qty)

                quantity = (
                    line.product_uom_qty
                    if allow_out_of_stock
                    else min(line.product_uom_qty, free_qty)
                )

                # Add product to cart
                order_sudo._cart_add(
                    product_id=product.id,
                    quantity=quantity,
                    product_custom_attribute_values=[
                        {
                            'custom_product_template_attribute_value_id': pcav.custom_product_template_attribute_value_id.id,
                            'custom_value': pcav.custom_value,
                        }
                        for pcav in line.product_custom_attribute_value_ids
                    ],
                    no_variant_attribute_value_ids=line.product_no_variant_attribute_value_ids.ids,
                )
            else:
                res['combination_info'] = {}

            products.append(res)

        return products
