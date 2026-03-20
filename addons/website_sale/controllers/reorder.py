# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.http import request, route

from odoo.addons.sale.controllers import portal as sale_portal
from odoo.addons.website_sale.controllers.cart import Cart


class CustomerPortal(sale_portal.CustomerPortal):

    @route(
        '/my/orders/reorder',
        type='jsonrpc',
        auth='public',
        website=True,
    )
    def my_orders_reorder(self, order_id, access_token=None):
        """ Retrieve reorder content and automatically add products to the cart.

        param int order_id: The ID of the sale order to reorder.
        param str access_token: The access token for the sale order.
        return: Details of the added products.
        rtype: dict
        """
        try:
            sale_order = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        lines_to_reorder = sale_order.order_line.filtered(
            # Skip section headers, deliveries, event tickets, ...
            lambda line: line.with_user(request.env.user).sudo()._is_reorder_allowed()
        )

        if not lines_to_reorder:
            raise ValidationError(request.env._("Nothing can be reordered in this order"))

        Cart_controller = Cart()
        order_sudo = request.cart or request.website._create_cart()
        warnings_to_aggregate = set()
        values = {
            'tracking_info': [],
        }
        for line in lines_to_reorder:

            linked_products = []
            if line.product_id.type == 'combo':
                for linked_line in line.linked_line_ids.filtered('combo_item_id'):
                    combination = (
                        linked_line.product_id.product_template_attribute_value_ids
                        | linked_line.product_no_variant_attribute_value_ids
                    )
                    linked_products.append({
                        'product_template_id': linked_line.product_id.product_tmpl_id.id,
                        'product_id': linked_line.product_id.id,
                        'combination': combination.ids,
                        'no_variant_attribute_value_ids': linked_line.product_no_variant_attribute_value_ids.ids,
                        'product_custom_attribute_values': [{
                            'custom_product_template_attribute_value_id': pcav.custom_product_template_attribute_value_id.id,
                            'custom_value': pcav.custom_value,
                        } for pcav in linked_line.product_custom_attribute_value_ids],
                        'quantity': linked_line.product_uom_qty,
                        'combo_item_id': linked_line.combo_item_id.id,
                        'parent_product_template_id': line.product_id.product_tmpl_id.id,
                    })

            cart_values = Cart_controller.add_to_cart(
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
            if not cart_values['quantity']:
                # Only aggregate order warnings
                warnings_to_aggregate.add(order_sudo.shop_warning)

            values['tracking_info'].extend(cart_values['tracking_info'])

        if warnings_to_aggregate:
            order_sudo.shop_warning = '\n'.join(warnings_to_aggregate)

        values['cart_quantity'] = order_sudo.cart_quantity
        return values
