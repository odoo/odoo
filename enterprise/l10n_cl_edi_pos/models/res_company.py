from odoo import models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'CL':
            result += ['l10n_cl_dte_resolution_number', 'l10n_cl_dte_resolution_date', 'l10n_cl_sii_regional_office']
        return result
