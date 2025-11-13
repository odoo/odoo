# -*- coding: utf-8 -*-

from odoo import models, _

DEFAULT_VAT = '0000000000000'
SECTOR_RO_CODES = ('SECTOR1', 'SECTOR2', 'SECTOR3', 'SECTOR4', 'SECTOR5', 'SECTOR6')


def get_formatted_sector_ro(city: str):
    return city.upper().replace(' ', '')


def _has_vat(vat):
    return bool(vat and len(vat) > 1)


class AccountEdiXmlUbl_Ro(models.AbstractModel):
    _name = 'account.edi.xml.ubl_ro'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "CIUS RO"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cius_ro.xml"

    def _get_document_type_code_node(self, invoice, invoice_data):
        # [UBL-SR-43] DocumentTypeCode should only show up on a CreditNote XML with the value '50'
        if invoice.move_type == 'out_refund':
            return {'_text': '50'}

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:CustomizationID'] = {
            '_text': 'urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1'
        }
        document_node['cbc:TaxCurrencyCode'] = {'_text': 'RON'}

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

    def _add_document_tax_total_nodes(self, document_node, vals):
        super()._add_document_tax_total_nodes(document_node, vals)

        document_node['cac:TaxTotal'] = [document_node['cac:TaxTotal']]

        company_currency = vals['invoice'].company_id.currency_id
        if vals['invoice'].currency_id != company_currency:
            self._add_tax_total_node_in_company_currency(document_node, vals)

            # Remove the tax subtotals from the TaxTotal in company currency
            document_node['cac:TaxTotal'][1]['cac:TaxSubtotal'] = None

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS 'account_edi_ubl_cii'
        constraints = super()._export_invoice_constraints(invoice, vals)

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
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_vals(self, tree, role):
        # EXTENDS account.edi.xml.ubl_bis3
        partner_vals = super()._import_retrieve_partner_vals(tree, role)
        if 'peppol_endpoint' in partner_vals:
            # ANAF allows for endpoints to be an address mail, since we don't want to create a new
            # user with an address mail as a PEPPOL endpoint, we simply remove it in that case.
            error = self.env['res.partner']._build_error_peppol_endpoint(False, partner_vals['peppol_endpoint'])
            if error:
                partner_vals['peppol_endpoint'] = False
                partner_vals['peppol_eas'] = False
        return partner_vals
