from odoo import api, fields, models


class UomUom(models.Model):
    _name = 'uom.uom'
    _inherit = ['uom.uom', 'pos.load.mixin']

    is_pos_groupable = fields.Boolean(string='Group Products in POS', help="Check if you want to group products of this unit in point of sale orders")

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'factor', 'is_pos_groupable', 'parent_path', 'rounding']
