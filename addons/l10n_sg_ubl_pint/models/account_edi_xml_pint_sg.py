# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


SG_TAX_CATEGORIES = {'SR', 'SRCA-S', 'SRCA-C', 'SROVR-RS', 'SRRC', 'SROVR-LVG', 'SRLVG', 'ZR', 'ES33', 'ESN33', 'DS', 'OS', 'NG', 'NA'}
SG_GST_CODES_REQUIRING_ADDRESS = {'SR', 'SRCA-S', 'SRCA-C', 'ZR', 'SRRC', 'SROVR-RS', 'SROVR-LVG', 'SRLVG', 'NA'}


class AccountEdiXmlPint_Sg(models.AbstractModel):
    _name = 'account.edi.xml.pint_sg'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "Singapore implementation of Peppol International (PINT) model for Billing"
    """
    Pint is a standard for International Billing from Peppol. It is based on Peppol BIS Billing 3.
    It serves as a base for per-country specialization, while keeping a standard core for data being used
    across countries. This is not meant to be used directly, but rather to be extended by country-specific modules.

    The SG PINT format is the Singapore implementation of PINT.

    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT SG Official documentation: https://docs.peppol.eu/poac/sg/2024-Q2/pint-sg/
    """

    def _export_invoice_filename(self, invoice):
        # OVERRIDE account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_sg.xml"

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:peppol:pint:billing-1@sg-1'

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        # see https://docs.peppol.eu/poac/sg/2024-Q2/pint-sg/bis/#_bis_identifiers
        document_node['cbc:ProfileID'] = {'_text': 'urn:peppol:bis:billing'}
        document_node['cbc:UUID'] = {'_text': invoice._l10n_sg_get_uuid()}

        if invoice.currency_id != invoice.company_id.currency_id:
            # see https://docs.peppol.eu/poac/sg/2024-Q2/pint-sg/bis/#_invoice_totals_in_gst_accounting_currency
            document_node['cbc:TaxCurrencyCode'] = {
                '_text': invoice.company_id.currency_id.name
            }  # accounting currency

            amounts_in_accounting_currency = (
                ('sgdtotal-excl-gst', invoice.amount_untaxed_signed),
                ('sgdtotal-incl-gst', invoice.amount_total_signed),
            )
            # [BR-53-GST-SG] - If the GST accounting currency code (BT-6-GST) is present, then the Invoice total GST amount (BT-111-GST),
            # Invoice total including GST amount and Invoice Total excluding GST amount in accounting currency shall be provided.

            document_node['cac:AdditionalDocumentReference'] = [
                {
                    'cbc:ID': {'_text': invoice.company_id.currency_id.name},
                    'cbc:DocumentTypeCode': {'_text': code},
                    'cbc:DocumentDescription': {'_text': amount},
                }
                for code, amount in amounts_in_accounting_currency
            ]

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_tax_total_nodes(document_node, vals)
        document_node['cac:TaxTotal'] = [document_node['cac:TaxTotal']]

        company_currency = vals['invoice'].company_id.currency_id
        if vals['invoice'].currency_id != company_currency:
            self._add_tax_total_node_in_company_currency(document_node, vals)

            # Remove the tax subtotals from the TaxTotal in company currency
            document_node['cac:TaxTotal'][1]['cac:TaxSubtotal'] = None

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)
        party_node['cac:PartyTaxScheme'][0]['cac:TaxScheme']['cbc:ID']['_text'] = 'GST'
        return party_node

    def _get_tax_category_node(self, vals):
        # EXTENDS account_edi_ubl_cii
        tax_category_node = super()._get_tax_category_node(vals)
        tax_category_node['cac:TaxScheme']['cbc:ID']['_text'] = 'GST'
        return tax_category_node

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account_edi_ubl_cii
        constraints = super()._export_invoice_constraints(invoice, vals)

        # Tax category must be filled on the line, with a value from SG categories.
        tax_total_node = vals['document_node']['cac:TaxTotal'][0]
        for tax_subtotal_node in tax_total_node['cac:TaxSubtotal']:
            if tax_subtotal_node['cac:TaxCategory']['cbc:ID']['_text'] not in SG_TAX_CATEGORIES:
                constraints['sg_vat_category_required'] = _("You must set a Singaporean tax category on each taxes of the invoice.")

            # Invoice with GST category code of value 'SR', 'SRCA-S', 'SRCA-C', 'ZR', 'SRRC',
            # 'SROVR-RS', 'SROVR-LVG', 'SRLVG', 'NA' should contain seller address line and seller
            # post code
            if tax_subtotal_node['cac:TaxCategory']['cbc:ID']['_text'] in SG_GST_CODES_REQUIRING_ADDRESS:
                constraints['sg_seller_street_addr_required'] = \
                    self._check_required_fields(vals['supplier'], 'street')
                constraints['sg_seller_post_code_required'] = \
                    self._check_required_fields(vals['supplier'], 'zip')

        return constraints
