import re

from odoo import models


siren_siret_re = re.compile(r'(\d{9}|\d{14})')


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

    def _l10n_fr_get_siret_or_siren(self):
        self.ensure_one()
        candidates = [
            self.additional_identifiers['FR_SIRET'] if self.additional_identifiers and siren_siret_re.match(self.additional_identifiers.get('FR_SIRET', '')) else '',
            self.additional_identifiers['FR_SIREN'] if self.additional_identifiers and siren_siret_re.match(self.additional_identifiers.get('FR_SIREN', '')) else '',
            self.company_registry if self.company_registry and siren_siret_re.match(self.company_registry) else '',
            self._l10n_fr_get_siren_from_vat(),
        ]
        for identifier in candidates:
            if not identifier:
                continue
            return identifier
        return ''

    def _l10n_fr_get_siren(self):
        self.ensure_one()
        siret_or_siren = self._l10n_fr_get_siret_or_siren()
        return siret_or_siren[:9]

    def _l10n_fr_get_siret(self):
        self.ensure_one()
        siret_or_siren = self._l10n_fr_get_siret_or_siren()
        return len(siret_or_siren) == 14 and siret_or_siren
