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

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:cen.eu:en16931:2017#conformant#urn:fdc:peppol.eu:2017:poacc:billing:international:sg:3.0'

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS account.edi.xml.ubl_bis3
        grouping_key = super()._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)
        if not grouping_key:
            return

        grouping_key['tax_exemption_reason'] = None
        grouping_key['tax_exemption_reason_code'] = None

        # For reference: https://www.peppolguide.sg/billing/bis/#_gst_category_codes
        if not tax_data or tax_data['tax'].amount == 0.0:
            grouping_key['tax_category_code'] = 'ZR'
        else:
            grouping_key['tax_category_code'] = 'SR'

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

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        """ https://www.peppolguide.sg/billing/bis/#_payment_means_information """
        super()._add_invoice_payment_means_nodes(document_node, vals)
        document_node['cac:PaymentMeans']['cbc:PaymentMeansCode'] = {
            '_text': 54,
            'name': 'Credit Card',
        }
