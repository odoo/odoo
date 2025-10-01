# -*- coding: utf-8 -*-
from odoo import models


class AccountEdiXmlUbl_Sg(models.AbstractModel):
    _name = 'account.edi.xml.ubl_sg'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "SG BIS Billing 3.0"

    """
    Documentation: https://www.peppolguide.sg/billing/bis/
    """

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_sg.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'eu.peppol.bis3.sg.ubl:invoice:1.0.3',
            'credit_note': 'eu.peppol.bis3.sg.ubl:creditnote:1.0.3',
        }

    def _get_partner_party_vals(self, partner, role):
        # EXTENDS account.edi.xml.ubl_bis3
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_partner_party_vals(partner, role)

        for party_tax_scheme in vals.get('party_tax_scheme_vals', []):
            party_tax_scheme['tax_scheme_vals'] = {'id': 'GST'}

        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        """ https://www.peppolguide.sg/billing/bis/#_payment_means_information
        """
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)
        for vals in vals_list:
            vals.update({
                'payment_means_code': 54,
                'payment_means_code_attrs': {'name': 'Credit Card'},
            })

        return vals_list

    def _get_tax_sg_codes(self, tax):
        """ https://www.peppolguide.sg/billing/bis/#_gst_category_codes
        """
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        tax_category_code = 'SR'
        if tax.amount == 0:
            tax_category_code = 'ZR'
        return tax_category_code

    def _get_tax_category_list(self, customer, supplier, taxes):
        # OVERRIDE
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        res = []
        for tax in taxes:
            res.append({
                'id': self._get_tax_sg_codes(tax),
                'percent': tax.amount if tax.amount_type == 'percent' else False,
                'tax_scheme_vals': {'id': 'GST'},
            })
        return res

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        # Old helper not used by default (see _export_invoice override in account.edi.xml.ubl_bis3)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': self._get_customization_ids()['ubl_sg'],
        })

        return vals

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:CustomizationID'] = {'_text': self._get_customization_ids()['ubl_sg']}

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        """ https://www.peppolguide.sg/billing/bis/#_payment_means_information """
        super()._add_invoice_payment_means_nodes(document_node, vals)
        document_node['cac:PaymentMeans']['cbc:PaymentMeansCode'] = {
            '_text': 54,
            'name': 'Credit Card',
        }

    def _get_party_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        party_node = super()._get_party_node(vals)
        party_node['cac:PartyTaxScheme'][0]['cac:TaxScheme']['cbc:ID']['_text'] = 'GST'
        return party_node

    def _get_tax_category_code(self, customer, supplier, tax):
        """ https://www.peppolguide.sg/billing/bis/#_gst_category_codes """
        if not tax or tax.amount == 0:
            return 'ZR'
        return 'SR'

    def _get_tax_category_node(self, vals):
        # OVERRIDE
        tax_category_node = super()._get_tax_category_node(vals)
        tax_category_node['cac:TaxScheme']['cbc:ID']['_text'] = 'GST'
        tax_category_node['cbc:TaxExemptionReason'] = None
        tax_category_node['cbc:TaxExemptionReasonCode'] = None
        return tax_category_node
