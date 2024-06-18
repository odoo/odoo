# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request

from odoo.addons.sale.controllers.variant import VariantController


class WebsiteSaleVariantController(VariantController):
    @http.route(['/sale/get_combination_info_website'], type='json', auth="public", methods=['POST'], website=True)
    def get_combination_info_website(self, product_template_id, product_id, combination, add_qty, **kw):
        """Special route to use website logic in get_combination_info override.
        This route is called in JS by appending _website to the base route.
        """
        kw.pop('pricelist_id')
        combination = self.get_combination_info(product_template_id, product_id, combination, add_qty, request.website.get_current_pricelist(), **kw)

        if request.website.google_analytics_key:
            combination['product_tracking_info'] = request.env['product.template'].get_google_analytics_data(combination)

        product = request.env['product.template'].browse(combination['product_template_id'])
        product_variant = request.env['product.product'].browse(combination['product_id'])
        website = request.env['website'].get_current_website()

        if request.website.product_page_image_width != 'none' and not request.env.context.get('website_sale_no_images', False):
            carousel_view = request.env['ir.ui.view']._render_template('website_sale.shop_product_images', values={
                'product': product,
                'product_variant': product_variant,
                'website': website,
            })
            combination['carousel'] = carousel_view

        # Send variant-specific extra fields we want rendered js-side so they can be rendered dynamically based
        # on the currently selected product variant.
        combination['variant_extra_fields'] = [
            [field.label, field._value_for_product(variant=product_variant)]
            for field in website.shop_extra_field_ids
            if
                field._value_for_product(variant=product_variant)
                and not field._value_for_product(template=product)
        ]
        combination['any_template_extra_field'] = any(f._value_for_product(product) for f in website.shop_extra_field_ids)

        return combination

    @http.route(auth="public")
    def create_product_variant(self, product_template_id, product_template_attribute_value_ids, **kwargs):
        """Override because on the website the public user must access it."""
        return super(WebsiteSaleVariantController, self).create_product_variant(product_template_id, product_template_attribute_value_ids, **kwargs)
