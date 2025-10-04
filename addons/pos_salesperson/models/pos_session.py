from odoo import api, models

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        if 'hr.employee' not in data:
            data += ['hr.employee']
        return data
