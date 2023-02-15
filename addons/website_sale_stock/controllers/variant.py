# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController


class WebsiteSaleStockVariantController(WebsiteSaleVariantController):
    @http.route()
    def get_combination_info_website(self, product_template_id, product_id, combination, add_qty, **kw):
        kw['context'] = kw.get('context') or {}  # context may be passed as None in some cases
        kw['context'].update(website_sale_stock_get_quantity=True)
        return super(WebsiteSaleStockVariantController, self).get_combination_info_website(product_template_id, product_id, combination, add_qty, **kw)
