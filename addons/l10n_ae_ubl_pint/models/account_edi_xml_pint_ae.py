# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt


class AccountEdiXmlPint_Ae(models.AbstractModel):
    _name = 'account.edi.xml.pint_ae'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "UAE implementation of Peppol International (PINT) model for Billing"
    """
    Pint is a standard for International Billing from Peppol. It is based on Peppol BIS Billing 3.
    It serves as a base for per-country specialization, while keeping a standard core for data being used
    across countries. This is not meant to be used directly, but rather to be extended by country-specific modules.

    The AE PINT format is the United Arab Emirates implementation of PINT.

    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT AE Official documentation: https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/
    """

    def _export_invoice_filename(self, invoice):
        # OVERRIDE account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_ae.xml"

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:peppol:pint:billing-1@ae-1'
        return None

    def _ubl_add_invoice_type_code_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        # see https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/bis/#_tax_invoice
        super()._ubl_add_invoice_type_code_node(vals)
        if vals['document_type'] != 'invoice':
            return

        if vals['invoice'].l10n_ae_is_out_of_scope:
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 480

    def _ubl_add_ae_invoice_transaction_type_node(self, vals):
        # EXTENDS account.edi.xml.ubl
        # see https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/bis/#_invoice_transaction_type_code
        if vals['document_type'] not in ['invoice', 'credit_note']:
            return

        if vals['invoice'].l10n_ae_is_out_of_scope:
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 81

    def _ubl_add_credit_note_type_code_node(self, vals):
        # https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/bis/#_tax_invoice
        super()._ubl_add_credit_note_type_code_node(vals)
        if vals['document_type'] != 'credit_note':
            return
        vals['document_node']['cbc:InvoiceTypeCode']['_text'] = vals['invoice'].l10n_ae_invoice_transaction_type

    def _ubl_add_party_endpoint_id_node(self, vals):
        # EXTENDS account.edi.ubl
        #
        # By default, invoices are routed to C3 using the buyer's endpoint.
        # However, in the following cases we must override the endpoint and use
        # a predefined one instead. In these scenarios, the document is not sent
        # to the buyer via C3, but only reported to C5.
        #
        # Cases:
        # 1. Deemed Supply (InvoiceTypeCode: X1XXXXXX)
        #    → schemeID: 0235, endpoint: 9900000097
        #
        # 2. Export where the receiver is not on Peppol (InvoiceTypeCode: XXXXXXX1)
        #    → schemeID: 0235, endpoint: 9900000099
        #
        # To be added later Case 3
        # 3. Buyer not subject to UAE e-invoicing
        #    → schemeID: 0235, endpoint: 9900000098
        #
        # Ref:
        # https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/bis/#_predefined_endpoint
        super()._ubl_add_party_endpoint_id_node(vals)
        invoice_transaction_type = vals['invoice'].l10n_ae_invoice_transaction_type
        if invoice_transaction_type == "01000000":
            vals['party_node']['cbc:EndpointID']['_text'] = '9900000097'
        if invoice_transaction_type == "00000001":
            vals['party_node']['cbc:EndpointID']['_text'] = '9900000099'

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # OVERRIDE account.edi.ubl
        #
        # Current implementation follows the standard PaymentMeans structure,
        # but the UAE has it is own AE-PINT specification for payment Means.
        # Reference:
        # https://docs.peppol.eu/poac/ae/v1.0.3/pint-ae/trn-invoice/syntax/cac-PaymentMeans/
        # Codes used in UAE: https://docs.peppol.eu/poac/ae/v1.0.3/pint-ae/trn-creditnote/codelist/UNCL4461/
        # Flows identified:
        #
        # 1. PaymentMeansCode = 30 (credit transfer)
        #    See: https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/bis/#_credit_transfer
        #
        # 2. Card payments:
        #    Missing support for codes: 48, 54, 55
        #    See: https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/bis/#_card_payment
        invoice = vals['invoice']
        payment_means_code, payment_means_name = invoice.l10n_ae_get_payment_means_details()

        payment_means_node = {
            'cbc:PaymentMeansCode': {
                '_text': payment_means_code,
                'name': payment_means_name,
            },
            'cbc:PaymentID': {
                '_text': invoice.payment_reference or invoice.name,
            },
        }

        if payment_means_code == 30:
            payment_means_node['cac:PayeeFinancialAccount'] = (
                self._get_financial_account_node({
                    **vals,
                    'partner_bank': invoice.partner_bank_id,
                })
            )

        document_node['cac:PaymentMeans'] = [payment_means_node]

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        self._ubl_add_credit_note_type_code_node(sub_vals)
        # see https://docs.peppol.eu/poac/ae/v1.0.3/pint-ae-sb/bis/#_bis_identifiers
        document_node['cbc:ProfileID'] = {'_text': 'urn:peppol:bis:billing'}
        document_node['cbc:UUID'] = {'_text': invoice._l10n_ae_get_uuid()}

        if vals['document_type'] == 'credit_note' and invoice.l10n_ae_is_volume_discount:
            document_node['cac:DiscrepancyResponse'] = {
                'cbc:ResponseCode': {'_text': 'VD'},
            }

    def _ubl_add_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_legal_entity_nodes(vals)
        nodes = vals['party_node']['cac:PartyLegalEntity']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        registration_identifier_type = commercial_partner.l10n_ae_registration_identifier_type
        # See https://docs.peppol.eu/poac/ae/v1.0.3/pint-ae/trn-invoice/syntax/cac-AccountingSupplierParty/cac-Party/cac-PartyLegalEntity/cbc-CompanyID/
        # For more details about legal registration identifier
        for node in nodes:
            node['cbc:CompanyID']['_text'] = commercial_partner.l10n_ae_registration_identifier
            node['cbc:CompanyID']['schemeAgencyID'] = registration_identifier_type
            if registration_identifier_type == 'TL':
                node['cbc:CompanyID']['schemeAgencyName'] = commercial_partner.l10n_ae_authority_name
            if registration_identifier_type == 'PAS':
                node['cbc:CompanyID']['schemeAgencyName'] = commercial_partner.l10n_ae_passport_issuing_country_id.code

    def _ubl_add_customization_id_node(self, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._ubl_add_customization_id_node(vals)
        vals['document_node']['cbc:CustomizationID']['_text'] = 'urn:peppol:pint:billing-1@ae-1'

    def _get_invoice_line_node(self, vals):
        line_node = super()._get_invoice_line_node(vals)
        self._add_invoice_line_price_extension_nodes(line_node, vals)
        return line_node

    def _add_invoice_line_price_extension_nodes(self, line_node, vals):
        # Documentation: https://docs.peppol.eu/poac/ae/v1.0.1/pint-ae/bis/#_vat_line_amount_btae_08_and_amount_payable_btae_10
        # For node structure https://docs.peppol.eu/poac/ae/v1.0.3/pint-ae/trn-invoice/syntax/cac-InvoiceLine/cac-ItemPriceExtension/
        move_line = vals['base_line']['record']
        currency = move_line.currency_id
        line_node['cac:ItemPriceExtension'] = {
            'cbc:Amount': {
                '_text': FloatFmt(
                    move_line.price_subtotal,
                    min_dp=currency.decimal_places,
                ),
                'currencyID': currency.name,
            },
            'cac:TaxTotal': {
                'cbc:TaxAmount': {
                    '_text': FloatFmt(
                        move_line.l10n_gcc_invoice_tax_amount,
                        min_dp=currency.decimal_places,
                    ),
                    'currencyID': currency.name,
                },
            },
        }
