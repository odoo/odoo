# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        # Prevent copy of the carrier and carrier price when generating return picking if it does not support them.
        new_picking, pick_type_id = super()._create_returns()
        picking = self.env['stock.picking'].browse(new_picking)
        if picking.carrier_id and not picking.carrier_id.can_generate_return:
            picking.write({'carrier_id': False,
                           'carrier_price': 0.0})
        return new_picking, pick_type_id
