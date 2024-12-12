# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpStockReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    def _final_vals_to_lines(self, final_vals, level):
        lines = super()._final_vals_to_lines(final_vals, level)

        for data in lines:
            lot = self.env['stock.lot'].search([('id', '=', data.get('lot_id'))])
            data['columns'].insert(4, lot.expiration_date)

        return lines
