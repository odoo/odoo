# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

from odoo.tools.partner_identifiers import TIN_CATEGORIES

from odoo.addons.l10n_co.tools.partner_identifiers import (
    CO_ADDITIONAL_IDENTIFIERS_METADATA,
    CO_DIAN_CODES,
    CO_FOREIGN_ID_DIAN_CODE,
    CO_FOREIGN_VAT_DIAN_CODE,
    CO_NIT_DIAN_CODE,
)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_co_dian_id_code = fields.Char(
        string='CO Identification Type Code',
        compute='_compute_l10n_co_dian_id',
        store=True,
        readonly=True,
    )
    l10n_co_dian_id_value = fields.Char(
        string='CO Identification Number',
        compute='_compute_l10n_co_dian_id',
        store=True,
        readonly=True,
    )

    @api.depends('vat', 'additional_identifiers', 'commercial_partner_id.country_id',
                 'commercial_partner_id.vat', 'commercial_partner_id.additional_identifiers')
    def _compute_l10n_co_dian_id(self):
        """ The DIAN identification the partner is invoiced with, its preferred identifier
        paired with the DIAN code describing which document it is."""
        for partner in self:
            vals = partner._get_preferred_legal_entity_identifier_vals()
            if not vals:
                partner.l10n_co_dian_id_code = partner.l10n_co_dian_id_value = False
                continue
            dian_code = CO_DIAN_CODES.get(vals['key'])
            if not dian_code:
                if vals.get('category') not in TIN_CATEGORIES:
                    dian_code = CO_FOREIGN_ID_DIAN_CODE
                elif 'CO' in (vals.get('countries') or []):
                    dian_code = CO_NIT_DIAN_CODE
                else:
                    dian_code = CO_FOREIGN_VAT_DIAN_CODE
            partner.l10n_co_dian_id_code = dian_code
            partner.l10n_co_dian_id_value = vals['value']

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **CO_ADDITIONAL_IDENTIFIERS_METADATA}
