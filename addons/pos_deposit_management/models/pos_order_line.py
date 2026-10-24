from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    deposit_main_line_id = fields.Many2one('pos.order.line', ondelete='cascade', index='btree_not_null')
    deposit_line_ids = fields.One2many('pos.order.line', 'deposit_main_line_id')

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['deposit_main_line_id', 'deposit_line_ids']
