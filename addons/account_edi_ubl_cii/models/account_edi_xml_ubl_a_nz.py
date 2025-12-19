# -*- coding: utf-8 -*-

from odoo import models


class AccountEdiXmlUbl_A_Nz(models.AbstractModel):
    _name = 'account.edi.xml.ubl_a_nz'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "A-NZ BIS Billing 3.0"

    """
    * Documentation: https://github.com/A-NZ-PEPPOL/A-NZ-PEPPOL-BIS-3.0/tree/master/Specifications
    """

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_a_nz.xml"

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:aunz:3.0'

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS account.edi.xml.ubl_bis3
        grouping_key = super()._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)
        if not grouping_key:
            return

        grouping_key['scheme_id'] = 'GST'
        return grouping_key

    def _ubl_get_line_allowance_charge_discount_node(self, vals, discount_values):
        # EXTENDS account.edi.xml.ubl_bis3
        discount_node = super()._ubl_get_line_allowance_charge_discount_node(vals, discount_values)
        discount_node['cbc:AllowanceChargeReason'] = None
        discount_node['cbc:MultiplierFactorNumeric'] = None
        discount_node['cbc:BaseAmount'] = None
        return discount_node

    def _ubl_add_values_tax_currency_code(self, vals):
        # OVERRIDE account.edi.xml.ubl_bis3
        self._ubl_add_values_tax_currency_code_empty(vals)

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # OVERRIDE
        document_node['cac:TaxTotal'] = [
            self._ubl_get_tax_total_node(vals, tax_total)
            for tax_total in vals['_ubl_values']['tax_totals_currency'].values()
        ]

    def _get_party_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        party_node = super()._get_party_node(vals)
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.country_code == 'AU' and commercial_partner.vat:
            vat = commercial_partner.vat.replace(" ", "")
            party_node['cbc:EndpointID']['_text'] = vat
            party_node['cac:PartyTaxScheme'][0]['cbc:CompanyID']['_text'] = vat
            party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                '_text': vat,
                'schemeID': '0151',
            }

        elif commercial_partner.country_code == 'NZ':
            party_node['cbc:EndpointID']['_text'] = commercial_partner.company_registry
            party_node['cac:PartyTaxScheme'][0]['cbc:CompanyID']['_text'] = commercial_partner.company_registry
            party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                '_text': commercial_partner.company_registry,
                'schemeID': '0088',
            }

        party_node['cac:PartyTaxScheme'][0]['cac:TaxScheme']['cbc:ID']['_text'] = 'GST'

        return party_node
