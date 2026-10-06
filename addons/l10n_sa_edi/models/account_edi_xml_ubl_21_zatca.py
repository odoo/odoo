from odoo import fields, models
from odoo.tools import html2plaintext

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt
from odoo.addons.l10n_sa_edi.models.zatca_ubl_mixin import PAYMENT_MEANS_CODE


class AccountEdiXmlUbl_21Zatca(models.AbstractModel):
    _name = 'account.edi.xml.ubl_21.zatca'
    _inherit = ['zatca.ubl.mixin', 'account.edi.ubl']
    _description = 'UBL 2.1 (ZATCA)'

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _ubl_setup_base_lines(self, vals):
        invoice = vals['invoice']

        # Filter out prepayment lines of final invoices
        if not invoice._is_downpayment():
            vals['base_lines'] = [
                base_line
                for base_line in vals['base_lines']
                if not base_line['record']._get_downpayment_lines()
            ]

        # Get downpayment moves' base lines
        if not invoice._is_downpayment():
            prepayment_moves = invoice.line_ids._get_downpayment_lines().move_id.filtered(lambda m: m.move_type == 'out_invoice')
            if non_reversed := prepayment_moves.filtered(lambda m: m.payment_state != 'reversed'):
                prepayment_moves = non_reversed
        else:
            prepayment_moves = self.env['account.move']

        prepayment_moves_base_lines = {}
        for prepayment_move in prepayment_moves:
            prepayment_move_base_lines, _dummy = prepayment_move._get_rounded_base_and_tax_lines()
            prepayment_moves_base_lines[prepayment_move] = prepayment_move_base_lines

        vals['prepayment_moves_base_lines'] = prepayment_moves_base_lines

        super()._ubl_setup_base_lines(vals)

    def _get_zatca_issue_date(self, vals):
        invoice = vals['invoice']
        return fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), invoice.l10n_sa_confirmation_datetime)

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document header nodes
    # -------------------------------------------------------------------------

    def _fill_document_values_invoice(self, vals):
        super()._fill_document_values_invoice(vals)
        self._add_zatca_uuid_node(vals)
        self._add_zatca_billing_reference_nodes(vals)
        self._add_zatca_additional_document_reference_nodes(vals)
        self._add_zatca_signature_node(vals)

    def _ubl_add_version_id_node(self, vals):
        vals['document_node']['cbc:UBLVersionID'] = {'_text': '2.1'}

    def _ubl_add_profile_id_node(self, vals):
        vals['document_node']['cbc:ProfileID'] = {'_text': 'reporting:1.0'}

    def _add_zatca_uuid_node(self, vals):
        vals['document_node']['cbc:UUID'] = {'_text': vals['invoice'].l10n_sa_uuid}

    def _ubl_add_issue_date_node(self, vals):
        issue_date = self._get_zatca_issue_date(vals)
        vals['document_node']['cbc:IssueDate'] = {'_text': issue_date.strftime('%Y-%m-%d')}
        vals['document_node']['cbc:IssueTime'] = {'_text': issue_date.strftime('%H:%M:%S')}

    def _ubl_add_due_date_node(self, vals):
        vals['document_node']['cbc:DueDate'] = {'_text': None}

    def _ubl_add_invoice_type_code_node(self, vals):
        invoice = vals['invoice']
        vals['document_node']['cbc:InvoiceTypeCode'] = {
            '_text': (
                383 if invoice.debit_origin_id else
                381 if invoice.move_type == 'out_refund' else
                386 if invoice._is_downpayment() else 388
            ),
            'name': invoice._get_l10n_sa_edi_invoice_type_code(),
        }

    def _ubl_add_notes_nodes(self, vals):
        invoice = vals['invoice']
        vals['document_node']['cbc:Note'] = [{'_text': html2plaintext(invoice.narration)}] if invoice.narration else []

    def _ubl_add_document_currency_code_node(self, vals):
        self._ubl_add_document_currency_code_node_foreign_currency(vals)

    def _ubl_add_tax_currency_code_node(self, vals):
        self._ubl_add_tax_currency_code_node_company_currency(vals)

    def _ubl_add_buyer_reference_node(self, vals):
        vals['document_node']['cbc:BuyerReference'] = {'_text': vals['invoice'].commercial_partner_id.ref}

    def _ubl_add_order_reference_node(self, vals):
        vals['document_node']['cac:OrderReference'] = None

    def _add_zatca_billing_reference_nodes(self, vals):
        invoice = vals['invoice']
        nodes = vals['document_node']['cac:BillingReference'] = []
        if invoice.move_type == 'out_refund' or invoice.debit_origin_id:
            nodes.append({
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {
                        '_text': (invoice.reversed_entry_id.name or invoice.ref)
                        if invoice.move_type == 'out_refund'
                        else invoice.debit_origin_id.name,
                    },
                },
            })

    def _add_zatca_additional_document_reference_nodes(self, vals):
        invoice = vals['invoice']
        vals['document_node']['cac:AdditionalDocumentReference'] = [
            {
                'cbc:ID': {'_text': 'QR'},
                'cac:Attachment': {
                    'cbc:EmbeddedDocumentBinaryObject': {
                        '_text': 'N/A',
                        'mimeCode': 'text/plain',
                    },
                },
            } if invoice.l10n_sa_invoice_type == 'simplified' else None,
            {
                'cbc:ID': {'_text': 'PIH'},
                'cac:Attachment': {
                    'cbc:EmbeddedDocumentBinaryObject': {
                        '_text': (
                            "NWZlY2ViNjZmZmM4NmYzOGQ5NTI3ODZjNmQ2OTZjNzljMmRiYzIzOWRkNGU5MWI0NjcyOWQ3M2EyN2ZiNTdlOQ=="
                            if invoice.company_id.l10n_sa_api_mode == 'sandbox' or not invoice.journal_id.l10n_sa_latest_submission_hash
                            else invoice.journal_id.l10n_sa_latest_submission_hash
                        ),
                        'mimeCode': 'text/plain',
                    },
                },
            },
            {
                'cbc:ID': {'_text': 'ICV'},
                'cbc:UUID': {'_text': invoice.l10n_sa_chain_index},
            },
        ]

    def _add_zatca_signature_node(self, vals):
        invoice = vals['invoice']
        vals['document_node']['cac:Signature'] = {
            'cbc:ID': {'_text': "urn:oasis:names:specification:ubl:signature:Invoice"},
            'cbc:SignatureMethod': {'_text': "urn:oasis:names:specification:ubl:dsig:enveloped:xades"},
        } if invoice.l10n_sa_invoice_type == 'simplified' else None

    def _ubl_add_delivery_nodes(self, vals):
        invoice = vals['invoice']
        vals['document_node']['cac:Delivery'] = [{
            'cbc:ActualDeliveryDate': {'_text': invoice.delivery_date or self._get_zatca_issue_date(vals)},
            'cbc:LatestDeliveryDate': {'_text': invoice.l10n_sa_edi_supply_end_date},
        }]

    def _ubl_add_payment_means_nodes(self, vals):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        invoice = vals['invoice']
        partner_bank = invoice.partner_bank_id
        vals['document_node']['cac:PaymentMeans'] = [{
            'cbc:PaymentMeansCode': {
                '_text': PAYMENT_MEANS_CODE.get(
                    invoice._l10n_sa_get_payment_means_code(),
                    PAYMENT_MEANS_CODE['unknown'],
                ),
                'listID': 'UN/ECE 4461',
            },
            'cbc:PaymentDueDate': {'_text': invoice.invoice_date_due or invoice.invoice_date},
            'cbc:InstructionID': {'_text': invoice.payment_reference},
            'cbc:InstructionNote': {'_text': invoice._l10n_sa_get_adjustment_reason()},
            'cbc:PaymentID': {'_text': invoice.payment_reference or invoice.name},
            'cac:PayeeFinancialAccount': (
                self._ubl_get_payment_means_payee_financial_account_node_from_partner_bank(vals, partner_bank)
                if partner_bank else None
            ),
        }]

    def _ubl_add_payment_terms_nodes(self, vals):
        vals['document_node']['cac:PaymentTerms'] = []

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document amount nodes
    # -------------------------------------------------------------------------

    def _get_zatca_payable_rounding_amount(self, vals):
        return sum(
            base_line['tax_details']['total_excluded_currency']
            for base_line in vals['base_lines']
            if self._ubl_is_cash_rounding_base_line(base_line)
        )

    def _get_zatca_prepaid_amount(self, vals):
        AccountTax = self.env['account.tax']
        currency = vals['currency']

        prepaid_amount = 0.0
        for prepayment_move_base_lines in vals['prepayment_moves_base_lines'].values():
            # Compute prepayment moves' totals, ignoring the withholding taxes
            base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(
                prepayment_move_base_lines,
                lambda base_line, tax_data: bool(self._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)),
            )
            values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
            for grouping_key, values in values_per_grouping_key.items():
                if grouping_key:
                    prepaid_amount += values['base_amount_currency'] + values['tax_amount_currency']
        return prepaid_amount

    def _ubl_add_legal_monetary_total_allowance_charge_total_amount_node(self, vals, in_foreign_currency=True):
        super()._ubl_add_legal_monetary_total_allowance_charge_total_amount_node(vals, in_foreign_currency=in_foreign_currency)

        # AllowanceTotalAmount is always present even if 0.0
        node = vals['legal_monetary_total_node']
        if not node['cbc:AllowanceTotalAmount']:
            currency = vals['currency'] if in_foreign_currency else vals['company_currency']
            node['cbc:AllowanceTotalAmount'] = {
                '_text': FloatFmt(0.0, min_dp=currency.decimal_places),
                'currencyID': currency.name,
            }

    def _ubl_add_legal_monetary_total_payable_rounding_amount_node(self, vals):
        currency = vals['currency']
        payable_rounding_amount = self._get_zatca_payable_rounding_amount(vals)
        vals['legal_monetary_total_node']['cbc:PayableRoundingAmount'] = {
            '_text': FloatFmt(payable_rounding_amount, min_dp=currency.decimal_places, max_dp=currency.decimal_places),
            'currencyID': currency.name,
        } if payable_rounding_amount else None

    def _ubl_add_legal_monetary_total_prepaid_payable_amount_node(self, vals, in_foreign_currency=True):
        currency = vals['currency']
        node = vals['legal_monetary_total_node']
        prepaid_amount = self._get_zatca_prepaid_amount(vals)
        payable_rounding_amount = self._get_zatca_payable_rounding_amount(vals)
        payable_amount = node['cbc:TaxInclusiveAmount']['_text'] - prepaid_amount + payable_rounding_amount
        node['cbc:PrepaidAmount'] = {
            '_text': FloatFmt(prepaid_amount, min_dp=currency.decimal_places, max_dp=currency.decimal_places),
            'currencyID': currency.name,
        }
        node['cbc:PayableAmount'] = {
            '_text': FloatFmt(payable_amount, min_dp=currency.decimal_places, max_dp=currency.decimal_places),
            'currencyID': currency.name,
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document line nodes
    # -------------------------------------------------------------------------

    def _line_nodes_filter_base_lines(self, vals, filter_function=None):
        # Discounts are reported as allowances/charges, and cash rounding lines in PayableRoundingAmount.
        def new_filter_function(base_line):
            if self._is_document_allowance_charge(base_line) or self._ubl_is_cash_rounding_base_line(base_line):
                return False
            return not filter_function or filter_function(base_line)

        return super()._line_nodes_filter_base_lines(vals, filter_function=new_filter_function)

    def _ubl_add_invoice_line_nodes(self, vals, filter_function=None):
        # First: the non-prepayment lines from the invoice
        super()._ubl_add_invoice_line_nodes(vals, filter_function=filter_function)

        # Then: all the prepayment adjustments
        nodes = vals['document_node']['cac:InvoiceLine']
        for prepayment_move, prepayment_move_base_lines in vals['prepayment_moves_base_lines'].items():
            nodes.append(self._get_prepayment_line_node({
                **vals,
                'line_idx': len(nodes) + 1,
                'prepayment_move': prepayment_move,
                'prepayment_move_base_lines': prepayment_move_base_lines,
            }))

    def _get_prepayment_line_node(self, vals):
        prepayment_move = vals['prepayment_move']
        currency = vals['currency']

        AccountTax = self.env['account.tax']
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(
            vals['prepayment_move_base_lines'],
            lambda base_line, tax_data: self._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency),
        )
        aggregated_tax_details = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)

        prepayment_move_issue_date = fields.Datetime.context_timestamp(
            self.with_context(tz='Asia/Riyadh'),
            prepayment_move.l10n_sa_confirmation_datetime,
        )

        return {
            'cbc:ID': {'_text': vals['line_idx']},
            'cbc:InvoicedQuantity': {
                '_text': '1.0',
                'unitCode': 'C62',
            },
            # The prepayment is not part of the monetary totals, except for the PrepaidAmount.
            'cbc:LineExtensionAmount': {
                '_text': FloatFmt(0.0, min_dp=2),
                'currencyID': currency.name,
            },
            'cac:DocumentReference': {
                'cbc:ID': {'_text': prepayment_move.name},
                'cbc:IssueDate': {
                    '_text': prepayment_move_issue_date.strftime('%Y-%m-%d') if prepayment_move_issue_date else None,
                },
                'cbc:IssueTime': {
                    '_text': prepayment_move_issue_date.strftime('%H:%M:%S') if prepayment_move_issue_date else None,
                },
                'cbc:DocumentTypeCode': {'_text': '386'},
            },
            'cac:TaxTotal': self._get_prepayment_line_tax_total_node({**vals, 'aggregated_tax_details': aggregated_tax_details}),
            'cac:Item': {
                'cbc:Description': {'_text': "Down Payment"},
                'cbc:Name': {'_text': "Down Payment"},
                'cac:ClassifiedTaxCategory': [
                    self._ubl_get_tax_category_node(vals, grouping_key)
                    for grouping_key in aggregated_tax_details
                    if grouping_key
                ],
            },
            'cac:Price': {
                'cbc:PriceAmount': {
                    '_text': '0',
                    'currencyID': currency.name,
                },
            },
        }

    def _get_prepayment_line_tax_total_node(self, vals):
        # Compute prepayment move subtotals by tax category
        aggregated_tax_details = vals['aggregated_tax_details']
        currency = vals['currency']

        return {
            'cbc:TaxAmount': {
                '_text': '0.00',
                'currencyID': currency.name,
            },
            'cbc:RoundingAmount': {
                '_text': '0.00',
                'currencyID': currency.name,
            },
            'cac:TaxSubtotal': [
                {
                    'cbc:TaxableAmount': {
                        '_text': FloatFmt(values['base_amount_currency'], min_dp=currency.decimal_places, max_dp=currency.decimal_places),
                        'currencyID': currency.name,
                    },
                    'cbc:TaxAmount': {
                        '_text': FloatFmt(values['tax_amount_currency'], min_dp=currency.decimal_places, max_dp=currency.decimal_places),
                        'currencyID': currency.name,
                    },
                    'cbc:Percent': {'_text': grouping_key['percent']},
                    'cac:TaxCategory': self._ubl_get_tax_category_node(vals, grouping_key),
                }
                for grouping_key, values in aggregated_tax_details.items()
                if grouping_key
            ],
        }

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_document_node_constraints(self, vals):
        constraints = super()._export_document_node_constraints(vals)
        invoice = vals['invoice']
        constraints.update(self._flatten_multilevel_constraints(self._invoice_constraints_common(invoice)))
        constraints.update({
            'ubl20_supplier_name_required': self._check_required_fields(vals['supplier'], 'name'),
            'ubl20_customer_name_required': self._check_required_fields(vals['customer'].commercial_partner_id, 'name'),
            'ubl20_invoice_name_required': self._check_required_fields(invoice, 'name'),
            'ubl20_invoice_date_required': self._check_required_fields(invoice, 'invoice_date'),
        })
        return constraints
