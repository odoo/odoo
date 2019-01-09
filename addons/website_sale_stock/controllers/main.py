# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteSale(WebsiteSale):
    def _get_combination_info(self, product_template_id, product_id, combination, add_qty, pricelist, **kw):
        """deprecated, use product method"""
        combination = request.env['product.template.attribute.value'].browse(combination)
        return request.env['product.template'].browse(int(product_template_id))._get_combination_info(combination, product_id, add_qty, pricelist)
