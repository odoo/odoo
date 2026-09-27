# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.l10n_ec.tools.partner_identifiers import EC_ADDITIONAL_IDENTIFIERS_METADATA

# ATS and SRI codes, keyed by move direction and identification type
EC_PARTNER_ID_CODES = {
    'in_ruc': '01',  # includes final consumer
    'in_cedula': '02',
    'in_passport': '03',
    'in_foreign': '03',
    'out_ruc': '04',  # includes final consumer
    'out_cedula': '05',
    'out_passport': '06',
    'out_foreign': '06',
    'final_consumer': '07',
    'foreign': '08',
}

# any identifier absent here is considered foreign
EC_IDENTIFICATION_TYPES = {
    'EC_RUC': 'ruc',
    'EC_DNI': 'cedula',
    'PASSPORT': 'passport',
}


def verify_final_consumer(vat):
    return vat == '9' * 13  # final consumer is identified with 9999999999999


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_ec_vat_validation = fields.Char(
        string="VAT Error message validation",
        compute="_compute_l10n_ec_vat_validation",
        help="Error message when validating the Ecuadorian VAT",
    )

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **EC_ADDITIONAL_IDENTIFIERS_METADATA}

    @api.depends("vat", "country_id", "additional_identifiers",
                 "commercial_partner_id.vat", "commercial_partner_id.additional_identifiers")
    def _compute_l10n_ec_vat_validation(self):
        for partner in self:
            partner.l10n_ec_vat_validation = False
            vals = partner._get_preferred_tax_identifier_vals()
            if partner.country_code != 'EC' or not vals or verify_final_consumer(vals['value']):
                continue
            if not partner._validate_identifier(vals['key'], vals['value'])['valid']:
                partner.l10n_ec_vat_validation = self.env._(
                    "The VAT %s seems to be invalid as the tenth digit doesn't comply with the validation algorithm "
                    "(SRI has stated that this validation is not required anymore for some VAT numbers)", vals['value'])

    def _l10n_ec_get_ats_code(self, move_type):
        """Returns the ID code of the partner for the given move type, based on a
        subset of Table 2 of SRI's ATS specification."""
        self.ensure_one()
        id_type, value = self._l10n_ec_get_identification_type()
        if verify_final_consumer(value):
            return EC_PARTNER_ID_CODES['final_consumer']
        direction = move_type.split('_')[0]  # 'in' or 'out'
        return EC_PARTNER_ID_CODES.get(f'{direction}_{id_type}')

    def _l10n_ec_get_identification_type(self):
        """Returns the Ecuadorian identification type of the partner's preferred
        identifier, together with its value."""
        self.ensure_one()
        vals = self._get_preferred_legal_entity_identifier_vals()
        return EC_IDENTIFICATION_TYPES.get(vals.get('key'), 'foreign'), vals.get('value', '')
