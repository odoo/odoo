# Part of Odoo. See LICENSE file for full copyright and licensing details
from odoo import fields, models, api

from odoo.tools.partner_identifiers import TIN_CATEGORIES

from odoo.addons.l10n_pe.tools.partner_identifiers import (
    PE_ADDITIONAL_IDENTIFIERS_METADATA,
    PE_FOREIGN_ID_SUNAT_CODE,
    PE_FOREIGN_VAT_SUNAT_CODE,
    PE_RUC_SUNAT_CODE,
    PE_SUNAT_CODES,
)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_pe_district = fields.Many2one(
        'l10n_pe.res.city.district', string='District',
        help='Districts are part of a province or city.')
    l10n_pe_district_name = fields.Char(string='District name', related='l10n_pe_district.name')
    l10n_pe_sunat_id_code = fields.Char(
        string='PE Identification Type Code',
        compute='_compute_l10n_pe_sunat_identification',
        store=True,
        readonly=True,
        help='SUNAT identification type code (catálogo 06) derived from the partner identifiers.',
    )
    l10n_pe_sunat_id_value = fields.Char(
        string='PE Identification Number',
        compute='_compute_l10n_pe_sunat_identification',
        store=True,
        readonly=True,
        help='Identification number reported to SUNAT.',
    )

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **PE_ADDITIONAL_IDENTIFIERS_METADATA}

    @api.depends('vat', 'additional_identifiers', 'commercial_partner_id.country_id',
                 'commercial_partner_id.vat', 'commercial_partner_id.additional_identifiers')
    def _compute_l10n_pe_sunat_identification(self):
        """ The identification the partner is invoiced with, its preferred identifier paired
        with the SUNAT code (catálogo 06) describing which document it is. """
        for partner in self:
            vals = partner._get_preferred_legal_entity_identifier_vals()
            if not (sunat_code := PE_SUNAT_CODES.get(vals.get('key'))):
                if 'PE' in (vals.get('countries') or []) and vals.get('category') in TIN_CATEGORIES:
                    sunat_code = PE_RUC_SUNAT_CODE
                elif vals and vals.get('category') not in TIN_CATEGORIES:
                    sunat_code = PE_FOREIGN_ID_SUNAT_CODE
                else:
                    sunat_code = PE_FOREIGN_VAT_SUNAT_CODE
            partner.l10n_pe_sunat_id_code = sunat_code
            partner.l10n_pe_sunat_id_value = vals.get('value')

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
