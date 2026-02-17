from odoo import fields, models


class AccountEdiXmlUbl_21Zatca(models.AbstractModel):
    _name = 'account.edi.xml.ubl_21.zatca'
    _inherit = ['zatca.ubl.mixin', 'account.edi.xml.ubl_21']
    _description = 'UBL 2.1 (ZATCA)'

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _add_invoice_base_lines_vals(self, vals):
        super()._add_invoice_base_lines_vals(vals)
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
        else:
            prepayment_moves = self.env['account.move']

        prepayment_moves_base_lines = {}
        for prepayment_move in prepayment_moves:
            prepayment_move_base_lines, _dummy = prepayment_move._get_rounded_base_and_tax_lines()
            prepayment_moves_base_lines[prepayment_move] = prepayment_move_base_lines

        vals['prepayment_moves_base_lines'] = prepayment_moves_base_lines

    # -------------------------------------------------------------------------
    # EXPORT: Helpers
    # -------------------------------------------------------------------------

    def _is_document_allowance_charge(self, base_line):
        return base_line['special_type'] == 'early_payment' or base_line['tax_details']['total_excluded_currency'] < 0

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document header nodes
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']
        issue_date = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), invoice.l10n_sa_confirmation_datetime)

        document_node.update({
            'cbc:ProfileID': {'_text': 'reporting:1.0'},
            'cbc:UUID': {'_text': invoice.l10n_sa_uuid},
            'cbc:IssueDate': {'_text': issue_date.strftime('%Y-%m-%d')},
            'cbc:IssueTime': {'_text': issue_date.strftime('%H:%M:%S')},
            'cbc:DueDate': None,
            'cbc:InvoiceTypeCode': {
                '_text': (
                    383 if invoice.debit_origin_id else
                    381 if invoice.move_type == 'out_refund' else
                    386 if invoice._is_downpayment() else 388
                ),
                'name': '0%s00%s00' % (
                    '2' if invoice._l10n_sa_is_simplified() else '1',
                    '1' if invoice.commercial_partner_id.country_id != invoice.company_id.country_id and not invoice._l10n_sa_is_simplified() else '0',
                ),
            },
            'cbc:TaxCurrencyCode': {'_text': vals['company_currency_id'].name},
            'cac:OrderReference': None,
            'cac:BillingReference': {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {
                        '_text': (invoice.reversed_entry_id.name or invoice.ref)
                        if invoice.move_type == 'out_refund'
                        else invoice.debit_origin_id.name,
                    },
                },
            } if invoice.move_type == 'out_refund' or invoice.debit_origin_id else None,
            'cac:AdditionalDocumentReference': [
                {
                    'cbc:ID': {'_text': 'QR'},
                    'cac:Attachment': {
                        'cbc:EmbeddedDocumentBinaryObject': {
                            '_text': 'N/A',
                            'mimeCode': 'text/plain',
                        },
                    },
                } if invoice._l10n_sa_is_simplified() else None,
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
            ],
            'cac:Signature': {
                'cbc:ID': {'_text': "urn:oasis:names:specification:ubl:signature:Invoice"},
                'cbc:SignatureMethod': {'_text': "urn:oasis:names:specification:ubl:dsig:enveloped:xades"},
            } if invoice._l10n_sa_is_simplified() else None,
            'cac:PaymentTerms': None,
        })

    def _add_invoice_delivery_nodes(self, document_node, vals):
        super()._add_invoice_delivery_nodes(document_node, vals)
        invoice = vals['invoice']
        self._set_delivery_nodes(document_node, invoice)

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document amount nodes
    # -------------------------------------------------------------------------

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        super()._add_invoice_monetary_total_nodes(document_node, vals)

        monetary_total_tag = 'cac:LegalMonetaryTotal' if vals['document_type'] in {'invoice', 'credit_note'} else 'cac:RequestedMonetaryTotal'
        monetary_total_node = document_node[monetary_total_tag]

        # Compute the prepaid amount
        prepaid_amount = 0.0
        AccountTax = self.env['account.tax']
        for prepayment_move_base_lines in vals['prepayment_moves_base_lines'].values():
            # Compute prepayment moves' totals
            prepayment_moves_base_lines_aggregated_tax_details = AccountTax._aggregate_base_lines_tax_details(
                prepayment_move_base_lines,
                vals['total_grouping_function'],
            )
            prepayment_moves_total_aggregated_tax_details = AccountTax._aggregate_base_lines_aggregated_values(prepayment_moves_base_lines_aggregated_tax_details)
            for grouping_key, values in prepayment_moves_total_aggregated_tax_details.items():
                if grouping_key:
                    prepaid_amount += values['base_amount_currency'] + values['tax_amount_currency']

        # AllowanceTotalAmount is always present even if 0.0
        monetary_total_node['cbc:AllowanceTotalAmount'] = {
            '_text': self.format_float(vals['total_allowance_currency'], vals['currency_dp']),
            'currencyID': vals['currency_name'],
        }

        # Retrieve the rounding amount
        payable_rounding_amount = vals['cash_rounding_base_amount_currency']

        payable_amount = vals['tax_inclusive_amount_currency'] - prepaid_amount + payable_rounding_amount
        monetary_total_node['cbc:PrepaidAmount']['_text'] = self.format_float(prepaid_amount, vals['currency_dp'])
        monetary_total_node['cbc:PayableAmount']['_text'] = self.format_float(payable_amount, vals['currency_dp'])

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document line nodes
    # -------------------------------------------------------------------------

    def _add_invoice_line_nodes(self, document_node, vals):
        document_line_tag = self._get_tags_for_document_type(vals)['document_line']
        document_node[document_line_tag] = []
        line_idx = 1

        # First: the non-prepayment lines from the invoice
        for base_line in vals['base_lines']:
            if not self._is_document_allowance_charge(base_line):
                line_vals = {
                    **vals,
                    'line_idx': line_idx,
                    'base_line': base_line,
                }
                self._add_invoice_line_vals(line_vals)

                line_node = {}
                self._add_invoice_line_id_nodes(line_node, line_vals)
                self._add_invoice_line_amount_nodes(line_node, line_vals)
                self._add_invoice_line_period_nodes(line_node, line_vals)
                self._add_invoice_line_allowance_charge_nodes(line_node, line_vals)
                self._add_invoice_line_tax_total_nodes(line_node, line_vals)
                self._add_invoice_line_item_nodes(line_node, line_vals)
                self._add_invoice_line_tax_category_nodes(line_node, line_vals)
                self._add_invoice_line_price_nodes(line_node, line_vals)
                self._add_invoice_line_pricing_reference_nodes(line_node, line_vals)

                document_node[document_line_tag].append(line_node)
                line_idx += 1

        # Then: all the prepayment adjustments
        for prepayment_move, prepayment_move_base_lines in vals['prepayment_moves_base_lines'].items():
            document_node[document_line_tag].append(
                self._get_prepayment_line_node({
                    **vals,
                    'line_idx': line_idx,
                    'prepayment_move': prepayment_move,
                    'prepayment_move_base_lines': prepayment_move_base_lines,
                }),
            )
            line_idx += 1

    def _get_prepayment_line_node(self, vals):
        prepayment_move = vals['prepayment_move']

        AccountTax = self.env['account.tax']
        prepayment_moves_base_lines_aggregated_tax_details = AccountTax._aggregate_base_lines_tax_details(
            vals['prepayment_move_base_lines'],
            vals['tax_grouping_function'],
        )
        aggregated_tax_details = AccountTax._aggregate_base_lines_aggregated_values(prepayment_moves_base_lines_aggregated_tax_details)

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
            'cbc:LineExtensionAmount': {
                '_text': '0.00',
                'currencyID': vals['currency_name'],
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
                    self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
                    for grouping_key in aggregated_tax_details
                ],
            },
            'cac:Price': {
                'cbc:PriceAmount': {
                    '_text': '0',
                    'currencyID': vals['currency_name'],
                },
            },
        }

    def _get_prepayment_line_tax_total_node(self, vals):
        # Compute prepayment move subtotals by tax category
        aggregated_tax_details = vals['aggregated_tax_details']

        return {
            'cbc:TaxAmount': {
                '_text': '0.00',
                'currencyID': vals['currency_name'],
            },
            'cbc:RoundingAmount': {
                '_text': '0.00',
                'currencyID': vals['currency_name'],
            },
            'cac:TaxSubtotal': [
                {
                    'cbc:TaxableAmount': {
                        '_text': self.format_float(values['base_amount_currency'], vals['currency_dp']),
                        'currencyID': vals['currency_name'],
                    },
                    'cbc:TaxAmount': {
                        '_text': self.format_float(values['tax_amount_currency'], vals['currency_dp']),
                        'currencyID': vals['currency_name'],
                    },
                    'cbc:Percent': {'_text': grouping_key['amount']},
                    'cac:TaxCategory': self._get_tax_category_node({**vals, 'grouping_key': grouping_key}),
                }
                for grouping_key, values in aggregated_tax_details.items()
                if grouping_key
            ],
        }
