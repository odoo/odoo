<<<<<<< 8c6c6d824d9ef100b18f776a742c044f8e7a3431
from odoo import api, fields, models
||||||| 023017c49899b33e23e3130144deda9ebbe99731
from odoo import models
=======
import re

from odoo import models
>>>>>>> 088f2712bb7d73ee947f4001ab15ef791df43e89


siren_siret_re = re.compile(r'(\d{9}|\d{14})')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_siret = fields.Char(compute='_compute_l10n_fr_siret', inverse='_inverse_l10n_fr_siret')
    l10n_fr_siren = fields.Char(compute='_compute_l10n_fr_siren', inverse='_inverse_l10n_fr_siren')

    @api.depends('additional_identifiers')
    def _compute_l10n_fr_siret(self):
        for partner in self:
            partner.l10n_fr_siret = partner._get_additional_identifier('FR_SIRET')

    def _inverse_l10n_fr_siret(self):
        for partner in self:
            partner._set_additional_identifier('FR_SIRET', partner.l10n_fr_siret)

    @api.depends('additional_identifiers')
    def _compute_l10n_fr_siren(self):
        for partner in self:
            # Will deduce SIREN from SIRET if available
            partner.l10n_fr_siren = partner._get_all_identifiers(enrich=True).get('FR_SIREN')

    def _inverse_l10n_fr_siren(self):
        for partner in self:
            partner._set_additional_identifier('FR_SIREN', partner.l10n_fr_siren)

    def _get_preferred_routing_identifier_vals(self, force_recompute=False):
        identifier_vals = super()._get_preferred_routing_identifier_vals(force_recompute=force_recompute)
        partner = self.commercial_partner_id or self
        if (
            partner.country_code == 'FR'
            and identifier_vals.get('key') == 'FR_VAT'
            and (siren := partner._l10n_fr_get_siren_from_vat())
        ):
<<<<<<< 8c6c6d824d9ef100b18f776a742c044f8e7a3431
            return {'scheme': '0225', 'value': siren, 'key': 'FR_CTC'}
        return identifier_vals
||||||| 023017c49899b33e23e3130144deda9ebbe99731
            return self._l10n_fr_get_siren_from_vat()
        return endpoint
=======
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
>>>>>>> 088f2712bb7d73ee947f4001ab15ef791df43e89
