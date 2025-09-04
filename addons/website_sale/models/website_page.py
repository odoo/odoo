# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class WebsitePage(models.Model):
    _inherit = 'website.page'

    @api.model
    def _allow_to_use_cache(self, request):
        if not super()._allow_to_use_cache(request):
            return False
        return not request.session.get('sale_order_id') or not request.session.get('website_sale_cart_quantity')

    @api.model
    def _allow_cache_insertion(self, layout):
        return ' data-order-id=' not in layout and super()._allow_cache_insertion(layout)
