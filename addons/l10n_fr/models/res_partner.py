import re

from odoo import api, fields, models


VAT_SIREN_RE = re.compile(r'FR[A-Z0-9]{2}([0-9]{9})', re.IGNORECASE)

siren_siret_re = re.compile(r'(\d{9}|\d{14})')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_is_french = fields.Boolean(compute='_compute_l10n_fr_is_french')

    @api.depends('country_code')
    def _compute_l10n_fr_is_french(self):
        for partner in self:
            partner.l10n_fr_is_french = partner.country_code in self.env['res.company']._get_france_country_codes()

    def _l10n_fr_get_siren_from_vat(self):
        self.ensure_one()
        vat = (self.vat or '').replace(' ', '')
        match = VAT_SIREN_RE.fullmatch(vat)
        return match and match.group(1)

    def _l10n_fr_get_siret_or_siren(self):
        self.ensure_one()
        return self.company_registry if self.company_registry and siren_siret_re.fullmatch(self.company_registry) else ''

    def _l10n_fr_get_siren(self):
        self.ensure_one()
        siret_or_siren = self._l10n_fr_get_siret_or_siren()
        if len(siret_or_siren) >= 9:
            return siret_or_siren[:9]
        return self._l10n_fr_get_siren_from_vat()

    def _l10n_fr_get_siret(self):
        self.ensure_one()
        siret_or_siren = self._l10n_fr_get_siret_or_siren()
        return len(siret_or_siren) == 14 and siret_or_siren
