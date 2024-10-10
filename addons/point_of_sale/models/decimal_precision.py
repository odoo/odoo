from odoo import models, api


class DecimalPrecision(models.Model):
    _inherit = ['decimal.precision', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'digits']
