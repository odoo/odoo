# Part of Odoo. See LICENSE file for full copyright and licensing details

import json

from odoo.http import Controller, request, route


class WebsiteSaleVariantController(Controller):

    @route('/website_sale/get_combination_info', type='json', auth='public', methods=['POST'], website=True)
    def get_combination_info_website(
        self, product_template_id, product_id, combination, add_qty, parent_combination=None,
        **kwargs
    ):
        product_template = request.env['product.template'].browse(
            product_template_id and int(product_template_id))

        combination_info = product_template._get_combination_info(
            combination=request.env['product.template.attribute.value'].browse(combination),
            product_id=product_id and int(product_id),
            add_qty=add_qty and float(add_qty) or 1.0,
            parent_combination=request.env['product.template.attribute.value'].browse(parent_combination),
        )

        # Pop data only computed to ease server-side computations.
        for key in ('product_taxes', 'taxes', 'currency', 'date', 'combination'):
            combination_info.pop(key)

        if request.website.product_page_image_width != 'none' and not request.env.context.get('website_sale_no_images', False):
            combination_info['carousel'] = request.env['ir.ui.view']._render_template(
                'website_sale.shop_product_images',
                values={
                    'product': product_template,
                    'product_variant': request.env['product.product'].browse(combination_info['product_id']),
                    'website': request.env['website'].get_current_website(),
                },
            )

        product = request.env['product.product'].browse(combination_info['product_id'])
        if product and request.website.is_view_active('website_sale.product_tags'):
            combination_info['product_tags'] = request.env['ir.ui.view']._render_template(
                'website_sale.product_tags', values={
                    'all_product_tags': product.all_product_tag_ids.filtered('visible_on_ecommerce')
                }
            )
        return combination_info

    @route('/sale/create_product_variant', type='json', auth='public', methods=['POST'])
    def create_product_variant(self, product_template_id, product_template_attribute_value_ids, **kwargs):
        """Old product configurator logic, only used by frontend configurator, will be deprecated soon"""
        return request.env['product.template'].browse(
            int(product_template_id)
        ).create_product_variant(json.loads(product_template_attribute_value_ids))
