from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['l10n_es_edi_verifactu_required']

    def _l10n_es_pos_get_available_fiscal_modes(self):
        modes = super()._l10n_es_pos_get_available_fiscal_modes()
        if self.l10n_es_edi_verifactu_required:
            modes.add('verifactu')
        return modes
