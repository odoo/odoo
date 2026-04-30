import re

from odoo import Command, fields, models

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


class AccountEdiXmlPint_Ae(models.AbstractModel):
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

    def _export_invoice(self, invoice):
        """ Render the document to XML, account.edi.ubl only builds its dict. """
        # OVERRIDE account.edi.ubl
        vals = self._export_document(self._init_invoice_export_values(invoice))
        errors = [v for v in vals['constraints'].values() if v]
        return self._etree_to_string(self._vals_to_etree(vals)), set(errors)

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _init_invoice_export_values(self, invoice):
        """ 'no_party_tax_scheme' is expected by account.edi.ubl_pint, and normally set by
        account.edi.ubl_cen_en16931, which this format doesn't inherit.
        """
        vals = super()._init_invoice_export_values(invoice)
        vals['l10n_ae_transaction_type_code'] = vals['invoice'].l10n_ae_transaction_type_ids._get_flags_code()
        vals['no_party_tax_scheme'] = False
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
        return bool(self._get_customization_id(process_type='selfbilling'))

    def _ubl_add_invoice_type_code_node(self, vals):
        """ 480 for a commercial invoice, 389 for a self-billed one (ibr-cl-01 of self-billing).

        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_tax_invoice
        https://docs.peppol.eu/poac/ae/pint-ae-sb/trn-invoice/rule/ibr-cl-01/
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_invoice_type_code_node(vals)
        if self._is_document(vals, 'self_invoice'):
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 389
        if vals['_document_type']['name'] != 'invoice':
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
        if vals['_document_type']['name'] not in ['credit_note', 'self_credit_note']:
            return
        if vals['invoice'].l10n_ae_invoice_type == 'commercial':
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 81

    def _ubl_add_party_endpoint_id_node(self, vals):
        """ Route documents only reported to the FTA (C5) to a predefined endpoint, not the buyer's.

        - Deemed Supply (X1XXXXXX): 0235:9900000097
        - Export to a receiver not on Peppol (XXXXXXX1): 0235:9900000099
        - TODO buyer not subject to UAE e-invoicing: 0235:9900000098

        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_predefined_endpoint
        """
        # EXTENDS account.edi.ubl_pint
        super()._ubl_add_party_endpoint_id_node(vals)
        invoice = vals['invoice']
        if invoice._l10n_ae_has_transaction_type('01000000'):
            vals['party_node']['cbc:EndpointID'] = {'_text': '9900000097', 'schemeID': '0235'}
        if invoice._l10n_ae_has_transaction_type('00000001'):
            vals['party_node']['cbc:EndpointID'] = {'_text': '9900000099', 'schemeID': '0235'}

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
            payment_means_node['cac:PayeeFinancialAccount'] = (
                self._ubl_get_payment_means_payee_financial_account_node_from_partner_bank(vals, invoice.partner_bank_id)
            )

        vals['document_node']['cac:PaymentMeans'] = [payment_means_node]

    def _ubl_add_order_reference_node(self, vals):
        """ Leave out cac:OrderReference without a Customer Reference.

        Its IBT-013 is mandatory, and base's fallback, the invoice number, isn't the buyer's order.
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-OrderReference/
        """
        # EXTENDS account.edi.ubl
        super()._ubl_add_order_reference_node(vals)
        if self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note') and not vals['invoice'].ref:
            vals['document_node']['cac:OrderReference'] = None

    def _ubl_add_billing_reference_nodes(self, vals):
        """ ibr-055-ae: credit notes reference the invoice they credit.

        Base only finds it through reconciliation, fall back to the reversed invoice.
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/rule/ibr-055-ae/
        """
        # EXTENDS account.edi.ubl_pint
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
        """ BTAE-14 Principal ID of a Disclosed Agent Billing, in its own SellerSupplierParty.

        ibr-137-ae, ibr-176-ae.
        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/btae-14/
        """
        principal_id = vals['invoice'].l10n_ae_principal_id
        if principal_id:
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
            conversion_date = invoice.invoice_date or fields.Date.context_today(self)
            total_company_ccy = document_currency._convert(invoice.amount_total, tax_currency, invoice.company_id, conversion_date)
            vals['document_node']['cac:AdditionalDocumentReference'] = [{
                'cbc:ID': {'_text': 'aedtotal-incl-vat'},
                'cbc:DocumentTypeCode': {'_text': 'aedtotal-incl-vat'},
                'cbc:DocumentDescription': {'_text': f'{total_company_ccy:.2f}'},
            }]

    def _ubl_add_party_legal_entity_nodes(self, vals):
        """ https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/syntax/cac-AccountingSupplierParty/cac-Party/cac-PartyLegalEntity/cbc-CompanyID/ """
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
        for node in nodes:
            node['cbc:CompanyID']['_text'] = commercial_partner.l10n_ae_registration_identifier
            node['cbc:CompanyID']['schemeAgencyID'] = registration_identifier_type
            if registration_identifier_type == 'TL':
                node['cbc:CompanyID']['schemeAgencyName'] = commercial_partner.l10n_ae_authority_name
            if registration_identifier_type == 'PAS':
                node['cbc:CompanyID']['schemeAgencyName'] = commercial_partner.l10n_ae_passport_issuing_country_id.code

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

    def _l10n_ae_import_selection_value(self, collected_values, field_name, value, term):
        """ Return the code if it is one of the field's selection values, else log it and return None. """
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

        # BTAE-03 Credit note reason code
        if reason := tree.findtext('./{*}DiscrepancyResponse/{*}ResponseCode'):
            if value := self._l10n_ae_import_selection_value(
                collected_values, 'l10n_ae_credit_note_reason', reason, self.env._("credit note reason"),
            ):
                to_write['l10n_ae_credit_note_reason'] = value

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

    def _ubl_add_invoice_line_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_invoice_line_node(vals)
        self._ubl_add_invoice_line_price_extension_nodes(vals['line_node'], {**vals, 'base_line': vals['line_vals']['base_line']})

    def _ubl_add_credit_note_line_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_credit_note_line_node(vals)
        self._ubl_add_invoice_line_price_extension_nodes(vals['line_node'], {**vals, 'base_line': vals['line_vals']['base_line']})

    def _ubl_add_invoice_line_price_extension_nodes(self, line_node, vals):
        """ BTAE-10 and BTAE-08, always in AED like the AED TaxTotal (IBT-111).

        ibr-163-ae: no BTAE-08 on an exempt line. The category is read off ClassifiedTaxCategory,
        which the rule checks: untaxed lines and uncategorized 0% taxes are 'E' too.
        https://docs.peppol.eu/poac/ae/pint-ae/bis/#_vat_line_amount_btae_08_and_amount_payable_btae_10
        """
        base_line = vals['base_line']
        currency = vals['company'].currency_id
        tax_details = base_line['tax_details']
        line_node['cac:ItemPriceExtension'] = {
            'cbc:Amount': {
                '_text': FloatFmt(
                    tax_details['total_excluded'],
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
                    '_text': FloatFmt(
                        sum(tax_data['tax_amount'] for tax_data in tax_details['taxes_data']),
                        min_dp=currency.decimal_places,
                    ),
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
        - ibr-co-19: needs a start or end date, from the lines' deferred dates (account_accountant,
          optional), else the invoice date up to its due date.

        https://docs.peppol.eu/poac/ae/pint-ae/trn-invoice/semantic-model/ibg-14/
        """
        super()._ubl_add_invoice_period_nodes(vals)
        invoice = vals.get('invoice')
        billing_frequency = invoice.invoice_payment_term_id.l10n_ae_billing_frequency
        if not invoice._l10n_ae_has_transaction_type('00010000') and not billing_frequency:
            return

        lines_with_period = invoice.invoice_line_ids.filtered(lambda line: 'deferred_start_date' in line._fields and line.deferred_start_date and line.deferred_end_date)
        if lines_with_period:
            start_date = min(lines_with_period.mapped('deferred_start_date'))
            end_date = max(lines_with_period.mapped('deferred_end_date'))
        else:
            start_date = invoice.invoice_date
            end_date = invoice.invoice_date_due or invoice.invoice_date
        vals['document_node']['cac:InvoicePeriod'].update({
            'cbc:StartDate': {'_text': start_date},
            'cbc:EndDate': {'_text': end_date},
            'cbc:DescriptionCode': {'_text': billing_frequency or None},
        })

    def _ubl_add_line_item_commodity_classification_nodes(self, vals):
        # EXTENDS account.edi.ubl
        nodes = super()._ubl_add_line_item_commodity_classification_nodes(vals)
        lines = self._l10n_ae_get_base_line_move_lines(vals['line_vals']['base_line'])
        item_types = set(lines.mapped('l10n_ae_item_type'))
        if not item_types:
            return nodes
        item_type = item_types.pop() if len(item_types) == 1 else 'B'
        commodity_classification = {'cbc:CommodityCode': {'_text': item_type}}
        nature_codes = set(lines.mapped('l10n_ae_goods_service_type'))
        if len(nature_codes) == 1 and (nature_code := nature_codes.pop()):
            commodity_classification['cbc:NatureCode'] = {'_text': nature_code}
        nodes.append(commodity_classification)
        hs_codes = lines.filtered(lambda line: line.l10n_ae_item_type in ('G', 'B')).mapped('l10n_ae_hs_code')
        for hs_code in dict.fromkeys(code for code in hs_codes if code):
            nodes.append({
                'cbc:ItemClassificationCode': {
                    '_text': hs_code,
                    'listID': 'HS',
                },
            })
        sac_codes = lines.filtered(lambda line: line.l10n_ae_item_type in ('S', 'B')).mapped('l10n_ae_service_accounting_code')
        sac_nodes = [
            {'cbc:ID': {'_text': sac_code, 'schemeID': 'SAC'}}
            for sac_code in dict.fromkeys(code for code in sac_codes if code)
        ]
        if sac_nodes:
            vals['item_node']['cac:AdditionalItemIdentification'] = sac_nodes
        return nodes

    def _l10n_ae_get_base_line_move_lines(self, base_line):
        """ Return the invoice lines a base line stands for.

        Its own record, or, in a section with hidden composition, all the lines of the section
        sharing its taxes. A collapsed subsection of a collapsed section is merged into the section.
        """
        line = base_line['record']
        if line._name != 'account.move.line':
            return self.env['account.move.line']
        root = line.parent_id
        if root.parent_id.collapse_composition:
            root = root.parent_id
        if not root.collapse_composition:
            return line
        return line.move_id.invoice_line_ids.filtered(
            lambda move_line: move_line.display_type == 'product'
            and root in (move_line.parent_id, move_line.parent_id.parent_id)
            and move_line.tax_ids == line.tax_ids,
        )
