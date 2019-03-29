# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class VariantController(http.Controller):
    @http.route(['/sale/get_combination_info'], type='json', auth="user", methods=['POST'])
    def get_combination_info(self, product_template_id, product_id, combination, add_qty, pricelist_id, **kw):
        combination = request.env['product.template.attribute.value'].browse(combination)
        pricelist = self._get_pricelist(pricelist_id)
        ProductTemplate = request.env['product.template']
        if 'context' in kw:
            ProductTemplate = ProductTemplate.with_context(**kw.get('context'))
        return ProductTemplate.browse(int(product_template_id))._get_combination_info(combination, int(product_id or 0), int(add_qty or 1), pricelist)

    @http.route(['/sale/create_product_variant'], type='json', auth="user", methods=['POST'])
    def create_product_variant(self, product_template_id, product_template_attribute_value_ids, **kwargs):
        return request.env['product.template'].browse(int(product_template_id)).create_product_variant(product_template_attribute_value_ids)

    def _get_pricelist(self, pricelist_id, pricelist_fallback=False):
        return request.env['product.pricelist'].browse(int(pricelist_id or 0))
