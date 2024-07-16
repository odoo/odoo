from odoo import models, api

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
