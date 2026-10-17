# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import fields, models

siren_siret_re = re.compile(r'(\d{9}|\d{14})')


VAT_SIREN_RE = re.compile(r'FR[A-Z0-9]{2}([0-9]{9})', re.IGNORECASE)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    siret = fields.Char(string='SIRET', size=14)

    def _deduce_country_code(self):
        if self.siret:
            return 'FR'
        return super()._deduce_country_code()

    def _peppol_eas_endpoint_depends(self):
        # extends account_edi_ubl_cii
        return super()._peppol_eas_endpoint_depends() + ['siret']

    def _l10n_fr_get_siren_from_vat(self):
        self.ensure_one()
        vat = (self.vat or '').replace(' ', '')
        match = VAT_SIREN_RE.fullmatch(vat)
        return match and match.group(1)

    def _l10n_fr_get_siret_or_siren(self):
        self.ensure_one()
        return self.siret or (self.company_registry if self.company_registry and siren_siret_re.fullmatch(self.company_registry) else '')

    def _l10n_fr_get_siren(self):
        self.ensure_one()
        siret_or_siren = self._l10n_fr_get_siret_or_siren()
        if len(siret_or_siren) >= 9:
            return siret_or_siren[:9]
        return self._l10n_fr_get_siren_from_vat()
