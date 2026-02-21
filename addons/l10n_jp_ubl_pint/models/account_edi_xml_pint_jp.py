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

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        # OVERRIDE
        return self.env['account.edi.ubl']._ubl_tax_totals_node_grouping_key(base_line, tax_data, vals, currency)

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

    def _ubl_add_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.ubl_bis3
        super()._ubl_add_party_legal_entity_nodes(vals)
        nodes = vals['party_node']['cac:PartyLegalEntity']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        # optional, if set: scheme_id should be taken from ISO/IEC 6523 list
        if commercial_partner.country_code == 'JP':
            for node in nodes:
                node['cbc:CompanyID'] = None
