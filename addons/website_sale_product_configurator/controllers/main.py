# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo import http
from odoo.http import request

from odoo.addons.sale_product_configurator.controllers.main import ProductConfiguratorController
from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteSaleProductConfiguratorController(ProductConfiguratorController):
    @http.route(['/sale_product_configurator/show_optional_products_website'], type='json', auth="public", methods=['POST'], website=True)
    def show_optional_products_website(self, product_id, variant_values, **kw):
        """Special route to use website logic in get_combination_info override.
        This route is called in JS by appending _website to the base route.
        """
        kw.pop('pricelist_id')
        return self.show_optional_products(product_id, variant_values, request.website.get_current_pricelist(), **kw)

    @http.route(['/sale_product_configurator/optional_product_items_website'], type='json', auth="public", methods=['POST'], website=True)
    def optional_product_items_website(self, product_id, **kw):
        """Special route to use website logic in get_combination_info override.
        This route is called in JS by appending _website to the base route.
        """
        kw.pop('pricelist_id')
        return self.optional_product_items(product_id, request.website.get_current_pricelist(), **kw)


class WebsiteSale(WebsiteSale):
    def _prepare_product_values(self, product, category, search, **kwargs):
        values = super(WebsiteSale, self)._prepare_product_values(product, category, search, **kwargs)

        values['optional_product_ids'] = [p.with_context({'active_id': p.id}) for p in product.optional_product_ids]
        return values

    @http.route(['/shop/cart/update_option'], type='http', auth="public", methods=['POST'], website=True, multilang=False)
    def cart_options_update_json(self, product_id, add_qty=1, set_qty=0, goto_shop=None, lang=None, **kw):
        """This route is called when submitting the optional product modal."""
        if lang:
            request.website = request.website.with_context(lang=lang)

        order = request.website.sale_get_order(force_create=True)
        if order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order(force_create=True)
        optional_product_ids = []
        for k, v in kw.items():
            if "optional-product-" in k and int(kw.get(k.replace("product", "add"))):
                optional_product_ids.append(int(v))

        custom_values = []
        if kw.get('custom_values'):
            custom_values = json.loads(kw.get('custom_values'))

        value = {}
        if add_qty or set_qty:
            value = order._cart_update(
                product_id=int(product_id),
                add_qty=add_qty,
                set_qty=set_qty,
                optional_product_ids=optional_product_ids,
                product_custom_attribute_values=self._get_product_custom_value(
                    int(product_id),
                    custom_values,
                    'product_custom_attribute_values'
                ),
                no_variant_attribute_values=self._get_product_custom_value(
                    int(product_id),
                    custom_values,
                    'no_variant_attribute_values'
                )
            )

        # options have all time the same quantity
        for option_id in optional_product_ids:
            order._cart_update(
                product_id=option_id,
                set_qty=value.get('quantity'),
                linked_line_id=value.get('line_id'),
                product_custom_attribute_values=self._get_product_custom_value(
                    option_id,
                    custom_values,
                    'product_custom_attribute_values'
                ),
                no_variant_attribute_values=self._get_product_custom_value(
                    option_id,
                    custom_values,
                    'no_variant_attribute_values'
                )
            )

        return str(order.cart_quantity)

    def _get_product_custom_value(self, product_id, custom_values, field):
        if custom_values:
            for custom_value in custom_values:
                if custom_value['product_id'] == product_id:
                    return custom_value[field]

        return None
