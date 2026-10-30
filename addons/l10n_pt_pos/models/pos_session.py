from odoo import api, models

from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER
from odoo.addons.l10n_pt_certification.models.account_tax import L10N_PT_TAX_EXEMPTION_PRINTED_REASONS


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def l10n_pt_pos_get_software_info(self, company_id, config_id):
        return {
            'l10n_pt_pos_certification_number': PT_CERTIFICATION_NUMBER,
        }

    @api.model
    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)
        if data and config.country_code == 'PT':
            data[0]['_l10n_pt_tax_exemption_reasons'] = L10N_PT_TAX_EXEMPTION_PRINTED_REASONS
        return data
