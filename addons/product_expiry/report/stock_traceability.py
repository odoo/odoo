# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools import format_date


class StockTraceabilityReport(models.TransientModel):
    _inherit = 'stock.traceability.report'

    @api.model
    def _make_dict_move(self, move_line, line_type, level, unfoldable=False):
        formatted_line = super()._make_dict_move(move_line, line_type, level, unfoldable=unfoldable)
        expiration_date_column = self._make_column('expiration_date', format_date(self.env, move_line.lot_id.expiration_date))
        for idx, column in enumerate(formatted_line['columns']):
            if column['name'] == 'lot_name':
                formatted_line['columns'].insert(idx + 1, expiration_date_column)
                break
        return formatted_line
