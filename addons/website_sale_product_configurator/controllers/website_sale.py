# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import request, route

from odoo.addons.website_sale.controllers import main


class WebsiteSale(main.WebsiteSale):

    def _prepare_product_values(self, product, category, search, **kwargs):
        values = super()._prepare_product_values(product, category, search, **kwargs)

        values['optional_product_ids'] = [p.with_context(active_id=p.id) for p in product.optional_product_ids]
        return values

    @route(
        '/shop/cart/update_option',
        type='json',
        auth='public',
        methods=['POST'],
        website=True,
        multilang=False,
    )
    def cart_options_update_json(self, main_product, optional_products, **kwargs):
        """This route is called when validating the product configurator """
        order = request.website.sale_get_order(force_create=True)
        if order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order(force_create=True)

        main_product = json.loads(main_product)

        values = order._cart_update(
            product_id=main_product['product_id'],
            add_qty=main_product['quantity'],
            product_custom_attribute_values=main_product['product_custom_attribute_values'],
            no_variant_attribute_values=main_product['no_variant_attribute_values'],
            **kwargs
        )

        line_ids = [values['line_id']]
        # TODO VCR WEIRD
        if optional_products and values['line_id']:
            optional_products = json.loads(optional_products)
            # Link option with its parent iff line has been created.
            option_parent = {main_product['unique_id']: values['line_id']}
            for option in optional_products:
                parent_unique_id = option['parent_unique_id']
                option_values = order._cart_update(
                    product_id=option['product_id'],
                    set_qty=option['quantity'],
                    linked_line_id=option_parent[parent_unique_id],
                    product_custom_attribute_values=option['product_custom_attribute_values'],
                    no_variant_attribute_values=option['no_variant_attribute_values'],
                    **kwargs
                )
                option_parent[option['unique_id']] = option_values['line_id']
                line_ids.append(option_values['line_id'])

        values['notification_info'] = self._get_cart_notification_information(order, line_ids)
        values['cart_quantity'] = order.cart_quantity
        request.session['website_sale_cart_quantity'] = order.cart_quantity

        return values
