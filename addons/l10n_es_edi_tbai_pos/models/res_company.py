from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_es_pos_get_available_fiscal_modes(self):
        # EXTENDS 'l10n_es_edi_pos'
        modes = super()._l10n_es_pos_get_available_fiscal_modes()
        if self.l10n_es_tbai_is_enabled:
            modes.add('tbai')
        return modes
