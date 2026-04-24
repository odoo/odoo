# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    history_line_ids = fields.One2many('pos.history.line', 'order_id', string='History Lines', copy=True)

    # update indexed db data with synced data for history lines
    def read_pos_data(self, data, config):
        results = super().read_pos_data(data, config)
        results['pos.history.line'] = self.env['pos.history.line']._load_pos_data_read(self.history_line_ids, config) if config else []
        return results
