from odoo import models


class AccountEdiXmlPint_Jp(models.AbstractModel):
    _name = 'account.edi.xml.pint_jp'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "Japanese implementation of Peppol International (PINT) model for Billing"
    """
    Pint is a standard for International Billing from Peppol. It is based on Peppol BIS Billing 3.
    It serves as a base for per-country specialization, while keeping a standard core for data being used
    across countries. This is not meant to be used directly, but rather to be extended by country-specific modules.

    The JP PINT format is the Japanese implementation of PINT.

    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT JP Official documentation: https://docs.peppol.eu/poac/jp/pint-jp
    """

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_jp.xml"

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:peppol:pint:billing-1@jp-1'

    def _ubl_default_tax_subtotal_grouping_key(self, tax_category_grouping_key, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        tax_subtotal_grouping_key = super()._ubl_default_tax_subtotal_grouping_key(tax_category_grouping_key, vals)

        # If there is a TaxTotal section in company currency,
        # its TaxSubtotals nodes should contain a 'Percent' node.
        currency = vals['currency_id']
        company = vals['company']
        if (
            currency != company.currency_id
            and tax_subtotal_grouping_key['currency'] == company.currency_id
        ):
            tax_subtotal_grouping_key['percent'] = tax_category_grouping_key['percent']

        return tax_subtotal_grouping_key

    def _ubl_get_tax_subtotal_node(self, vals, tax_subtotal):
        # EXTENDS account.edi.xml.ubl_bis3
        tax_subtotal_node = super()._ubl_get_tax_subtotal_node(vals, tax_subtotal)

        # If there is a TaxTotal section in company currency,
        # its TaxSubtotals nodes should contain a 'Percent' node.
        currency = vals['currency_id']
        company = vals['company']
        if (
            currency != company.currency_id
            and tax_subtotal['currency'] == company.currency_id
        ):
            tax_subtotal_node['cbc:Percent'] = {'_text': tax_subtotal['percent']}

        return tax_subtotal_node

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        document_node['cac:TaxTotal'] = [
            self._ubl_get_tax_total_node(vals, tax_total)
            for tax_total in vals['_ubl_values']['tax_totals_currency'].values()
        ] + [
            self._ubl_get_tax_total_node(vals, tax_total)
            for tax_total in vals['_ubl_values']['tax_totals'].values()
        ]

    def _add_invoice_header_nodes(self, document_node, vals):
        invoice = vals['invoice']
        super()._add_invoice_header_nodes(document_node, vals)

        # see https://docs.peppol.eu/poac/jp/pint-jp/bis/#profiles
        document_node['cbc:ProfileID'] = {'_text': 'urn:peppol:bis:billing'}

        # [aligned-ibrp-052] An Invoice MUST have an invoice period (ibg-14) or an Invoice line period (ibg-26).
        document_node['cac:InvoicePeriod'] = {
            'cbc:StartDate': {'_text': invoice.invoice_date},
            'cbc:EndDate': {'_text': invoice.invoice_date},
        }

    def _get_address_node(self, vals):
        address_node = super()._get_address_node(vals)
        address_node['cbc:CountrySubentityCode'] = None
        return address_node

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)
        # optional, if set: scheme_id should be taken from ISO/IEC 6523 list
        party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = None
        return party_node
