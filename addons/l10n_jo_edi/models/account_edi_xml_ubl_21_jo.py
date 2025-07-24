import functools
import re
from types import SimpleNamespace

from odoo import models
from odoo.tools import float_round, float_is_zero
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import FloatFmt

JO_MAX_DP = 9


class HashableNamespace(SimpleNamespace):
    """ We need to use a hashable namespace to be able to use it as a key in a dictionary.
    This is because the `SimpleNamespace` class is not hashable by default.
    """
    def __hash__(self):
        return hash(self.name)


class AccountEdiXmlUBL21JO(models.AbstractModel):
    _name = 'account.edi.xml.ubl_21.jo'
    _inherit = 'account.edi.xml.ubl_21'
    _description = 'UBL 2.1 (JoFotara)'

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _add_invoice_config_vals(self, vals):
        super()._add_invoice_config_vals(vals)
        vals['document_type'] = 'invoice'  # Only use Invoice in JO, even for credit and debit notes
        vals['fixed_taxes_as_allowance_charges'] = False  # In JO, fixed taxes should be reported as taxes, not as AllowanceCharges

        # We cannot use a new `res.currency` record to round to 9 decimals, because the
        # `res.currency.rounding` field definition prevents rounding to more than 6 decimal places.
        vals['currency_id'] = HashableNamespace(
            name='JO',  # Every amount will be reported with currencyID="JO"
            round=functools.partial(float_round, precision_digits=JO_MAX_DP),
            is_zero=functools.partial(float_is_zero, precision_digits=JO_MAX_DP),
            rounding=10**-JO_MAX_DP,
            decimal_places=JO_MAX_DP,
        )

    def _add_invoice_base_lines_vals(self, vals):
        # OVERRIDE account_edi_xml_ubl_20.py
        currency_9_dp = vals['currency_id']
        invoice = vals['invoice']

        # Compute values for invoice lines. In Jordan, because the web-service has absolutely no tolerance,
        # what we do is: use round per line with 9 decimals (yes!)
        base_amls = invoice.line_ids.filtered(lambda line: line.display_type == 'product')
        base_lines = [invoice._prepare_product_base_line_for_taxes_computation(line) for line in base_amls]
        epd_amls = invoice.line_ids.filtered(lambda line: line.display_type == 'epd')
        base_lines += [invoice._prepare_epd_base_line_for_taxes_computation(line) for line in epd_amls]
        cash_rounding_amls = invoice.line_ids.filtered(lambda line: line.display_type == 'rounding' and not line.tax_repartition_line_id)
        base_lines += [invoice._prepare_cash_rounding_base_line_for_taxes_computation(line) for line in cash_rounding_amls]

        AccountTax = self.env['account.tax']
        for base_line in base_lines:
            base_line['currency_id'] = currency_9_dp
            AccountTax._add_tax_details_in_base_line(base_line, base_line['record'].company_id, 'round_per_line')

        # Round to 9 decimals
        AccountTax._round_base_lines_tax_details(base_lines, company=invoice.company_id)

        # raw_total_* values need to calculated with `round_globally` because these values should not be rounded per line
        # However, taxes need to be calculated with `round_per_line` so that _round_base_lines_tax_details does not
        # end up generating lines taxes using unrounded base amounts
        new_base_lines = [base_line.copy() for base_line in base_lines]
        for base_line, new_base_line in zip(base_lines, new_base_lines):
            AccountTax._add_tax_details_in_base_line(new_base_line, new_base_line['record'].company_id, 'round_globally')
            for key in [
                'raw_total_excluded_currency',
                'raw_total_excluded',
                'raw_total_included_currency',
                'raw_total_included',
            ]:
                base_line['tax_details'][key] = new_base_line['tax_details'][key]

        vals['base_lines'] = base_lines

    # -------------------------------------------------------------------------
    # EXPORT: Helpers
    # -------------------------------------------------------------------------

    def format_float(self, amount, precision_digits=3):
        # Force all floats to be formatted with at least 3 decimals and at most 9 decimals
        return FloatFmt(amount, 3, max_dp=JO_MAX_DP)

    def _get_tax_category_code(self, customer, supplier, tax):
        if tax and tax._l10n_jo_is_exempt_tax():
            return "Z"
        if tax and tax.amount:
            return "S"
        return "O"

    def _sanitize_phone(self, raw):
        return re.sub(r'[^0-9]', '', raw or '')[:15]

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document header nodes
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        invoice = vals['invoice']

        document_node.update({
            'cbc:UBLVersionID': None,
            'cbc:ProfileID': {'_text': 'reporting:1.0'},
            'cbc:ID': {'_text': invoice.name.replace('/', '_')},
            'cbc:UUID': {'_text': invoice.l10n_jo_edi_uuid},
            'cbc:DueDate': None,
            'cbc:InvoiceTypeCode': {
                '_text': "381" if invoice.move_type == 'out_refund' else "388",
                'name': invoice._get_invoice_scope_code() + invoice._get_invoice_payment_method_code() + invoice._get_invoice_tax_payer_type_code(),
            },
            'cbc:DocumentCurrencyCode': {'_text': invoice.currency_id.name},
            'cbc:TaxCurrencyCode': {'_text': invoice.currency_id.name},
            'cbc:BuyerReference': None,
            'cac:OrderReference': None,
        })

        if invoice.reversed_entry_id:
            document_node['cac:BillingReference'] = {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': (invoice.reversed_entry_id.name or '').replace('/', '_')},
                    'cbc:UUID': {'_text': invoice.reversed_entry_id.l10n_jo_edi_uuid},
                    'cbc:DocumentDescription': {
                        '_text': self.format_float(
                            abs(invoice.reversed_entry_id.amount_total),
                            vals['currency_dp'],
                        )
                    },
                }
            }

        document_node['cac:AdditionalDocumentReference'] = {
            'cbc:ID': {'_text': 'ICV'},
            'cbc:UUID': {'_text': invoice.id},
        }

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        super()._add_invoice_accounting_customer_party_nodes(document_node, vals)
        # Override AccountingCustomerParty for refunds
        invoice = vals['invoice']
        if invoice.move_type == 'out_refund':
            document_node['cac:AccountingCustomerParty'] = {
                'cac:Party': {
                    'cac:PostalAddress': {
                        'cac:Country': {
                            'cbc:IdentificationCode': {'_text': 'JO'}
                        }
                    },
                    'cac:PartyTaxScheme': {
                        'cac:TaxScheme': {
                            'cbc:ID': {'_text': 'VAT'}
                        }
                    }
                },
                'cac:AccountingContact': {
                    'cbc:Telephone': {
                        '_text': ''
                    }
                }
            }
        else:
            # For non-refund invoices, use the standard party node
            document_node['cac:AccountingCustomerParty']['cac:AccountingContact'] = {
                'cbc:Telephone': {
                    '_text': self._sanitize_phone(invoice.partner_id.phone)
                }
            }

    def _add_invoice_seller_supplier_party_nodes(self, document_node, vals):
        # Add SellerSupplierParty
        invoice = vals['invoice']
        document_node['cac:SellerSupplierParty'] = {
            'cac:Party': {
                'cac:PartyIdentification': {
                    'cbc:ID': {
                        '_text': invoice.company_id.l10n_jo_edi_sequence_income_source
                    }
                }
            }
        }

    def _add_invoice_delivery_nodes(self, document_node, vals):
        pass

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        invoice = vals['invoice']
        if invoice.move_type == 'out_refund':
            document_node['cac:PaymentMeans'] = {
                'cbc:PaymentMeansCode': {
                    '_text': 10,
                    'listID': "UN/ECE 4461",
                },
                'cbc:InstructionNote': {
                    '_text': (invoice.ref or '').replace('/', '_')
                },
            }

    def _get_party_node(self, vals):
        partner = vals['partner']
        role = vals['role']

        party_node = {
            'cac:PartyIdentification': {
                'cbc:ID': {
                    '_text': partner.vat if partner.vat and partner.vat != '/' else '',
                    'schemeID': 'TN' if partner.country_code == 'JO' else 'PN',
                }
            } if role != 'supplier' else None,
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cbc:CompanyID': {'_text': partner.vat},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT'}
                }
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': partner.name}
            },
        }
        return party_node

    def _get_address_node(self, vals):
        partner = vals['partner']

        return {
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentityCode': {'_text': partner.state_id.code},
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': partner.country_id.code}
            }
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document amount nodes
    # -------------------------------------------------------------------------

    def _add_document_tax_total_nodes(self, document_node, vals):
        # Tax unregistered companies should have no tax values
        if vals['invoice'].company_id.l10n_jo_edi_taxpayer_type == 'income':
            return

        # In the document-level tax total, we only report general (not special) taxes
        def tax_grouping_function(base_line, tax_data):
            if tax_data and tax_data['tax'].amount_type == 'fixed':
                return None
            return vals['tax_grouping_function'](base_line, tax_data)

        super()._add_document_tax_total_nodes(document_node, {**vals, 'tax_grouping_function': tax_grouping_function})

        # Only credit notes should have tax subtotals
        if not vals['invoice']._is_sales_refund():
            document_node['cac:TaxTotal']['cac:TaxSubtotal'] = None

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        # OVERRIDE account_edi_xml_ubl_20.py
        invoice = vals['invoice']
        allowance_total_amount = 0.0
        tax_exclusive_amount = 0.0
        for base_line in vals['base_lines']:
            # Compute the gross subtotal and discount for the line
            vals['base_line'] = base_line
            self._add_document_line_gross_subtotal_and_discount_vals(vals)

            # The document-level AllowanceTotalAmount is an aggregation of the lines' discounts.
            allowance_total_amount += vals['discount_amount_currency']

            # The tax exclusive amount is the sum of the lines' gross amounts (before discount)
            tax_exclusive_amount += vals['gross_subtotal_currency']

        tax_inclusive_amount = tax_exclusive_amount - allowance_total_amount

        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], vals['total_grouping_function'])
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        for grouping_key, tax_details in aggregated_tax_details.items():
            if grouping_key:
                tax_inclusive_amount += tax_details['tax_amount_currency']

        monetary_total_tag = 'cac:LegalMonetaryTotal' if vals['document_type'] in {'invoice', 'credit_note'} else 'cac:RequestedMonetaryTotal'
        document_node[monetary_total_tag] = {
            'cbc:TaxExclusiveAmount': {
                '_text': self.format_float(tax_exclusive_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:TaxInclusiveAmount': {
                '_text': self.format_float(tax_inclusive_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:AllowanceTotalAmount': {
                '_text': self.format_float(allowance_total_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if allowance_total_amount else None,
            'cbc:PrepaidAmount': {
                '_text': self.format_float(0.0, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if invoice._is_sales_refund() else None,
            'cbc:PayableAmount': {
                '_text': self.format_float(tax_inclusive_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document allowance charge nodes
    # -------------------------------------------------------------------------

    def _add_document_allowance_charge_nodes(self, document_node, vals):
        # In JoFotara, there is only one document-level AllowanceCharge, which is a *recap* of the line discounts.
        document_node['cac:AllowanceCharge'] = self._get_document_allowance_charge_node(vals)

    def _get_document_allowance_charge_node(self, vals):
        """ For JO UBL the document allowance charge needs to be the sum of the line discounts. """
        base_lines = vals['base_lines']
        discount_amount = 0.0
        for base_line in base_lines:
            vals['base_line'] = base_line
            self._add_document_line_gross_subtotal_and_discount_vals(vals)
            discount_amount += vals['discount_amount_currency']

        return {
            'cbc:ChargeIndicator': {'_text': 'false'},
            'cbc:AllowanceChargeReason': {'_text': 'discount'},
            'cbc:Amount': {
                '_text': self.format_float(discount_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }

    def _get_tax_subtotal_node(self, vals):
        tax_subtotal_node = super()._get_tax_subtotal_node(vals)
        tax_subtotal_node['cbc:Percent'] = None
        return tax_subtotal_node

    def _get_tax_category_node(self, vals):
        grouping_key = vals['grouping_key']
        return {
            'cbc:ID': {
                '_text': grouping_key['tax_category_code'],
                'schemeID': 'UN/ECE 5305',
                'schemeAgencyID': '6',
            },
            'cbc:Percent': {'_text': grouping_key['amount']} if grouping_key['amount_type'] == 'percent' else None,
            'cac:TaxScheme': {
                'cbc:ID': {
                    '_text': 'VAT' if grouping_key['amount_type'] == 'percent' else 'OTH',
                    'schemeID': 'UN/ECE 5153',
                    'schemeAgencyID': '6',
                }
            }
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document line nodes
    # -------------------------------------------------------------------------

    def _add_invoice_line_id_nodes(self, line_node, vals):
        line = vals['base_line']['record']
        line_node['cbc:ID'] = {
            '_text': self._get_line_edi_id(line, vals['line_idx']),
        }

    def _get_line_edi_id(self, line, default_id):
        if not line.is_refund:  # in case it's invoice not credit note
            return default_id

        refund_move = line.move_id
        invoice_move = refund_move.reversed_entry_id
        invoice_lines = invoice_move.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_subsection', 'line_note'))
        n = len(invoice_lines)

        line_id = -1
        for invoice_line_id, invoice_line in enumerate(invoice_lines, 1):
            if line.product_id == invoice_line.product_id \
                    and line.name == invoice_line.name \
                    and line.price_unit == invoice_line.price_unit \
                    and line.discount == invoice_line.discount:
                line_id = invoice_line_id
                break
        if line_id == -1:
            line_id = n + default_id

        return line_id

    def _add_document_line_gross_subtotal_and_discount_vals(self, vals):
        """ In JO, because of the precision requirements, we first compute an exact
        gross unit price, rounded to 9 decimals, and then use it to compute the discount amounts.
        """
        base_line = vals['base_line']
        currency_9_dp = vals['currency_id']

        # OVERRIDE account_edi_xml_ubl_20.py
        discount_factor = 1 - (base_line['discount'] / 100.0)
        if discount_factor != 0.0:
            gross_subtotal_currency = base_line['tax_details']['raw_total_excluded_currency'] / discount_factor
        else:
            gross_subtotal_currency = base_line['currency_id'].round(base_line['price_unit'] * base_line['quantity'])

        # Start by getting a gross unit price rounded to 9 decimals
        vals['gross_price_unit_currency'] = currency_9_dp.round(gross_subtotal_currency / base_line['quantity']) if base_line['quantity'] else 0.0

        # Then compute the gross subtotal from the rounded unit price
        vals['gross_subtotal_currency'] = currency_9_dp.round(vals['gross_price_unit_currency'] * base_line['quantity'])

        # Then compute the discount from the gross subtotal
        vals['discount_amount_currency'] = vals['gross_subtotal_currency'] - base_line['tax_details']['total_excluded_currency']

    def _add_invoice_line_amount_nodes(self, line_node, vals):
        super()._add_invoice_line_amount_nodes(line_node, vals)
        quantity_tag = self._get_tags_for_document_type(vals)['line_quantity']
        line_node[quantity_tag]['unitCode'] = 'PCE'

    def _add_invoice_line_allowance_charge_nodes(self, line_node, vals):
        # The line-level AllowanceCharge should be added to the Price node
        pass

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        base_line = vals['base_line']

        # Tax unregistered companies should have no tax values
        if base_line['record'].move_id.company_id.l10n_jo_edi_taxpayer_type == 'income':
            return

        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])

        total_tax_amount_percent = sum(
            values['tax_amount_currency']
            for grouping_key, values in aggregated_tax_details.items()
            if grouping_key and grouping_key['amount_type'] == 'percent'
        )

        line_node['cac:TaxTotal'] = {
            # This contains the total amount of general (percent) taxes
            'cbc:TaxAmount': {
                '_text': self.format_float(total_tax_amount_percent, vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:RoundingAmount': {
                '_text': self.format_float(base_line['tax_details']['total_included_currency'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cac:TaxSubtotal': [
                {
                    'cbc:TaxableAmount': {
                        # Always report the line's tax-excluded total as base amount, even if it isn't the base of the tax
                        # (e.g. if there is first a fixed tax and then a percent tax). This is required by the JoFotara spec.
                        '_text': self.format_float(base_line['tax_details']['total_excluded_currency'], vals['currency_dp']),
                        'currencyID': vals['currency_name']
                    },
                    'cbc:TaxAmount': {
                        '_text': self.format_float(values['tax_amount_currency'], vals['currency_dp']),
                        'currencyID': vals['currency_name']
                    },
                    'cac:TaxCategory': self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
                }
                for grouping_key, values in aggregated_tax_details.items()
                if grouping_key
            ],
        }

    def _add_invoice_line_item_nodes(self, line_node, vals):
        super()._add_invoice_line_item_nodes(line_node, vals)
        line_node['cac:Item']['cbc:Description'] = None

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        # No InvoiceLine/Item/ClassifiedTaxCategory in Jordan
        pass

    def _add_invoice_line_price_nodes(self, line_node, vals):
        # OVERRIDE account_edi_xml_ubl_20.py
        line_node['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': self.format_float(vals['gross_price_unit_currency'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            # Add the line-level AllowanceCharge to the Price node
            'cac:AllowanceCharge': self._get_line_discount_allowance_charge_node(vals),
        }

    def _get_line_discount_allowance_charge_node(self, vals):
        # OVERRIDE account_edi_xml_ubl_20.py
        base_line = vals['base_line']
        if base_line['discount'] == 0.0:
            return None

        return {
            'cbc:ChargeIndicator': {'_text': 'false' if vals['discount_amount_currency'] > 0 else 'true'},
            'cbc:AllowanceChargeReason': {'_text': 'DISCOUNT'},
            'cbc:Amount': {
                '_text': self.format_float(
                    abs(vals['discount_amount_currency']),
                    vals['currency_dp'],
                ),
                'currencyID': vals['currency_name'],
            }
        }
