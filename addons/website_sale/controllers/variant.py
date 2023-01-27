# Part of Odoo. See LICENSE file for full copyright and licensing details

import json

from odoo.http import request, route, Controller


class WebsiteSaleVariantController(Controller):

    @route('/sale/get_combination_info_website', type='json', auth="public", methods=['POST'], website=True)
    def get_combination_info_website(self, product_template_id, product_id, combination, add_qty, **kw):
        """Old product configurator logic, only used by frontend configurator, will be deprecated soon"""
        combination = request.env['product.template.attribute.value'].browse(combination)
        pricelist = request.website.get_current_pricelist()
        cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
        allowed_company_ids = [int(cid) for cid in cids.split(',')]
        ProductTemplate = request.env['product.template'].with_context(allowed_company_ids=allowed_company_ids)
        if 'context' in kw:
            ProductTemplate = ProductTemplate.with_context(**kw.get('context'))
        product_template = ProductTemplate.browse(int(product_template_id))
        combination_info = product_template._get_combination_info(combination, int(product_id or 0), int(add_qty or 1), pricelist)
        if 'parent_combination' in kw:
            parent_combination = request.env['product.template.attribute.value'].browse(kw.get('parent_combination'))
            if not combination.exists() and product_id:
                product = request.env['product.product'].browse(int(product_id))
                if product.exists():
                    combination = product.product_template_attribute_value_ids
            combination_info.update({
                'is_combination_possible': product_template._is_combination_possible(combination=combination, parent_combination=parent_combination),
                'parent_exclusions': product_template._get_parent_attribute_exclusions(parent_combination=parent_combination)
            })

        if request.website.google_analytics_key:
            combination_info['product_tracking_info'] = request.env['product.template'].get_google_analytics_data(combination_info)

        if request.website.product_page_image_width != 'none' and not request.env.context.get('website_sale_no_images', False):
            combination_info['carousel'] = request.env['ir.ui.view']._render_template('website_sale.shop_product_images', values={
                'product': request.env['product.template'].browse(combination_info['product_template_id']),
                'product_variant': request.env['product.product'].browse(combination_info['product_id']),
                'website': request.env['website'].get_current_website(),
            })
        return combination_info

    @route('/sale/create_product_variant', type='json', auth="public", methods=['POST'])
    def create_product_variant(self, product_template_id, product_template_attribute_value_ids, **kwargs):
        """Old product configurator logic, only used by frontend configurator, will be deprecated soon"""
        return request.env['product.template'].browse(int(product_template_id)).create_product_variant(json.loads(product_template_attribute_value_ids))
