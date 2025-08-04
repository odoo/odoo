from odoo import models, api


class DecimalPrecision(models.Model):
    _name = 'decimal.precision'
    _inherit = ['decimal.precision', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'max_digits']
