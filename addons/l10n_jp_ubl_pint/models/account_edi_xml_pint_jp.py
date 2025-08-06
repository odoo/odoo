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

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_jp.xml"

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:peppol:pint:billing-1@jp-1'

    def _add_invoice_header_nodes(self, document_node, vals):
        invoice = vals['invoice']
        super()._add_invoice_header_nodes(document_node, vals)

        # see https://docs.peppol.eu/poac/jp/pint-jp/bis/#profiles
        document_node['cbc:ProfileID'] = {'_text': 'urn:peppol:bis:billing'}

        if invoice.currency_id != invoice.company_id.currency_id:
            # see https://docs.peppol.eu/poac/jp/pint-jp/bis/#_tax_in_accounting_currency
            document_node['cbc:TaxCurrencyCode'] = {'_text': invoice.company_id.currency_id.name}  # accounting currency

        # [aligned-ibrp-052] An Invoice MUST have an invoice period (ibg-14) or an Invoice line period (ibg-26).
        document_node['cac:InvoicePeriod'] = {
            'cbc:StartDate': {'_text': invoice.invoice_date},
            'cbc:EndDate': {'_text': invoice.invoice_date},
        }

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        super()._add_invoice_tax_total_nodes(document_node, vals)

        # if company currency != invoice currency, need to add a TaxTotal section
        # see https://docs.peppol.eu/poac/jp/pint-jp/bis/#_tax_in_accounting_currency
        document_node['cac:TaxTotal'] = [document_node['cac:TaxTotal']]

        company_currency = vals['invoice'].company_id.currency_id
        if vals['invoice'].currency_id != company_currency:
            self._add_tax_total_node_in_company_currency(document_node, vals)

    def _get_tax_subtotal_node(self, vals):
        tax_subtotal_node = super()._get_tax_subtotal_node(vals)

        # If there is a TaxTotal section in company currency,
        # its TaxSubtotals nodes should contain a 'Percent' node.
        if (
            vals['invoice'].currency_id != vals['invoice'].company_id.currency_id
            and vals['currency_name'] == vals['company_currency_id'].name
        ):
            tax_subtotal_node['cbc:Percent'] = tax_subtotal_node['cac:TaxCategory']['cbc:Percent']
        return tax_subtotal_node

    def _get_address_node(self, vals):
        address_node = super()._get_address_node(vals)
        address_node['cbc:CountrySubentityCode'] = None
        return address_node

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)
        # optional, if set: scheme_id should be taken from ISO/IEC 6523 list
        party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = None
        return party_node
