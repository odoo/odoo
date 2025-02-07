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

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:CustomizationID'] = {'_text': self._get_customization_ids()['ubl_a_nz']}

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

    def _get_tax_category_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        tax_category_node = super()._get_tax_category_node(vals)
        tax_category_node['cac:TaxScheme']['cbc:ID']['_text'] = 'GST'
        return tax_category_node
