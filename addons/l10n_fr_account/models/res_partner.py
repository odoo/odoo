# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_peppol_endpoint_value(self, country_code, field):
        if country_code == 'FR' and field == 'peppol_endpoint':
            # Let l10n_fr_pdp, if installed, use its own SIREN lookup regardless of the model extension order.
            if hasattr(self, '_get_suggested_pdp_identifier'):
                return self._get_suggested_pdp_identifier()
            if not self.siret:
                return self._l10n_fr_get_siren_from_vat()
        return super()._get_peppol_endpoint_value(country_code, field)
