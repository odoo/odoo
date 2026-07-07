from stdnum.fr import siret
from stdnum.util import isdigits

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_is_french = fields.Boolean(compute='_compute_l10n_fr_is_french')

    @api.depends('country_code')
    def _compute_l10n_fr_is_french(self):
        for partner in self:
            partner.l10n_fr_is_french = partner.country_code in self.env['res.company']._get_france_country_codes()

    def _synced_commercial_fields(self):
        # override to propagate siret / siren for french partners, in addition
        # to other synchronized commercial fields (upstream and downstream,
        # see original method's docstring)
        if all(partner.l10n_fr_is_french for partner in self):
            return [
            *super()._synced_commercial_fields(),
            'company_registry',
        ]
        return super()._synced_commercial_fields()

    def _fields_sync_upstream_sync_commercial_values(self, targets, synced_commercials):
        # override to find siren from siret and propagate change only if siret
        # (company_registry) is valid, and if siren changed
        targets_same_siren = targets.browse()
        for fname, fvalue in synced_commercials.items():
            if fname != 'company_registry':
                continue
            if not siret.is_valid(fvalue):
                # does not matches siret -> do not propagate upstream
                synced_commercials.pop('company_registry')
                break
            new_siren = siret.to_siren(fvalue)
            for target in targets:
                old_siren = target._l10nfr_get_siren()
                if old_siren == new_siren:
                    targets_same_siren += target
        if targets_same_siren:
            synced_commercials_wo_siret = dict(synced_commercials)
            synced_commercials_wo_siret.pop('company_registry')
            if synced_commercials_wo_siret:
                super()._fields_sync_upstream_sync_commercial_values(targets_same_siren, synced_commercials_wo_siret)

        return super()._fields_sync_upstream_sync_commercial_values(targets - targets_same_siren, synced_commercials)

    def _l10nfr_is_company_registry_siret_valid(self):
        """ Expectation: people put a siret number into company_registry.
        Siret is a char string of 14 characters: 9 first are siren (company)
        and 5 next are specific to an institution of this company. Number
        should follow luhn algorithm to be valid (checksum).

        VAT can be deduced from siren directly, if valid. """
        self.ensure_one()
        return siret.is_valid(self.company_registry or '')

    def _l10nfr_get_institution(self) -> str:
        if self._l10nfr_is_company_registry_siret_valid():
            return self._l10nfr_siret_to_institution(self.company_registry)
        return ''

    def _l10nfr_get_siren(self) -> str:
        if self._l10nfr_is_company_registry_siret_valid():
            return siret.to_siren(self.company_registry)
        return ''

    @staticmethod
    def _l10nfr_siret_to_institution(siret_number: str) -> str:
        """ Convert the SIRET number to an institution number, aka the 5 following
        digits after the SIREN. Inspired from stdnum.fr.siret.to_siren. """
        if not siret.is_valid(siret_number):
            return ''
        institution = []
        digit_count = 0
        for char in siret_number:
            if isdigits(char):
                if digit_count >= 9:
                    institution.append(char)
                digit_count += 1
        return ''.join(institution)

    @staticmethod
    def _l10nfr_siren_to_vat(siret_number: str) -> str:
        """ Replace stdnum.fr.siren to_tva as it seems wrong. Computation should
        be '[ 12 + 3 * ( SIREN modulo 97 ) ] modulo 97', and the 3* has been
        forgotten in computation.

        Note: siret = siren + 5 characters"""
        if not siret.is_valid(siret_number):
            return ''
        siren_number = siret.to_siren(siret_number)
        compated_number = int(siret.compact(siren_number))
        return '%02d%s%s' % (
            ((compated_number % 97) * 3 + 12) % 97,
            ' ' if ' ' in siren_number else '',
            siren_number,
        )
