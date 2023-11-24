# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers import reorder


class CustomerPortal(reorder.CustomerPortal):

    def _sale_reorder_get_line_context(self):
        return {
            **super()._sale_reorder_get_line_context(),
            'website_sale_stock_get_quantity': True,
        }
