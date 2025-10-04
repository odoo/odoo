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
    def cart_options_update_json(self, product_and_options, lang=None, **kwargs):
        """This route is called when submitting the optional product modal.
            The product without parent is the main product, the other are options.
            Options need to be linked to their parents with a unique ID.
            The main product is the first product in the list and the options
            need to be right after their parent.
            product_and_options {
                'product_id',
                'product_template_id',
                'quantity',
                'parent_unique_id',
                'unique_id',
                'product_custom_attribute_values',
                'no_variant_attribute_values'
            }
        """
        if lang:
            request.website = request.website.with_context(lang=lang)

        order = request.website.sale_get_order(force_create=True)
        if order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order(force_create=True)

        product_and_options = json.loads(product_and_options)
        if product_and_options:
            # The main product is the first, optional products are the rest
            main_product = product_and_options[0]
            values = order._cart_update(
                product_id=main_product['product_id'],
                add_qty=main_product['quantity'],
                product_custom_attribute_values=main_product['product_custom_attribute_values'],
                no_variant_attribute_values=main_product['no_variant_attribute_values'],
                **kwargs
            )

            line_ids = [values['line_id']]

            if values['line_id']:
                # Link option with its parent iff line has been created.
                option_parent = {main_product['unique_id']: values['line_id']}
                for option in product_and_options[1:]:
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
