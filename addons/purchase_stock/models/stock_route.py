# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class StockRoute(models.Model):
    _inherit = 'stock.route'

    def _get_global_routes(self):
        return super()._get_global_routes() + [self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False)]

