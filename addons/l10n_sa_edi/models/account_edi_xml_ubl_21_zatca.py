# -*- coding: utf-8 -*-
from hashlib import sha256
from base64 import b64encode
from lxml import etree
from odoo import models, fields
from odoo.tools.misc import file_path
import re

TAX_EXEMPTION_CODES = ['VATEX-SA-29', 'VATEX-SA-29-7', 'VATEX-SA-30']
TAX_ZERO_RATE_CODES = ['VATEX-SA-32', 'VATEX-SA-33', 'VATEX-SA-34-1', 'VATEX-SA-34-2', 'VATEX-SA-34-3', 'VATEX-SA-34-4',
                       'VATEX-SA-34-5', 'VATEX-SA-35', 'VATEX-SA-36', 'VATEX-SA-EDU', 'VATEX-SA-HEA']

PAYMENT_MEANS_CODE = {
    'bank': 42,
    'card': 48,
    'cash': 10,
    'transfer': 30,
    'unknown': 1
}


class AccountEdiXmlUbl_21Zatca(models.AbstractModel):
    _name = 'account.edi.xml.ubl_21.zatca'
    _inherit = ['account.edi.xml.ubl_21']
    _description = "UBL 2.1 (ZATCA)"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        """
            Generate the name of the invoice XML file according to ZATCA business rules:
            Seller Vat Number (BT-31), Date (BT-2), Time (KSA-25), Invoice Number (BT-1)
        """
        vat = invoice.company_id.partner_id.commercial_partner_id.vat
        invoice_number = re.sub(r'[^a-zA-Z0-9 -]+', '-', invoice.name)
        invoice_date = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), invoice.l10n_sa_confirmation_datetime)
        file_name = f"{vat}_{invoice_date.strftime('%Y%m%dT%H%M%S')}_{invoice_number}"
        file_format = self.env.context.get('l10n_sa_file_format', 'xml')
        if file_format:
            file_name = f'{file_name}.{file_format}'
        return file_name

    def _add_invoice_config_vals(self, vals):
        super()._add_invoice_config_vals(vals)
        vals['document_type'] = 'invoice'  # Only use Invoice in ZATCA, even for credit and debit notes

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

    def _add_document_tax_grouping_function_vals(self, vals):
        # OVERRIDE account.edi.xml.ubl_21

        # Always ignore withholding taxes in the UBL
        def total_grouping_function(base_line, tax_data):
            if tax_data and tax_data['tax'].l10n_sa_is_retention:
                return None
            return True

        def tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']

            # Ignore withholding taxes
            if tax and tax.l10n_sa_is_retention:
                return None
            return {
                'tax_category_code': self._get_tax_category_code(vals['customer'].commercial_partner_id, vals['supplier'], tax),
                **self._get_tax_exemption_reason(vals['customer'].commercial_partner_id, vals['supplier'], tax),
                'amount': tax.amount if tax else 0.0,
                'amount_type': tax.amount_type if tax else 'percent',
            }

        vals['total_grouping_function'] = total_grouping_function
        vals['tax_grouping_function'] = tax_grouping_function

    # -------------------------------------------------------------------------
    # EXPORT: Helpers
    # -------------------------------------------------------------------------

    def _get_tax_category_code(self, customer, supplier, tax):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        if supplier.country_id.code == 'SA':
            if tax and tax.amount != 0:
                return 'S'
            elif tax and tax.l10n_sa_exemption_reason_code in TAX_EXEMPTION_CODES:
                return 'E'
            elif tax and tax.l10n_sa_exemption_reason_code in TAX_ZERO_RATE_CODES:
                return 'Z'
            else:
                return 'O'
        return super()._get_tax_category_code(customer, supplier, tax)

    def _get_tax_exemption_reason(self, customer, supplier, tax):
        if supplier.country_id.code == 'SA':
            if tax and tax.amount == 0:
                exemption_reason_by_code = dict(tax._fields["l10n_sa_exemption_reason_code"]._description_selection(self.env))
                code = tax.l10n_sa_exemption_reason_code
                return {
                    'tax_exemption_reason_code': code or "VATEX-SA-OOS",
                    'tax_exemption_reason': (
                        exemption_reason_by_code[code].split(code)[1].lstrip()
                        if code else "Not subject to VAT"
                    )
                }
            else:
                return {
                    'tax_exemption_reason_code': None,
                    'tax_exemption_reason': None,
                }

        return super()._get_tax_exemption_reason(customer, supplier, tax)

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
                    '1' if invoice.commercial_partner_id.country_id != invoice.company_id.country_id and not invoice._l10n_sa_is_simplified() else '0'
                ),
            },
            'cbc:TaxCurrencyCode': {'_text': vals['company_currency_id'].name},
            'cac:OrderReference': None,
            'cac:BillingReference': {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {
                        '_text': (invoice.reversed_entry_id.name or invoice.ref)
                        if invoice.move_type == 'out_refund'
                        else invoice.debit_origin_id.name
                    }
                }
            } if invoice.move_type == 'out_refund' or invoice.debit_origin_id else None,
            'cac:AdditionalDocumentReference': [
                {
                    'cbc:ID': {'_text': 'QR'},
                    'cac:Attachment': {
                        'cbc:EmbeddedDocumentBinaryObject': {
                            '_text': 'N/A',
                            'mimeCode': 'text/plain',
                        }
                    }
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
                        }
                    }
                },
                {
                    'cbc:ID': {'_text': 'ICV'},
                    'cbc:UUID': {'_text': invoice.l10n_sa_chain_index},
                }
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
        if 'cac:Delivery' in document_node:
            if document_node['cac:Delivery']['cac:DeliveryLocation']:
                document_node['cac:Delivery']['cac:DeliveryLocation'] = None

            if not document_node['cac:Delivery']['cbc:ActualDeliveryDate']['_text']:
                document_node['cac:Delivery']['cbc:ActualDeliveryDate'] = {'_text': invoice.invoice_date}

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        super()._add_invoice_payment_means_nodes(document_node, vals)
        payment_means_node = document_node['cac:PaymentMeans']
        invoice = vals['invoice']

        payment_means_node['cbc:PaymentMeansCode'] = {
            '_text': PAYMENT_MEANS_CODE.get(
                self._l10n_sa_get_payment_means_code(invoice),
                PAYMENT_MEANS_CODE['unknown']
            ),
            'listID': 'UN/ECE 4461',
        }
        payment_means_node['cbc:InstructionNote'] = {'_text': invoice._l10n_sa_get_adjustment_reason()}

    def _get_address_node(self, vals):
        partner = vals['partner']
        country = partner['country' if partner._name == 'res.bank' else 'country_id']
        state = partner['state' if partner._name == 'res.bank' else 'state_id']
        building_number = partner.l10n_sa_edi_building_number if partner._name == 'res.partner' else ''
        edi_plot_identification = partner.l10n_sa_edi_plot_identification if partner._name == 'res.partner' else ''

        return {
            'cbc:StreetName': {'_text': partner.street},
            'cbc:BuildingNumber': {'_text': building_number},
            'cbc:PlotIdentification': {'_text': edi_plot_identification},
            'cbc:CitySubdivisionName': {'_text': partner.street2},
            'cbc:CityName': {'_text': partner.city},
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentity': {'_text': state.name},
            'cbc:CountrySubentityCode': {'_text': state.code},
            'cac:AddressLine': None,
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': country.code},
                'cbc:Name': {'_text': country.name},
            }
        }

    def _get_partner_party_identification_number(self, partner):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        identification_number = partner.l10n_sa_edi_additional_identification_number
        vat = re.sub(r'[^a-zA-Z0-9]', '', partner.vat or "")
        if partner.country_code != "SA" and vat:
            identification_number = vat
        elif partner.l10n_sa_edi_additional_identification_scheme == 'TIN':
            # according to ZATCA, the TIN number is always the first 10 digits of the VAT number
            identification_number = vat[:10]
        return identification_number

    def _get_party_node(self, vals):
        partner = vals['partner']
        role = vals['role']
        commercial_partner = partner.commercial_partner_id

        party_node = {}

        if identification_number := self._get_partner_party_identification_number(commercial_partner):
            party_node['cac:PartyIdentification'] = {
                'cbc:ID': {
                    '_text': identification_number,
                    'schemeID': commercial_partner.l10n_sa_edi_additional_identification_scheme,
                }
            }

        party_node.update({
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name}
            },
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
                'cac:RegistrationAddress': self._get_address_node({'partner': commercial_partner}),
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT'}
                }
            } if (role != 'customer' or partner.country_id.code == 'SA') and commercial_partner.vat and commercial_partner.vat != '/' else None,  # BR-KSA-46
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat} if commercial_partner.country_code == 'SA' else None,
                'cac:RegistrationAddress': self._get_address_node({'partner': commercial_partner}),
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {
                    '_text': re.sub(r"[^+\d]", '', partner.phone) if partner.phone else None
                },
                'cbc:ElectronicMail': {'_text': partner.email},
            }
        })
        return party_node

    def _l10n_sa_get_payment_means_code(self, invoice):
        """ Return payment means code to be used to set the value on the XML file """
        return 'unknown'

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document amount nodes
    # -------------------------------------------------------------------------

    def _add_document_tax_total_nodes(self, document_node, vals):
        super()._add_document_tax_total_nodes(document_node, vals)

        document_node['cac:TaxTotal'] = [document_node['cac:TaxTotal']]

        self._add_tax_total_node_in_company_currency(document_node, vals)
        document_node['cac:TaxTotal'][1]['cac:TaxSubtotal'] = None

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
        monetary_total_node['cbc:PrepaidAmount']['_text'] = self.format_float(prepaid_amount, vals['currency_dp'])
        monetary_total_node['cbc:PayableAmount']['_text'] = self.format_float(vals['tax_inclusive_amount_currency'] - prepaid_amount, vals['currency_dp'])

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document allowance charge nodes
    # -------------------------------------------------------------------------

    def _get_document_allowance_charge_node(self, vals):
        """ Charge Reasons & Codes (As per ZATCA):
            https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5189.htm
            As far as ZATCA is concerned, we calculate Allowance/Charge vals for global discounts as
            a document level allowance, and we do not include any other charges or allowances.
        """
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])

        base_amount_currency = base_line['tax_details']['total_excluded_currency']
        if base_line['special_type'] == 'early_payment':
            return super()._get_document_allowance_charge_node(vals)
        elif base_amount_currency < 0:
            return {
                'cbc:ChargeIndicator': {'_text': 'false'},
                'cbc:AllowanceChargeReasonCode': {'_text': '95'},
                'cbc:AllowanceChargeReason': {'_text': 'Discount'},
                'cbc:Amount': {
                    '_text': self.format_float(abs(base_amount_currency), 2),
                    'currencyID': vals['currency_id'].name,
                },
                'cac:TaxCategory': [
                    self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
                    for grouping_key in aggregated_tax_details
                    if grouping_key
                ]
            }

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
                })
            )
            line_idx += 1

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])

        total_tax_amount = sum(
            values['tax_amount_currency']
            for grouping_key, values in aggregated_tax_details.items()
            if grouping_key
        )
        total_base_amount = sum(
            values['base_amount_currency']
            for grouping_key, values in aggregated_tax_details.items()
            if grouping_key
        )
        total_amount = total_base_amount + total_tax_amount

        line_node['cac:TaxTotal'] = {
            'cbc:TaxAmount': {
                '_text': self.format_float(total_tax_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:RoundingAmount': {
                # This should simply contain the net (base + tax) amount for the line.
                '_text': self.format_float(total_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            # No TaxSubtotal: BR-KSA-80: only downpayment lines should have a tax subtotal breakdown.
        }

    def _add_document_line_item_nodes(self, line_node, vals):
        super()._add_document_line_item_nodes(line_node, vals)
        product = vals['base_line']['product_id']
        line_node['cac:Item']['cac:SellersItemIdentification'] = {
            'cbc:ID': {'_text': product.code or product.default_code},
        }

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])

        line_node['cac:Item']['cac:ClassifiedTaxCategory'] = [
            self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
            for grouping_key in aggregated_tax_details
            if grouping_key
        ]

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
            prepayment_move.l10n_sa_confirmation_datetime
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
                    '_text': prepayment_move_issue_date.strftime('%Y-%m-%d') if prepayment_move_issue_date else None
                },
                'cbc:IssueTime': {
                    '_text': prepayment_move_issue_date.strftime('%H:%M:%S') if prepayment_move_issue_date else None
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
                ]
            },
            'cac:Price': {
                'cbc:PriceAmount': {
                    '_text': '0',
                    'currencyID': vals['currency_name'],
                }
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

    def _add_document_line_price_nodes(self, line_node, vals):
        """
        Use 10 decimal places for PriceAmount to satisfy ZATCA validation BR-KSA-EN16931-11
        """
        currency_suffix = vals['currency_suffix']
        line_node['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': round(vals[f'gross_price_unit{currency_suffix}'], 10),
                'currencyID': vals['currency_name'],
            },
        }

    # -------------------------------------------------------------------------
    # EXPORT: Helpers for hash generation
    # -------------------------------------------------------------------------

    def _l10n_sa_get_namespaces(self):
        """
            Namespaces used in the final UBL declaration, required to canonalize the finalized XML document of the Invoice
        """
        return {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
            'sac': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2',
            'sbc': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'xades': 'http://uri.etsi.org/01903/v1.3.2#'
        }

    def _l10n_sa_generate_invoice_xml_sha(self, xml_content):
        """
            Transform, canonicalize then hash the invoice xml content using the SHA256 algorithm,
            then return the hashed content
        """

        def _canonicalize_xml(content):
            """
                Canonicalize XML content using the c14n method. The specs mention using the c14n11 canonicalization,
                which is simply calling etree.tostring and setting the method argument to 'c14n'. There are minor
                differences between c14n11 and c14n canonicalization algorithms, but for the purpose of ZATCA signing,
                c14n is enough
            """
            return etree.tostring(content, method="c14n", exclusive=False, with_comments=False,
                                  inclusive_ns_prefixes=self._l10n_sa_get_namespaces())

        def _transform_and_canonicalize_xml(content):
            """ Transform XML content to remove certain elements and signatures using an XSL template """
            invoice_xsl = etree.parse(file_path('l10n_sa_edi/data/pre-hash_invoice.xsl'))
            transform = etree.XSLT(invoice_xsl)
            return _canonicalize_xml(transform(content))

        root = etree.fromstring(xml_content)
        # Transform & canonicalize the XML content
        transformed_xml = _transform_and_canonicalize_xml(root)
        # Get the SHA256 hashed value of the XML content
        return sha256(transformed_xml)

    def _l10n_sa_generate_invoice_xml_hash(self, xml_content, mode='hexdigest'):
        """
            Generate the b64 encoded sha256 hash of a given xml string:
                - First: Transform the xml content using a pre-hash_invoice.xsl file
                - Second: Canonicalize the transformed xml content using the c14n method
                - Third: hash the canonicalized content using the sha256 algorithm then encode it into b64 format
        """
        xml_sha = self._l10n_sa_generate_invoice_xml_sha(xml_content)
        if mode == 'hexdigest':
            xml_hash = xml_sha.hexdigest().encode()
        elif mode == 'digest':
            xml_hash = xml_sha.digest()
        return b64encode(xml_hash)
