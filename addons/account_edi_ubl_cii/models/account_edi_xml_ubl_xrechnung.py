# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUbl_De(models.AbstractModel):
    _name = 'account.edi.xml.ubl_de'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "BIS3 DE (XRechnung)"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_de.xml"

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        constraints = super()._export_invoice_constraints(invoice, vals)

        constraints.update({
            'bis3_de_supplier_telephone_required': self._check_required_fields(vals['supplier'], ['phone']),
            'bis3_de_supplier_electronic_mail_required': self._check_required_fields(vals['supplier'], 'email'),
        })

        return constraints

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0'

    def _ubl_add_values_tax_currency_code(self, vals):
        # OVERRIDE account.edi.xml.ubl_bis3
        self._ubl_add_values_tax_currency_code_empty(vals)

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS account.edi.xml.ubl_bis3
        tax_total_keys = super()._ubl_tax_totals_node_grouping_key(base_line, tax_data, vals, currency)

        company_currency = vals['company'].currency_id
        if (
            tax_total_keys['tax_total_key']
            and company_currency != vals['currency']
            and tax_total_keys['tax_total_key']['currency'] == company_currency
        ):
            tax_total_keys['tax_total_key'] = None

        return tax_total_keys

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        if not document_node['cbc:BuyerReference']['_text']:
            document_node['cbc:BuyerReference']['_text'] = 'N/A'

    def _ubl_add_party_endpoint_id_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_party_endpoint_id_node(vals)
        partner = vals['party_vals']['partner']

        if not vals['party_node']['cbc:EndpointID']['_text'] and partner.email:
            vals['party_node']['cbc:EndpointID'] = {
                '_text': partner.email,
                'schemeID': 'EM'
            }

    def _ubl_add_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_party_tax_scheme_nodes(vals)
        nodes = vals['party_node']['cac:PartyTaxScheme']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if (
            not nodes
            and commercial_partner.peppol_eas
        ):
            nodes.append({
                'cbc:CompanyID': {'_text': None},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': commercial_partner.peppol_eas},
                },
            })

    def _ubl_add_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_party_legal_entity_nodes(vals)
        nodes = vals['party_node']['cac:PartyLegalEntity']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if (
            not nodes
            and commercial_partner.name
        ):
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': None,
                    'schemeID': None,
                },
            })

    def _ubl_get_line_allowance_charge_discount_node(self, vals, discount_values):
        # EXTENDS account.edi.xml.ubl_bis3
        discount_node = super()._ubl_get_line_allowance_charge_discount_node(vals, discount_values)
        discount_node['cbc:AllowanceChargeReason'] = None
        discount_node['cbc:MultiplierFactorNumeric'] = None
        discount_node['cbc:BaseAmount'] = None
        return discount_node
