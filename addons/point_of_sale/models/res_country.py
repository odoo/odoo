from odoo import models, api


class ResCountry(models.Model):
    _name = 'res.country'
    _inherit = ['res.country', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'code', 'vat_label']
