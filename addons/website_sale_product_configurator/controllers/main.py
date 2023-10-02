# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo import http
from odoo.http import request

from odoo.addons.sale_product_configurator.controllers.main import ProductConfiguratorController
from odoo.addons.website_sale.controllers import main


class WebsiteSaleProductConfiguratorController(ProductConfiguratorController):
    @http.route(['/sale_product_configurator/show_advanced_configurator_website'], type='json', auth="public", methods=['POST'], website=True)
    def show_advanced_configurator_website(self, product_id, variant_values, **kw):
        """Special route to use website logic in get_combination_info override.
        This route is called in JS by appending _website to the base route.
        """
        kw.pop('pricelist_id')
        product = request.env['product.product'].browse(int(product_id))
        combination = request.env['product.template.attribute.value'].browse(variant_values)
        has_optional_products = product.optional_product_ids.filtered(
            lambda p: p._is_add_to_cart_possible(combination)
                      and (not request.website.prevent_zero_price_sale or p._get_contextual_price())
        )
        force_dialog = kw.get('force_dialog')

        if not force_dialog and not has_optional_products and (product.product_variant_count <= 1 or variant_values):
            # The modal is not shown if there are no optional products and
            # the main product either has no variants or is already configured
            return False
        if variant_values:
            kw["already_configured"] = True
        return self.show_advanced_configurator(product_id, variant_values, request.website.pricelist_id, **kw)

    @http.route(['/sale_product_configurator/optional_product_items_website'], type='json', auth="public", methods=['POST'], website=True)
    def optional_product_items_website(self, product_id, **kw):
        """Special route to use website logic in get_combination_info override.
        This route is called in JS by appending _website to the base route.
        """
        kw.pop('pricelist_id')
        return self.optional_product_items(product_id, request.website.pricelist_id, **kw)


class WebsiteSale(main.WebsiteSale):
    def _prepare_product_values(self, product, category, search, **kwargs):
        values = super(WebsiteSale, self)._prepare_product_values(product, category, search, **kwargs)

        values['optional_product_ids'] = [p.with_context(active_id=p.id) for p in product.optional_product_ids]
        return values

    @http.route(['/shop/cart/update_option'], type='http', auth="public", methods=['POST'], website=True, multilang=False)
    def cart_options_update_json(self, product_and_options, goto_shop=None, lang=None, **kwargs):
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
            value = order._cart_update(
                product_id=main_product['product_id'],
                add_qty=main_product['quantity'],
                product_custom_attribute_values=main_product['product_custom_attribute_values'],
                no_variant_attribute_values=main_product['no_variant_attribute_values'],
                **kwargs
            )

            if value['line_id']:
                # Link option with its parent iff line has been created.
                option_parent = {main_product['unique_id']: value['line_id']}
                for option in product_and_options[1:]:
                    parent_unique_id = option['parent_unique_id']
                    option_value = order._cart_update(
                        product_id=option['product_id'],
                        set_qty=option['quantity'],
                        linked_line_id=option_parent[parent_unique_id],
                        product_custom_attribute_values=option['product_custom_attribute_values'],
                        no_variant_attribute_values=option['no_variant_attribute_values'],
                        **kwargs
                    )
                    option_parent[option['unique_id']] = option_value['line_id']

        request.session['website_sale_cart_quantity'] = order.cart_quantity

        return str(order.cart_quantity)
