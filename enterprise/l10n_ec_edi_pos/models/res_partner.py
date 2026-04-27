from odoo import models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'EC':
            result += ['l10n_latam_identification_type_id']
        return result
