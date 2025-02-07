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

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:CustomizationID'] = {'_text': self._get_customization_ids()['xrechnung']}
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
