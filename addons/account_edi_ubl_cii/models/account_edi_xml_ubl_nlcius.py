# -*- coding: utf-8 -*-

from odoo import models


class AccountEdiXmlUbl_Nl(models.AbstractModel):
    _name = 'account.edi.xml.ubl_nl'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "SI-UBL 2.0 (NLCIUS)"

    """
    SI-UBL 2.0 (NLCIUS) and UBL Bis 3 are 2 different formats used in the Netherlands.
    (source: https://github.com/peppolautoriteit-nl/publications/tree/master/NLCIUS-PEPPOLBIS-Differences)
    NLCIUS defines a set of rules
    (source: https://www.softwarepakketten.nl/wiki_uitleg/60&bronw=7/Nadere_specificaties_EN_16931_1_norm_voor_de_Europese_kernfactuur.htm)
    Fortunately, some of these rules are already present in UBL Bis 3, but some are missing.

    For instance, Bis 3 states that the customizationID should be
    "urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0".
    while in NLCIUS:
    "urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0".

    Bis 3 and NLCIUS are thus incompatible. Hence, the two separate formats and the additional rules in this file.

    The trick is to understand which rules are only NLCIUS specific and which are applied to the Bis 3 format.
    """

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_nlcius.xml"

    def _get_tax_category_list(self, customer, supplier, taxes):
        # EXTENDS account.edi.xml.ubl_bis3
        vals_list = super()._get_tax_category_list(customer, supplier, taxes)
        for tax in vals_list:
            # [BR-NL-35] The use of a tax exemption reason code (cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory
            # /cbc:TaxExemptionReasonCode) is not recommended
            tax.pop('tax_exemption_reason_code', None)
        return vals_list

    def _get_invoice_line_allowance_vals_list(self, base_line):
        # EXTENDS account.edi.xml.ubl_bis3
        vals_list = super()._get_invoice_line_allowance_vals_list(base_line)
        # [BR-NL-32] Use of Discount reason code ( AllowanceChargeReasonCode ) is not recommended.
        # [BR-EN-34] Use of Charge reason code ( AllowanceChargeReasonCode ) is not recommended.
        # Careful! [BR-42]-Each Invoice line allowance (BG-27) shall have an Invoice line allowance reason (BT-139)
        # or an Invoice line allowance reason code (BT-140).
        for vals in vals_list:
            if vals.get('allowance_charge_reason'):
                vals.pop('allowance_charge_reason_code')
        return vals_list

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:CustomizationID'] = {'_text': self._get_customization_ids()['nlcius']}

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_payment_means_nodes(document_node, vals)
        # [BR-NL-29] The use of a payment means text (cac:PaymentMeans/cbc:PaymentMeansCode/@name) is not recommended
        payment_means_node = document_node['cac:PaymentMeans']
        if 'name' in payment_means_node['cbc:PaymentMeansCode']:
            payment_means_node['cbc:PaymentMeansCode']['name'] = None
        if 'listID' in payment_means_node['cbc:PaymentMeansCode']:
            payment_means_node['cbc:PaymentMeansCode']['listID'] = None

    def _get_address_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        address_node = super()._get_address_node(vals)
        # [BR-NL-28] The use of a country subdivision (cac:AccountingCustomerParty/cac:Party/cac:PostalAddress
        # /cbc:CountrySubentity) is not recommended
        address_node['cbc:CountrySubentity'] = None
        return address_node
