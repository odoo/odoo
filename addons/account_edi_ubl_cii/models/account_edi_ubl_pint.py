from odoo import _, models
from odoo.tools import formatLang, html2plaintext
from odoo.tools.misc import NON_BREAKING_SPACE
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt


class AccountEdiUBLPint(models.AbstractModel):
    _name = "account.edi.ubl_pint"
    _inherit = 'account.edi.ubl'
    _description = "UBL PINT"

    # -------------------------------------------------------------------------
    # EXPORT: NODES
    # -------------------------------------------------------------------------

    def _ubl_add_invoice_type_code_node(self, vals):
        super()._ubl_add_invoice_type_code_node(vals)

        if self._is_document(vals, 'invoice'):
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 380
        elif self._is_document(vals, 'self_invoice'):
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 389

    def _ubl_add_credit_note_type_code_node(self, vals):
        super()._ubl_add_credit_note_type_code_node(vals)

        if self._is_document(vals, 'credit_note'):
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 381
        elif self._is_document(vals, 'self_credit_note'):
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 261

    def _ubl_add_notes_nodes_all_invoices(self, vals):
        invoice = vals['invoice']
        notes = []

        # WithholdingTaxTotal is not allowed.
        # Instead, withholding tax amounts are reported as a PrepaidAmount.
        AccountTax = self.env['account.tax']
        base_lines = vals['base_lines']
        currency = vals['currency']

        def grouping_function(base_line, tax_data):
            if not tax_data:
                return
            tax_grouping_key = self._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)
            if not tax_grouping_key:
                return
            return tax_grouping_key['is_withholding']

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        ubl_values = vals['_ubl_values']
        ubl_values['tax_withholding_amount'] = 0.0
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            tax_amount = values['tax_amount_currency']
            ubl_values['tax_withholding_amount'] -= tax_amount

        if not currency.is_zero(ubl_values['tax_withholding_amount']):
            notes.append(_(
                "The prepaid amount of %s corresponds to the withholding tax applied.",
                formatLang(self.env, ubl_values['tax_withholding_amount'], currency_obj=currency).replace(NON_BREAKING_SPACE, ''),
            ))

        terms_and_condition = html2plaintext(invoice.narration) if invoice.narration else None
        if terms_and_condition:
            notes.append(terms_and_condition)

        vals['document_node']['cbc:Note'] = {'_text': ' '.join(notes) if notes else None}

    def _ubl_add_notes_nodes(self, vals):
        # [ibr-sr-51]-Note (ibt-022) MUST occur maximum once
        super()._ubl_add_notes_nodes(vals)

        if self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note'):
            self._ubl_add_notes_nodes_all_invoices(vals)

    def _ubl_add_delivery_nodes(self, vals):
        # [ibr-107]-Deliver to information (ibg-13) MUST occur maximum once.
        super()._ubl_add_delivery_nodes(vals)

        if self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note'):
            document_node = vals['document_node']
            if document_node['cac:Delivery']:
                document_node['cac:Delivery'] = document_node['cac:Delivery'][0]
            else:
                document_node['cac:Delivery'] = None

    def _ubl_add_document_currency_code_node(self, vals):
        # The currency in which the invoice is issued and in which all monetary amounts are expressed.
        # [ibr-005]-An Invoice MUST have an Invoice currency code (ibt-005).
        # [ibr-cl-04]-Invoice currency code (ibt-005) MUST be coded using ISO code list 4217 alpha-3
        super()._ubl_add_document_currency_code_node(vals)
        vals['document_node']['cbc:DocumentCurrencyCode']['_text'] = vals['currency'].name

    def _ubl_add_tax_currency_code_node(self, vals):
        # The currency used for TAX accounting and reporting purposes as accepted or required in the country of the Seller.
        # [ibr-077]-Tax accounting currency code (ibt-006) MUST be different from invoice currency code (ibt-005) when provided.
        # [ibr-cl-05]-Tax currency code (ibt-006) MUST be coded using ISO code list 4217 alpha-3
        super()._ubl_add_tax_currency_code_node(vals)
        company_currency = vals['company'].currency_id
        if vals['document_node']['cbc:DocumentCurrencyCode']['_text'] != company_currency.name:
            vals['document_node']['cbc:TaxCurrencyCode']['_text'] = company_currency.name

    def _ubl_add_buyer_reference_node(self, vals):
        super()._ubl_add_buyer_reference_node(vals)

        customer = vals['customer']
        if customer_ref := customer.commercial_partner_id.ref:
            vals['document_node']['cbc:BuyerReference']['_text'] = customer_ref

    def _ubl_add_billing_reference_nodes(self, vals):
        # A group of business terms providing information on one or more preceding Invoices.
        # [ibr-055]-Each Preceding Invoice reference (ibg-03) MUST contain a Preceding Invoice reference (ibt-025).
        # [ibr-sr-06]-Preceding invoice reference (ibt-025) MUST occur maximum once
        super()._ubl_add_billing_reference_nodes(vals)

        if self._is_document(vals, 'credit_note', 'self_credit_note'):
            credit_note = vals['invoice']
            payment_term_lines = credit_note.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')
            preceding_invoice_names = [
                preceding_invoice_name
                for preceding_invoice_name in (
                    payment_term_lines
                    .matched_credit_ids.credit_move_id.move_id
                    .mapped('name')
                )
                if preceding_invoice_name and preceding_invoice_name != '/'
            ]

            nodes = vals['document_node']['cac:BillingReference']
            for preceding_invoice_name in preceding_invoice_names:
                nodes.append({
                    'cac:InvoiceDocumentReference': {
                        'cbc:ID': {'_text': preceding_invoice_name},
                    }
                })

    def _ubl_get_partner_address_node(self, vals, partner):
        node = super()._ubl_get_partner_address_node(vals, partner)
        node['cbc:CountrySubentityCode'] = None
        node['cac:Country']['cbc:Name'] = None
        return node

    def _ubl_add_party_endpoint_id_node(self, vals):
        super()._ubl_add_party_endpoint_id_node(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        if commercial_partner.peppol_endpoint and commercial_partner.peppol_eas:
            vals['party_node']['cbc:EndpointID']['_text'] = commercial_partner.peppol_endpoint
            vals['party_node']['cbc:EndpointID']['schemeID'] = commercial_partner.peppol_eas

    def _ubl_add_party_identification_nodes(self, vals):
        super()._ubl_add_party_identification_nodes(vals)
        self._ubl_add_party_identification_nodes_iso_6523_icd(vals)

        nodes = vals['party_node']['cac:PartyIdentification']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        country_code = commercial_partner.country_code

        if not nodes and commercial_partner.ref and country_code != 'DK':  # DK-R-013
            nodes.append({
                'cbc:ID': {
                    '_text': commercial_partner.ref,
                    'schemeID': None,
                },
            })

    def _ubl_add_party_tax_scheme_nodes(self, vals):
        super()._ubl_add_party_tax_scheme_nodes(vals)
        if vals['no_party_tax_scheme']:
            return

        super()._ubl_add_party_tax_scheme_nodes_vat_gst(vals)

        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        nodes = vals['party_node']['cac:PartyTaxScheme']
        if not nodes and commercial_partner.peppol_endpoint and commercial_partner.peppol_eas:
            # TaxScheme based on partner's EAS/Endpoint.
            nodes.append({
                'cbc:CompanyID': {'_text': commercial_partner.peppol_endpoint},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': commercial_partner.peppol_eas},
                },
            })

    def _ubl_add_party_legal_entity_nodes(self, vals):
        super()._ubl_add_party_legal_entity_nodes(vals)
        self._ubl_add_party_legal_entity_nodes_iso_6523_icd(vals)

    def _ubl_add_accounting_supplier_party_tax_scheme_nodes(self, vals):
        super()._ubl_add_accounting_supplier_party_tax_scheme_nodes(vals)
        nodes = vals['party_node']['cac:PartyTaxScheme']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        country_code = commercial_partner.country_code

        if country_code == 'NO':
            # [NO-R-002] For Norwegian suppliers, most invoice issuers are required to append
            # "Foretaksregisteret" to their invoice.
            nodes.append({
                'cbc:CompanyID': {'_text': "Foretaksregisteret"},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': "TAX"},
                },
            })
        elif country_code == 'SE':
            # [SE-R-005] For Swedish suppliers, when using Seller tax registration identifier,
            # 'Godkänd för F-skatt' must be stated
            nodes.append({
                'cbc:CompanyID': {'_text': "GODKÄND FÖR F-SKATT"},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': "TAX"},
                },
            })

    def _ubl_add_delivery_party_endpoint_id_node(self, vals):
        pass

    def _ubl_add_delivery_party_identification_nodes(self, vals):
        pass

    def _ubl_add_delivery_party_postal_address_node(self, vals):
        pass

    def _ubl_add_delivery_party_tax_scheme_nodes(self, vals):
        pass

    def _ubl_add_delivery_party_legal_entity_nodes(self, vals):
        pass

    def _ubl_add_delivery_party_contact_node(self, vals):
        pass

    def _ubl_get_payment_means_payee_financial_account_institution_branch_node_from_partner_bank(self, vals, partner_bank):
        node = super()._ubl_get_payment_means_payee_financial_account_institution_branch_node_from_partner_bank(vals, partner_bank)
        if node:
            node['cbc:ID']['schemeID'] = None
            node['cac:FinancialInstitution'] = None
        return node

    def _ubl_add_payment_means_nodes_all_invoices(self, vals):
        invoice = vals['invoice']
        nodes = vals['document_node']['cac:PaymentMeans']

        if invoice.move_type == 'out_invoice':
            if invoice.partner_bank_id:
                payment_means_code, payment_means_name = 30, 'credit transfer'
            else:
                payment_means_code, payment_means_name = 'ZZZ', 'mutually defined'
        else:
            payment_means_code, payment_means_name = 57, 'standing agreement'

        partner_bank = invoice.partner_bank_id
        payment_means_node = {
            'cbc:PaymentMeansCode': {
                '_text': payment_means_code,
                'name': payment_means_name,
            },
            'cbc:PaymentID': {'_text': invoice.payment_reference or invoice.name},
        }

        if partner_bank:
            payment_means_node['cac:PayeeFinancialAccount'] = self._ubl_get_payment_means_payee_financial_account_node_from_partner_bank(vals, partner_bank)
        else:
            payment_means_node['cac:PayeeFinancialAccount'] = None

        nodes.append(payment_means_node)

    def _ubl_add_payment_means_nodes(self, vals):
        super()._ubl_add_payment_means_nodes(vals)

        if self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note'):
            self._ubl_add_payment_means_nodes_all_invoices(vals)

    def _ubl_get_tax_subtotal_node(self, vals, tax_subtotal):
        # This override is a fix for the taxes engine.
        # Currently the taxes computation is not perfect for PINT and then,
        # produce discrepancies between the tax's base amount and the sum of base amount of lines.
        node = super()._ubl_get_tax_subtotal_node(vals, tax_subtotal)

        # [BR-S-08]/[BR-E-08]/[BR-Z-08]/... cac:TaxSubtotal -> cbc:TaxableAmount should be
        # computed based on the cbc:LineExtensionAmount of each line linked to the tax.
        # This applies to all tax category codes (S, E, Z, AE, etc.) as each has a
        # corresponding BR-*-08 schematron rule requiring this consistency.
        currency = tax_subtotal['currency']
        corresponding_line_node_amounts = [
            line_node['cbc:LineExtensionAmount']['_text']
            for tax_category_node in node['cac:TaxCategory']
            for line_key in ('cac:InvoiceLine', 'cac:CreditNoteLine')
            for line_node in vals['document_node'].get(line_key, [])
            for line_node_tax_category_node in line_node['cac:Item']['cac:ClassifiedTaxCategory']
            if (
                    line_node_tax_category_node['cbc:ID']['_text'] == tax_category_node['cbc:ID']['_text']
                    and line_node_tax_category_node['cbc:Percent']['_text'] == tax_category_node['cbc:Percent']['_text']
                    and line_node_tax_category_node['_currency'] == tax_category_node['_currency']
            )
            ] + [
            -allowance_node['cbc:Amount']['_text']
            for tax_category_node in node['cac:TaxCategory']
            for allowance_node in vals['document_node']['cac:AllowanceCharge']
            if allowance_node['cbc:ChargeIndicator']['_text'] == 'false'
            for allowance_node_tax_category_node in allowance_node['cac:TaxCategory']
            if (
                    allowance_node_tax_category_node['cbc:ID']['_text'] == tax_category_node['cbc:ID']['_text']
                    and allowance_node_tax_category_node['cbc:Percent']['_text'] == tax_category_node['cbc:Percent']['_text']
                    and allowance_node_tax_category_node['_currency'] == tax_category_node['_currency']
            )
            ] + [
            allowance_node['cbc:Amount']['_text']
            for tax_category_node in node['cac:TaxCategory']
            for allowance_node in vals['document_node']['cac:AllowanceCharge']
            if allowance_node['cbc:ChargeIndicator']['_text'] == 'true'
            for allowance_node_tax_category_node in allowance_node['cac:TaxCategory']
            if (
                    allowance_node_tax_category_node['cbc:ID']['_text'] == tax_category_node['cbc:ID']['_text']
                    and allowance_node_tax_category_node['cbc:Percent']['_text'] == tax_category_node['cbc:Percent']['_text']
                    and allowance_node_tax_category_node['_currency'] == tax_category_node['_currency']
            )
        ]
        if corresponding_line_node_amounts:
            node['cbc:TaxableAmount'] = {
                '_text': FloatFmt(sum(corresponding_line_node_amounts), min_dp=currency.decimal_places),
                'currencyID': currency.name,
            }

        # Percent is not reported in TaxSubtotal
        node['cbc:Percent']['_text'] = None

        return node

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        tax_total_keys = super()._ubl_tax_totals_node_grouping_key(base_line, tax_data, vals, currency)

        # WithholdingTaxTotal is not allowed.
        # Instead, withholding tax amounts are reported as a PrepaidAmount.
        if tax_total_keys['tax_total_key'] and tax_total_keys['tax_total_key']['is_withholding']:
            tax_total_keys['tax_total_key'] = None

        # In case of multi-currencies, there will be 2 TaxTotals but the one expressed in
        # foreign currency must not have any TaxSubtotal.
        company_currency = vals['company'].currency_id
        if (
            tax_total_keys['tax_subtotal_key']
            and company_currency != vals['currency']
            and tax_total_keys['tax_subtotal_key']['currency'] == company_currency
        ):
            tax_total_keys['tax_subtotal_key'] = None

        return tax_total_keys

    def _ubl_add_legal_monetary_total_payable_rounding_amount_node(self, vals):
        super()._ubl_add_legal_monetary_total_payable_rounding_amount_node(vals)
        currency = vals['currency']
        node = vals['legal_monetary_total_node']

        if self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note'):
            tax_withholding_amount = vals['_ubl_values']['tax_withholding_amount']

            # WithholdingTaxTotal is not allowed.
            # Instead, withholding tax amounts are reported as a PrepaidAmount.
            # Since the UBL layer is putting the difference between TaxInclusiveAmount and the total
            # amount of the base_lines in PayableRoundingAmount, the withholding tax amount ends there.
            # Let's remove them since they are accounted in PrepaidAmount.
            if tax_withholding_amount:
                payable_rounding_amount_node = node['cbc:PayableRoundingAmount']
                payable_rounding_amount = (payable_rounding_amount_node['_text'] or 0.0) + tax_withholding_amount
                if currency.is_zero(payable_rounding_amount):
                    payable_rounding_amount_node['_text'] = None
                    payable_rounding_amount_node['currencyID'] = None
                else:
                    payable_rounding_amount_node['_text'] = FloatFmt(payable_rounding_amount, min_dp=currency.decimal_places)
                    payable_rounding_amount_node['currencyID'] = currency.name

    def _ubl_add_legal_monetary_total_prepaid_payable_amount_node(self, vals, in_foreign_currency=True):
        super()._ubl_add_legal_monetary_total_prepaid_payable_amount_node(vals, in_foreign_currency=in_foreign_currency)
        currency = vals['currency_id'] if in_foreign_currency else vals['company_currency']
        node = vals['legal_monetary_total_node']

        if self._is_document(vals, 'invoice', 'credit_note', 'self_invoice', 'self_credit_note'):
            node['cbc:PrepaidAmount']['_text'] = FloatFmt(
                node['cbc:PrepaidAmount']['_text']
                # WithholdingTaxTotal is not allowed.
                # Instead, withholding tax amounts are reported as a PrepaidAmount.
                # Suppose an invoice of 1000 with a tax 21% +100 -100.
                # The super will compute a PrepaidAmount or 0.0 and a PayableAmount or 1000.
                # This extension is there to increase PrepaidAmount to 210 and PayableAmount to 1210.
                + vals['_ubl_values']['tax_withholding_amount'],
                min_dp=currency.decimal_places,
            )

    def _init_invoice_export_values(self, invoice):
        vals = super()._init_invoice_export_values(invoice)
        AccountTax = self.env['account.tax']
        company = vals['company']

        # Manage taxes for emptying.
        vals['base_lines'] = self._ubl_turn_emptying_taxes_as_new_base_lines(
            base_lines=vals['base_lines'],
            company=company,
            vals=vals,
        )

        # Sub-dictionaries to store UBL-related values along the whole process.
        vals['_ubl_values'] = {}
        for base_line in vals['base_lines']:
            base_line['_ubl_values'] = {}

        # Global rounding of tax_details using 6 digits.
        AccountTax._round_raw_total_excluded(vals['base_lines'], company)
        AccountTax._round_raw_total_excluded(vals['base_lines'], company, in_foreign_currency=False)
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(vals['base_lines'], company)
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(vals['base_lines'], company, in_foreign_currency=False)
        AccountTax._round_raw_gross_total_excluded_and_discount(vals['base_lines'], company)
        AccountTax._round_raw_gross_total_excluded_and_discount(vals['base_lines'], company, in_foreign_currency=False)

        return vals
