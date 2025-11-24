# -*- coding: utf-8 -*-

from odoo import models, _

DEFAULT_VAT = '0000000000000'
SECTOR_RO_CODES = ('SECTOR1', 'SECTOR2', 'SECTOR3', 'SECTOR4', 'SECTOR5', 'SECTOR6')


def get_formatted_sector_ro(city: str):
    return city.upper().replace(' ', '')


def _has_vat(vat):
    return bool(vat and len(vat) > 1)


class AccountEdiXmlUBLRO(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = "account.edi.xml.ubl_ro"
    _description = "CIUS RO"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _get_partner_address_vals(self, partner):
        # EXTENDS 'account_edi_ubl_cii'
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_partner_address_vals(partner)

        if partner.state_id:
            vals["country_subentity"] = partner.country_code + '-' + partner.state_id.code

            # Romania requires the CityName to be in the format of "SECTORX" if the address state is in Bucharest.
            if partner.state_id.code == 'B' and partner.city:
                vals['city_name'] = get_formatted_sector_ro(partner.city)

        return vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS 'account_edi_ubl_cii'
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        if invoice.currency_id.name != 'RON':
            ron_currency = self.env.ref("base.RON")
            vals_list.append({
                'currency': ron_currency,
                'currency_dp': ron_currency.decimal_places,
                'tax_amount': taxes_vals['tax_amount'],
            })

        return vals_list

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS 'account_edi_ubl_cii'
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        if not _has_vat(partner.vat):
            if (
                role == 'supplier'
                and partner.company_registry
            ):
                # Use company_registry (Company ID) as the VAT replacement
                for vals in vals_list:
                    tax_scheme_id = 'VAT' if partner.company_registry[:2].isalpha() else 'NOT_EU_VAT'
                    vals.update({'company_id': partner.company_registry, 'tax_scheme_vals': {'id': tax_scheme_id}})
            elif role == 'customer':
                for vals in vals_list:
                    vals.update({'company_id': DEFAULT_VAT, 'tax_scheme_vals': {'id': 'NOT_EU_VAT'}})

        return vals_list

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'account_edi_ubl_cii'
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1',
            'tax_currency_code': 'RON',
        })

        # Deal with legal_entity_vals here, as there is no way to distinguish between customer and supplier in _get_partner_party_legal_entity_vals_list
        for role in ['supplier', 'customer']:
            for legal_entity_vals in vals['vals'][f'accounting_{role}_party_vals']['party_vals']['party_legal_entity_vals']:
                partner = legal_entity_vals['commercial_partner']
                if not _has_vat(partner.vat):
                    legal_entity_vals['company_id'] = partner.company_registry if role == 'supplier' else DEFAULT_VAT

        return vals

    def _get_document_type_code_vals(self, invoice, invoice_data):
        # EXTENDS 'account_edi_ubl_cii
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_document_type_code_vals(invoice, invoice_data)
        # [UBL-SR-43] DocumentTypeCode should only show up on a CreditNote XML with the value '50'
        vals['value'] = '50' if invoice.move_type == 'out_refund' else False
        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS 'account_edi_ubl_cii'
        constraints = super()._export_invoice_constraints(invoice, vals)
        constraints.update(self._export_invoice_constraints_ciusro(vals))
        return constraints

    def _export_invoice_constraints_ciusro(self, vals):
        constraints = {}
        # Default VAT is only allowed for the receiver (customer), not the provider (supplier)
        supplier = vals['supplier'].commercial_partner_id
        if (
            not _has_vat(supplier.vat)
            and not vals['supplier'].commercial_partner_id.company_registry
        ):
            constraints["ciusro_supplier_tax_identifier_required"] = _(
                "The following partner doesn't have a VAT nor Company ID: %s. "
                "At least one of them is required. ",
                vals['supplier'].display_name)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]

            constraints.update({
                f"ciusro_{partner_type}_city_required": self._check_required_fields(partner, 'city'),
                f"ciusro_{partner_type}_street_required": self._check_required_fields(partner, 'street'),
                f"ciusro_{partner_type}_state_id_required": self._check_required_fields(partner, 'state_id'),
            })

            if (partner.country_code == 'RO'
                    and partner.state_id
                    and partner.state_id.code == 'B'
                    and partner.city
                    and get_formatted_sector_ro(partner.city) not in SECTOR_RO_CODES):
                constraints[f"ciusro_{partner_type}_invalid_city_name"] = _(
                    "The following partner's city name is invalid: %s. "
                    "If partner's state is București, the city name must be 'SECTORX', "
                    "where X is a number between 1-6.",
                    partner.display_name)

        return constraints

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _ubl_add_values_tax_currency_code(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        self._ubl_add_values_tax_currency_code_company_currency(vals)

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:CustomizationID'] = {
            '_text': 'urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1'
        }

    def _get_address_node(self, vals):
        address_node = super()._get_address_node(vals)
        partner = vals['partner']

        if partner._name == 'res.bank':
            state = partner.state
        else:
            state = partner.state_id

        if state:
            address_node['cbc:CountrySubentity']['_text'] = partner.country_code + '-' + state.code

            # Romania requires the CityName to be in the format of "SECTORX" if the address state is in Bucharest.
            if state.code == 'B' and partner.city:
                address_node['cbc:CityName']['_text'] = get_formatted_sector_ro(partner.city)

        return address_node

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)
        commercial_partner = vals['partner'].commercial_partner_id

        # Use the default VAT if the VAT is not filled or just has a placeholder
        if not _has_vat(commercial_partner.vat):
            if vals['role'] == 'supplier' and commercial_partner.company_registry:
                # Use company_registry (Company ID) as the VAT replacement
                vat_replacement = commercial_partner.company_registry
            else:
                vat_replacement = DEFAULT_VAT

            party_node['cac:PartyTaxScheme'][0]['cbc:CompanyID']['_text'] = vat_replacement
            party_node['cac:PartyTaxScheme'][0]['cac:TaxScheme']['cbc:ID']['_text'] = (
                'VAT' if vat_replacement[:2].isalpha() else 'NOT_EU_VAT'
            )
            party_node['cac:PartyLegalEntity']['cbc:CompanyID']['_text'] = vat_replacement

        return party_node

    def _export_invoice_constraints_new(self, invoice, vals):
        constraints = super()._export_invoice_constraints_new(invoice, vals)
        constraints.update(self._export_invoice_constraints_ciusro(vals))
        return constraints
