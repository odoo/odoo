from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.partner"

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        if self.env.company.country_id.code == 'IN':
            fields += ['l10n_in_gst_treatment']
        return fields
