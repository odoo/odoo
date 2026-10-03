# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from stdnum.fr import siren, siret

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    siret = fields.Char(string='SIRET', size=14)

    @api.model
    def _l10n_fr_compact_identifiers(self, vals, country_id=None):
        if vals.get('siret'):
            compacted = siret.compact(vals['siret'])
            if compacted.isascii() and compacted.isdigit():
                vals['siret'] = compacted
        if vals.get('company_registry') and country_id == self.env.ref('base.fr').id:
            compacted = siren.compact(vals['company_registry'])
            if len(compacted) in (9, 14) and compacted.isascii() and compacted.isdigit():
                vals['company_registry'] = compacted

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._l10n_fr_compact_identifiers(vals, vals.get('country_id'))
        return super().create(vals_list)

    def write(self, vals):
        country_id = vals.get('country_id')
        if vals.get('company_registry') and 'country_id' not in vals:
            country_ids = self.country_id
            if len(country_ids) == 1:
                country_id = country_ids.id
        self._l10n_fr_compact_identifiers(vals, country_id)
        return super().write(vals)

    def _deduce_country_code(self):
        if self.siret:
            return 'FR'
        return super()._deduce_country_code()

    def _peppol_eas_endpoint_depends(self):
        # extends account_edi_ubl_cii
        return super()._peppol_eas_endpoint_depends() + ['siret']
