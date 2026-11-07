# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _create_returns(self):
        # Prevent copy of the carrier and carrier price when generating return picking
        # (we have no integration of returns for now)
        new_picking, pick_type_id = super()._create_returns()
        self._reset_carrier_id(new_picking)
        return new_picking, pick_type_id

    def _reset_carrier_id(self, new_picking):
        """ Prevent copy of the carrier and carrier price when generating return picking
        (we have no integration of returns for now).
        """
        picking = self.env['stock.picking'].browse(new_picking)
        picking.write({
            'carrier_id': False,
            'carrier_price': 0.0,
        })
