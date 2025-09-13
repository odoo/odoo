from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _l10n_es_edi_verifactu_get_values(self):
        values = self._l10n_es_edi_get_partner_info()
        values['NombreRazon'] = (self.name or '')[:120]
        return values
