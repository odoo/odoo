# -*- coding: utf-8 -*-

from odoo import models


class AccountEdiXmlUBLNL(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.ubl_nl'
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

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'org.simplerinvoicing:invoice:2.0.3.3',
            'credit_note': 'org.simplerinvoicing:creditnote:2.0.3.3',
        }

    def _get_tax_category_list(self, invoice, taxes):
        # EXTENDS account.edi.xml.ubl_bis3
        vals_list = super()._get_tax_category_list(invoice, taxes)
        for tax in vals_list:
            # [BR-NL-35] The use of a tax exemption reason code (cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory
            # /cbc:TaxExemptionReasonCode) is not recommended
            tax.pop('tax_exemption_reason_code', None)
        return vals_list

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._get_partner_address_vals(partner)
        # [BR-NL-28] The use of a country subdivision (cac:AccountingCustomerParty/cac:Party/cac:PostalAddress
        # /cbc:CountrySubentity) is not recommended
        vals.pop('country_subentity', None)
        return vals

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list=None):
        # EXTENDS account.edi.xml.ubl_bis3
        vals_list = super()._get_invoice_line_allowance_vals_list(line, tax_values_list=tax_values_list)
        # [BR-NL-32] Use of Discount reason code ( AllowanceChargeReasonCode ) is not recommended.
        # [BR-EN-34] Use of Charge reason code ( AllowanceChargeReasonCode ) is not recommended.
        # Careful! [BR-42]-Each Invoice line allowance (BG-27) shall have an Invoice line allowance reason (BT-139)
        # or an Invoice line allowance reason code (BT-140).
        for vals in vals_list:
            if vals['allowance_charge_reason_code'] == 95:
                vals['allowance_charge_reason'] = 'Discount'
            if vals.get('allowance_charge_reason'):
                vals.pop('allowance_charge_reason_code')
        return vals_list

    def _get_invoice_payment_means_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)
        # [BR-NL-29] The use of a payment means text (cac:PaymentMeans/cbc:PaymentMeansCode/@name) is not recommended
        for vals in vals_list:
            vals.pop('payment_means_code_attrs', None)
        return vals_list

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)

        vals['vals']['customization_id'] = self._get_customization_ids()['nlcius']

        # [BR-NL-24] Use of previous invoice date ( IssueDate ) is not recommended.
        # vals['vals'].pop('issue_date')  # careful, this causes other errors from the validator...

        return vals
