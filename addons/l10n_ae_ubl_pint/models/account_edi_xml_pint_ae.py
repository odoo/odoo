import re

from odoo import Command, models

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt

# ibr-128-ae: CountrySubentity is the 3-letter emirate code, not Odoo's state code or name.
AE_COUNTRY_SUBENTITY_CODES = {
    'AZ': 'AUH',  # Abu Dhabi
    'AJ': 'AJM',  # Ajman
    'DU': 'DXB',  # Dubai
    'FU': 'FUJ',  # Fujairah
    'RK': 'RAK',  # Ras al-Khaimah
    'SH': 'SHJ',  # Sharjah
    'UQ': 'UAQ',  # Umm al-Quwain
}


class AccountEdiXmlPintAe(models.AbstractModel):
    """ United Arab Emirates implementation of Peppol International (PINT) Billing.

    * PINT: https://docs.peppol.eu/poac/pint/pint/
    * PINT AE: https://docs.peppol.eu/poac/ae/pint-ae/
    """
    _name = 'account.edi.xml.pint_ae'
    _inherit = ["account.edi.ubl_pint"]
    _description = "UAE implementation of Peppol International (PINT) model for Billing"

    def _export_invoice_filename(self, invoice):
        # OVERRIDE account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_ae.xml"

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _init_invoice_export_values(self, invoice):
        """ The transaction type flags (BTAE-02), exported as cbc:ProfileExecutionID. """
        vals = super()._init_invoice_export_values(invoice)
        vals['l10n_ae_transaction_type_code'] = vals['invoice'].l10n_ae_transaction_type_ids._get_flags_code()
        return vals

    def _get_customization_id(self, process_type='billing'):
        """ Specification identifier (IBT-024).

        https://docs.peppol.eu/poac/ae/pint-ae/bis/#profiles
        """
        if process_type in ('billing', 'selfbilling'):
            return f'urn:peppol:pint:{process_type}-1@ae-1'
        return None

    def _can_export_selfbilling(self):
        """ https://docs.peppol.eu/poac/ae/pint-ae/bis/#_self_billing_invoice """
        # EXTENDS account.edi.common
        return True

    def _ubl_add_invoice_type_code_node(self, vals):
        """ 480 for a commercial invoice, 389 for a self-billed one (ibr-cl-01 of self-billing).

        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_tax_invoice
        https://docs.peppol.eu/poac/ae/pint-ae-sb/trn-invoice/rule/ibr-cl-01/
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_invoice_type_code_node(vals)
        if self._is_document(vals, 'self_invoice'):
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 389
        if not self._is_document(vals, 'invoice'):
            return
        if vals['invoice'].l10n_ae_invoice_type == 'commercial':
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 480

    def _get_document_type_code_node(self, invoice, invoice_data):
        """ Type code of the embedded PDF, the same as the document's own. """
        # EXTENDS account.edi.ubl
        is_commercial = invoice.l10n_ae_invoice_type == 'commercial'
        code = {
            'out_invoice': 480 if is_commercial else 380,
            'out_refund': 81 if is_commercial else 381,
            'in_invoice': 389,
            'in_refund': 261,
        }.get(invoice.move_type)
        return {'_text': code} if code else None

    def _ubl_add_credit_note_type_code_node(self, vals):
        """ 81 for a commercial credit note, 261 for a self-billed one (ibr-cl-01 of self-billing).

        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_tax_invoice
        https://docs.peppol.eu/poac/ae/pint-ae-sb/trn-invoice/rule/ibr-cl-01/
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_credit_note_type_code_node(vals)
        if self._is_document(vals, 'self_credit_note'):
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 261
        if not self._is_document(vals, 'credit_note', 'self_credit_note'):
            return
        if vals['invoice'].l10n_ae_invoice_type == 'commercial':
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 81

    def _ubl_add_accounting_customer_party_endpoint_id_node(self, vals):
        """ Route documents only reported to the FTA (C5) to a predefined endpoint, not the buyer's
        (see account.move._l10n_ae_get_predefined_buyer_endpoint). The seller keeps its own endpoint.

        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_predefined_endpoint
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_accounting_customer_party_endpoint_id_node(vals)
        if predefined_endpoint := vals['invoice']._l10n_ae_get_predefined_buyer_endpoint():
            vals['party_node']['cbc:EndpointID'] = {'_text': predefined_endpoint, 'schemeID': '0235'}

    def _ubl_add_accounting_supplier_party_tax_scheme_nodes(self, vals):
        """ Seller tax registration identifier (IBT-032): the TIN of a seller without TRN, the
        vendor on a self-billed invoice included.

        MoF e-invoicing guidelines, 18.1.1.
        https://mof.gov.ae/wp-content/uploads/2026/10/UAE-Electronic-Invoicing-Guidelines_En.pdf
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_accounting_supplier_party_tax_scheme_nodes(vals)
        seller = vals['party_vals']['partner'].commercial_partner_id
        if not seller.vat and seller.peppol_eas == '0235' and seller.peppol_endpoint:
            vals['party_node']['cac:PartyTaxScheme'] = [{
                'cbc:CompanyID': {'_text': seller.peppol_endpoint},
                'cac:TaxScheme': {'cbc:ID': {'_text': 'TIN'}},
            }]

    def _ubl_add_accounting_customer_party_identification_nodes(self, vals):
        """ Buyer identifier (IBT-046): the TIN of a UAE buyer without TRN (scheme 0235), or the
        identifier of a foreign buyer, from the ISO/IEC 6523 ICD list.

        MoF e-invoicing guidelines, 18.2.2 and 18.2.3.
        https://mof.gov.ae/wp-content/uploads/2026/10/UAE-Electronic-Invoicing-Guidelines_En.pdf
        """
        # EXTENDS account.edi.ubl
        super()._ubl_add_accounting_customer_party_identification_nodes(vals)
        buyer = vals['party_vals']['partner'].commercial_partner_id
        # ibr-cl-10: the scheme is an ISO/IEC 6523 ICD code (0xxx), unlike Peppol's own 99xx and letter schemes.
        if (
            buyer.peppol_endpoint
            and buyer.peppol_eas
            and buyer.peppol_eas.startswith('0')
            and (buyer.country_code != 'AE' or not buyer.vat)
        ):
            vals['party_node']['cac:PartyIdentification'] = [{
                'cbc:ID': {'_text': buyer.peppol_endpoint, 'schemeID': buyer.peppol_eas},
            }]

    def _ubl_add_accounting_customer_party_tax_scheme_nodes(self, vals):
        """ Buyer VAT identifier (IBT-048): only the buyer's VAT, never its identifier.

        MoF e-invoicing guidelines, 18.2.2 and 18.2.3.
        https://mof.gov.ae/wp-content/uploads/2026/10/UAE-Electronic-Invoicing-Guidelines_En.pdf
        """
        # EXTENDS account.edi.ubl
        super()._ubl_add_accounting_customer_party_tax_scheme_nodes(vals)
        if not vals['party_vals']['partner'].commercial_partner_id.vat:
            vals['party_node']['cac:PartyTaxScheme'] = []

    def _ubl_get_partner_address_node(self, vals, partner):
        """ ibr-128-ae: the emirate code as CountrySubentity.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/PINT-jurisdiction-aligned-rules/
        """
        # EXTENDS account.edi.ubl
        node = super()._ubl_get_partner_address_node(vals, partner)
        if partner.country_id.code == 'AE' and partner.state_id:
            node['cbc:CountrySubentity']['_text'] = AE_COUNTRY_SUBENTITY_CODES.get(partner.state_id.code, partner.state_id.name)
        return node

    def _ubl_add_payment_means_nodes(self, vals):
        """ Codes 30 (credit transfer), 10 (cash) and 1 (not defined), cards (48, 54, 55) unsupported.

        ibr-191-ae: no PaymentMeans on credit notes and Deemed Supply, mandatory otherwise.
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-PaymentMeans/
        """
        # OVERRIDE account.edi.ubl
        invoice = vals['invoice']
        if self._is_document(vals, 'credit_note', 'self_credit_note') or invoice._l10n_ae_has_transaction_type('01000000'):
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
            payment_means_node['cac:PayeeFinancialAccount'] = self._ubl_get_payment_means_payee_financial_account_node_from_partner_bank(vals, invoice.partner_bank_id)

        vals['document_node']['cac:PaymentMeans'] = [payment_means_node]

    def _ubl_add_order_reference_node(self, vals):
        """ Only export cac:OrderReference when the invoice has a Customer Reference.

        cac:OrderReference is optional, but when present its cbc:ID (IBT-013, the buyer's purchase
        order number) is mandatory. Without a Customer Reference, base fills that ID with the
        invoice number, which is not a purchase order number, so we drop the element instead.
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-OrderReference/
        """
        # EXTENDS account.edi.ubl
        super()._ubl_add_order_reference_node(vals)
        if self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note') and not vals['invoice'].ref:
            vals['document_node']['cac:OrderReference'] = None

    def _ubl_add_billing_reference_nodes(self, vals):
        """ ibr-055-ae: credit notes reference the invoice they credit, except Volume Discount ones.

        Base only finds it through reconciliation, fall back to the reversed invoice.
        A Volume Discount credit note must not have a reference, even when it reverses an invoice.
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-055-ae/
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_billing_reference_nodes(vals)
        if not self._is_document(vals, 'credit_note', 'self_credit_note'):
            return
        credit_note = vals['invoice']
        if credit_note.l10n_ae_credit_note_reason == 'VD':
            vals['document_node']['cac:BillingReference'] = []
            return
        nodes = vals['document_node']['cac:BillingReference']
        if nodes:
            return
        if credit_note.reversed_entry_id and credit_note.reversed_entry_id.name and credit_note.reversed_entry_id.name != '/':
            nodes.append({
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': credit_note.reversed_entry_id.name},
                },
            })

    def _get_tax_category_code(self, customer, supplier, tax):
        """ No category for a line without a tax, rather than base's 'E' guess: PINT AE requires
        one per line (ibr-sr-58), which the validation then reports.
        """
        # EXTENDS account.edi.common
        if not tax:
            return None
        return super()._get_tax_category_code(customer, supplier, tax)

    def _ubl_get_tax_category_node(self, vals, tax_category):
        """ ibr-121-ae: no VAT rate on category 'E' in the breakdown.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/aligned-ibrp-e-05/
        """
        # EXTENDS account.edi.ubl
        node = super()._ubl_get_tax_category_node(vals, tax_category)
        if tax_category.get('tax_category_code') == 'E':
            node['cbc:Percent']['_text'] = None
        return node

    def _ubl_get_line_item_node_classified_tax_category_node(self, vals, tax_category):
        """ Add the exemption reason, and drop the VAT rate on category 'E' (aligned-ibrp-e-05).

        The rate is dropped per node rather than in the grouping key, which the document level
        allowances/charges share and need the rate in (aligned-ibrp-e-06/07).
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/aligned-ibrp-e-05/
        """
        # EXTENDS account.edi.ubl
        node = super()._ubl_get_line_item_node_classified_tax_category_node(vals, tax_category)
        if exemption_reason_code := tax_category.get('tax_exemption_reason_code'):
            node['cbc:TaxExemptionReasonCode']['_text'] = exemption_reason_code
            node['cbc:TaxExemptionReason']['_text'] = tax_category.get('tax_exemption_reason')
        if tax_category.get('tax_category_code') == 'E':
            node['cbc:Percent']['_text'] = None
        return node

    def _export_document_node_constraints(self, vals):
        """
        Validates invoice constraints for PINT AE payload
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/
        """
        # EXTENDS account.edi.ubl_pint
        constraints = super()._export_document_node_constraints(vals)

        document_node = vals['document_node']
        is_invoice = self._is_document(vals, 'invoice', 'self_invoice')
        transaction_type_code = document_node['cbc:ProfileExecutionID']['_text'] or ''

        # -----------------------------------------------------------------
        # 1. Transaction Type (BTAE-02)
        # -----------------------------------------------------------------
        # [IBR-007-AE] - When the Invoice transaction type code (BTAE-02) is 1XXXXXXX (Free trade
        # zone), the Beneficiary ID (BTAE-01) MUST be provided.
        if transaction_type_code[:1] == '1' and not (document_node.get('cac:BuyerCustomerParty') or {}).get('cac:Party'):
            constraints['ibr_007_ae_beneficiary_id_required'] = self.env._(
                "Beneficiary ID is missing for a Free Trade Zone supply [IBR-007-AE]."
            )

        # [IBR-137-AE] - When the Invoice transaction type code (BTAE-02) is XXXXX1XX (Disclosed
        # agent billing), the Principal ID (BTAE-14) MUST be provided.
        if transaction_type_code[5:6] == '1' and not (document_node.get('cac:SellerSupplierParty') or {}).get('cac:Party'):
            constraints['ibr_137_ae_principal_id_required'] = self.env._(
                "Principal ID is missing for a Disclosed Agent Billing supply [IBR-137-AE]."
            )

        # [IBR-160-AE] - When the Frequency of billing (BTAE-06) is 'Others', the Invoice note
        # (IBT-022) MUST be provided.
        invoice_period = document_node.get('cac:InvoicePeriod') or {}
        if (
            (invoice_period.get('cbc:DescriptionCode') or {}).get('_text') == 'OTH'
            and not (document_node.get('cbc:Note') or {}).get('_text')
        ):
            constraints['ibr_160_ae_billing_frequency_note_required'] = self.env._(
                "The \"Others\" billing frequency must be described in the Terms & Conditions [IBR-160-AE]."
            )

        # -----------------------------------------------------------------
        # 2. Credit Note (BTAE-03, IBG-03)
        # -----------------------------------------------------------------
        if not is_invoice:
            reason_code = document_node['cac:DiscrepancyResponse']['cbc:ResponseCode']['_text']

            # [IBR-158-AE] - A Credit note (381) MUST have a Credit note reason code (BTAE-03).
            if document_node['cbc:CreditNoteTypeCode']['_text'] == 381 and not reason_code:
                constraints['ibr_158_ae_credit_note_reason_required'] = self.env._(
                    "Credit Note Reason is missing [IBR-158-AE]."
                )

            # [IBR-055-AE] - A Credit note MUST have a Preceding invoice reference (IBG-03), except
            # when the Credit note reason code (BTAE-03) is 'VD'.
            if reason_code and reason_code != 'VD' and not document_node['cac:BillingReference']:
                constraints['ibr_055_ae_preceding_invoice_required'] = self.env._(
                    "The credited invoice is missing: set it in \"Reversal Of\", or use the Volume Discount reason [IBR-055-AE]."
                )

        # -----------------------------------------------------------------
        # 3. Legal Registration Identifier (BTAE-15, BTAE-16)
        # -----------------------------------------------------------------
        for party_key, passport_rule, authority_rule in (
            ('cac:AccountingSupplierParty', 'IBR-012-AE', 'IBR-172-AE'),
            ('cac:AccountingCustomerParty', 'IBR-010-AE', 'IBR-101-AE'),
        ):
            party = document_node[party_key]['cac:Party']
            party_name = party['cac:PartyName']['cbc:Name']['_text']
            for legal_entity in party.get('cac:PartyLegalEntity') or []:
                company_id_node = legal_entity['cbc:CompanyID']
                if company_id_node.get('schemeAgencyName'):
                    continue
                # [IBR-010-AE/IBR-012-AE] - The Passport issuing country code (BTAE-18/19) MUST be
                # provided when the legal registration identifier type is 'Passport'.
                if company_id_node.get('schemeAgencyID') == 'PAS':
                    constraints[f'{passport_rule.lower().replace("-", "_")}_passport_country_required'] = self.env._(
                        "%(partner)s: Passport Issuing Country is missing [%(rule)s].", partner=party_name, rule=passport_rule
                    )
                # [IBR-101-AE/IBR-172-AE] - The Authority name (BTAE-11/12) MUST be provided when the
                # legal registration identifier type is 'Commercial/Trade license'.
                elif company_id_node.get('schemeAgencyID') == 'TL':
                    constraints[f'{authority_rule.lower().replace("-", "_")}_authority_name_required'] = self.env._(
                        "%(partner)s: Authority Name is missing [%(rule)s].", partner=party_name, rule=authority_rule
                    )

        # -----------------------------------------------------------------
        # 4. Invoice Lines (IBG-25)
        # -----------------------------------------------------------------
        line_key = 'cac:InvoiceLine' if is_invoice else 'cac:CreditNoteLine'
        for line_idx, line in enumerate(document_node[line_key], start=1):
            line_item = line['cac:Item']
            classifications = line_item.get('cac:CommodityClassification') or []
            item_type = next(
                (node['cbc:CommodityCode']['_text'] for node in classifications if node.get('cbc:CommodityCode')),
                None,
            )
            has_hs_code = any(node.get('cbc:ItemClassificationCode') for node in classifications)
            has_sac = bool(((line_item.get('cac:AdditionalItemIdentification') or {}).get('cbc:ID') or {}).get('_text'))

            # [IBR-184-AE/IBR-186-AE] - Goods (G) or Both (B) MUST have an Item classification
            # identifier (IBT-158).
            if item_type in ('G', 'B') and not has_hs_code:
                constraints[f'ibr_184_ae_line_hs_code_required_{line_idx}'] = self.env._(
                    "Line %s: HS Code is missing for goods [IBR-184-AE].", line_idx
                )

            # [IBR-185-AE/IBR-186-AE] - Services (S) or Both (B) MUST have a Service accounting
            # code (BTAE-17).
            if item_type in ('S', 'B') and not has_sac:
                constraints[f'ibr_185_ae_line_service_accounting_code_required_{line_idx}'] = self.env._(
                    "Line %s: Service Accounting Code is missing for services [IBR-185-AE].", line_idx
                )

        return constraints

    def _fill_document_values_invoice(self, vals):
        """ https://docs.peppol.eu/poac/ae/pint-ae/bis/#_invoice_transaction_type_code """
        # EXTENDS account.edi.ubl
        super()._fill_document_values_invoice(vals)
        vals['document_node']['cbc:UUID'] = {'_text': vals['invoice'].l10n_ae_uuid}
        vals['document_node']['cbc:ProfileExecutionID'] = {'_text': vals['l10n_ae_transaction_type_code'] or '00000000'}
        self._ubl_add_ae_buyer_customer_party_node(vals)
        self._ubl_add_ae_seller_supplier_party_node(vals)

    def _fill_document_values_credit_note(self, vals):
        """ The transaction type code (ibr-154-ae) and BTAE-03 reason code are mandatory.

        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_invoice_transaction_type_code
        https://docs.peppol.eu/poac/ae/pint-ae/trn-creditnote/semantic-model/btae-03/
        """
        # EXTENDS account.edi.ubl
        super()._fill_document_values_credit_note(vals)
        vals['document_node']['cbc:UUID'] = {'_text': vals['invoice'].l10n_ae_uuid}
        vals['document_node']['cbc:ProfileExecutionID'] = {'_text': vals['l10n_ae_transaction_type_code'] or '00000000'}
        vals['document_node']['cac:DiscrepancyResponse'] = {
            'cbc:ResponseCode': {'_text': vals['invoice'].l10n_ae_credit_note_reason},
        }
        self._ubl_add_billing_reference_nodes(vals)
        self._ubl_add_ae_buyer_customer_party_node(vals)
        self._ubl_add_ae_seller_supplier_party_node(vals)

    def _ubl_add_ae_buyer_customer_party_node(self, vals):
        """ BTAE-01 Beneficiary ID of a Free Trade Zone supply, in its own BuyerCustomerParty.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-01/
        """
        if beneficiary_id := vals['invoice'].l10n_ae_beneficiary_id:
            vals['document_node']['cac:BuyerCustomerParty'] = {
                'cac:Party': {
                    'cac:PartyIdentification': {
                        'cbc:ID': {'_text': beneficiary_id},
                    },
                },
            }

    def _ubl_add_ae_seller_supplier_party_node(self, vals):
        """ BTAE-14 Principal ID of a Disclosed Agent Billing, in its own SellerSupplierParty.

        ibr-137-ae, ibr-176-ae.
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-14/
        """
        if principal_id := vals['invoice'].l10n_ae_principal_id:
            vals['document_node']['cac:SellerSupplierParty'] = {
                'cac:Party': {
                    'cac:PartyIdentification': {
                        'cbc:ID': {'_text': principal_id},
                    },
                },
            }

    def _ubl_add_tax_currency_code_node(self, vals):
        """ BTAE-04 exchange rate, and the AED total with VAT next to base's AED TaxTotal.

        The rate is the inverse of invoice_currency_rate (company -> document), rounded to the
        6 decimal places ibr-002-ae allows (1 / (1 / 3.67) is 3.6699999999999995).
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-04/
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-002-ae/
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_tax_currency_code_node(vals)
        invoice = vals['invoice']
        document_currency = vals['currency']
        tax_currency = vals['company'].currency_id
        if document_currency != tax_currency:
            vals['document_node']['cac:TaxExchangeRate'] = {
                'cbc:SourceCurrencyCode': {'_text': document_currency.name},
                'cbc:TargetCurrencyCode': {'_text': tax_currency.name},
                'cbc:CalculationRate': {'_text': invoice.invoice_currency_rate and round(1 / invoice.invoice_currency_rate, 6)},
                'cbc:Date': {'_text': invoice.invoice_date},
            }
            # The total as booked in AED: the same rate as the journal items, no conversion of its own.
            total_company_ccy = abs(invoice.amount_total_signed)
            vals['document_node']['cac:AdditionalDocumentReference'] = [{
                'cbc:ID': {'_text': 'aedtotal-incl-vat'},
                'cbc:DocumentTypeCode': {'_text': 'aedtotal-incl-vat'},
                'cbc:DocumentDescription': {'_text': f'{total_company_ccy:.2f}'},
            }]

    def _ubl_add_party_legal_entity_nodes(self, vals):
        """ https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-AccountingSupplierParty/cac-Party/cac-PartyLegalEntity/cbc-CompanyID/ """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_party_legal_entity_nodes(vals)
        commercial_partner = vals['party_vals']['partner'].commercial_partner_id
        # Always one legal entity: its registration name (IBT-027/IBT-044) is mandatory. Its
        # CompanyID is the AE legal registration identifier with its type (BTAE-15/BTAE-16), not
        # the VAT number base puts there (the TRN goes in PartyTaxScheme), and only when set.
        company_id_node = {'_text': None}
        if registration_identifier := commercial_partner.l10n_ae_registration_identifier:
            registration_identifier_type = commercial_partner.l10n_ae_registration_identifier_type
            company_id_node = {
                '_text': registration_identifier,
                'schemeAgencyID': registration_identifier_type,
            }
            if registration_identifier_type == 'TL':
                company_id_node['schemeAgencyName'] = commercial_partner.l10n_ae_authority_name
            elif registration_identifier_type == 'PAS':
                company_id_node['schemeAgencyName'] = commercial_partner.l10n_ae_passport_issuing_country_id.code
        vals['party_node']['cac:PartyLegalEntity'] = [{
            'cbc:RegistrationName': {'_text': commercial_partner.name},
            'cbc:CompanyID': company_id_node,
        }]

    def _ubl_add_customization_id_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_customization_id_node(vals)
        is_self_billing = self._is_document(vals, 'self_invoice', 'self_credit_note')
        vals['document_node']['cbc:CustomizationID']['_text'] = self._get_customization_id(
            process_type='selfbilling' if is_self_billing else 'billing')

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_ubl_invoice_add_incoterm_values(self, collected_values):
        """ Read BTAE-22 under cac:Delivery, base only reads cac:TransportExecutionTerms.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-22/
        """
        # EXTENDS account.edi.ubl
        super()._import_ubl_invoice_add_incoterm_values(collected_values)
        codes = collected_values['incoterm_values']['codes']
        for node in collected_values['tree'].findall('./{*}Delivery/{*}DeliveryTerms/{*}ID'):
            if node.text:
                codes.add(node.text)

    def _import_ubl_invoice_optional_fields(self, collected_values):
        # EXTENDS account.edi.ubl
        super()._import_ubl_invoice_optional_fields(collected_values)
        self._l10n_ae_import_document_values(collected_values)

    def _l10n_ae_import_document_values(self, collected_values):
        """ Decode the AE specific business terms the export writes.

        Only 'commercial' can be read back from the type code, 'simplified' and 'tax' are both 380/381.
        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_invoice_transaction_type_code
        """
        tree = collected_values['tree']
        to_write = collected_values['to_write']

        # BTAE-07 UUID
        if document_uuid := tree.findtext('./{*}UUID'):
            to_write['l10n_ae_uuid'] = document_uuid

        # BTAE-02 transaction type flags (ibr-154-ae)
        transaction_type_code = tree.findtext('./{*}ProfileExecutionID')
        if transaction_type_code and transaction_type_code != '00000000':
            if re.fullmatch(r'[01]{8}', transaction_type_code):
                to_write['l10n_ae_transaction_type_ids'] = [
                    Command.set(self.env['l10n_ae.transaction.type']._get_from_flags_code(transaction_type_code).ids),
                ]
            else:
                collected_values['logs'].append(self.env._(
                    "The %(term)s code %(code)s is not supported and was ignored.",
                    term=self.env._("invoice transaction type"), code=transaction_type_code,
                ))

        type_code = tree.findtext('./{*}InvoiceTypeCode') or tree.findtext('./{*}CreditNoteTypeCode')
        if type_code in ('480', '81'):
            to_write['l10n_ae_invoice_type'] = 'commercial'

        # BTAE-03 Credit note reason code, ignored when unknown: writing it would abort the import.
        if reason := tree.findtext('./{*}DiscrepancyResponse/{*}ResponseCode'):
            if reason in self.env['account.move']._fields['l10n_ae_credit_note_reason'].get_values(self.env):
                to_write['l10n_ae_credit_note_reason'] = reason
            else:
                collected_values['logs'].append(self.env._(
                    "The %(term)s code %(code)s is not supported and was ignored.",
                    term=self.env._("credit note reason"), code=reason,
                ))

        # BTAE-01 Beneficiary ID
        if beneficiary_id := tree.findtext('./{*}BuyerCustomerParty/{*}Party/{*}PartyIdentification/{*}ID'):
            to_write['l10n_ae_beneficiary_id'] = beneficiary_id

        # BTAE-14 Principal ID
        if principal_id := tree.findtext('./{*}SellerSupplierParty/{*}Party/{*}PartyIdentification/{*}ID'):
            to_write['l10n_ae_principal_id'] = principal_id

    # -------------------------------------------------------------------------
    # EXPORT: Templates (continued)
    # -------------------------------------------------------------------------

    def _ubl_add_line_item_name_description_nodes(self, vals):
        """ ibr-125-ae: Item description (IBT-154) is mandatory, fall back to the item name.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-125-ae/
        """
        # EXTENDS account.edi.ubl
        super()._ubl_add_line_item_name_description_nodes(vals)
        item_node = vals['item_node']
        if not item_node['cbc:Description']:
            item_node['cbc:Description'] = item_node['cbc:Name']

    def _ubl_add_line_price_node(self, vals, in_foreign_currency=True):
        """ ibr-126-ae: Item price base quantity (IBT-149) and gross price (IBT-148) are mandatory.

        Without a line discount, the gross price is the net price with a zero allowance.
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-126-ae/
        """
        # EXTENDS account.edi.ubl
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

    def _ubl_add_line_id_node(self, vals):
        """ Invoice line identifier (IBT-126): the journal item's, like the ClearTax JSON. A line of
        a collapsed section carries its first journal item.
        """
        # EXTENDS account.edi.ubl
        super()._ubl_add_line_id_node(vals)
        record = vals['line_vals']['base_line']['record']
        if record and record._name == 'account.move.line':
            vals['line_node']['cbc:ID'] = {'_text': record.id}

    def _ubl_add_legal_monetary_total_prepaid_payable_amount_node(self, vals, in_foreign_currency=True):
        """ The full amount due (IBT-115), like the ClearTax JSON: the payments already reconciled
        are not deducted as a paid amount (IBT-113).
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_legal_monetary_total_prepaid_payable_amount_node(vals, in_foreign_currency=in_foreign_currency)
        currency = vals['currency_id'] if in_foreign_currency else vals['company_currency']
        node = vals['legal_monetary_total_node']
        payable_rounding_amount = (node['cbc:PayableRoundingAmount'] or {}).get('_text') or 0.0
        node['cbc:PrepaidAmount'] = None
        node['cbc:PayableAmount']['_text'] = FloatFmt(
            node['cbc:TaxInclusiveAmount']['_text'] + payable_rounding_amount,
            min_dp=currency.decimal_places,
        )

    def _ubl_add_invoice_line_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_invoice_line_node(vals)
        self._l10n_ae_add_line_price_extension_nodes(vals['line_node'], {**vals, 'base_line': vals['line_vals']['base_line']})

    def _ubl_add_credit_note_line_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_credit_note_line_node(vals)
        self._l10n_ae_add_line_price_extension_nodes(vals['line_node'], {**vals, 'base_line': vals['line_vals']['base_line']})

    def _l10n_ae_add_line_price_extension_nodes(self, line_node, vals):
        """ BTAE-10, the line amount with VAT, and BTAE-08, its VAT, always in AED like the AED
        TaxTotal (IBT-111).

        ibr-163-ae: no BTAE-08 on an exempt line. The category is read off ClassifiedTaxCategory,
        which the rule checks: untaxed lines and uncategorized 0% taxes are 'E' too.
        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_vat_line_amount_btae_08_and_amount_payable_btae_10
        """
        base_line = vals['base_line']
        currency = vals['company'].currency_id
        tax_details = base_line['tax_details']
        tax_amount = sum(tax_data['tax_amount'] for tax_data in tax_details['taxes_data'])
        line_node['cac:ItemPriceExtension'] = {
            'cbc:Amount': {
                '_text': FloatFmt(
                    tax_details['total_excluded'] + tax_amount,
                    min_dp=currency.decimal_places,
                ),
                'currencyID': currency.name,
            },
        }
        tax_category_codes = {
            node['cbc:ID']['_text']
            for node in line_node['cac:Item']['cac:ClassifiedTaxCategory']
        }
        if 'E' not in tax_category_codes:
            line_node['cac:ItemPriceExtension']['cac:TaxTotal'] = {
                'cbc:TaxAmount': {
                    '_text': FloatFmt(tax_amount, min_dp=currency.decimal_places),
                    'currencyID': currency.name,
                },
            }

    def _ubl_add_delivery_nodes(self, vals):
        """ BTAE-22 Incoterms, only when set: ibr-196-ae rejects a DeliveryTerms without an ID.

        cac:Delivery is a single node on billing documents (account.edi.ubl_pint, ibr-107).
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-22/
        """
        # EXTENDS account.edi.ubl
        super()._ubl_add_delivery_nodes(vals)
        incoterm_code = vals['invoice'].invoice_incoterm_id.code
        if not incoterm_code:
            return
        delivery_node = vals['document_node'].get('cac:Delivery')
        for node in delivery_node if isinstance(delivery_node, list) else [delivery_node]:
            if node:
                node['cac:DeliveryTerms'] = {'cbc:ID': {'_text': incoterm_code}}

    def _ubl_add_invoice_period_nodes(self, vals):
        """ Invoicing period (IBG-14), with the frequency of billing (BTAE-06, ibr-005-ae).

        - ibr-138-ae: mandatory on a Summary invoice.
        - ibr-co-19: needs a start or end date.

        Like the CII export: when every line has a start and an end date (account_accountant,
        optional), the period goes from the earliest start to the latest end, so it contains every
        line period. Otherwise, it is the delivery date, else the invoice date. The due date is
        never used: it is a payment deadline, not a period end.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibg-14/
        """
        super()._ubl_add_invoice_period_nodes(vals)
        invoice = vals.get('invoice')
        billing_frequency = invoice.invoice_payment_term_id.l10n_ae_billing_frequency
        if not invoice._l10n_ae_has_transaction_type('00010000') and not billing_frequency:
            return

        line_periods = [
            (line_vals['line_vals']['base_line'].get('deferred_start_date'), line_vals['line_vals']['base_line'].get('deferred_end_date'))
            for line_vals in self._line_nodes_filter_base_lines(vals)
        ]
        if line_periods and all(start_date and end_date for start_date, end_date in line_periods):
            start_dates, end_dates = zip(*line_periods)
            start_date, end_date = min(start_dates), max(end_dates)
        else:
            start_date = end_date = invoice.delivery_date or invoice.invoice_date
        vals['document_node']['cac:InvoicePeriod'].update({
            'cbc:StartDate': {'_text': start_date},
            'cbc:EndDate': {'_text': end_date},
            'cbc:DescriptionCode': {'_text': billing_frequency or None},
        })

    def _ubl_add_line_item_commodity_classification_nodes(self, vals):
        # EXTENDS account.edi.ubl
        nodes = super()._ubl_add_line_item_commodity_classification_nodes(vals)
        line = vals['line_vals']['base_line']['record']
        if line._name != 'account.move.line' or not line.l10n_ae_item_type:
            return nodes
        commodity_classification = {'cbc:CommodityCode': {'_text': line.l10n_ae_item_type}}
        if goods_type := line.l10n_ae_goods_service_type:
            commodity_classification['cbc:NatureCode'] = {'_text': goods_type}
        nodes.append(commodity_classification)
        if line.l10n_ae_item_type in ('G', 'B') and line.l10n_ae_hs_code:
            nodes.append({
                'cbc:ItemClassificationCode': {
                    '_text': line.l10n_ae_hs_code,
                    'listID': 'HS',
                },
            })
        if line.l10n_ae_item_type in ('S', 'B') and line.l10n_ae_service_accounting_code:
            vals['item_node']['cac:AdditionalItemIdentification'] = {
                'cbc:ID': {'_text': line.l10n_ae_service_accounting_code, 'schemeID': 'SAC'},
            }
        return nodes

    def _l10n_ae_get_line_classification_key(self, line):
        """ The classification values an item carries once: lines differing in any of them are
        different items.
        """
        return (
            line.l10n_ae_item_type or '',
            line.l10n_ae_goods_service_type or '',
            line.l10n_ae_hs_code or '',
            line.l10n_ae_service_accounting_code or '',
        )

    def _ubl_get_collapsed_base_line_grouping_key(self, base_line):
        """ A collapsed section keeps one line per item classification rather than merging items
        that differ in it: the item type, goods type, HS code and service accounting code are all
        single per item (BTAE-13, BTAE-09, IBT-158 per classification, BTAE-17).
        """
        # EXTENDS account.edi.ubl
        return (
            *super()._ubl_get_collapsed_base_line_grouping_key(base_line),
            *self._l10n_ae_get_line_classification_key(base_line['record']),
        )
