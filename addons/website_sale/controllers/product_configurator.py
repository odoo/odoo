# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.http import request, route
from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteSaleProductConfiguratorController(WebsiteSale):

    @route(
        '/sale_product_configurator/show_advanced_configurator',
        type='json', auth='public', methods=['POST'], website=True,
    )
    def show_advanced_configurator(
        self, product_id, variant_values, add_qty=1, force_dialog=False, **kw,
    ):
        product = request.env['product.product'].browse(int(product_id))
        product_template = product.product_tmpl_id
        combination = request.env['product.template.attribute.value'].browse(variant_values)
        has_optional_products = product.optional_product_ids.filtered(
            lambda p: p._is_add_to_cart_possible(combination)
                      and (not request.website.prevent_zero_price_sale or p._get_contextual_price())
        )

        already_configured = bool(combination)
        if not force_dialog and not has_optional_products and (
            product.product_variant_count <= 1 or already_configured
        ):
            # The modal is not shown if there are no optional products and
            # the main product either has no variants or is already configured
            return False

        add_qty = float(add_qty)
        combination_info = product_template._get_combination_info(
            combination=combination,
            product_id=product.id,
            add_qty=add_qty,
        )

        return request.env['ir.ui.view']._render_template(
            'website_sale.optional_products_modal',
            {
                'product': product,
                'product_template': product_template,
                'combination': combination,
                'combination_info': combination_info,
                'add_qty': add_qty,
                'parent_name': product.name,
                'variant_values': variant_values,
                'already_configured': already_configured,
                'mode': kw.get('mode', 'add'),
                'product_custom_attribute_values': kw.get('product_custom_attribute_values', None),
                'no_attribute': kw.get('no_attribute', False),
                'custom_attribute': kw.get('custom_attribute', False),
            }
        )

    @route(
        '/sale_product_configurator/optional_product_items',
        type='json', auth='public', methods=['POST'], website=True,
    )
    def optional_product_items(self, product_id, add_qty=1, **kw):
        product = request.env['product.product'].browse(int(product_id))

        return request.env['ir.ui.view']._render_template(
            'website_sale.optional_product_items',
            {
                'product': product,
                'parent_name': product.name,
                'parent_combination': product.product_template_attribute_value_ids,
                'add_qty': float(add_qty) or 1.0,
            }
        )

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
                no_variant_attribute_value_ids=[
                    int(ptav_data['value'])
                    for ptav_data in main_product['no_variant_attribute_values']
                ],
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
                        no_variant_attribute_value_ids=[
                            int(ptav_data['value'])
                            for ptav_data in option['no_variant_attribute_values']
                        ],
                        **kwargs
                    )
                    option_parent[option['unique_id']] = option_values['line_id']
                    line_ids.append(option_values['line_id'])

            values['notification_info'] = self._get_cart_notification_information(order, line_ids)

        values['cart_quantity'] = order.cart_quantity
        request.session['website_sale_cart_quantity'] = order.cart_quantity

        return values
