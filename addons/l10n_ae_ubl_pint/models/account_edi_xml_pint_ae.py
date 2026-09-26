from odoo import _, fields, models

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt

# countrySubentity for AE addresses must be one of these 3-letter emirate codes - confirmed by
# the real PINT-AE spec examples (e.g. Dubai shows as "DXB"). Neither Odoo's own 2-letter state
# code ("DU") nor the full emirate name ("Dubai", what the base UBL address builder sends by
# default via state_id.name) is the actual expected value - keyed by name since that's the one
# we're confident is stable/correctly spelled.
AE_COUNTRY_SUBENTITY_CODES = {
    'Abu Dhabi': 'AUH',
    'Ajman': 'AJM',
    'Dubai': 'DXB',
    'Fujairah': 'FUJ',
    'Ras Al Khaimah': 'RAK',
    'Sharjah': 'SHJ',
    'Umm Al Quwain': 'UAQ',
}


class AccountEdiXmlPint_Ae(models.AbstractModel):
    """
    Pint is a standard for International Billing from Peppol. It is based on Peppol BIS Billing 3.
    It serves as a base for per-country specialization, while keeping a standard core for data being used
    across countries. This is not meant to be used directly, but rather to be extended by country-specific modules.

    The AE PINT format is the United Arab Emirates implementation of PINT.

    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT AE Official documentation: https://docs.peppol.eu/poac/ae/pint-ae/
    """
    _name = 'account.edi.xml.pint_ae'
    _inherit = ["account.edi.ubl_pint"]
    _description = "UAE implementation of Peppol International (PINT) model for Billing"

    def _export_invoice_filename(self, invoice):
        # OVERRIDE account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_ae.xml"

    def _export_invoice(self, invoice):
        # OVERRIDE account.edi.ubl
        # account.edi.ubl's own _export_invoice/_export_document only build the vals/document_node
        # dict, they never render it to actual XML - do that final step here ourselves.
        vals = self._export_document(self._init_invoice_export_values(invoice))
        errors = [v for v in vals['constraints'].values() if v]
        return self._etree_to_string(self._vals_to_etree(vals)), set(errors)

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _init_invoice_export_values(self, invoice):
        vals = super()._init_invoice_export_values(invoice)
        vals['l10n_ae_invoice_transaction_type'] = vals['invoice'].l10n_ae_invoice_transaction_type
        # account.edi.ubl_pint's own _ubl_add_party_tax_scheme_nodes expects this key to be set
        # (normally done by account_edi_ubl_cen_en16931, which we don't inherit).
        vals['no_party_tax_scheme'] = False
        return vals

    def _get_customization_id(self, process_type='billing'):
        # Specification identifier (IBT-024) - the exact strings come from the profiles table.
        # https://docs.peppol.eu/poac/ae/pint-ae/bis/#profiles
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibt-024/
        if process_type in ('billing', 'selfbilling'):
            return f'urn:peppol:pint:{process_type}-1@ae-1'
        return None

    def _can_export_selfbilling(self):
        # EXTENDS account.edi.common (defaults to False there). AE publishes a selfbilling
        # customization, so the format supports it.
        # https://docs.peppol.eu/poac/ae/pint-ae/bis/#_self_billing_invoice
        # https://docs.peppol.eu/poac/ae/pint-ae/bis/#_self_billing_credit_note
        return bool(self._get_customization_id(process_type='selfbilling'))

    def _ubl_add_invoice_type_code_node(self, vals):
        # EXTENDS account.edi.ubl_pint
        # see https://docs.peppol.eu/poac/ae/pint-ae/bis/#_tax_invoice
        super()._ubl_add_invoice_type_code_node(vals)
        # PINT-AE's ibr-cl-01 code list doesn't include 389 (self-billed invoice): self-billing
        # is already signalled via the customization/profile ID, so reuse the regular code here.
        if self._is_document(vals, 'self_invoice'):
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 380
        if vals['_document_type']['name'] != 'invoice':
            return
        if vals['invoice'].l10n_ae_invoice_type == 'commercial':
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 480

    def _get_document_type_code_node(self, invoice, invoice_data):
        # EXTENDS account.edi.ubl
        # DocumentTypeCode on the embedded PDF's own AdditionalDocumentReference (added by
        # account_move_send.py's _postprocess_invoice_ubl_xml) - mirror the same code already
        # used for the invoice/credit note itself (see _ubl_add_invoice_type_code_node/
        # _ubl_add_credit_note_type_code_node) so the attached PDF's declared type stays
        # consistent with the actual UBL document instead of being left empty.
        # Unlike cbc:InvoiceTypeCode/cbc:CreditNoteTypeCode (see _ubl_add_invoice_type_code_node/
        # _ubl_add_credit_note_type_code_node), this DocumentTypeCode isn't restricted by
        # PINT-AE's ibr-cl-01 code list, so self-billing keeps the real 389/261 codes here.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-cl-01/
        is_commercial = invoice.l10n_ae_invoice_type == 'commercial'
        code = {
            'out_invoice': 480 if is_commercial else 380,
            'out_refund': 81 if is_commercial else 381,
            'in_invoice': 389,
            'in_refund': 261,
        }.get(invoice.move_type)
        return {'_text': code} if code else None

    def _ubl_add_credit_note_type_code_node(self, vals):
        # EXTENDS account.edi.ubl_pint
        # see https://docs.peppol.eu/poac/ae/pint-ae/bis/#_tax_invoice
        super()._ubl_add_credit_note_type_code_node(vals)
        # PINT-AE's ibr-cl-01 code list doesn't include 261 (self-billed credit note): self-billing
        # is already signalled via the customization/profile ID, so reuse the regular code here.
        if self._is_document(vals, 'self_credit_note'):
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 381
        if vals['_document_type']['name'] not in ['credit_note', 'self_credit_note']:
            return
        if vals['invoice'].l10n_ae_invoice_type == 'commercial':
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 81

    def _ubl_add_party_endpoint_id_node(self, vals):
        # EXTENDS account.edi.ubl_pint
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
        # https://docs.peppol.eu/poac/ae/pint-ae/bis/#_predefined_endpoint
        super()._ubl_add_party_endpoint_id_node(vals)
        invoice_transaction_type = vals['l10n_ae_invoice_transaction_type']
        if invoice_transaction_type == "01000000":
            vals['party_node']['cbc:EndpointID'] = {'_text': '9900000097', 'schemeID': '0235'}
        if invoice_transaction_type == "00000001":
            vals['party_node']['cbc:EndpointID'] = {'_text': '9900000099', 'schemeID': '0235'}

    def _ubl_get_partner_address_node(self, vals, partner):
        # EXTENDS account.edi.ubl
        # see https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/PINT-jurisdiction-aligned-rules/ (ibr-128-ae)
        node = super()._ubl_get_partner_address_node(vals, partner)
        if partner.country_id.code == 'AE' and partner.state_id:
            node['cbc:CountrySubentity']['_text'] = AE_COUNTRY_SUBENTITY_CODES.get(partner.state_id.name, partner.state_id.name)
        return node

    def _ubl_add_payment_means_nodes(self, vals):
        # OVERRIDE account.edi.ubl
        #
        # Current implementation follows the standard PaymentMeans structure,
        # but the UAE has it is own AE-PINT specification for payment Means.
        # Reference:
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-PaymentMeans/
        # Codes used in UAE: https://docs.peppol.eu/poac/ae/pint-ae/trn-creditnote/codelist/UNCL4461/
        # Flows identified:
        #
        # 1. PaymentMeansCode = 30 (credit transfer), 10 (cash)
        #    See: https://docs.peppol.eu/poac/ae/pint-ae/bis/#_credit_transfer
        #
        # 2. Card payments (code 55, debit card only):
        #    Missing support for codes: 48, 54
        #    See: https://docs.peppol.eu/poac/ae/pint-ae/bis/#_card_payment
        #
        # ibr-191-ae: PaymentMeans MUST be absent for credit notes and Deemed Supply invoices,
        # and MUST be present otherwise - base's own default is an unconditional empty list
        # regardless of document type, so this needs its own guard.
        invoice = vals['invoice']
        if self._is_document(vals, 'credit_note', 'self_credit_note') or vals['l10n_ae_invoice_transaction_type'] == '01000000':
            vals['document_node']['cac:PaymentMeans'] = []
            return
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

        if payment_means_code == 30 and invoice.partner_bank_id:
            payment_means_node['cac:PayeeFinancialAccount'] = (
                self._ubl_get_payment_means_payee_financial_account_node_from_partner_bank(vals, invoice.partner_bank_id)
            )
        elif payment_means_code == 55 and invoice.l10n_ae_card_number:
            payment_means_node['cac:CardAccount'] = {
                'cbc:PrimaryAccountNumberID': {'_text': invoice.l10n_ae_card_number},
                'cbc:NetworkID': {'_text': invoice.l10n_ae_card_network},
            }

        vals['document_node']['cac:PaymentMeans'] = [payment_means_node]

    def _ubl_add_billing_reference_nodes(self, vals):
        # EXTENDS account.edi.ubl_pint
        # ibr-055-ae: a preceding invoice reference is mandatory on (almost) every AE credit
        # note. Base only populates it from actual ledger reconciliation (matched_credit_ids),
        # which isn't guaranteed to exist yet at export time even though the credit note clearly
        # does reverse a specific invoice - fall back to reversed_entry_id (always set by the
        # reversal flow, regardless of reconciliation state) when base found nothing.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-055-ae/
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-BillingReference/
        super()._ubl_add_billing_reference_nodes(vals)
        if not self._is_document(vals, 'credit_note', 'self_credit_note'):
            return
        nodes = vals['document_node']['cac:BillingReference']
        if nodes:
            return
        credit_note = vals['invoice']
        if credit_note.reversed_entry_id and credit_note.reversed_entry_id.name and credit_note.reversed_entry_id.name != '/':
            nodes.append({
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': credit_note.reversed_entry_id.name},
                },
            })

    def _export_document_node_constraints(self, vals):
        # EXTENDS account.edi.ubl
        constraints = super()._export_document_node_constraints(vals)
        # ibr-167-ae: category 'E' MUST carry an exemption reason code. l10n_ae's exempt taxes
        # ship without one, and there's no generic code to default to - the company has to pick
        # one of the four DL8.46.x itself.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/PINT-jurisdiction-aligned-rules/
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/codelist/Aligned-TaxExemptionCodes/
        exempt_without_reason = vals['invoice'].invoice_line_ids.tax_ids.filtered(
            lambda tax: tax.ubl_cii_tax_category_code == 'E' and not tax.ubl_cii_tax_exemption_reason_code,
        )
        if exempt_without_reason:
            constraints['l10n_ae_exempt_tax_missing_reason_code'] = _(
                "The UAE requires a Tax Exemption Reason Code on taxes exempt from VAT. "
                "Please set one on: %(tax_names)s",
                tax_names=", ".join(exempt_without_reason.mapped('name')),
            )
        # ibr-151-ae: a tax invoice or tax credit note (380/381) needs at least one line that is
        # neither 'E' nor 'O' - a wholly exempt/out-of-scope supply belongs on a commercial
        # document (480/81) instead. Read the code off the built node rather than
        # l10n_ae_invoice_type, since self-billing forces 380/381 too.
        document_node = vals['document_node']
        type_code = (document_node.get('cbc:InvoiceTypeCode') or document_node.get('cbc:CreditNoteTypeCode') or {}).get('_text')
        if type_code in (380, 381, '380', '381'):
            line_categories = vals['invoice'].invoice_line_ids.filtered(
                lambda line: line.display_type == 'product',
            ).tax_ids.mapped('ubl_cii_tax_category_code')
            if line_categories and set(line_categories) <= {'E', 'O'}:
                constraints['l10n_ae_tax_document_only_exempt_lines'] = _(
                    "A UAE tax invoice must have at least one line that is not exempt from VAT "
                    "or out of scope. Use a commercial invoice for a wholly exempt supply.",
                )
        return constraints

    def _ubl_get_tax_category_node(self, vals, tax_category):
        # EXTENDS account.edi.ubl
        # ibr-121-ae: no VAT rate on category 'E' in the breakdown.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/PINT-jurisdiction-aligned-rules/
        node = super()._ubl_get_tax_category_node(vals, tax_category)
        if tax_category.get('tax_category_code') == 'E':
            node['cbc:Percent']['_text'] = None
        return node

    def _ubl_get_line_item_node_classified_tax_category_node(self, vals, tax_category):
        # EXTENDS account.edi.ubl
        # For node structure https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-InvoiceLine/cac-ItemPriceExtension/
        node = super()._ubl_get_line_item_node_classified_tax_category_node(vals, tax_category)
        if exemption_reason_code := tax_category.get('tax_exemption_reason_code'):
            node['cbc:TaxExemptionReasonCode']['_text'] = exemption_reason_code
            node['cbc:TaxExemptionReason']['_text'] = tax_category.get('tax_exemption_reason')
        # aligned-ibrp-e-05: no VAT rate on category 'E' - EN16931's BR-E-05 wants 0 instead.
        # Suppressed per node, not in the shared grouping key: document level allowances and
        # charges need the rate kept (aligned-ibrp-e-06/e-07 require 0) and read the same key.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/PINT-jurisdiction-aligned-rules/
        if tax_category.get('tax_category_code') == 'E':
            node['cbc:Percent']['_text'] = None
        return node

    def _fill_document_values_invoice(self, vals):
        # EXTENDS account.edi.ubl
        super()._fill_document_values_invoice(vals)
        vals['document_node']['cbc:UUID'] = {'_text': vals['invoice'].l10n_ae_uuid}
        # see https://docs.peppol.eu/poac/ae/pint-ae/bis/#_invoice_transaction_type_code
        vals['document_node']['cbc:ProfileExecutionID'] = {'_text': vals['l10n_ae_invoice_transaction_type'] or '00000000'}
        self._ubl_add_ae_buyer_customer_party_node(vals)
        self._ubl_add_ae_seller_supplier_party_node(vals)

    def _fill_document_values_credit_note(self, vals):
        # EXTENDS account.edi.ubl
        super()._fill_document_values_credit_note(vals)
        vals['document_node']['cbc:UUID'] = {'_text': vals['invoice'].l10n_ae_uuid}
        # ibr-154-ae: Invoice Transaction-type code is mandatory on every document, credit notes
        # included - see https://docs.peppol.eu/poac/ae/pint-ae/bis/#_invoice_transaction_type_code
        vals['document_node']['cbc:ProfileExecutionID'] = {'_text': vals['l10n_ae_invoice_transaction_type'] or '00000000'}
        # BTAE-03 Credit note reason code is mandatory (1..1) on every UAE credit note.
        # See https://docs.peppol.eu/poac/ae/pint-ae/trn-creditnote/semantic-model/btae-03/
        vals['document_node']['cac:DiscrepancyResponse'] = {
            'cbc:ResponseCode': {'_text': vals['invoice'].l10n_ae_credit_note_reason},
        }
        # ibr-055-ae: mandatory preceding invoice reference - _ubl_add_billing_reference_nodes
        self._ubl_add_billing_reference_nodes(vals)
        self._ubl_add_ae_buyer_customer_party_node(vals)
        self._ubl_add_ae_seller_supplier_party_node(vals)

    def _ubl_add_ae_buyer_customer_party_node(self, vals):
        # BTAE-01 Beneficiary ID: in case of free trade zone supply, the TRN/TIN of the beneficiary
        # of the supply, reported in its own BuyerCustomerParty block - NOT under
        # AccountingCustomerParty/PartyIdentification, which is the actual customer/buyer.
        # See https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-01/
        beneficiary_id = vals['invoice'].l10n_ae_beneficiary_id
        if beneficiary_id:
            vals['document_node']['cac:BuyerCustomerParty'] = {
                'cac:Party': {
                    'cac:PartyIdentification': {
                        'cbc:ID': {'_text': beneficiary_id},
                    },
                },
            }

    def _ubl_add_ae_seller_supplier_party_node(self, vals):
        # BTAE-14 Principal ID: in case of disclosed agent billing, the TRN of the principal on
        # whose behalf the agent is billing, reported in its own SellerSupplierParty block - NOT
        # under AccountingSupplierParty/PartyIdentification, which is the agent doing the billing.
        # ibr-137-ae/ibr-176-ae both key off this exact node.
        # See https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-14/
        principal_id = vals['invoice'].l10n_ae_principal_id
        if principal_id:
            vals['document_node']['cac:SellerSupplierParty'] = {
                'cac:Party': {
                    'cac:PartyIdentification': {
                        'cbc:ID': {'_text': principal_id},
                    },
                },
            }

    def _ubl_add_profile_id_node(self, vals):
        # EXTENDS account.edi.ubl
        # Business process type (IBT-023) - urn:peppol:bis:billing / :selfbilling per the
        # profiles table. https://docs.peppol.eu/poac/ae/pint-ae/bis/#profiles
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibt-023/
        super()._ubl_add_profile_id_node(vals)
        is_self_billing = self._is_document(vals, 'self_invoice', 'self_credit_note')
        vals['document_node']['cbc:ProfileID']['_text'] = f"urn:peppol:bis:{'selfbilling' if is_self_billing else 'billing'}"

    def _ubl_add_tax_currency_code_node(self, vals):
        # EXTENDS account.edi.ubl_pint
        # BTAE-04 Currency Exchange Rate between the document currency and the tax currency.
        # See https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-04/
        super()._ubl_add_tax_currency_code_node(vals)
        invoice = vals['invoice']
        document_currency = vals['currency']
        tax_currency = vals['company'].currency_id
        if document_currency != tax_currency:
            vals['document_node']['cac:TaxExchangeRate'] = {
                'cbc:SourceCurrencyCode': {'_text': document_currency.name},
                'cbc:TargetCurrencyCode': {'_text': tax_currency.name},
                # invoice_currency_rate is company -> document; we need the inverse (document -> tax,
                # since tax_currency == company currency here) for Source/Target above.
                # ibr-002-ae: max 6 decimal places - a raw 1/rate division produces long
                # repeating floats that silently exceed it.
                'cbc:CalculationRate': {'_text': invoice.invoice_currency_rate and round(1 / invoice.invoice_currency_rate, 6)},
                'cbc:Date': {'_text': invoice.invoice_date},
            }
            # The second TaxTotal entry in the company/tax currency (amount only, no subtotal
            # breakdown) is already built generically by account_edi_ubl.py's own
            # _ubl_add_tax_totals_nodes whenever document currency != company currency - only the
            # top-level AdditionalDocumentReference giving the AED-equivalent total is AE-specific
            # and missing.
            conversion_date = invoice.invoice_date or fields.Date.context_today(self)
            total_company_ccy = document_currency._convert(invoice.amount_total, tax_currency, invoice.company_id, conversion_date)
            vals['document_node']['cac:AdditionalDocumentReference'] = [{
                'cbc:ID': {'_text': 'aedtotal-incl-vat'},
                'cbc:DocumentTypeCode': {'_text': 'aedtotal-incl-vat'},
                'cbc:DocumentDescription': {'_text': f'{total_company_ccy:.2f}'},
            }]

    def _ubl_add_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_party_legal_entity_nodes(vals)
        nodes = vals['party_node']['cac:PartyLegalEntity']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        registration_identifier_type = commercial_partner.l10n_ae_registration_identifier_type
        if not nodes and commercial_partner.l10n_ae_registration_identifier:
            nodes.append({
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': None},
            })
        # See https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-AccountingSupplierParty/cac-Party/cac-PartyLegalEntity/cbc-CompanyID/
        # For more details about legal registration identifier
        for node in nodes:
            node['cbc:CompanyID']['_text'] = commercial_partner.l10n_ae_registration_identifier
            node['cbc:CompanyID']['schemeAgencyID'] = registration_identifier_type
            if registration_identifier_type == 'TL':
                node['cbc:CompanyID']['schemeAgencyName'] = commercial_partner.l10n_ae_authority_name
            if registration_identifier_type == 'PAS':
                node['cbc:CompanyID']['schemeAgencyName'] = commercial_partner.l10n_ae_passport_issuing_country_id.code

    def _ubl_add_customization_id_node(self, vals):
        # EXTENDS account.edi.ubl
        # Specification identifier (IBT-024), see _get_customization_id above.
        # https://docs.peppol.eu/poac/ae/pint-ae/bis/#profiles
        super()._ubl_add_customization_id_node(vals)
        is_self_billing = self._is_document(vals, 'self_invoice', 'self_credit_note')
        vals['document_node']['cbc:CustomizationID']['_text'] = self._get_customization_id(
            process_type='selfbilling' if is_self_billing else 'billing')

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_ubl_invoice_optional_fields(self, collected_values):
        # EXTENDS account.edi.ubl
        super()._import_ubl_invoice_optional_fields(collected_values)
        self._l10n_ae_import_document_values(collected_values)

    def _l10n_ae_import_selection_value(self, collected_values, field_name, value, term):
        """Accept a code only if it is one of the field's own selection values.

        Incoming documents come from other systems, which may legitimately use codes this
        version of the module doesn't model yet - writing one straight onto a Selection field
        would raise and abort the whole import, so skip it and say so in the chatter instead.
        """
        if not value:
            return None
        if value not in self.env['account.move']._fields[field_name].get_values(self.env):
            collected_values['logs'].append(self.env._(
                "The %(term)s code %(code)s is not supported and was ignored.",
                term=term, code=value,
            ))
            return None
        return value

    def _l10n_ae_import_document_values(self, collected_values):
        """Decode the AE specific business terms, mirroring what the export builds.

        See _fill_document_values_invoice / _fill_document_values_credit_note above for the
        node each term is written to.
        """
        tree = collected_values['tree']
        to_write = collected_values['to_write']

        # BTAE-02 Invoice document UUID. The generated one account_move.py's create() stamps is
        # derived from this database, so it is meaningless for a document issued elsewhere -
        # keep the sender's instead.
        if document_uuid := tree.findtext('./{*}UUID'):
            to_write['l10n_ae_uuid'] = document_uuid

        # Invoice transaction type (ibr-154-ae). '00000000' is what the export writes when no
        # transaction type applies, and is not a selection value - it means 'unset'.
        # https://docs.peppol.eu/poac/ae/pint-ae/bis/#_invoice_transaction_type_code
        transaction_type = tree.findtext('./{*}ProfileExecutionID')
        if transaction_type and transaction_type != '00000000':
            if value := self._l10n_ae_import_selection_value(
                collected_values, 'l10n_ae_invoice_transaction_type', transaction_type, self.env._("invoice transaction type"),
            ):
                to_write['l10n_ae_invoice_transaction_type'] = value

        # Only 'commercial' can be recovered from the document type code: the export maps both
        # 'simplified' and 'tax' onto 380/381 (see _ubl_add_invoice_type_code_node), so a 380
        # carries no information to tell those two apart and the field keeps its default.
        type_code = tree.findtext('./{*}InvoiceTypeCode') or tree.findtext('./{*}CreditNoteTypeCode')
        if type_code in ('480', '81'):
            to_write['l10n_ae_invoice_type'] = 'commercial'

        # BTAE-03 Credit note reason code.
        if reason := tree.findtext('./{*}DiscrepancyResponse/{*}ResponseCode'):
            if value := self._l10n_ae_import_selection_value(
                collected_values, 'l10n_ae_credit_note_reason', reason, self.env._("credit note reason"),
            ):
                to_write['l10n_ae_credit_note_reason'] = value

        # BTAE-01 Beneficiary ID - its own BuyerCustomerParty block, not the actual buyer.
        if beneficiary_id := tree.findtext('./{*}BuyerCustomerParty/{*}Party/{*}PartyIdentification/{*}ID'):
            to_write['l10n_ae_beneficiary_id'] = beneficiary_id

        # BTAE-14 Principal ID - its own SellerSupplierParty block, not the billing agent.
        if principal_id := tree.findtext('./{*}SellerSupplierParty/{*}Party/{*}PartyIdentification/{*}ID'):
            to_write['l10n_ae_principal_id'] = principal_id

        # Card payment (UNCL4461 code 55), the only payment means carrying AE specific data.
        # https://docs.peppol.eu/poac/ae/pint-ae/bis/#_card_payment
        for payment_means_node in tree.iterfind('./{*}PaymentMeans'):
            if payment_means_node.findtext('{*}PaymentMeansCode') != '55':
                continue
            if card_number := payment_means_node.findtext('{*}CardAccount/{*}PrimaryAccountNumberID'):
                to_write['l10n_ae_card_number'] = card_number
            if card_network := payment_means_node.findtext('{*}CardAccount/{*}NetworkID'):
                to_write['l10n_ae_card_network'] = card_network

    # -------------------------------------------------------------------------
    # EXPORT: Templates (continued)
    # -------------------------------------------------------------------------

    def _ubl_add_line_item_name_description_nodes(self, vals):
        # EXTENDS account.edi.ubl
        # ibr-125-ae: Item description (IBT-154) is mandatory for AE. Base UBL only fills
        # Description with the free-text portion of the line beyond the product's own name (to
        # avoid duplicating Name into Description) and leaves it empty otherwise - fall back to
        # the item Name so it's always populated.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-125-ae/
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibt-154/
        super()._ubl_add_line_item_name_description_nodes(vals)
        item_node = vals['item_node']
        if not item_node['cbc:Description']:
            item_node['cbc:Description'] = item_node['cbc:Name']

    def _ubl_add_line_price_node(self, vals, in_foreign_currency=True):
        # EXTENDS account.edi.ubl
        # ibr-126-ae: Item price base quantity (IBT-149) and Item Gross Price (IBT-148, inside
        # cac:Price/cac:AllowanceCharge/cbc:BaseAmount per IBG-29) are mandatory for AE, but base
        # UBL's Price node never sets them. No line-level discount is modeled here, so this is a
        # no-op zero-amount allowance/charge with BaseAmount == PriceAmount.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-126-ae/
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibt-149/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibt-148/
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-InvoiceLine/cac-Price/
        super()._ubl_add_line_price_node(vals, in_foreign_currency=in_foreign_currency)
        line_node = vals['line_node']
        base_line = vals['line_vals']['base_line']
        currency = base_line['currency_id'] if in_foreign_currency else vals['company_currency']
        price_node = line_node['cac:Price']
        price_node['cbc:BaseQuantity'] = {
            '_text': 1,
            'unitCode': self._get_uom_unece_code(base_line['product_uom_id']),
        }
        price_node['cac:AllowanceCharge'] = {
            'cbc:ChargeIndicator': {'_text': 'false'},
            'cbc:Amount': {
                '_text': FloatFmt(0, min_dp=currency.decimal_places),
                'currencyID': currency.name,
            },
            'cbc:BaseAmount': {
                '_text': price_node['cbc:PriceAmount']['_text'],
                'currencyID': currency.name,
            },
        }

    def _ubl_add_line_allowance_charge_nodes(self, vals):
        # EXTENDS account.edi.ubl
        # Line-level discounts need this hook to actually populate cac:AllowanceCharge (and
        # therefore LineExtensionAmount) - normally wired by account.edi.ubl_cen_en16931, which
        # this format doesn't inherit (see the no_party_tax_scheme comment in
        # _init_invoice_export_values above). Without it, LineExtensionAmount silently stays at
        # the gross (pre-discount) amount regardless of the line's actual discount %, which is
        # exactly what aligned-ibrp-s-09 catches (VAT amount no longer reconciles).
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/aligned-ibrp-s-09/
        super()._ubl_add_line_allowance_charge_nodes(vals)
        self._ubl_add_line_allowance_charge_nodes_for_discount(vals)

    def _ubl_add_invoice_line_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_invoice_line_node(vals)
        self._ubl_add_invoice_line_price_extension_nodes(vals['line_node'], {**vals, 'base_line': vals['line_vals']['base_line']})

    def _ubl_add_credit_note_line_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_credit_note_line_node(vals)
        self._ubl_add_invoice_line_price_extension_nodes(vals['line_node'], {**vals, 'base_line': vals['line_vals']['base_line']})

    def _ubl_add_invoice_line_price_extension_nodes(self, line_node, vals):
        # Documentation: https://docs.peppol.eu/poac/ae/pint-ae/bis/#_vat_line_amount_btae_08_and_amount_payable_btae_10
        # For node structure https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-InvoiceLine/cac-ItemPriceExtension/
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
        }
        # ibr-163-ae: VAT Line amount (BTAE-08) shall not be there at all (not just zero) when
        # the line's VAT category is Exempt.
        tax_category_code = move_line.tax_ids[:1].ubl_cii_tax_category_code
        if tax_category_code != 'E':
            line_node['cac:ItemPriceExtension']['cac:TaxTotal'] = {
                'cbc:TaxAmount': {
                    '_text': FloatFmt(
                        move_line.l10n_gcc_invoice_tax_amount,
                        min_dp=currency.decimal_places,
                    ),
                    'currencyID': currency.name,
                },
            }

    def _ubl_add_invoice_period_nodes(self, vals):
        # For node structure https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibg-14/
        super()._ubl_add_invoice_period_nodes(vals)
        invoice = vals.get('invoice')

        if invoice.l10n_ae_invoice_transaction_type == '00010000':
            # Summary Invoice needs a startDate/endDate range rather than the description-only
            # invoicePeriod other transaction types use - reuse the deferred revenue period
            # (account_accountant's deferred_start_date/deferred_end_date on the invoice lines)
            # instead of a bespoke field, since that's the standard place this is already
            # recorded. Not a hard dependency (account_accountant may not be installed), so check
            # for the field first and fall back to the invoice's own date when it's absent/unset.
            lines_with_period = invoice.invoice_line_ids.filtered(lambda line: 'deferred_start_date' in line._fields and line.deferred_start_date and line.deferred_end_date)
            if lines_with_period:
                start_date = min(lines_with_period.mapped('deferred_start_date'))
                end_date = max(lines_with_period.mapped('deferred_end_date'))
            else:
                start_date = end_date = invoice.invoice_date
            vals['document_node']['cac:InvoicePeriod'].update({
                'cbc:StartDate': {'_text': start_date},
                'cbc:EndDate': {'_text': end_date},
            })
        elif invoice.invoice_payment_term_id and invoice.invoice_payment_term_id.l10n_ae_billing_frequency:
            vals['document_node']['cac:InvoicePeriod'].update({
                'cbc:Description': {'_text': invoice.invoice_payment_term_id.l10n_ae_billing_frequency},
            })

    def _ubl_add_line_item_commodity_classification_nodes(self, vals):
        # EXTENDS account.edi.ubl
        nodes = super()._ubl_add_line_item_commodity_classification_nodes(vals)
        product = vals['line_vals']['base_line']['product_id']
        item_type = 'G'
        if product.l10n_ae_is_good_and_service:
            item_type = 'B'
        elif product.type == 'service':
            item_type = 'S'
        commodity_classification = {'cbc:CommodityCode': {'_text': item_type}}
        if nature_code := product.l10n_ae_goods_service_type:
            commodity_classification['cbc:NatureCode'] = {'_text': nature_code}
        nodes.append(commodity_classification)
        # ibr-184-ae: Item classification identifier (IBT-158) is mandatory when Item type
        # (BTAE-13, cbc:CommodityCode above) is 'Goods' (or 'Both' - ibr-186-ae).
        # ibr-185-ae/ibr-186-ae: Service accounting code (BTAE-17) is mandatory when Item type
        # is 'Services' (or 'Both'). Odoo only tracks one classification code per product, so the
        # same value is reused for whichever node(s) the item type requires.
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-184-ae/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-185-ae/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-186-ae/
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-13/ - https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibt-158/
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-17/
        # https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-InvoiceLine/cac-Item/cac-CommodityClassification/
        if item_type in ('G', 'B') and product.l10n_ae_classification_code:
            nodes.append({
                'cbc:ItemClassificationCode': {
                    '_text': product.l10n_ae_classification_code,
                    'listID': 'HS',
                },
            })
        if item_type in ('S', 'B') and product.l10n_ae_classification_code:
            vals['item_node']['cac:AdditionalItemIdentification'] = {
                'cbc:ID': {
                    '_text': product.l10n_ae_classification_code,
                    'schemeID': 'SAC',
                },
            }
        return nodes
