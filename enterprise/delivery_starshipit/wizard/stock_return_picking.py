# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _reset_carrier_id(self, picking):
        """ For starshipit, we want to keep the provider when generating a return. """
        if picking.carrier_id.delivery_type != 'starshipit' or not picking.carrier_id.can_generate_return:
            super()._reset_carrier_id(picking)
