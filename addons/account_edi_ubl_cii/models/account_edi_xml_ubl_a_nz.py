# -*- coding: utf-8 -*-

from odoo import models


class AccountEdiXmlUBLANZ(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_a_nz'
    _description = "A-NZ BIS Billing 3.0"

    """
    * Documentation: https://github.com/A-NZ-PEPPOL/A-NZ-PEPPOL-BIS-3.0/tree/master/Specifications
    """

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_a_nz.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'eu.peppol.bis3.aunz.ubl:invoice:1.0.8',
            'credit_note': 'eu.peppol.bis3.aunz.ubl:creditnote:1.0.8',
        }

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS account.edi.xml.ubl_bis3
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        for vals in vals_list:
            if partner.country_id.code == "AU" and partner.vat:
                vals['company_id'] = partner.vat.replace(" ", "")

        return vals_list

    def _get_partner_party_vals(self, partner, role):
        # EXTENDS account.edi.xml.ubl_bis3
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_partner_party_vals(partner, role)
        vals.setdefault('party_tax_scheme_vals', [])

        if partner.country_code == 'AU' and partner.vat:
            vals['endpoint_id'] = partner.vat.replace(" ", "")
        if partner.country_code == 'NZ':
            vals['endpoint_id'] = partner.company_registry

        for party_tax_scheme in vals['party_tax_scheme_vals']:
            party_tax_scheme['tax_scheme_vals'] = {'id': 'GST'}

        return vals

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_bis3
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)

        for vals in vals_list:
            if partner.country_code == 'AU' and partner.vat:
                vals.update({
                    'company_id': partner.vat.replace(" ", ""),
                    'company_id_attrs': {'schemeID': '0151'},
                })
            if partner.country_code == 'NZ':
                vals.update({
                    'company_id': partner.company_registry,
                    'company_id_attrs': {'schemeID': '0088'},
                })
        return vals_list

    def _get_tax_category_list(self, customer, supplier, taxes):
        # EXTENDS account.edi.xml.ubl_bis3
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_tax_category_list(customer, supplier, taxes)
        for vals in vals_list:
            vals['tax_scheme_vals'] = {'id': 'GST'}
        return vals_list

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': self._get_customization_ids()['ubl_a_nz'],
        })

        return vals

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

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
