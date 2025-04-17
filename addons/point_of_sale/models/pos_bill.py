# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosBill(models.Model):
    _name = 'pos.bill'
    _order = 'value'
    _description = 'Coins/Bills'
    _inherit = ['pos.load.mixin']

    name = fields.Char('Name')
    value = fields.Float('Value', required=True, digits=(16, 4))
    pos_config_ids = fields.Many2many('pos.config', string='Point of Sales')

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'value']
