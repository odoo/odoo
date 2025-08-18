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

    def _get_tax_category_code(self, customer, supplier, tax):
        """ https://www.peppolguide.sg/billing/bis/#_gst_category_codes """
        if not tax or tax.amount == 0:
            return 'ZR'
        return 'SR'

    # -------------------------------------------------------------------------
    # EXPORT: Templates
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

    def _get_tax_category_node(self, vals):
        # OVERRIDE
        tax_category_node = super()._get_tax_category_node(vals)
        tax_category_node['cac:TaxScheme']['cbc:ID']['_text'] = 'GST'
        return tax_category_node
