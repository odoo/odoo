from odoo import api, fields, models


class PosPreset(models.Model):
    _inherit = 'pos.preset'

    use_guest = fields.Boolean(string='Guest', default=False, help="Force guest selection when clicking on order button in PoS restaurant")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['use_guest']
