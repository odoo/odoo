# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _prepare_move_for_asset_depreciation(self, vals):
        # Overridden in order to link the depreciation entries with the vehicle_id
        move_vals = super()._prepare_move_for_asset_depreciation(vals)
        if vals['asset_id'].vehicle_id:
            for _command, _id, line_vals in move_vals['line_ids']:
                line_vals['vehicle_id'] = vals['asset_id'].vehicle_id.id
        return move_vals
