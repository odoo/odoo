# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale_stock.controllers.variant import WebsiteSaleStockVariantController


class WebsiteSaleMrpVariantController(WebsiteSaleStockVariantController):

    @route('/website_sale_mrp/get_unavailable_qty_from_kits', type='jsonrpc', auth='public', website=True)
    def get_unavailable_qty_from_kits(self, product_id=None, *args, **kwargs):
        so = request.cart
        if not so:
            return 0
        product = request.env['product.product'].browse(product_id)
        return so._get_unavailable_quantity_from_kits(product)
