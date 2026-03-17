from stdnum.fr import siret

from odoo import models, Command
from odoo.tools import formatLang, frozendict, html2plaintext
from odoo.tools.misc import NON_BREAKING_SPACE
from datetime import datetime
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import (
    FloatFmt,
)

DEFAULT_CII_DATE_FORMAT = '%Y%m%d'

PAYMENT_MEAN_CODES = {
    'Payment to bank account': 42,
    'SEPA direct debit': 59
}


class AccountEdiCii(models.AbstractModel):
    _name = "account.edi.cii"
    _inherit = 'account.edi.common'
    _description = "Base helpers for CII"

    # -------------------------------------------------------------------------
    # NEW EXPORT : helpers
    # -------------------------------------------------------------------------

    def _cii_add_invoice_config_vals(self, vals):
        invoice = vals['invoice']
        vals['currency_id'] = invoice.currency_id
        vals['company_currency'] = invoice.company_id.currency_id
        vals['supplier'] = invoice.company_id.partner_id
        vals['customer'] = invoice.partner_id
        vals['partner_shipping'] = invoice.partner_shipping_id or invoice.partner_id
        vals['company'] = invoice.company_id

        if invoice.is_purchase_document():
            vals['supplier'], vals['customer'] = vals['customer'], vals['supplier']
            vals['partner_shipping'] = vals['customer'].child_ids.filtered(lambda p: p.type == 'delivery')[:1] or vals['customer']

        self._cii_add_values_delivery_date(vals, invoice.delivery_date or invoice.invoice_date)

        vals['base_lines'], vals['tax_lines'] = invoice._get_rounded_base_and_tax_lines()

        self._turn_price_unit_positive(vals)
        self._cii_extract_cash_rounding_lines(vals)
        self._cii_extract_early_pay_discount_lines(vals)

        AccountTax = self.env['account.tax']
        AccountTax._round_raw_total_excluded(vals['base_lines'], invoice.company_id)
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(vals['base_lines'], invoice.company_id)
        AccountTax._round_raw_gross_total_excluded_and_discount(vals['base_lines'], invoice.company_id)

    def _cii_add_values_delivery_date(self, vals, delivery_date):
        vals['delivery_date'] = delivery_date

    def _cii_add_values_billing_dates(self, vals, start_date, end_date):
        vals['billing_start_date'] = start_date
        vals['billing_end_date'] = end_date

    def _cii_get_default_tax_grouping_key(self, base_line, tax_data, vals, currency):
        """ Give the values about the tax category for a given tax.

        :param base_line:   A base line (see '_prepare_base_line_for_taxes_computation').
        :param tax_data:    One of the tax data in base_line['tax_details']['taxes_data'].
        :param vals:        Some custom data.
        :param currency:    The currency for which the grouping key is expressed.
        :return:            A dictionary that could be used as a grouping key for the taxes helpers.
        """
        customer = vals['customer']
        supplier = vals['supplier']
        if tax_data and (
            tax_data['tax'].amount_type != 'percent'
            or self._cii_is_recycling_contribution_tax(tax_data)
            or self._cii_is_excise_tax(tax_data)
        ):
            return
        else:
            if tax_data:
                tax = tax_data['tax']
                tax_category_code = self._get_tax_category_code(customer.commercial_partner_id, supplier, tax)
                if tax_category_code == 'O':
                    percent = None
                else:
                    percent = tax.amount if not tax.has_negative_factor else 0.0
                return {
                    'tax_category_code': tax_category_code,
                    **self.with_context(tax_exemption_reason_invoice=vals['invoice'])._get_tax_exemption_reason(customer.commercial_partner_id, supplier, tax),
                    'percent': percent,
                    'scheme_id': "VAT",
                    'is_withholding': tax.amount < 0.0,
                    'currency': currency,
                }
            else:
                return {
                    'tax_category_code': self._get_tax_category_code(customer.commercial_partner_id, supplier, self.env['account.tax']),
                    **self._get_tax_exemption_reason(customer.commercial_partner_id, supplier, self.env['account.tax']),
                    'percent': 0.0,
                    'scheme_id': "VAT",
                    'is_withholding': False,
                    'currency': currency,
                }

    def _cii_get_default_applicable_trade_tax_grouping_key(self, base_line, tax_data, vals, currency):
        """ Give the grouping key when computing taxes for
        IncludedSupplyChainTradeLineItem -> SpecifiedLineTradeSettlement -> ApplicableTradeTax.

        :param base_line:   A base line (see '_prepare_base_line_for_taxes_computation').
        :param tax_data:    One of the tax data in base_line['tax_details']['taxes_data'].
        :param vals:        Some custom data.
        :param currency:    The currency for which the grouping key is expressed.
        :return:            A dictionary that could be used as a grouping key for the taxes helpers.
        """
        tax_grouping_key = self._cii_get_default_tax_grouping_key(base_line, tax_data, vals, currency)
        if not tax_grouping_key or tax_grouping_key['is_withholding']:
            return
        return tax_grouping_key

    def _cii_is_recycling_contribution_tax(self, tax_data):
        """ Indicate if the 'tax_data' passed as parameter is a recycling contribution tax.

        :param tax_data:    One of the tax data in base_line['tax_details']['taxes_data'].
        :return:            True if tax_data['tax'] is a recycling contribution tax, False otherwise.
        """
        if not tax_data:
            return False

        tax = tax_data['tax']
        return tax.amount_type == 'fixed' and tax.include_base_amount

    def _cii_is_excise_tax(self, tax_data):
        """ Indicate if the 'tax_data' passed as parameter is an excise tax.

        :param tax_data:    One of the tax data in base_line['tax_details']['taxes_data'].
        :return:            True if tax_data['tax'] is an excise tax, False otherwise.
        """
        if not tax_data:
            return False

        tax = tax_data['tax']
        return tax.amount_type == 'code' and tax.include_base_amount

    def _cii_extract_cash_rounding_lines(self, vals):
        """
        Extract the cash rounding lines for the 'add_invoice_line' cash rounding strategy.

        :param vals: Some custom data
        """
        base_lines = vals['base_lines']
        vals['base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] != 'cash_rounding']
        vals['cash_rounding_base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] == 'cash_rounding']

    def _cii_extract_early_pay_discount_lines(self, vals):
        """
        Extract the early payment discount lines.

        :param vals: Some custom data
        """
        base_lines = vals['base_lines']
        vals['base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] != 'early_payment']
        vals['early_payment_discount_lines'] = [base_line for base_line in base_lines if base_line['special_type'] == 'early_payment']

    # ----------------------------------------------------------------------------
    # EXPORT : build nodes
    # ----------------------------------------------------------------------------

    def _cii_add_exchanged_document_context_node(self, vals):
        node = vals['document_node'].setdefault('rsm:ExchangedDocumentContext', {})
        node['ram:GuidelineSpecifiedDocumentContextParameter'] = {
                'ram:ID': {'_text': "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"},
            }

    def _cii_add_exchanged_document_node(self, vals):
        invoice = vals['invoice']
        vals['document_node']['rsm:ExchangedDocument'] = {
            'ram:ID': {'_text': invoice.name},
            'ram:TypeCode': {'_text': '380' if invoice.move_type == 'out_invoice' else '381'},
            'ram:IssueDateTime': self._cii_get_date_time_string_node(vals, invoice.invoice_date),
            'ram:IncludedNote': self._cii_get_included_note_node(vals)
        }

    def _cii_get_date_time_string_node(self, vals, date):
        return {
            'udt:DateTimeString': {
                '_text': date.strftime(DEFAULT_CII_DATE_FORMAT),
                'format': "102",
            }
        }

    def _cii_get_included_note_node(self, vals):
        nodes = []
        if note := self._cii_get_included_note(vals):
            nodes.append({
                'ram:Content': {'_text': note},
            })
        for code, content in self._get_default_notes(vals).items():
            nodes.append({
                'ram:Content': {'_text': content},
                'ram:SubjectCode': {'_text': code},
            })
        return nodes

    def _cii_get_included_note(self, vals):
        invoice = vals['invoice']
        notes = []

        AccountTax = self.env['account.tax']
        base_lines = vals['base_lines']
        currency = vals['currency_id']

        def grouping_function(base_line, tax_data):
            if not tax_data:
                return
            tax_grouping_key = self._cii_get_default_tax_grouping_key(base_line, tax_data, vals, currency)
            if not tax_grouping_key:
                return
            return tax_grouping_key['is_withholding']

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        vals['tax_withholding_amount'] = 0.0
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue

            tax_amount = values['tax_amount_currency']
            vals['tax_withholding_amount'] -= tax_amount

        if not currency.is_zero(vals['tax_withholding_amount']):
            notes.append(self.env._(
                "The prepaid amount of %s corresponds to the withholding tax applied.",
                formatLang(self.env, vals['tax_withholding_amount'], currency_obj=currency).replace(NON_BREAKING_SPACE, ''),
            ))

        terms_and_condition = html2plaintext(invoice.narration) if invoice.narration else None
        if terms_and_condition:
            notes.append(terms_and_condition)

        return ' '.join(notes) if notes else None

    def _cii_add_supply_chain_trade_transaction_node(self, vals):
        vals['document_node']['rsm:SupplyChainTradeTransaction'] = {
            'ram:IncludedSupplyChainTradeLineItem': self._cii_get_included_supply_chain_trade_line_item_nodes(vals),
            'ram:ApplicableHeaderTradeAgreement': self._cii_get_applicable_header_trade_agreement_node(vals),
            'ram:ApplicableHeaderTradeDelivery': self._cii_get_applicable_header_trade_delivery_node(vals),
            'ram:ApplicableHeaderTradeSettlement': self._cii_get_applicable_header_trade_settlement_node(vals),
        }

    def _cii_get_included_supply_chain_trade_line_item_nodes(self, vals):
        nodes = []
        for idx, base_line in enumerate(vals['base_lines']):
            nodes.append(self._cii_get_included_supply_chain_trade_line_item_node(vals, idx + 1, base_line))
        return nodes

    def _cii_get_included_supply_chain_trade_line_item_node(self, vals, line_idx, base_line):
        return {
            'ram:AssociatedDocumentLineDocument': {
                'ram:LineID': {'_text': line_idx},
            },
            'ram:SpecifiedTradeProduct': self._cii_get_line_specified_trade_product_node(vals, base_line),
            'ram:SpecifiedLineTradeAgreement': {
                'ram:GrossPriceProductTradePrice': self._cii_get_gross_price_product_trade_price_node(vals, base_line),
                'ram:NetPriceProductTradePrice': self._cii_get_net_price_product_trade_price_node(vals, base_line),
            },
            'ram:SpecifiedLineTradeDelivery': {
                'ram:BilledQuantity': {
                    'unitCode': self._get_uom_unece_code(base_line['product_uom_id']),
                    '_text': base_line['quantity'],
                },
            },
            'ram:SpecifiedLineTradeSettlement': self._cii_get_specified_line_trade_settlement_node(vals, base_line),
        }

    def _cii_get_line_specified_trade_product_node(self, vals, base_line):
        product = base_line['product_id']
        return {
            'ram:GlobalID': {
                '_text': product.barcode,
                'schemeID': "0160",
            } if product.barcode else None,
            'ram:SellerAssignedID': {'_text': product.default_code} if product.default_code else None,
            'ram:Name': {'_text': base_line['name']},
            'ram:Description': {
                '_text': html2plaintext(product.description),
            } if product.description else None,
        }

    def _cii_get_gross_price_product_trade_price_node(self, vals, base_line):
        return {
            'ram:ChargeAmount': {'_text': FloatFmt(base_line['tax_details']['raw_gross_price_unit_currency'], max_dp=2)},
            'ram:AppliedTradeAllowanceCharge': self._cii_get_applied_trade_allowance_charge_node(vals, base_line) if base_line.get('discount') else None,
        }

    def _cii_get_applied_trade_allowance_charge_node(self, vals, base_line):
        discount_percentage = abs(base_line['discount']) / 100.0
        return {
            'ram:ChargeIndicator': {
                'udt:Indicator': {'_text': 'false' if base_line['discount'] > 0 else 'true'},
            },
            'ram:ActualAmount': {
                '_text': FloatFmt(vals['currency_id'].round(base_line['tax_details']['raw_gross_price_unit_currency'] * discount_percentage), max_dp=2),
            }
        }

    def _cii_get_net_price_product_trade_price_node(self, vals, base_line):
        return {
            'ram:ChargeAmount': {
                '_text': FloatFmt(base_line['tax_details']['raw_total_excluded_currency'] / (base_line['quantity'] or 1.0), max_dp=2),
            }
        }

    def _cii_get_specified_line_trade_settlement_node(self, vals, base_line):
        return {
            'ram:ApplicableTradeTax': self._cii_get_line_applicable_trade_tax_nodes(vals, base_line),
            'ram:BillingSpecifiedPeriod': {
                'ram:StartDateTime': self._cii_get_date_time_string_node(vals, base_line['deferred_start_date']) if base_line.get('deferred_start_date') else None,
                'ram:EndDateTime': self._cii_get_date_time_string_node(vals, base_line['deferred_end_date']) if base_line.get('deferred_end_date') else None,
            },
            'ram:SpecifiedTradeAllowanceCharge': self._cii_get_specified_line_trade_allowance_charge_nodes(vals, base_line),
            'ram:SpecifiedTradeSettlementLineMonetarySummation': self._cii_get_specified_trade_settlement_line_monetary_summation_node(vals, base_line),
        }

    def _cii_get_line_applicable_trade_tax_nodes(self, vals, base_line):
        tax_nodes = []
        aggregated_values = self.env['account.tax']._aggregate_base_line_tax_details(
            base_line=base_line,
            grouping_function=lambda base_line, tax_data: self._cii_get_default_applicable_trade_tax_grouping_key(
                base_line=base_line,
                tax_data=tax_data,
                vals=vals,
                currency=vals['currency_id'],
            ),
        )
        for grouping_key, values in aggregated_values.items():
            if not grouping_key:
                continue
            tax_nodes.append(self._cii_get_line_applicable_trade_tax_node(vals, {
                'tax_category_code': grouping_key['tax_category_code'],
                'rate_applicable_percent': grouping_key['percent'],
            }))
        return tax_nodes

    def _cii_get_line_applicable_trade_tax_node(self, vals, trade_tax_values):
        return {
            'ram:TypeCode': {'_text': "VAT"},
            'ram:CategoryCode': {'_text': trade_tax_values['tax_category_code']},
            'ram:RateApplicablePercent': {'_text': trade_tax_values['rate_applicable_percent']},
        }

    def _cii_get_specified_line_trade_allowance_charge_nodes(self, vals, base_line):
        nodes = vals['line_trade_allowance_charge_nodes'] = []
        sub_vals = {
            **vals,
            'allowance_charge_node': nodes,
            'base_line': base_line,
        }
        # Recycling contribution taxes.
        self._cii_add_line_allowance_charge_nodes_for_recycling_contribution_taxes(sub_vals)
        # Excise taxes.
        self._cii_add_line_allowance_charge_nodes_for_excise_taxes(sub_vals)
        return nodes

    def _cii_add_line_allowance_charge_nodes_for_recycling_contribution_taxes(self, vals):
        base_line = vals['base_line']
        currency = base_line['currency_id']

        allowance_charges_nodes = vals['allowance_charge_node']
        for tax_data in base_line['tax_details']['taxes_data']:
            if not self._cii_is_recycling_contribution_tax(tax_data):
                continue

            allowance_charges_nodes.append(self._cii_get_line_allowance_charge_recycling_contribution_node(vals, {
                'tax': tax_data['tax'],
                'is_charge': tax_data['tax_amount'] * tax_data['base_amount'] > 0.0,
                'amount': tax_data['tax_amount_currency'],
                'currency': currency,
            }))

    def _cii_get_line_allowance_charge_recycling_contribution_node(self, vals, recycling_contribution_values):
        currency = recycling_contribution_values['currency']
        amount = recycling_contribution_values['amount']
        tax = recycling_contribution_values['tax']
        if 'bebat' in tax.name.lower():
            charge_reason_code = 'CAV'
        else:
            charge_reason_code = 'AEO'
        is_charge = recycling_contribution_values['is_charge']
        return {
            'ram:ChargeIndicator': {
                'udt:Indicator': {'_text': 'true' if is_charge else 'false'},
            },
            'ram:ReasonCode': {'_text': charge_reason_code if is_charge else '100'},
            'ram:Reason': {'_text': tax.name},
            'ram:ActualAmount': {
                '_text': FloatFmt(amount, max_dp=currency.decimal_places),
            },
        }

    def _cii_add_line_allowance_charge_nodes_for_excise_taxes(self, vals):
        base_line = vals['base_line']
        currency = base_line['currency_id']

        allowance_charges_nodes = vals['allowance_charge_node']
        for tax_data in base_line['tax_details']['taxes_data']:
            if not self._cii_is_excise_tax(tax_data):
                continue

            allowance_charges_nodes.append(self._cii_get_line_allowance_charge_excise_node(vals, {
                'tax': tax_data['tax'],
                'is_charge': tax_data['tax_amount'] > 0.0,
                'amount': tax_data['tax_amount_currency'],
                'currency': currency,
            }))

    def _cii_get_line_allowance_charge_excise_node(self, vals, excise_values):
        currency = excise_values['currency']
        amount = excise_values['amount']
        tax = excise_values['tax']
        is_charge = excise_values['is_charge']
        return {
            'ram:ChargeIndicator': {
                'udt:Indicator': {'_text': 'true' if is_charge else 'false'},
            },
            'ram:Reason': {'_text': tax.name},
            'ram:ActualAmount': {
                '_text': FloatFmt(abs(amount), max_dp=currency.decimal_places),
            },
        }

    def _cii_get_specified_trade_settlement_line_monetary_summation_node(self, vals, base_line):
        currency = vals['currency_id']
        tax_details = base_line['tax_details']

        total_excluded = currency.round(tax_details['raw_total_excluded_currency'])
        for allowance_charge_node in vals['line_trade_allowance_charge_nodes']:
            sign = 1 if allowance_charge_node['ram:ChargeIndicator']['udt:Indicator']['_text'] == 'true' else -1
            total_excluded += sign * allowance_charge_node['ram:ActualAmount']['_text']
        return {
            'ram:LineTotalAmount': {'_text': FloatFmt(total_excluded, max_dp=2)},
        }

    def _cii_get_applicable_header_trade_agreement_node(self, vals):
        invoice = vals['invoice']
        return {
            'ram:BuyerReference': {'_text': invoice.buyer_reference
                if 'buyer_reference' in invoice._fields and invoice.buyer_reference
                else invoice.commercial_partner_id.ref,
            },
            'ram:SellerTradeParty': self._cii_get_seller_trade_party_node(vals),
            'ram:BuyerTradeParty': self._cii_get_buyer_trade_party_node(vals),
            'ram:BuyerOrderReferencedDocument': {
                'ram:IssuerAssignedID': {'_text': invoice.purchase_order_reference
                    if 'purchase_order_reference' in invoice._fields and invoice.purchase_order_reference
                    else invoice.ref or invoice.name
                },
            },
            'ram:ContractReferencedDocument': {
                'ram:IssuerAssignedID': {'_text': invoice.contract_reference
                    if 'contract_reference' in invoice._fields and invoice.contract_reference
                    else ''
                },
            },
        }

    def _cii_get_seller_trade_party_node(self, vals):
        invoice = vals['invoice']
        supplier = vals['supplier']
        commercial_partner = supplier.commercial_partner_id
        scheme_id = None
        legal_organization_val = commercial_partner.company_registry
        if siret.is_valid(legal_organization_val):
            scheme_id = "0002"
            legal_organization_val = legal_organization_val[:9]
        supplier_vat = invoice.fiscal_position_id.foreign_vat or commercial_partner.vat
        return self._cii_get_partner_trade_party_node(vals, {
            'gln': False,
            'name': supplier.name,
            'partner_specified_legal_organization': legal_organization_val,
            'partner_specified_legal_organization_scheme': scheme_id,
            'contact_values': {
                'name': supplier.name,
                'phone': supplier.phone,
                'email': supplier.email,
            },
            'address_values': {
                'postcode': supplier.zip,
                'line_one': supplier.street,
                'line_two': supplier.street2,
                'city': supplier.city,
                'country_code': supplier.country_id.code,
            },
            'peppol_eas': supplier.peppol_eas,
            'peppol_endpoint': supplier.peppol_endpoint,
            'partner_tax_registration': supplier_vat,
        })

    def _cii_get_partner_trade_party_node(self, vals, partner_values):
        return {
            'ram:ID': {
                'schemeID': '0088',
                '_text': partner_values['gln'],
            } if partner_values['gln'] else None,
            'ram:Name': {'_text': partner_values['name']},
            'ram:SpecifiedLegalOrganization': {
                'ram:ID': {
                    '_text': partner_values['partner_specified_legal_organization'],
                    'schemeID': partner_values['partner_specified_legal_organization_scheme'],
                },
            } if partner_values['partner_specified_legal_organization'] else None,
            'ram:DefinedTradeContact': self._cii_get_defined_trade_contact_node(vals, partner_values['contact_values']),
            'ram:PostalTradeAddress': self._cii_get_postal_trade_address_node(vals, partner_values['address_values']),
            'ram:URIUniversalCommunication': {
                'ram:URIID': {
                    'schemeID': partner_values['peppol_eas'],
                    '_text': partner_values['peppol_endpoint'],
                },
            } if partner_values['peppol_eas'] and partner_values['peppol_endpoint'] else None,
            'ram:SpecifiedTaxRegistration': {
                'ram:ID': {
                    '_text': partner_values['partner_tax_registration'],
                    'schemeID': 'VA',
                },
            } if partner_values['partner_tax_registration'] else None,
        }

    def _cii_get_defined_trade_contact_node(self, vals, contact_values):
        return {
            'ram:PersonName': {'_text': contact_values['name']},
            'ram:TelephoneUniversalCommunication': {
                'ram:CompleteNumber': {'_text': contact_values['phone']},
            } if contact_values['phone'] else None,
            'ram:EmailURIUniversalCommunication': {
                'ram:URIID': {'_text': contact_values['email']},
            } if contact_values['email'] else None,
        }

    def _cii_get_postal_trade_address_node(self, vals, address_values):
        return {
            'ram:PostcodeCode': {'_text': address_values['postcode']},
            'ram:LineOne': {'_text': address_values['line_one']},
            'ram:LineTwo': {
                '_text': address_values['line_two'],
            } if address_values['line_two'] else None,
            'ram:CityName': {'_text': address_values['city']},
            'ram:CountryID': {'_text': address_values['country_code']},
        }

    def _cii_get_buyer_trade_party_node(self, vals):
        customer = vals['customer']
        commercial_partner = customer.commercial_partner_id
        scheme_id = None
        legal_organization_val = commercial_partner.company_registry
        if siret.is_valid(legal_organization_val):
            scheme_id = "0002"
            legal_organization_val = legal_organization_val[:9]
        return self._cii_get_partner_trade_party_node(vals, {
            'gln': False,
            'name': customer.name,
            'partner_specified_legal_organization': legal_organization_val,
            'partner_specified_legal_organization_scheme': scheme_id,
            'contact_values': {
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
            },
            'address_values': {
                'postcode': customer.zip,
                'line_one': customer.street,
                'line_two': customer.street2,
                'city': customer.city,
                'country_code': customer.country_id.code,
            },
            'peppol_eas': customer.peppol_eas,
            'peppol_endpoint': customer.peppol_endpoint,
            'partner_tax_registration': customer.vat,
        })

    def _cii_get_applicable_header_trade_delivery_node(self, vals):
        return {
            'ram:ShipToTradeParty': self._cii_get_ship_to_trade_party_node(vals),
            'ram:ActualDeliverySupplyChainEvent': {
                'ram:OccurrenceDateTime': self._cii_get_date_time_string_node(vals, vals['delivery_date'])
            } if vals['delivery_date'] else None,
        }

    def _cii_get_ship_to_trade_party_node(self, vals):
        invoice = vals['invoice']
        partner_shipping = vals['partner_shipping']
        return self._cii_get_partner_trade_party_node(vals, {
            'gln': 'global_location_number' in invoice.partner_shipping_id._fields and invoice.partner_shipping_id.global_location_number,
            'name': partner_shipping.name,
            'partner_specified_legal_organization': False,
            'partner_specified_legal_organization_scheme': None,
            'contact_values': {
                'name': partner_shipping.name,
                'phone': partner_shipping.phone,
                'email': partner_shipping.email,
            },
            'address_values': {
                'postcode': partner_shipping.zip,
                'line_one': partner_shipping.street,
                'line_two': partner_shipping.street2,
                'city': partner_shipping.city,
                'country_code': partner_shipping.country_id.code,
            },
            'peppol_eas': False,
            'peppol_endpoint': False,
            'partner_tax_registration': False,
        })

    def _cii_get_applicable_header_trade_settlement_node(self, vals):
        invoice = vals['invoice']
        return {
            'ram:PaymentReference': {'_text': invoice.payment_reference},
            'ram:InvoiceCurrencyCode': {'_text': vals['currency_id'].name},
            'ram:SpecifiedTradeSettlementPaymentMeans': {
                'ram:TypeCode': {'_text': PAYMENT_MEAN_CODES['SEPA direct debit']
                    if self.env['account.payment']._fields.get('sdd_mandate_id') and invoice.reconciled_payment_ids.sdd_mandate_id
                    else PAYMENT_MEAN_CODES['Payment to bank account'],
                },
                'ram:PayeePartyCreditorFinancialAccount': self._cii_get_payee_party_creditor_financial_account_node(vals),
            },
            'ram:ApplicableTradeTax': self._cii_get_applicable_trade_tax_nodes(vals),
            'ram:BillingSpecifiedPeriod': self._cii_get_billing_specified_period_node(vals),
            'ram:SpecifiedTradePaymentTerms': self._cii_get_specified_trade_payment_terms_node(vals),
            'ram:SpecifiedTradeSettlementHeaderMonetarySummation': self._cii_get_specified_trade_settlement_header_monetary_summary_node(vals),
        }

    def _cii_get_payee_party_creditor_financial_account_node(self, vals):
        invoice = vals['invoice']
        if invoice.partner_bank_id.acc_type == 'iban':
            return {
                'ram:IBANID': {'_text': invoice.partner_bank_id.sanitized_acc_number}
            }
        else:
            return {
                'ram:ProprietaryID': {'_text': invoice.partner_bank_id.sanitized_acc_number}
            }

    def _cii_get_applicable_trade_tax_nodes(self, vals):
        tax_nodes = []
        currency = vals['currency_id']
        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(
            base_lines=vals['base_lines'],
            grouping_function=lambda base_line, tax_data: self._cii_get_default_applicable_trade_tax_grouping_key(
                base_line=base_line,
                tax_data=tax_data,
                vals=vals,
                currency=currency,
            )
        )
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        vals['tax_details'] = {}
        for grouping_key, values in aggregated_tax_details.items():
            if not grouping_key:
                continue
            vals['tax_details'][grouping_key] = values
            amount_currency = values['tax_amount_currency']
            tax_nodes.append(self._cii_get_applicable_trade_tax_node(vals, {
                'calculated_amount': amount_currency if not currency.is_zero(amount_currency) else 0.0,
                'tax_exemption_reason': grouping_key['tax_exemption_reason'],
                'basis_amount': values['base_amount_currency'],
                'tax_category_code': grouping_key['tax_category_code'],
                'tax_exemption_reason_code': grouping_key['tax_exemption_reason_code'],
                'rate_applicable_percent': grouping_key['percent'],
            }))
        return tax_nodes

    def _cii_get_applicable_trade_tax_node(self, vals, trade_tax_values):
        return {
            'ram:CalculatedAmount': {
                '_text': FloatFmt(trade_tax_values['calculated_amount'], max_dp=2),
            },
            'ram:TypeCode': {'_text': "VAT"},
            'ram:ExemptionReason': {'_text': trade_tax_values['tax_exemption_reason']},
            'ram:BasisAmount': {'_text': FloatFmt(trade_tax_values['basis_amount'], max_dp=2)},
            'ram:CategoryCode': {'_text': trade_tax_values['tax_category_code']},
            'ram:ExemptionReasonCode': {'_text': trade_tax_values['tax_exemption_reason_code']},
            'ram:DueDateTypeCode': {'_text': 5},
            'ram:RateApplicablePercent': {'_text': trade_tax_values['rate_applicable_percent']},
        }

    def _cii_get_billing_specified_period_node(self, vals):
        invoice = vals['invoice']
        billing_start_dates = [invoice.invoice_date] if invoice.invoice_date else []
        billing_start_dates += [move_line.deferred_start_date for move_line in invoice.invoice_line_ids if move_line.deferred_start_date]
        billing_end_dates = [invoice.invoice_date_due] if invoice.invoice_date_due else []
        billing_end_dates += [move_line.deferred_end_date for move_line in invoice.invoice_line_ids if move_line.deferred_end_date]
        start_date = end_date = None
        if billing_start_dates:
            start_date = min(billing_start_dates)
        if billing_end_dates:
            end_date = max(billing_end_dates)
        return {
            'ram:StartDateTime': self._cii_get_date_time_string_node(vals, start_date) if start_date else None,
            'ram:EndDateTime': self._cii_get_date_time_string_node(vals, end_date) if end_date else None,
        }

    def _cii_get_specified_trade_payment_terms_node(self, vals):
        invoice = vals['invoice']
        return {
            'ram:Description': {
                '_text': invoice.invoice_payment_term_id.name,
            } if invoice.invoice_payment_term_id else None,
            'ram:DueDateDateTime': self._cii_get_date_time_string_node(vals, invoice.invoice_date_due) if invoice.invoice_date_due else None,
            'ram:ApplicableTradePaymentDiscountTerms': {
                'ram:BasisPeriodMeasure': {
                    '_text': invoice.invoice_payment_term_id.discount_days,
                    'unitCode': 'DAY',
                },
                'ram:CalculationPercent': {
                    '_text': invoice.invoice_payment_term_id.discount_percentage,
                }
            } if invoice.invoice_payment_term_id.early_discount else None,
        }

    def _cii_get_specified_trade_settlement_header_monetary_summary_node(self, vals):
        node = {}
        sub_vals = {
            **vals,
            'monetary_summation_node': node,
        }
        self._cii_add_monetary_summation_line_total_amount_node(sub_vals)
        self._cii_add_monetary_summation_tax_basis_total_amount_node(sub_vals)
        self._cii_add_monetary_summation_tax_total_amount_node(sub_vals)
        self._cii_add_monetary_summation_rounding_amount_node(sub_vals)
        self._cii_add_monetary_summation_grand_total_amount_node(sub_vals)
        self._cii_add_monetary_summation_total_prepaid_amount(sub_vals)
        self._cii_add_monetary_summation_due_payable_amount_node(sub_vals)
        return node

    def _cii_add_monetary_summation_line_total_amount_node(self, vals):
        vals['monetary_summation_node']['ram:LineTotalAmount'] = {
            '_text': FloatFmt(sum(
                tax_data['base_amount_currency']
                for _grouping_key, tax_data in vals['tax_details'].items()
            ), max_dp=2),
        }

    def _cii_add_monetary_summation_tax_basis_total_amount_node(self, vals):
        vals['monetary_summation_node']['ram:TaxBasisTotalAmount'] = {
            '_text': FloatFmt(sum(
                tax_data['base_amount_currency']
                for _grouping_key, tax_data in vals['tax_details'].items()
            ), max_dp=2),
        }

    def _cii_add_monetary_summation_tax_total_amount_node(self, vals):
        currency = vals['currency_id']
        vals['monetary_summation_node']['ram:TaxTotalAmount'] = {
            'currencyID': currency.name,
            '_text': FloatFmt(sum(
                tax_data['tax_amount_currency']
                for _grouping_key, tax_data in vals['tax_details'].items()
            ), max_dp=2),
        }

    def _cii_add_monetary_summation_rounding_amount_node(self, vals):
        cash_rounding_amount = sum(
                base_line['tax_details']['total_excluded_currency']
                for base_line in vals.setdefault('cash_rounding_base_lines', [])
            )
        if cash_rounding_amount:
            vals['monetary_summation_node']['ram:RoundingAmount'] = {
                '_text': FloatFmt(cash_rounding_amount, max_dp=2),
            }

    def _cii_add_monetary_summation_grand_total_amount_node(self, vals):
        vals['monetary_summation_node']['ram:GrandTotalAmount'] = {
            '_text': FloatFmt(sum(vals['monetary_summation_node'].get(node, {}).get('_text', 0.0)
            for node in ['ram:LineTotalAmount', 'ram:TaxTotalAmount', 'ram:RoundingAmount']), max_dp=2),
        }

    def _cii_add_monetary_summation_total_prepaid_amount(self, vals):
        prepaid_amount = vals['monetary_summation_node']['ram:GrandTotalAmount']['_text'] - vals['invoice'].amount_residual
        vals['monetary_summation_node']['ram:TotalPrepaidAmount'] = {
            '_text': FloatFmt(prepaid_amount, max_dp=2),
        }

    def _cii_add_monetary_summation_due_payable_amount_node(self, vals):
        vals['monetary_summation_node']['ram:DuePayableAmount'] = {
            '_text': FloatFmt(vals['monetary_summation_node']['ram:GrandTotalAmount']['_text'] -
                              vals['monetary_summation_node']['ram:TotalPrepaidAmount']['_text'], max_dp=2),
        }

    def _cii_constraints(self, invoice, vals):
        constraints = {}
        self._cii_check_seller(invoice, vals, constraints)
        self._cii_check_buyer(vals, constraints)

        if vals.get('intracom_delivery'):
            self._cii_check_intracom_delivery(vals, constraints)

        if vals['customer']['country_id']['code'] == 'ES' \
            and vals['customer']['zip'] \
            and vals['customer']['zip'][:2] in ['35', '38']:
            self._cii_check_igi_tax_rate(invoice, vals, constraints)

        return constraints

    def _cii_check_seller(self, invoice, vals, constraints):
        self._cii_check_invoice_payment_instructions(invoice, vals, constraints)
        self._cii_check_seller_postal_address(vals, constraints)
        self._cii_check_seller_identifier(vals, constraints)
        self._cii_check_seller_contact(vals, constraints)

    def _cii_check_buyer(self, vals, constraints):
        self._cii_check_buyer_postal_address(vals, constraints)

    def _cii_check_invoice_payment_instructions(self, invoice, vals, constraints):
        """
        [BR-DE-1] An Invoice must contain information on "PAYMENT INSTRUCTIONS" (BG-16).
        First check that a partner_bank_id exists, then check that there is an account number.
        """
        if invoice.move_type == 'out_invoice':
            constraints.update({
                'seller_payment_instructions_1': self._check_required_fields(
                    vals['invoice'], 'partner_bank_id'
                ),
                'seller_payment_instructions_2': self._check_required_fields(
                    vals['invoice']['partner_bank_id'], 'sanitized_acc_number',
                    self.env._("The field 'Sanitized Account Number' is required on the Recipient Bank.")
                ),
            })

    def _cii_check_seller_postal_address(self, vals, constraints):
        """
        [BR-08]-An Invoice shall contain the Seller postal address (BG-5).
        [BR-09]-The Seller postal address (BG-5) shall contain a Seller country code (BT-40).
        """
        constraints['seller_postal_address'] = self._check_required_fields(
                vals['supplier'].commercial_partner_id, 'country_id'
            )

    def _cii_check_seller_identifier(self, vals, constraints):
        """
        [BR-CO-26]-In order for the buyer to automatically identify a supplier, the Seller identifier (BT-29),
        the Seller legal registration identifier (BT-30) and/or the Seller VAT identifier (BT-31) shall be present.
        """
        constraints['seller_identifier'] = self._check_required_fields(
                vals['supplier'], ['vat']
            )

    def _cii_check_seller_contact(self, vals, constraints):
        """
        [BR-DE-6] The element "Seller contact telephone number" (BT-42) must be transmitted.
        [BR-DE-7] The element "Seller contact email address" (BT-43) must be transmitted.
        """
        constraints.update({
            'seller_phone': self._check_required_fields(
                vals['supplier'].commercial_partner_id, 'phone',
            ),
            'seller_email': self._check_required_fields(
                vals['supplier'], 'email'
            ),
        })

    def _cii_check_buyer_postal_address(self, vals, constraints):
        """
        [BR-10]-An Invoice shall contain the Buyer postal address (BG-8).
        [BR-11]-The Buyer postal address shall contain a Buyer country code (BT-55).
        """
        constraints['buyer_postal_address'] = self._check_required_fields(
                vals['customer'].commercial_partner_id, 'country_id'
            )

    def _cii_check_intracom_delivery(self, vals, constraints):
        """
        [BR-IC-02]-An Invoice that contains an Invoice line (BG-25) where the Invoiced item VAT category code (BT-151)
        is "Intra-community supply" shall contain the Seller VAT Identifier (BT-31) or the Seller tax representative
        VAT identifier (BT-63) and the Buyer VAT identifier (BT-48).
        """
        constraints.update({
            'intracom_seller_vat': self._check_required_fields(
                vals['supplier'], 'vat'
            ),
            'intracom_buyer_vat': self._check_required_fields(
                vals['customer']['commercial_partner_id'], 'vat'
            ),
        })

    def _cii_check_igi_tax_rate(self, invoice, vals, constraints):
        for line in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section')):
            tax_rate_list = line.tax_ids.flatten_taxes_hierarchy().mapped("amount")
            if not any(rate > 0 for rate in tax_rate_list):
                constraints['igic_tax_rate'] = self.env._("When the Canary Island General Indirect Tax (IGIC) applies, the tax rate on "
                         "each invoice line should be greater than 0.")

    # -------------------------------------------------------------------------
    # NEW IMPORT : helpers
    # -------------------------------------------------------------------------

    def _import_cii_init_collected_values(self, invoice, collected_values):
        return self._import_init_collected_values(invoice, collected_values)

    def _import_cii_invoice_document_sign(self, collected_values):
        self._import_invoice_document_sign(collected_values)

    def _import_cii_invoice_update_move_type(self, collected_values):
        self._import_invoice_update_move_type(collected_values)

    def _import_cii_invoice_add_ref(self, collected_values):
        tree = collected_values['tree']
        if ref := tree.findtext('./{*}ExchangedDocument/{*}ID'):
            collected_values['to_write']['ref'] = ref

    def _import_cii_invoice_add_invoice_origin(self, collected_values):
        tree = collected_values['tree']
        if invoice_origin := tree.findtext('.//{*}BuyerOrderReferencedDocument/{*}IssuerAssignedID'):
            collected_values['to_write']['invoice_origin'] = invoice_origin

    def _import_cii_invoice_add_issue_date(self, collected_values):
        tree = collected_values['tree']
        if issue_date_str := tree.findtext('./{*}ExchangedDocument/{*}IssueDateTime/{*}DateTimeString'):
            collected_values['to_write']['invoice_date'] = datetime.strptime(issue_date_str.strip(), DEFAULT_CII_DATE_FORMAT)

    def _import_cii_invoice_add_date_due(self, collected_values):
        tree = collected_values['tree']
        if invoice_date_due_str := tree.findtext(".//{*}SpecifiedTradePaymentTerms/{*}DueDateDateTime/{*}DateTimeString"):
            collected_values['to_write']['invoice_date_due'] = datetime.strptime(invoice_date_due_str.strip(), DEFAULT_CII_DATE_FORMAT)

    def _import_cii_invoice_add_invoice_delivery_date(self, collected_values):
        tree = collected_values['tree']
        if delivery_date_str := tree.findtext(".//{*}ActualDeliverySupplyChainEvent/{*}OccurrenceDateTime/{*}DateTimeString"):
            collected_values['to_write']['delivery_date'] = datetime.strptime(delivery_date_str.strip(), DEFAULT_CII_DATE_FORMAT)

    def _import_cii_invoice_add_narration(self, collected_values):
        tree = collected_values['tree']
        notes = []
        for node in tree.findall('./{*}ExchangedDocument/{*}IncludedNote'):
            note = ""
            if code := node.findtext('./{*}SubjectCode'):
                note += code + ": "
            if content := node.findtext('./{*}Content'):
                note += content
            if note:
                notes.append(note)

        if narration := ''.join(f'<p>{note}</p>' for note in notes):
            collected_values['to_write']['narration'] = narration

    def _import_cii_invoice_add_customer_values(self, collected_values):
        customer_values = collected_values['customer_values'] = {}
        odoo_document_type = collected_values['odoo_document_type']
        party_tag = "BuyerTradeParty" if odoo_document_type == 'sale' else "SellerTradeParty"
        tree = collected_values['tree']
        party_node = tree.find(f".//{{*}}ApplicableHeaderTradeAgreement/{{*}}{party_tag}")
        if party_node is None:
            return

        for key, xpath in (
            ('name', "./{*}Name"),
            ('phone', ".//{*}TelephoneUniversalCommunication/{*}CompleteNumber"),
            ('email', ".//{*}EmailURIUniversalCommunication/{*}URIID"),
            ('zip', ".//{*}PostcodeCode"),
            ('street', ".//{*}LineOne"),
            ('street2', ".//{*}LineTwo"),
            ('city', ".//{*}CityName"),
            ('country_code', ".//{*}CountryID"),
            ('vat', "./{*}SpecifiedTaxRegistration/{*}ID")
        ):
            customer_values[key] = None
            if (node := party_node.find(xpath)) is not None:
                customer_values[key] = node.text

        # Peppol EAS/Endpoint.
        if (node := party_node.find(".//{*}URIUniversalCommunication/{*}URIID")) is not None:
            customer_values['peppol_endpoint'] = node.text
            if peppol_eas := node.attrib.get('schemeID'):
                customer_values['peppol_eas'] = peppol_eas

    def _import_cii_retrieve_customer(self, collected_values):
        self._import_retrieve_customer(collected_values)

    def _import_cii_create_missing_customer(self, collected_values):
        self._import_create_missing_customer(collected_values)

    def _import_cii_invoice_add_currency_code(self, collected_values):
        currency_values = collected_values['currency_values'] = {}
        tree = collected_values['tree']
        currency_values['currency_code'] = tree.findtext('.//{*}InvoiceCurrencyCode')

    def _import_cii_invoice_add_currency(self, collected_values):
        self._import_invoice_add_currency(collected_values)

    def _import_cii_invoice_add_partner_bank_values(self, collected_values):
        partner_bank_values = collected_values['partner_bank_values'] = {}
        tree = collected_values['tree']
        financial_nodes = tree.findall(".//{*}SpecifiedTradeSettlementPaymentMeans/{*}PayeePartyCreditorFinancialAccount")
        partner_bank_values['account_numbers'] = account_numbers = set()
        for node in financial_nodes:
            account_number = node.findtext('./{*}IBANID') or node.findtext('./{*}ProprietaryID')
            if account_number:
                account_numbers.add(account_number)

    def _import_cii_retrieve_partner_bank(self, collected_values):
        self._import_retrieve_partner_bank(collected_values)

    def _import_cii_invoice_add_prepaid_amount(self, collected_values):
        file_document_sign = collected_values['file_document_sign']
        currency = collected_values['currency_values']['currency']
        tree = collected_values['tree']
        prepaid_amount_str = tree.findtext('.//{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}TotalPrepaidAmount')
        prepaid_amount = file_document_sign * float(prepaid_amount_str or 0.0)
        if currency.is_zero(prepaid_amount):
            return

        collected_values['prepaid_amount'] = prepaid_amount
        formatted_prepaid_amount = formatLang(self.env, prepaid_amount, currency_obj=currency)
        collected_values['logs'].append(self.env._("A payment of %s was detected.", formatted_prepaid_amount))

    def _import_cii_invoice_add_tax_total_values(self, collected_values):
        file_document_sign = collected_values['file_document_sign']
        odoo_document_type = collected_values['odoo_document_type']

        taxes_values = collected_values['tax_total_values'] = {}
        tree = collected_values['tree']
        for subtotal_elem in tree.findall('.//{*}ApplicableHeaderTradeSettlement/{*}ApplicableTradeTax'):
            amount = subtotal_elem.findtext('./{*}CalculatedAmount')
            category_code = subtotal_elem.findtext('./{*}CategoryCode')
            if amount is None or category_code is None:
                continue

            percentage = subtotal_elem.findtext('./{*}RateApplicablePercent')
            if percentage is None:
                continue

            percentage = float(percentage)
            tax_key = frozendict({
                'category_code': category_code,
                'percentage': percentage,
            })
            tax_values = taxes_values.setdefault(tax_key, {
                'amount_type': 'percent',
                'type_tax_use': odoo_document_type,
                'amount': percentage,
                'ubl_cii_tax_category_code': category_code,
                'tax_amount_currency': 0.0,
                'related_taxes_values': [],
            })
            tax_values['tax_amount_currency'] += file_document_sign * float(amount)

    def _import_cii_invoice_add_allowances_charges_values(self, collected_values):
        tree = collected_values['tree']
        allowances = collected_values['allowances'] = []
        charges = collected_values['charges'] = []
        tax_total_values = collected_values['tax_total_values']

        for element in tree.iterfind('./{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeSettlement/{*}SpecifiedTradeAllowanceCharge'):
            reason = element.findtext('./{*}Reason')
            reason_code = element.findtext('./{*}ReasonCode')
            charge_indicator = element.findtext('./{*}ChargeIndicator/{*}Indicator')
            amount_str = element.findtext('./{*}ActualAmount')
            base_amount_str = element.findtext('./{*}BasisAmount')
            multiplier_factor_numeric_str = element.findtext('./{*}CalculationPercent')
            percentage_str = element.findtext('./{*}CategoryTradeTax/{*}RateApplicablePercent')

            if amount_str:
                amount = float(amount_str)
            else:
                amount = 0.0

            if not percentage_str:
                continue

            percentage = float(percentage_str)
            allowance_charge_values = {
                'amount': amount,
                'base_amount': float(base_amount_str) if base_amount_str else None,
                'reason': reason,
                'reason_code': reason_code,
                'multiplier_factor_numeric': float(multiplier_factor_numeric_str) if multiplier_factor_numeric_str else None,
                'tax_percentage': percentage,
                'charge_indicator': charge_indicator,
            }

            tax_category_tree = element.find('./{*}CategoryTradeTax')
            tax_values = self._import_cii_invoice_line_prepare_classified_tax_category_tax_values(collected_values, tax_category_tree)
            if tax_values:
                allowance_charge_values['taxes_values'] = tax_values
                global_tax_values = tax_total_values.get(tax_values['_tax_key'])
                global_tax_values['related_taxes_values'].append(tax_values)

            if charge_indicator.lower() == 'true':
                charges.append(allowance_charge_values)
            else:
                allowances.append(allowance_charge_values)

    def _import_cii_invoice_add_invoice_line_values(self, collected_values):
        lines_collected_values = collected_values['lines_collected_values'] = []
        tree = collected_values['tree']
        for line_tree in tree.iterfind("./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem"):
            line_collected_values = {
                **collected_values,
                'line_tree': line_tree,
                'to_write': {},
            }
            # allowance / charges of the line
            self._import_cii_invoice_line_add_allowance_charges_values(line_collected_values)

            # name / quantity / price_unit / discount / deferred_start_date / deferred_end_date
            self._import_cii_invoice_line_add_name(line_collected_values)
            self._import_cii_invoice_line_add_price_unit_quantity_discount(line_collected_values)
            self._import_cii_invoice_line_add_deferred_dates(line_collected_values)

            # product / product_uom / taxes
            self._import_cii_invoice_line_add_product_values(line_collected_values)
            self._import_cii_invoice_line_add_product_uom_values(line_collected_values)
            self._import_cii_invoice_line_add_account_values(line_collected_values)
            self._import_cii_invoice_line_add_taxes_values(line_collected_values)

            lines_collected_values.append(line_collected_values)

    def _import_cii_invoice_line_add_allowance_charges_values(self, collected_values):
        line_tree = collected_values['line_tree']
        allowances = collected_values['allowances'] = []
        charges = collected_values['charges'] = []
        for allowance_charge_elem in line_tree.iterfind('.//{*}SpecifiedTradeAllowanceCharge'):
            charge_indicator = allowance_charge_elem.findtext('.//{*}ChargeIndicator/{*}Indicator')
            amount_str = allowance_charge_elem.findtext('.//{*}ActualAmount')
            base_amount_str = allowance_charge_elem.findtext('.//{*}BasisAmount')
            reason = allowance_charge_elem.findtext('.//{*}Reason')
            reason_code = allowance_charge_elem.findtext('.//{*}ReasonCode')

            if amount_str:
                amount = float(amount_str)
            else:
                continue

            allowance_charge_values = {
                'amount': amount,
                'base_amount': float(base_amount_str) if base_amount_str else None,
                'reason': reason,
                'reason_code': reason_code,
            }
            if charge_indicator.lower() == 'true':
                charges.append(allowance_charge_values)
            else:
                allowances.append(allowance_charge_values)

        allowance_elem = line_tree.find('.//{*}GrossPriceProductTradePrice/{*}AppliedTradeAllowanceCharge')
        collected_values['price_allowance_values'] = {}
        if allowance_elem is not None:
            charge_indicator = allowance_elem.findtext('./{*}ChargeIndicator/{*}Indicator') or 'false'
            amount_str = allowance_elem.findtext('./{*}ActualAmount')
            base_amount_str = allowance_elem.findtext('./{*}BasisAmount')
            reason = allowance_elem.findtext('./{*}AllowanceChargeReason')
            reason_code = allowance_elem.findtext('./{*}AllowanceChargeReasonCode')

            if charge_indicator.lower() == 'true':
                charge_indicator_sign = 1
            else:
                charge_indicator_sign = -1

            collected_values['price_allowance_values'] = {
                'charge_indicator_sign': charge_indicator_sign,
                'amount': float(amount_str) if amount_str else None,
                'base_amount': float(base_amount_str) if base_amount_str else None,
                'reason': reason,
                'reason_code': reason_code,
            }

    def _import_cii_invoice_line_add_name(self, collected_values):
        line_tree = collected_values['line_tree']
        name = collected_values['name'] = (
            line_tree.findtext('.//{*}SpecifiedTradeProduct/{*}Name')
            or line_tree.findtext('.//{*}SpecifiedTradeProduct/{*}Description')
        )
        if name:
            collected_values['to_write']['name'] = name

    def _import_cii_invoice_line_add_price_unit_quantity_discount(self, collected_values):
        file_document_sign = collected_values['file_document_sign']
        line_tree = collected_values['line_tree']
        currency = collected_values['currency_values']['currency']

        line_total_amount_str = line_tree.findtext('.//{*}SpecifiedTradeSettlementLineMonetarySummation/{*}LineTotalAmount')
        price_amount_str = line_tree.findtext('.//{*}NetPriceProductTradePrice/{*}ChargeAmount')
        billed_quantity_str = line_tree.findtext('.//{*}BilledQuantity')
        base_quantity_str = (
            line_tree.findtext('.//{*}GrossPriceProductTradePrice/{*}BasisQuantity')
            or line_tree.findtext(".//{*}NetPriceProductTradePrice/{*}BasisQuantity")
        )

        line_total_amount = line_total_amount_str and float(line_total_amount_str) * file_document_sign
        price_amount = price_amount_str and float(price_amount_str)
        billed_quantity = billed_quantity_str and float(billed_quantity_str) * file_document_sign
        base_quantity = base_quantity_str and float(base_quantity_str)

        total_allowances = sum(allowance['amount'] for allowance in collected_values['allowances'])
        total_charges = sum(charge['amount'] for charge in collected_values['charges'])
        price_allowance_values = collected_values.get('price_allowance_values', {})
        price_allowance_base_amount = price_allowance_values.get('base_amount')
        price_allowance_amount = price_allowance_values.get('amount')
        if price_allowance_amount and (price_allowance_charge_indicator_sign := price_allowance_values.get('charge_indicator_sign')):
            price_allowance_amount *= price_allowance_charge_indicator_sign
        subtotal = (line_total_amount or 0.0) + total_allowances - total_charges

        # Price level.
        # Define at the product level the price for which quantity and how many discount you get
        # by buying it
        if price_amount:
            price_quantity = base_quantity or 1.0
            if price_allowance_base_amount:
                price_discount_amount = price_allowance_base_amount - price_amount
                price_subtotal = price_allowance_base_amount
            elif price_allowance_amount:
                price_discount_amount = -price_allowance_amount
                price_subtotal = price_amount
            else:
                price_discount_amount = 0.0
                price_subtotal = price_amount
        elif price_allowance_base_amount:
            price_subtotal = price_allowance_base_amount
            price_quantity = base_quantity or 1.0
            price_discount_amount = -(price_allowance_amount or 0.0)
        else:
            price_subtotal = 0.0
            price_quantity = 0.0
            price_discount_amount = 0.0

        # Line level.
        if (
            line_total_amount is not None
            and not billed_quantity
        ):
            price_unit = subtotal
            quantity = 1.0
            discount_amount = total_allowances

            # Combine with the price level. Suppose:
            # line_total_amount = 1000.0
            # price_subtotal = 1250.0
            # price_quantity = 5.0
            # price_discount_amount = 250.0
            # In that case, we want to compute:
            # price_unit = 250.0
            # quantity = 5.0
            # discount_amount = 250.0
            if not currency.is_zero(price_subtotal):
                quantity = subtotal * price_quantity / price_subtotal
                if quantity:
                    price_unit = (subtotal / quantity) + (price_discount_amount / price_quantity)
                else:
                    price_unit = price_amount
                discount_amount += price_discount_amount * quantity / price_quantity

        elif (
            line_total_amount
            and billed_quantity
        ):
            quantity = billed_quantity
            price_unit = subtotal / quantity
            discount_amount = total_allowances

            # Combine with the price level. Suppose:
            # line_total_amount = 1200.0
            # quantity = 6
            # price_subtotal = 1250.0
            # price_quantity = 5.0
            # price_discount_amount = 50.0
            # In that case, we want to compute:
            # price_unit = 250.0
            # quantity = 6.0
            # discount_amount = 300.0
            if not currency.is_zero(price_subtotal):
                price_unit = round((price_subtotal + price_discount_amount) / price_quantity, 2)
                discount_amount += price_discount_amount * quantity / price_quantity
        else:
            quantity = 0.0
            price_unit = 0.0
            discount_amount = total_allowances

            # Combine with the price level.
            if not currency.is_zero(price_subtotal):
                price_unit = price_subtotal / price_quantity
                quantity = price_quantity
                discount_amount += price_discount_amount

        # Extra charges.
        price_unit += total_charges / (quantity or 1.0)

        # Turn discount_amount to a percentage
        gross_subtotal = price_unit * quantity
        discount = (discount_amount * 100 / gross_subtotal) if gross_subtotal else 0.0

        to_write = collected_values['to_write']
        to_write['quantity'] = quantity
        to_write['price_unit'] = price_unit
        to_write['discount'] = discount

    def _import_cii_invoice_line_add_deferred_dates(self, collected_values):
        if not self.module_installed('account_accountant'):
            return

        line_tree = collected_values['line_tree']
        start_date_str = line_tree.findtext('.//{*}BillingSpecifiedPeriod/{*}StartDateTime/{*}DateTimeString')
        end_date_str = line_tree.findtext('.//{*}BillingSpecifiedPeriod/{*}EndDateTime/{*}DateTimeString')
        if start_date_str and end_date_str:
            to_write = collected_values['to_write']
            to_write['deferred_start_date'] = datetime.strptime(start_date_str.strip(), DEFAULT_CII_DATE_FORMAT)
            to_write['deferred_end_date'] = datetime.strptime(end_date_str.strip(), DEFAULT_CII_DATE_FORMAT)

    def _import_cii_invoice_line_add_product_values(self, collected_values):
        line_tree = collected_values['line_tree']
        partner = collected_values.get('customer_values', {}).get('customer')
        name = collected_values['to_write'].get('name')

        collected_values['product_values'] = {
            'default_code': line_tree.findtext('.//{*}SpecifiedTradeProduct/{*}SellerAssignedID'),
            'name': line_tree.findtext('.//{*}SpecifiedTradeProduct/{*}Name'),
            'barcode': line_tree.findtext('.//{*}SpecifiedTradeProduct/{*}GlobalID[@schemeID="0160"]'),
            'invoice_predictive': {
                'invoice': collected_values['invoice'],
                'name': name,
                'partner': partner or self.env['res.partner'],
            },
        }

    def _import_cii_invoice_line_add_product_uom_values(self, collected_values):
        line_tree = collected_values['line_tree']
        product_uom_values = collected_values['product_uom_values'] = {}

        quantity_node = line_tree.find('.//{*}SpecifiedLineTradeDelivery/{*}BilledQuantity')
        if quantity_node is not None:
            if uom_code := quantity_node.attrib.get('unitCode'):
                product_uom_values['uom_code'] = uom_code

    def _import_cii_invoice_line_add_account_values(self, collected_values):
        account_values = collected_values['account_values'] = {}
        partner = collected_values.get('customer_values', {}).get('customer')
        name = collected_values['to_write'].get('name')
        account_values['invoice_predictive'] = {
            'invoice': collected_values['invoice'],
            'name': name,
            'partner': partner or self.env['res.partner'],
        }

    def _import_cii_invoice_line_prepare_classified_tax_category_tax_values(self, collected_values, tax_category_tree):
        percentage = tax_category_tree.findtext('./{*}RateApplicablePercent')
        category_code = tax_category_tree.findtext('./{*}CategoryCode')

        if percentage is None or category_code is None:
            return

        percentage = float(percentage)
        tax_key = frozendict({
            'category_code': category_code,
            'percentage': percentage,
        })
        global_tax_values = collected_values['tax_total_values'].get(tax_key)
        if not global_tax_values:
            return

        tax_values = {
            'amount_type': global_tax_values['amount_type'],
            'type_tax_use': global_tax_values['type_tax_use'],
            'amount': global_tax_values['amount'],
            'ubl_cii_tax_category_code': global_tax_values['ubl_cii_tax_category_code'],
            '_tax_key': tax_key,
        }

        partner = collected_values.get('customer_values', {}).get('customer')
        if partner and (name := collected_values['to_write'].get('name')):
            tax_values['invoice_predictive'] = {
                'invoice': collected_values['invoice'],
                'name': name,
                'partner': partner,
            }
        return tax_values

    def _import_cii_invoice_line_prepare_charge_tax_values(self, collected_values, charge):
        if charge['reason_code'] != 'AEO':
            return

        odoo_document_type = collected_values['odoo_document_type']
        fixed_tax_amount = charge['amount'] / collected_values['to_write']['quantity']
        charge['attempt_tax_values'] = tax_values = {
            'name': charge['reason'],
            'amount_type': 'fixed',
            'type_tax_use': odoo_document_type,
            'amount': fixed_tax_amount,
            'tax_amount_currency': fixed_tax_amount,
        }

        partner = collected_values.get('customer_values', {}).get('customer')
        if partner and (name := collected_values['to_write'].get('name')):
            tax_values['invoice_predictive'] = {
                'invoice': collected_values['invoice'],
                'name': name,
                'partner': partner,
            }
        return tax_values

    def _import_cii_invoice_line_add_taxes_values(self, collected_values):
        line_tree = collected_values['line_tree']
        taxes_values = collected_values['taxes_values'] = []
        tax_total_values = collected_values['tax_total_values']

        # Percentage taxes.
        for tax_category_tree in line_tree.findall('./{*}SpecifiedLineTradeSettlement/{*}ApplicableTradeTax'):
            tax_values = self._import_cii_invoice_line_prepare_classified_tax_category_tax_values(collected_values, tax_category_tree)
            if tax_values:
                taxes_values.append(tax_values)
                global_tax_values = tax_total_values.get(tax_values['_tax_key'])
                global_tax_values['related_taxes_values'].append(tax_values)

        # Fixed taxes.
        for charge in collected_values['charges']:
            tax_values = self._import_cii_invoice_line_prepare_charge_tax_values(collected_values, charge)
            if tax_values:
                taxes_values.append(tax_values)

    def _import_cii_invoice_retrieve_products(self, collected_values):
        self._import_invoice_retrieve_products(collected_values)

    def _import_cii_invoice_retrieve_product_uoms(self, collected_values):
        self._import_invoice_retrieve_product_uoms(collected_values)

    def _import_cii_invoice_retrieve_accounts(self, collected_values):
        self._import_invoice_retrieve_accounts(collected_values)

    def _import_cii_invoice_retrieve_taxes(self, collected_values):
        self._import_invoice_retrieve_taxes(collected_values)

    def _import_cii_invoice_add_base_lines(self, collected_values):
        self._import_invoice_add_base_lines(collected_values)

    def _import_cii_invoice_write_collected_values(self, collected_values):
        self._import_invoice_write_collected_values(collected_values)

    def _import_cii_invoice_fix_taxes_amounts(self, collected_values):
        self._import_invoice_fix_taxes_amounts(collected_values)

    def _import_cii_invoice_fix_untaxed_amount(self, collected_values):
        if not collected_values['are_taxes_complete']:
            return

        tree = collected_values['tree']
        file_document_sign = collected_values['file_document_sign']
        currency = collected_values['currency_values']['currency']
        tax_exclusive_amount_str = tree.findtext('.//{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}TaxBasisTotalAmount')
        if not tax_exclusive_amount_str:
            return

        payable_rounding_amount_str = tree.findtext('.//{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}RoundingAmount')
        tax_exclusive_amount = file_document_sign * float(tax_exclusive_amount_str or 0.0)
        payable_rounding_amount = file_document_sign * float(payable_rounding_amount_str or 0.0)
        expected_untaxed_amount = tax_exclusive_amount + payable_rounding_amount
        invoice = collected_values['invoice']
        difference = currency.round(expected_untaxed_amount - invoice.amount_untaxed)
        for line_collected_values in collected_values['lines_collected_values']:
            for charge in line_collected_values['charges']:
                attempt_tax_values = charge.get('attempt_tax_values')
                if attempt_tax_values and attempt_tax_values.get('tax'):
                    difference -= charge['amount']
        if currency.is_zero(difference):
            return

        container = {'records': invoice}
        with (
            invoice._check_balanced(container),
            invoice._disable_discount_precision(),
            invoice._sync_dynamic_lines(container),
        ):
            invoice.invoice_line_ids = [
                Command.create({
                    'display_type': 'product',
                    'name': self.env._("Rounding"),
                    'quantity': 1,
                    'price_unit': difference,
                    'tax_ids': [],
                }),
            ]

    def _import_cii_invoice_post_processing(self, collected_values):
        self._import_invoice_post_processing(collected_values)

    def _cii_import_invoice(self, invoice, file_data, new=False):

        collected_values = self._import_cii_init_collected_values(invoice, file_data)

        self._import_cii_invoice_document_sign(collected_values)
        self._import_cii_invoice_update_move_type(collected_values)

        self._import_cii_invoice_add_partner_bank_values(collected_values)

        # invoice ref / invoice_origin / date / date_due / delivery_date / narration
        self._import_cii_invoice_add_ref(collected_values)
        self._import_cii_invoice_add_invoice_origin(collected_values)
        self._import_cii_invoice_add_issue_date(collected_values)
        self._import_cii_invoice_add_date_due(collected_values)
        self._import_cii_invoice_add_invoice_delivery_date(collected_values)
        self._import_cii_invoice_add_narration(collected_values)

        # customer
        self._import_cii_invoice_add_customer_values(collected_values)
        self._import_cii_retrieve_customer(collected_values)
        self._import_cii_create_missing_customer(collected_values)

        # currency
        self._import_cii_invoice_add_currency_code(collected_values)
        self._import_cii_invoice_add_currency(collected_values)

        # bank account
        self._import_cii_retrieve_partner_bank(collected_values)

        # Prepaid / rounding amounts / Tax total values.
        self._import_cii_invoice_add_prepaid_amount(collected_values)
        self._import_cii_invoice_add_tax_total_values(collected_values)

        # allowance / charge of the document
        self._import_cii_invoice_add_allowances_charges_values(collected_values)

        # Invoice lines values.
        self._import_cii_invoice_add_invoice_line_values(collected_values)
        self._import_cii_invoice_retrieve_products(collected_values)
        self._import_cii_invoice_retrieve_product_uoms(collected_values)
        self._import_cii_invoice_retrieve_accounts(collected_values)
        self._import_cii_invoice_retrieve_taxes(collected_values)
        self._import_cii_invoice_add_base_lines(collected_values)

        # End the invoice.
        self._import_cii_invoice_write_collected_values(collected_values)
        self._import_cii_invoice_fix_taxes_amounts(collected_values)
        self._import_cii_invoice_fix_untaxed_amount(collected_values)
        self._import_cii_invoice_post_processing(collected_values)
        return True
