# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class StockRoute(models.Model):
    _inherit = 'stock.route'

    def _get_global_routes(self):
        return super()._get_global_routes() + [self.env.ref('mrp_subcontracting.route_resupply_subcontractor_mto', raise_if_not_found=False)]

