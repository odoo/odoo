# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.http import request

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleStockRenting(WebsiteSale):

    def _shop_lookup_products(self, attrib_set, options, post, search, website):
        # Override to add rental stock search on /shop
        fuzzy_search_term, product_count, search_result = super()._shop_lookup_products(attrib_set, options, post, search, website)
        if options.get('from_date') and options.get('to_date'):
            try:
                search_result = search_result.sudo()._filter_on_available_rental_products(
                    fields.Datetime.to_datetime(options.get('from_date')),
                    fields.Datetime.to_datetime(options.get('to_date')),
                    request.website.warehouse_id.id,
                )
                product_count = len(search_result)
            except ValueError:
                # Invalid date format
                pass
        return fuzzy_search_term, product_count, search_result
