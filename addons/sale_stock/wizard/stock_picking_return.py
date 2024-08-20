# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _exchange_move_location(self):
        return self.picking_id.sale_id.picking_ids[0].location_id.id
