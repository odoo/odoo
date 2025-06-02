# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.website_sale.controllers.cart import Cart


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
        """ Retrieve reorder content and automatically add products to the cart.

        param int order_id: The ID of the sale order to reorder.
        param str access_token: The access token for the sale order.
        return: The number of items in the cart after reordering.
        rtype: int
        """
        try:
            sale_order = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        for line in sale_order.order_line:
            if not line._is_reorder_allowed():
                continue  # Skip section headers, deliveries, or combo item lines

            linked_products = None

            if line.product_id.type == 'combo':
                linked_products = [{
                    'product_template_id': linked_line.product_id.product_tmpl_id.id,
                    'parent_product_template_id': line.product_id.product_tmpl_id.id,
                    'quantity': linked_line.product_uom_qty,
                    'combo_item_id': linked_line.combo_item_id.id,
                    'product_id': linked_line.product_id.id,
                    'product_custom_attribute_values': [{
                        'custom_product_template_attribute_value_id': pcav.custom_product_template_attribute_value_id.id,
                        'custom_value': pcav.custom_value,
                    } for pcav in linked_line.product_custom_attribute_value_ids],
                    'no_variant_attribute_value_ids': linked_line.product_no_variant_attribute_value_ids.ids,
                } for linked_line in line.linked_line_ids]

            Cart().add_to_cart(
                product_id=line.product_id.id,
                product_template_id=line.product_id.product_tmpl_id.id,
                quantity=line.product_uom_qty,
                product_custom_attribute_values=[{
                    'custom_product_template_attribute_value_id': pcav.custom_product_template_attribute_value_id.id,
                    'custom_value': pcav.custom_value,
                } for pcav in line.product_custom_attribute_value_ids],
                no_variant_attribute_value_ids=line.product_no_variant_attribute_value_ids.ids,
                linked_products=linked_products,
            )

        return request.session.get('website_sale_cart_quantity', request.cart.cart_quantity)
