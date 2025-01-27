from odoo import api, models
from odoo.addons.l10n_pt.const import PT_CERTIFICATION_NUMBER


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def l10n_pt_pos_get_software_info(self, company_id):
        company = self.env['res.company'].browse(company_id)
        return {
            'l10n_pt_pos_certification_number': PT_CERTIFICATION_NUMBER,
            'l10n_pt_training_mode': company.account_fiscal_country_id.code == 'PT' and company.l10n_pt_training_mode,
        }

    def _load_pos_data(self, response):
        data = super()._load_pos_data(response)
        if self.env.company.country_id.code == 'PT':
            data[0]['_l10n_pt_tax_exemption_reason_selection'] = dict(self.env['account.tax']._fields['l10n_pt_tax_exemption_reason'].selection)
        return data
