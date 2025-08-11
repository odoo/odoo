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

        if partner.state_id:
            address_node['cbc:CountrySubentity']['_text'] = partner.country_code + '-' + partner.state_id.code

            # Romania requires the CityName to be in the format of "SECTORX" if the address state is in Bucharest.
            if partner.state_id.code == 'B' and partner.city:
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

    def _get_uom_unece_code(self, uom):
        """Use RO SAF-T code if available, else fall back to standard UNECE code."""
        if not uom:
            return 'H87'

        return uom.ro_saft_code or uom._get_unece_code()

    def _add_document_line_amount_nodes(self, line_node, vals):
        currency_suffix = vals['currency_suffix']
        base_line = vals['base_line']

        quantity_tag = self._get_tags_for_document_type(vals)['line_quantity']

        line_node.update({
            quantity_tag: {
                '_text': base_line['quantity'],
                'unitCode': self._get_uom_unece_code(base_line['product_uom_id']),
            },
            'cbc:LineExtensionAmount': {
                '_text': self.format_float(vals[f'total_excluded{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        })
