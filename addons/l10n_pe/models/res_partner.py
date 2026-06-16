# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import fields, models, api


# Map a PE-specific additional identifier to the SUNAT vat code reported on
# the EDI document (catalogue 06). RUC lives on `vat` (country=PE) and is
# resolved separately.
# SUNAT code '4' (Carnet de extranjería) is reported for an identifier from another country.
PE_FOREIGN_SUNAT_CODE = '4'
PE_IDENTIFIER_TO_SUNAT_CODE = {
    'PE_DNI': '1',
    'PASSPORT': '7',
    'PE_NDTD': '0',
    'PE_DIC': 'A',
    'PE_IDCR': 'B',
    'PE_TIN': 'C',
    'PE_IN': 'D',
    'PE_TAM': 'E',
    'PE_PTP': 'F',
    'PE_SP': 'G',
    'PE_CPP': 'H',
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pe_district = fields.Many2one(
        'l10n_pe.res.city.district', string='District',
        help='Districts are part of a province or city.')
    l10n_pe_district_name = fields.Char(string='District name', related='l10n_pe_district.name')
    l10n_pe_sunat_code = fields.Char(
        string='PE Identification Type Code',
        compute='_compute_l10n_pe_sunat_code',
        store=True,
        readonly=True,
        help='SUNAT identification type code (catálogo 06) derived from the partner identifiers.',
    )

    @api.depends(
        'vat', 'country_id', 'additional_identifiers',
        'commercial_partner_id.vat', 'commercial_partner_id.country_id',
        'commercial_partner_id.additional_identifiers',
    )
    def _compute_l10n_pe_sunat_code(self):
        for partner in self:
            partner.l10n_pe_sunat_code = partner._l10n_pe_get_identifier()[0]

    def _l10n_pe_get_identifier(self):
        """ Return ``(sunat_code, value)`` of the partner's primary identification for PE
        electronic invoicing, derived from its preferred legal entity identifier (so the
        SUNAT code and the value always agree).

        RUC is the primary identifier and takes precedence over any additional identifier.
        Resolution order:
            1. PE partner with a RUC (`vat`) → '6'.
            2. PE-specific additional identifier (DNI, NDTD, DIC, …) → its mapped code.
            3. A tax id from another country (foreign `vat`) → '0' (SUNAT default).
            4. A typed identifier from another country → '4' (foreign document).
            5. No determinable identification → '0'.
        """
        if not self:
            return ('', '')
        vals = self._get_preferred_legal_entity_identifier_vals()
        key = vals.get('key')
        value = vals.get('value', '')
        if key == 'PE_RUC':
            return ('6', value)  # RUC — the primary identifier
        if key in PE_IDENTIFIER_TO_SUNAT_CODE:
            return (PE_IDENTIFIER_TO_SUNAT_CODE[key], value)
        if vals.get('category') in ('TIN', 'VAT', 'GST'):
            return ('0', value)  # foreign tax number without a typed identifier
        if key:
            return (PE_FOREIGN_SUNAT_CODE, value)  # typed identifier from another country
        return ('0', '')

    @api.onchange('l10n_pe_district')
    def _onchange_l10n_pe_district(self):
        if self.l10n_pe_district:
            self.city_id = self.l10n_pe_district.city_id

    @api.onchange('city_id')
    def _onchange_l10n_pe_city_id(self):
        if self.city_id and self.l10n_pe_district.city_id and self.l10n_pe_district.city_id != self.city_id:
            self.l10n_pe_district = False

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return super()._formatting_address_fields() + ['l10n_pe_district_name']

    def _get_frontend_writable_fields(self):
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.add('l10n_pe_district')

        return frontend_writable_fields

    def _get_mandatory_address_fields(self, country_sudo, **kwargs):
        mandatory_fields = super()._get_mandatory_address_fields(country_sudo, **kwargs)
        if self.env.company.country_code == country_sudo.code == "PE":
            mandatory_fields.add('l10n_pe_district')
        return mandatory_fields
