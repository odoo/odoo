from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'MX':
            result += ['l10n_mx_edi_fiscal_regime', 'l10n_mx_edi_usage', 'l10n_mx_edi_no_tax_breakdown', 'country_code']
        return result
