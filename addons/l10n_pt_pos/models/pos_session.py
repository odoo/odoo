from odoo import api, models

from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def l10n_pt_pos_get_software_info(self, company_id, config_id):
        company = self.env['res.company'].browse(company_id)
        config = self.env['pos.config'].browse(config_id)
        return {
            'l10n_pt_pos_certification_number': PT_CERTIFICATION_NUMBER,
            'l10n_pt_training_mode': company.account_fiscal_country_id.code == 'PT' and config.l10n_pt_pos_at_series_id.training_series,
        }

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        if self.env.company.country_id.code == 'PT':
            data['data'][0]['_l10n_pt_tax_exemption_reason_selection'] = dict(
                self.env['account.tax']._fields['l10n_pt_tax_exemption_reason'].selection
            )
        return data
