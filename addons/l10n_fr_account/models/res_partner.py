from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_peppol_endpoint_value(self, country_code, field, eas):
        endpoint = super()._get_peppol_endpoint_value(country_code, field, eas)
        identifiers = self.additional_identifiers or {}
        if (
            not endpoint
            and country_code == 'FR'
            and field == 'peppol_endpoint'
            and not identifiers.get('FR_SIRET')
            and not identifiers.get('FR_SIREN')
            and not self.company_registry
        ):
            return self._l10n_fr_get_siren_from_vat()
        return endpoint
