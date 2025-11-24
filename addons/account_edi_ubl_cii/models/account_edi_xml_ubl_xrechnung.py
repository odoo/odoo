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

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # OVERRIDE
        document_node['cac:TaxTotal'] = [
            self._ubl_get_tax_total_node(vals, tax_total)
            for tax_total in vals['_ubl_values']['tax_totals_currency'].values()
        ]

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        if not document_node['cbc:BuyerReference']['_text']:
            document_node['cbc:BuyerReference']['_text'] = 'N/A'

    def _get_party_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        party_node = super()._get_party_node(vals)
        partner = vals['partner']
        if not party_node.get('cbc:EndpointID', {}).get('_text') and partner.email:
            party_node['cbc:EndpointID'] = {
                '_text': partner.email,
                'schemeID': 'EM'
            }
        return party_node

    def _ubl_get_line_allowance_charge_discount_node(self, vals, discount_values):
        # EXTENDS account.edi.xml.ubl_bis3
        discount_node = super()._ubl_get_line_allowance_charge_discount_node(vals, discount_values)
        discount_node['cbc:AllowanceChargeReason'] = None
        discount_node['cbc:MultiplierFactorNumeric'] = None
        discount_node['cbc:BaseAmount'] = None
        return discount_node
