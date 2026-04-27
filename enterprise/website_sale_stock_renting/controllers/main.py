# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.http import request, route

from odoo.addons.website_sale_renting.controllers.main import WebsiteSaleRenting

class WebsiteSaleStockRenting(WebsiteSaleRenting):

    @route(
        '/rental/product/availabilities', type='json', auth='public', methods=['POST'], website=True
    )
    def renting_product_availabilities(self, product_id, min_date, max_date):
        """ Return rental product availabilities.

        Availabilities are the available quantities of a product for a given period. This is
        expressed by an ordered list of dict {'start': ..., 'end': ..., 'available_quantity': ...).

        :rtype: list(dict)
        """
        product_sudo = request.env['product.product'].sudo().browse(product_id).exists()
        result = {'preparation_time': product_sudo.preparation_time}
        if product_sudo.is_storable and not product_sudo.allow_out_of_stock_order:
            result['renting_availabilities'] = product_sudo._get_availabilities(
                fields.Datetime.to_datetime(min_date),
                fields.Datetime.to_datetime(max_date),
                request.website.warehouse_id.id,
                with_cart=True,
            )
        return result
