# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController


class WebsiteSaleStockVariantController(WebsiteSaleVariantController):

    @route()
    def get_combination_info_website(self, *args, **kwargs):
        request.update_context(website_sale_stock_get_quantity=True)
        res = super().get_combination_info_website(*args, **kwargs)
        res['is_storable'] = request.env['product.template'].browse(res['product_template_id']).is_storable
        return res
