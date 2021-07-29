# -*- coding: utf-8 -*-
from odoo import models, _


# Electronic Address Scheme (EAS), see https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
COUNTRY_EAS = {
    'HU': 9910,

    'AD': 9922,
    'AL': 9923,
    'BA': 9924,
    'BE': 9925,
    'BG': 9926,
    'CH': 9927,
    'CY': 9928,
    'CZ': 9929,
    'DE': 9930,
    'EE': 9931,
    'UK': 9932,
    'GR': 9933,
    'HR': 9934,
    'IE': 9935,
    'LI': 9936,
    'LT': 9937,
    'LU': 9938,
    'LV': 9939,
    'MC': 9940,
    'ME': 9941,
    'MK': 9942,
    'MT': 9943,
    'NL': 9944,
    'PL': 9945,
    'PT': 9946,
    'RO': 9947,
    'RS': 9948,
    'SI': 9949,
    'SK': 9950,
    'SM': 9951,
    'TR': 9952,
    'VA': 9953,

    'SE': 9955,

    'FR': 9957,
}


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _name = "account.edi.xml.ubl_bis3"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL BIS3"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _get_country_vals(self, country):
        # OVERRIDE
        vals = super()._get_country_vals(country)

        vals.pop('name', None)

        return vals

    def _get_partner_party_tax_scheme_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_tax_scheme_vals(partner)

        vals.pop('registration_name', None)
        vals.pop('RegistrationAddress_vals', None)

        return vals

    def _get_partner_party_legal_entity_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_legal_entity_vals(partner)

        vals.pop('RegistrationAddress_vals', None)

        return vals

    def _get_partner_contact_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_contact_vals(partner)

        vals.pop('id', None)

        return vals

    def _get_partner_party_vals(self, partner):
        # OVERRIDE
        vals = super()._get_partner_party_vals(partner)

        vals['endpoint_id'] = partner.vat
        vals['endpoint_id_attrs'] = {'schemeID': COUNTRY_EAS.get(partner.country_id.code)}

        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        # OVERRIDE
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)

        for vals in vals_list:
            vals.pop('payment_due_date', None)
            vals.pop('instruction_id', None)
            if vals.get('payment_id_vals'):
                vals['payment_id_vals'] = vals['payment_id_vals'][:1]

        return vals_list

    def _get_tax_category_list(self, taxes):
        # OVERRIDE
        vals_list = super()._get_tax_category_list(taxes)

        for vals in vals_list:
            vals.pop('name', None)

        return vals_list

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # OVERRIDE
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        for vals in vals_list:
            for subtotal_vals in vals.get('TaxSubtotal_vals', []):
                subtotal_vals.pop('percent', None)

        return vals_list

    def _get_invoice_line_vals(self, invoice_line_vals, taxes_vals):
        # OVERRIDE
        vals = super()._get_invoice_line_vals(invoice_line_vals, taxes_vals)

        vals.pop('TaxTotal_vals', None)

        vals['invoiced_quantity_attrs'] = {'unitCode': 'C62'}
        vals['Price_vals']['base_quantity_attrs'] = {'unitCode': 'C62'}

        return vals

    def _export_invoice_vals(self, invoice):
        # OVERRIDE
        vals = super()._export_invoice_vals(invoice)

        vals['TaxSubtotalType_template'] = 'account_edi_ubl.ubl_bis3_TaxSubtotalType'
        vals['TaxTotalType_template'] = 'account_edi_ubl.ubl_bis3_TaxTotalType'
        vals['MonetaryTotalType_template'] = 'account_edi_ubl.ubl_bis3_MonetaryTotalType'
        vals['InvoiceLineType_template'] = 'account_edi_ubl.ubl_bis3_InvoiceLineType'

        vals['vals'].update({
            'buyer_reference': None,
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
            'profile_id': 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
        })
        vals['vals']['buyer_reference'] = None

        return vals
