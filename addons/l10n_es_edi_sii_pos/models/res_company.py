from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_es_pos_get_available_fiscal_modes(self):
        modes = super()._l10n_es_pos_get_available_fiscal_modes()
        if self.l10n_es_sii_tax_agency:
            modes.add('sii')
        return modes
