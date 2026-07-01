from odoo import models, Command
from odoo.tools import float_repr, formatLang, frozendict, html2plaintext
from datetime import datetime

DEFAULT_CII_DATE_FORMAT = '%Y%m%d'


class AccountEdiCii(models.AbstractModel):
    _name = "account.edi.cii"
    _inherit = 'account.edi.common'
    _description = "Base helpers for CII"

    def _cii_format_date(self, dt):
        """ Format the date in the CII standard. """
        dt = dt or datetime.now()
        return dt.strftime(DEFAULT_CII_DATE_FORMAT)

    def _cii_format_monetary(self, number, decimal_places=2):
        """ CII requires the monetary values to be rounded to 2 decimal values. """
        return float_repr(number, decimal_places)

    # -------------------------------------------------------------------------
    # NEW EXPORT : helpers
    # -------------------------------------------------------------------------

    def _cii_add_values_currency(self, vals, currency_id, company_currency_id):
        vals['currency_id'] = currency_id
        vals['company_currency_id'] = company_currency_id

    def _cii_add_values_supplier(self, vals, supplier):
        vals['supplier'] = supplier

    def _cii_add_values_customer(self, vals, customer):
        vals['customer'] = customer

    def _cii_add_values_partner_shipping(self, vals, partner_shipping):
        vals['partner_shipping'] = partner_shipping

    def _cii_add_values_use_company_currency(self, vals, use_company_currency):
        vals['use_company_currency'] = use_company_currency

    def _cii_add_values_fixed_taxes_as_allowance_charges(self, vals, fixed_taxes_as_allowance_charges):
        vals['fixed_taxes_as_allowance_charges'] = fixed_taxes_as_allowance_charges

    def _cii_add_values_intracom_delivery(self, vals, intracom_delivery):
        vals['intracom_delivery'] = intracom_delivery

    def _cii_add_values_buyer_reference(self, vals, buyer_reference):
        vals['buyer_reference'] = buyer_reference

    def _cii_add_values_seller_and_buyer_siret(self, vals, seller_siret, buyer_siret):
        vals['seller_specified_legal_organization'] = seller_siret
        vals['buyer_specified_legal_organization'] = buyer_siret

    def _cii_add_values_seller_and_buyer_vat(self, vals, seller_vat, buyer_vat):
        vals['seller_tax_registration'] = seller_vat
        vals['buyer_tax_registration'] = buyer_vat

    def _cii_add_values_purchase_order_reference(self, vals, purchase_order_reference):
        vals['purchase_order_reference'] = purchase_order_reference

    def _cii_add_values_contract_reference(self, vals, contract_reference):
        vals['contract_reference'] = contract_reference

    def _cii_add_values_delivery_date(self, vals, delivery_date):
        vals['delivery_date'] = delivery_date

    def _cii_add_values_gln(self, vals, gln):
        vals['gln'] = gln

    def _cii_add_values_payment_means_code(self, vals, payment_means_code):
        vals['payment_means_code'] = payment_means_code

    def _cii_add_values_billing_dates(self, vals, start_date, end_date):
        vals['billing_start_date'] = start_date
        vals['billing_end_date'] = end_date

    def _cii_add_values_invoice_base_lines(self, vals):
        invoice = vals['invoice']
        vals['base_lines'], _tax_lines = invoice._get_rounded_base_and_tax_lines()

    def _cii_add_values_invoice_currency(self, vals):
        vals['currency_suffix'] = '' if vals['use_company_currency'] else '_currency'
        currency = vals['company_currency_id'] if vals['use_company_currency'] else vals['currency_id']
        vals['currency_dp'] = self._get_currency_decimal_places(currency)
        vals['currency_name'] = currency.name

    def _cii_add_values_invoice_tax_grouping_function(self, vals):
        # Add the grouping function for the tax totals
        customer = vals['customer']
        supplier = vals['supplier']

        def tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            if not tax:
                return None
            grouping_key = {
                **self._get_tax_unece_codes(customer, supplier, tax),
                # **self._get_tax_exemption_reason(customer, supplier, tax),
                'amount': tax.amount,
                'amount_type': tax.amount_type,
            }
            # If the tax is fixed, we want to have one group per tax
            # s.t. when the invoice is imported, we can try to guess the fixed taxes
            if tax and tax.amount_type == 'fixed':
                grouping_key['tax_name'] = tax.name
            return grouping_key

        vals['tax_grouping_function'] = tax_grouping_function

    def _cii_setup_base_lines(self, vals):
        """
        Prepares the base_lines:
            * Ensures the price_unit s always positive
            * Turns fixed taxes into allowance or charge and updates the totals accordingly
            * Retrieves the one main tax (in factur-x, only one tax per line, excepted the fixed ones)
            * Retrieves the cash rounding lines
            * Retrieves the early payment discount lines

        :param vals: Some custom data
        """
        base_lines = vals['base_lines']

        for base_line in base_lines:

            self._cii_turn_price_unit_positive(base_line)

            base_line['allowance_charge_vals_list'] = allowance_charge_vals_list = []
            base_line['main_tax'] = main_tax = []
            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']
            for tax_data in taxes_data:
                tax = tax_data['tax']
                # Fixed taxes as allowance and charges
                if tax and tax.amount_type == 'fixed':
                    allowance_charge_vals_list.append({'tax_data': tax_data})
                    for currency_suffix in ['', '_currency']:
                        tax_details[f'raw_total_excluded{currency_suffix}'] += tax_data[f'raw_tax_amount{currency_suffix}']
                        tax_details[f'total_excluded{currency_suffix}'] += tax_data[f'tax_amount{currency_suffix}']
                elif tax:
                    main_tax.append(tax_data)

        self._cii_extract_cash_rounding_lines(vals)
        self._cii_extract_early_pay_discount_lines(vals)

    def _cii_turn_price_unit_positive(self, base_line):
        """
        Turn the unit_price positive and the quantity negative of the base_line when negative unit_price.
        [BR-27]-The Item net price (BT-146) shall NOT be negative.
        [BR-28]-The Item gross price (BT-148) shall NOT be negative.

        :param base_line: The base line of the item.
        """
        if base_line['price_unit'] < 0.0:
            base_line['quantity'] *= -1
            base_line['price_unit'] *= -1

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

    def _cii_add_values_invoice_tax_details(self, vals):
        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], vals['tax_grouping_function'])
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        vals['tax_details'] = {}
        for grouping_key, values in aggregated_tax_details.items():
            if grouping_key and grouping_key['amount_type'] != 'fixed':
                vals['tax_details'][grouping_key] = values

            if grouping_key and grouping_key['tax_category_code'] == 'K':
                vals['intracom_delivery'] = True

    def _cii_add_values_total_amount(self, vals):
        for currency_suffix in ['', '_currency']:
            # Total base amount
            vals[f'line_total_amount{currency_suffix}'] = sum(
                tax_data[f'base_amount{currency_suffix}']
                for _grouping_key, tax_data in vals['tax_details'].items()
            )
            # Total tax amount
            vals[f'tax_total_amount{currency_suffix}'] = sum(
                tax_data[f'tax_amount{currency_suffix}']
                for _grouping_key, tax_data in vals['tax_details'].items()
            )
            # Cash rounding for 'add_invoice_line' cash rounding strategy
            vals[f'cash_rounding_base_amount{currency_suffix}'] = sum(
                base_line['tax_details'][f'total_excluded{currency_suffix}']
                for base_line in vals.setdefault('cash_rounding_base_lines', [])
            )
            # Total grand amount
            vals[f'grand_total_amount{currency_suffix}'] = (
                    vals[f'line_total_amount{currency_suffix}'] +
                    vals[f'tax_total_amount{currency_suffix}'] +
                    vals[f'cash_rounding_base_amount{currency_suffix}']
            )
            # Prepaid amount
            vals[f'total_prepaid_amount{currency_suffix}'] = (
                vals[f'grand_total_amount{currency_suffix}'] -
                vals['invoice'].amount_residual
            )
            # Due payable amount
            vals[f'due_payable_amount{currency_suffix}'] = (
                vals[f'grand_total_amount{currency_suffix}'] -
                vals[f'total_prepaid_amount{currency_suffix}']
            )

    # ----------------------------------------------------------------------------
    # EXPORT : build nodes
    # ----------------------------------------------------------------------------

    def _cii_add_exchanged_document_context(self, vals):
        vals['document_node']['rsm:ExchangedDocumentContext'] = {
            'ram:GuidelineSpecifiedDocumentContextParameter': {
                'ram:ID': {'_text': "urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended"},
            }
        }

    def _cii_add_date_time_string_node(self, vals):
        vals['date_time_node']['udt:DateTimeString'] = {
                '_text': self._cii_format_date(vals['date']),
                'format': "102",
        }

    def _cii_add_exchanged_document_node(self, vals):
        node = vals['document_node']['rsm:ExchangedDocument'] = {}
        sub_vals = {
            **vals,
            'exchanged_document_node': node,
        }
        self._cii_add_exchanged_document_id_node(sub_vals)
        self._cii_add_exchanged_document_type_code_node(sub_vals)
        self._cii_add_exchanged_document_issue_date_time_node(sub_vals)
        self._cii_add_exchanged_document_included_note_node(sub_vals)

    def _cii_add_exchanged_document_id_node(self, vals):
        invoice = vals['invoice']
        vals['exchanged_document_node']['ram:ID'] = {
            '_text': invoice.name,
        }

    def _cii_add_exchanged_document_type_code_node(self, vals):
        invoice = vals['invoice']
        vals['exchanged_document_node']['ram:TypeCode'] = {
            '_text': '380' if invoice.move_type == 'out_invoice' else '381',
        }

    def _cii_add_exchanged_document_issue_date_time_node(self, vals):
        invoice = vals['invoice']
        node = vals['exchanged_document_node']['ram:IssueDateTime'] = {}
        sub_vals = {
            **vals,
            'date_time_node': node,
            'date': invoice.invoice_date,
        }
        self._cii_add_date_time_string_node(sub_vals)

    def _cii_add_exchanged_document_included_note_node(self, vals):
        invoice = vals['invoice']
        vals['exchanged_document_node']['ram:IncludedNote'] = {
            'ram:Content': {'_text': html2plaintext(invoice.narration) if invoice.narration else ""},
        }

    def _cii_add_line_item_nodes(self, vals):
        node = vals['supply_chain_node']['ram:IncludedSupplyChainTradeLineItem'] = []
        for idx, base_line in enumerate(vals['base_lines']):
            line_vals = {
                **vals,
                'line_idx': idx + 1,
                'base_line': base_line,
                'line_node': {},
            }
            self._cii_add_line_item_node(line_vals)
            node.append(line_vals['line_node'])

    def _cii_add_line_item_node(self, vals):
        self._cii_add_invoice_line_vals(vals)

        self._cii_add_line_id_node(vals)
        self._cii_add_line_product_node(vals)
        self._cii_add_specified_line_trade_agreement_node(vals)
        self._cii_add_specified_line_trade_delivery_node(vals)
        self._add_line_trade_settlement_node(vals)

    def _cii_add_invoice_line_vals(self, vals):
        base_line = vals['base_line']
        move_line = base_line['record']
        company_currency = vals['company_currency_id']
        invoice_currency = base_line['currency_id']
        tax = base_line['main_tax'][0]['tax'] if base_line['main_tax'] else None

        gross_charge_amount_currency = invoice_currency.round(base_line['price_unit'])
        if tax and tax.price_include:
            gross_charge_amount_currency = invoice_currency.round(base_line['price_unit'] / (1 + (tax.amount / 100)))
            for allowance_charge in base_line['allowance_charge_vals_list']:
                gross_charge_amount_currency -= invoice_currency.round(allowance_charge['tax_data']['tax_amount_currency'] / base_line['quantity'])
        gross_charge_amount = company_currency.round(gross_charge_amount_currency / base_line['rate'])

        discount_data = None
        if base_line.get('discount'):
            discount_percentage = base_line['discount'] / 100.0
            discount_data = {
                'charge_indicator': 'false',
                'actual_amount_currency': invoice_currency.round(gross_charge_amount_currency * discount_percentage),
                'actual_amount': company_currency.round(gross_charge_amount * discount_percentage),
            }

        net_charge_amount_currency = gross_charge_amount_currency - (discount_data or {}).get('actual_amount_currency', 0.0)
        net_charge_amount = gross_charge_amount - (discount_data or {}).get('actual_amount', 0.0)

        vals.update({
            'gross_charge_amount_currency': gross_charge_amount_currency,
            'gross_charge_amount': gross_charge_amount,
            'discount': discount_data,
            'net_charge_amount_currency': net_charge_amount_currency,
            'net_charge_amount': net_charge_amount,
            'deferred_start_date': move_line.deferred_start_date,
            'deferred_end_date': move_line.deferred_end_date,
        })

    def _cii_add_line_id_node(self, vals):
        vals['line_node']['ram:AssociatedDocumentLineDocument'] = {
            'ram:LineID': {'_text': vals['line_idx']},
        }

    def _cii_add_line_product_node(self, vals):
        node = vals['line_node']['ram:SpecifiedTradeProduct'] = {}
        sub_vals = {
            **vals,
            'product': vals['base_line']['product_id'],
            'product_name': vals['base_line']['name'],
            'product_node': node,
        }
        self._cii_add_line_product_global_id_node(sub_vals)
        self._cii_add_line_product_seller_assigned_id_node(sub_vals)
        self._cii_add_line_product_name_node(sub_vals)
        self._cii_add_line_product_description_node(sub_vals)

    def _cii_add_line_product_global_id_node(self, vals):
        if vals['product'].barcode:
            vals['product_node']['ram:GlobalID'] = {
                '_text': vals['product'].barcode,
                'schemeID': "0160",
            }

    def _cii_add_line_product_seller_assigned_id_node(self, vals):
        if vals['product'].default_code:
            vals['product_node']['ram:SellerAssignedID'] = {
                '_text': vals['product'].default_code,
            }

    def _cii_add_line_product_name_node(self, vals):
        vals['product_node']['ram:Name'] = {
            '_text': vals['product_name'],
        }

    def _cii_add_line_product_description_node(self, vals):
        if vals['product'].description:
            vals['product_node']['ram:Description'] = {
                '_text': html2plaintext(vals['product'].description),
            }

    def _cii_add_specified_line_trade_agreement_node(self, vals):
        node = vals['line_node']['ram:SpecifiedLineTradeAgreement'] = {}
        sub_vals = {
            **vals,
            'line_trade_agreement_node': node,
        }
        self._cii_add_gross_price_product_node(sub_vals)
        self._cii_add_net_price_product_node(sub_vals)

    def _cii_add_gross_price_product_node(self, vals):
        node = vals['line_trade_agreement_node']['ram:GrossPriceProductTradePrice'] = {}
        currency_suffix = vals['currency_suffix']
        sub_vals = {
            **vals,
            'trade_price_node': node,
            'charge_amount': vals[f'gross_charge_amount{currency_suffix}'],
        }
        self._cii_add_charge_amount_node(sub_vals)
        self._cii_add_applied_trade_allowance_charge_node(sub_vals)

    def _cii_add_charge_amount_node(self, vals):
        vals['trade_price_node']['ram:ChargeAmount'] = {
            '_text': self._cii_format_monetary(vals['charge_amount'], 2),
        }

    def _cii_add_applied_trade_allowance_charge_node(self, vals):
        if vals['discount']:
            node = vals['trade_price_node']['ram:AppliedTradeAllowanceCharge'] = {}
            currency_suffix = vals['currency_suffix']
            sub_vals = {
                **vals,
                'indicator': vals['discount']['charge_indicator'],
                'actual_amount': vals['discount'][f'actual_amount{currency_suffix}'],
                'allowance_charge_node': node,
            }
            self._cii_add_allowance_charge_charge_indicator_node(sub_vals)
            self._cii_add_allowance_charge_actual_amount_node(sub_vals)

    def _cii_add_allowance_charge_charge_indicator_node(self, vals):
        vals['allowance_charge_node']['ram:ChargeIndicator'] = {
            'udt:Indicator': {
                '_text': vals['indicator'],
            },
        }

    def _cii_add_allowance_charge_actual_amount_node(self, vals):
        vals['allowance_charge_node']['ram:ActualAmount'] = {
            '_text': self._cii_format_monetary(vals['actual_amount'], 2),
        }

    def _cii_add_net_price_product_node(self, vals):
        node = vals['line_trade_agreement_node']['ram:NetPriceProductTradePrice'] = {}
        currency_suffix = vals['currency_suffix']
        sub_vals = {
            **vals,
            'trade_price_node': node,
            'charge_amount': vals[f'net_charge_amount{currency_suffix}'],
        }
        self._cii_add_charge_amount_node(sub_vals)

    def _cii_add_specified_line_trade_delivery_node(self, vals):
        vals['line_node']['ram:SpecifiedLineTradeDelivery'] = {
            'ram:BilledQuantity': {
                'unitCode': self._get_uom_unece_code(vals['base_line']['product_uom_id']),
                '_text': vals['base_line']['quantity'],
            },
        }

    def _add_line_trade_settlement_node(self, vals):
        node = vals['line_node']['ram:SpecifiedLineTradeSettlement'] = {}
        sub_vals = {
            **vals,
            'line_trade_settlement_node': node,
        }
        self._cii_add_line_applicable_trade_tax_node(sub_vals)
        self._cii_add_line_billing_specified_period_node(sub_vals)
        self._cii_add_line_specified_trade_allowance_charge_node(sub_vals)
        self._cii_add_line_monetary_summation_node(sub_vals)

    def _cii_add_line_applicable_trade_tax_node(self, vals):
        tax_data = vals['base_line']['main_tax'][0] if vals['base_line']['main_tax'] else None
        if tax_data:
            node = vals['line_trade_settlement_node']['ram:ApplicableTradeTax'] = {}
            sub_vals = {
                **vals,
                'trade_tax_node': node,
                'tax': tax_data['tax'],
            }
            self._cii_add_tax_type_code(sub_vals)
            self._cii_add_tax_category_code(sub_vals)
            self._cii_add_tax_rate_applicable_percent(sub_vals)

    def _cii_add_tax_type_code(self, vals):
        vals['trade_tax_node']['ram:TypeCode'] = {
            '_text': "VAT",
        }

    def _cii_add_tax_category_code(self, vals):
        vals['trade_tax_node']['ram:CategoryCode'] = {
            '_text': self._get_tax_category_code(vals['customer'].commercial_partner_id, vals['supplier'], vals['tax']),
        }

    def _cii_add_tax_rate_applicable_percent(self, vals):
        vals['trade_tax_node']['ram:RateApplicablePercent'] = {
            '_text': vals['tax'].amount,
        }

    def _cii_add_line_billing_specified_period_node(self, vals):
        node = vals['line_trade_settlement_node']['ram:BillingSpecifiedPeriod'] = {}
        sub_vals = {
            **vals,
            'billing_node': node,
            'billing_start_date': vals['deferred_start_date'],
            'billing_end_date': vals['deferred_end_date'],
        }
        self._cii_add_billing_specified_start_date_time(sub_vals)
        self._cii_add_billing_specified_end_date_time(sub_vals)

    def _cii_add_billing_specified_start_date_time(self, vals):
        if vals['billing_start_date']:
            node = vals['billing_node']['ram:StartDateTime'] = {}
            sub_vals = {
                **vals,
                'date_time_node': node,
                'date': vals['billing_start_date'],
            }
            self._cii_add_date_time_string_node(sub_vals)

    def _cii_add_billing_specified_end_date_time(self, vals):
        if vals['billing_end_date']:
            node = vals['billing_node']['ram:EndDateTime'] = {}
            sub_vals = {
                **vals,
                'date_time_node': node,
                'date': vals['billing_end_date'],
            }
            self._cii_add_date_time_string_node(sub_vals)

    def _cii_add_line_specified_trade_allowance_charge_node(self, vals):
        node = vals['line_trade_settlement_node']['ram:SpecifiedTradeAllowanceCharge'] = []
        base_line = vals['base_line']
        currency_suffix = vals['currency_suffix']
        for allowance_charge in base_line['allowance_charge_vals_list']:
            tax_data = allowance_charge['tax_data']
            sub_vals = {
                **vals,
                'allowance_charge_node': {},
                'tax': tax_data['tax'],
                'actual_amount': tax_data[f'tax_amount{currency_suffix}'],
                'indicator': 'true',
            }
            self._cii_add_allowance_charge_charge_indicator_node(sub_vals)
            self._cii_add_allowance_charge_actual_amount_node(sub_vals)
            self._cii_add_allowance_charge_reason_code_node(sub_vals)
            self._cii_add_allowance_charge_reason_node(sub_vals)
            node.append(sub_vals['allowance_charge_node'])

    def _cii_add_allowance_charge_reason_code_node(self, vals):
        vals['allowance_charge_node']['ram:ReasonCode'] = {
            '_text': "AEO",
        }

    def _cii_add_allowance_charge_reason_node(self, vals):
        vals['allowance_charge_node']['ram:Reason'] = {
            '_text': vals['tax'].name,
        }

    def _cii_add_line_monetary_summation_node(self, vals):
        node = vals['line_trade_settlement_node']['ram:SpecifiedTradeSettlementLineMonetarySummation'] = {}
        currency_suffix = vals['currency_suffix']
        sub_vals = {
            **vals,
            'monetary_summation_node': node,
            'line_total_amount': vals['base_line']['tax_details'][f'total_excluded{currency_suffix}'],
        }
        self._cii_add_line_monetary_summation_total_amount_node(sub_vals)

    def _cii_add_line_monetary_summation_total_amount_node(self, vals):
        vals['monetary_summation_node']['ram:LineTotalAmount'] = {
            '_text': self._cii_format_monetary(vals['line_total_amount'], 2),
        }

    def _cii_add_applicable_header_trade_agreement_node(self, vals):
        node = vals['supply_chain_node']['ram:ApplicableHeaderTradeAgreement'] = {}
        sub_vals = {
            **vals,
            'trade_agreement_node': node,
        }
        self._cii_add_buyer_reference_node(sub_vals)
        self._cii_add_seller_trade_party_node(sub_vals)
        self._cii_add_buyer_trade_party_node(sub_vals)
        self._cii_add_order_reference_node(sub_vals)
        self._cii_add_contract_reference_node(sub_vals)

    def _cii_add_buyer_reference_node(self, vals):
        vals['trade_agreement_node']['ram:BuyerReference'] = {
            '_text': vals['buyer_reference'],
        }

    def _cii_add_seller_trade_party_node(self, vals):
        node = vals['trade_agreement_node']['ram:SellerTradeParty'] = {}
        sub_vals = {
            **vals,
            'trade_party_node': node,
            'partner': vals['supplier'],
            'partner_specified_legal_organization': vals['seller_specified_legal_organization'],
            'partner_tax_registration': vals['seller_tax_registration'],
            'peppol_eas': vals['supplier'].peppol_eas,
            'peppol_endpoint': vals['supplier'].peppol_endpoint,
            'gln': False,
        }
        self._cii_add_trade_party_node(sub_vals)
        self._cii_add_peppol_endpoint_node(sub_vals)
        self._cii_add_tax_registration_node(sub_vals)

    def _cii_add_buyer_trade_party_node(self, vals):
        node = vals['trade_agreement_node']['ram:BuyerTradeParty'] = {}
        sub_vals = {
            **vals,
            'trade_party_node': node,
            'partner': vals['customer'],
            'partner_specified_legal_organization': vals['buyer_specified_legal_organization'],
            'partner_tax_registration': vals['buyer_tax_registration'],
            'peppol_eas': vals['customer'].peppol_eas,
            'peppol_endpoint': vals['customer'].peppol_endpoint,
            'gln': False,
        }
        self._cii_add_trade_party_node(sub_vals)
        self._cii_add_peppol_endpoint_node(sub_vals)
        self._cii_add_tax_registration_node(sub_vals)

    def _cii_add_trade_party_node(self, vals):
        if vals['gln']:
            self._cii_add_gln_node(vals)
        self._cii_add_partner_name_node(vals)
        self._cii_add_partner_specified_legal_organisation_node(vals)
        self._cii_add_partner_defined_trade_contact_node(vals)
        self._cii_add_partner_postal_trade_address_node(vals)

    def _cii_add_gln_node(self, vals):
        vals['trade_party_node']['ram:ID'] = {
            'schemeID': '0088',
            '_text': vals['gln'],
        }

    def _cii_add_partner_name_node(self, vals):
        vals['trade_party_node']['ram:Name'] = {
            '_text': vals['partner'].name,
        }

    def _cii_add_partner_specified_legal_organisation_node(self, vals):
        if vals['partner_specified_legal_organization']:
            vals['trade_party_node']['ram:SpecifiedLegalOrganization'] = {
                'ram:ID': {
                    '_text': vals['partner_specified_legal_organization'],
                    'schemeID': '0002',
                }
            }

    def _cii_add_partner_defined_trade_contact_node(self, vals):
        node = vals['trade_party_node']['ram:DefinedTradeContact'] = {}
        sub_vals = {
            **vals,
            'trade_contact_node': node,
            'phone': vals['partner'].phone or vals['partner'].mobile,
            'email': vals['partner'].email,
        }
        self._cii_add_person_name_node(sub_vals)
        self._cii_add_telephone_universal_communication_node(sub_vals)
        self._cii_add_email_uri_universal_communication_node(sub_vals)

    def _cii_add_person_name_node(self, vals):
        vals['trade_contact_node']['ram:PersonName'] = {
            '_text': vals['partner'].name,
        }

    def _cii_add_telephone_universal_communication_node(self, vals):
        if vals['phone']:
            vals['trade_contact_node']['ram:TelephoneUniversalCommunication'] = {
                'ram:CompleteNumber': {'_text': vals['phone']},
            }

    def _cii_add_email_uri_universal_communication_node(self, vals):
        if vals['email']:
            vals['trade_contact_node']['ram:EmailURIUniversalCommunication'] = {
                'ram:URIID': {'_text': vals['email']},
            }

    def _cii_add_partner_postal_trade_address_node(self, vals):
        node = vals['trade_party_node']['ram:PostalTradeAddress'] = {}
        sub_vals = {
            **vals,
            'postal_address_node': node,
        }
        self._cii_add_address_post_code_node(sub_vals)
        self._cii_add_address_line_one_node(sub_vals)
        self._cii_add_address_line_two(sub_vals)
        self._cii_add_address_city_name(sub_vals)
        self._cii_add_address_country_id(sub_vals)

    def _cii_add_address_post_code_node(self, vals):
        vals['postal_address_node']['ram:PostcodeCode'] = {
            '_text': vals['partner'].zip,
        }

    def _cii_add_address_line_one_node(self, vals):
        vals['postal_address_node']['ram:LineOne'] = {
            '_text': vals['partner'].street,
        }

    def _cii_add_address_line_two(self, vals):
        if vals['partner'].street2:
            vals['postal_address_node']['ram:LineTwo'] = {
                '_text': vals['partner'].street2,
            }

    def _cii_add_address_city_name(self, vals):
        vals['postal_address_node']['ram:CityName'] = {
            '_text': vals['partner'].city,
        }

    def _cii_add_address_country_id(self, vals):
        vals['postal_address_node']['ram:CountryID'] = {
            '_text': vals['partner'].country_id.code,
        }

    def _cii_add_peppol_endpoint_node(self, vals):
        if vals['peppol_eas'] and vals['peppol_endpoint']:
            vals['trade_party_node']['ram:URIUniversalCommunication'] = {
                'ram:URIID': {
                    'schemeID': vals['peppol_eas'],
                    '_text': vals['peppol_endpoint'],
                },
            }

    def _cii_add_tax_registration_node(self, vals):
        if vals['partner_tax_registration']:
            vals['trade_party_node']['ram:SpecifiedTaxRegistration'] = {
                'ram:ID': {
                    '_text': vals['partner_tax_registration'],
                    'schemeID': 'VA',
                },
            }

    def _cii_add_order_reference_node(self, vals):
        vals['trade_agreement_node']['ram:BuyerOrderReferencedDocument'] = {
            'ram:IssuerAssignedID': {'_text': vals['purchase_order_reference']},
        }

    def _cii_add_contract_reference_node(self, vals):
        vals['trade_agreement_node']['ram:ContractReferencedDocument'] = {
            'ram:IssuerAssignedID': {'_text': vals['contract_reference']},
        }

    def _cii_add_trade_delivery_node(self, vals):
        node = vals['supply_chain_node']['ram:ApplicableHeaderTradeDelivery'] = {}
        sub_vals = {
            **vals,
            'trade_delivery_node': node,
        }
        self._cii_add_shipping_trade_party_node(sub_vals)
        self._cii_add_delivery_date_node(sub_vals)

    def _cii_add_shipping_trade_party_node(self, vals):
        node = vals['trade_delivery_node']['ram:ShipToTradeParty'] = {}
        sub_vals = {
            **vals,
            'trade_party_node': node,
            'partner': vals['partner_shipping'],
            'partner_specified_legal_organization': None,
            'gln': vals['gln'],
        }
        self._cii_add_trade_party_node(sub_vals)

    def _cii_add_delivery_date_node(self, vals):
        if vals['delivery_date']:
            node = vals['trade_delivery_node']\
                .setdefault('ram:ActualDeliverySupplyChainEvent', {})\
                .setdefault('ram:OccurrenceDateTime', {})
            sub_vals = {
                **vals,
                'date_time_node': node,
                'date': vals['delivery_date'],
            }
            self._cii_add_date_time_string_node(sub_vals)

    def _cii_add_applicable_header_trade_settlement_node(self, vals):
        node = vals['supply_chain_node']['ram:ApplicableHeaderTradeSettlement'] = {}
        sub_vals = {
            **vals,
            'trade_settlement_node': node,
        }
        self._cii_add_payment_reference_node(sub_vals)
        self._cii_add_invoice_currency_code_node(sub_vals)
        self._cii_add_specified_trade_settlement_payment_means_node(sub_vals)
        self._cii_add_tax_details_node(sub_vals)
        self._cii_add_billing_period_node(sub_vals)
        self._cii_add_specified_trade_payment_terms_node(sub_vals)
        self._cii_add_specified_trade_monetary_summation_node(sub_vals)

    def _cii_add_payment_reference_node(self, vals):
        vals['trade_settlement_node']['ram:PaymentReference'] = {
            '_text': vals['invoice'].payment_reference,
        }

    def _cii_add_invoice_currency_code_node(self, vals):
        vals['trade_settlement_node']['ram:InvoiceCurrencyCode'] = {
            '_text': vals['currency_id'].name,
        }

    def _cii_add_specified_trade_settlement_payment_means_node(self, vals):
        if vals['invoice'].partner_bank_id.sanitized_acc_number:
            node = vals['trade_settlement_node']['ram:SpecifiedTradeSettlementPaymentMeans'] = {}
            sub_vals = {
                **vals,
                'payment_means_node': node,
            }
            self._cii_add_payment_type_code_node(sub_vals)
            self._cii_add_payee_party_creditor_financial_account_node(sub_vals)

    def _cii_add_payment_type_code_node(self, vals):
        vals['payment_means_node']['ram:TypeCode'] = {
            '_text': vals['payment_means_code'],
        }

    def _cii_add_payee_party_creditor_financial_account_node(self, vals):
        invoice = vals['invoice']
        node = vals['payment_means_node']['ram:PayeePartyCreditorFinancialAccount'] = {}
        sub_vals = {
            **vals,
            'creditor_account_node': node,
            'account_number': invoice.partner_bank_id.sanitized_acc_number,
        }
        if invoice.partner_bank_id.acc_type == 'iban':
            self._cii_add_iban_id_node(sub_vals)
        else:
            self._cii_add_proprietary_id_node(sub_vals)

    def _cii_add_iban_id_node(self, vals):
        vals['creditor_account_node']['ram:IBANID'] = {
            '_text': vals['account_number'],
        }

    def _cii_add_proprietary_id_node(self, vals):
        vals['creditor_account_node']['ram:ProprietaryID'] = {
            '_text': vals['account_number'],
        }

    def _cii_add_tax_details_node(self, vals):
        node = vals['trade_settlement_node']['ram:ApplicableTradeTax'] = []
        for grouping_key, tax_details in vals['tax_details'].items():
            sub_vals = {
                **vals,
                **grouping_key,
                **tax_details,
                'tax_node': {},
            }
            self._cii_add_calculated_amount_node(sub_vals)
            self._cii_add_type_code_node(sub_vals)
            self._cii_add_exemption_reason_node(sub_vals)
            self._cii_add_basis_amount_node(sub_vals)
            self._cii_add_category_code_node(sub_vals)
            self._cii_add_exemption_reason_code_node(sub_vals)
            self._cii_add_due_date_type_code_node(sub_vals)
            self._cii_add_rate_applicable_percent_node(sub_vals)
            node.append(sub_vals['tax_node'])

    def _cii_add_calculated_amount_node(self, vals):
        invoice = vals['invoice']
        currency_suffix = vals['currency_suffix']
        amount_currency = vals[f'tax_amount{currency_suffix}']
        vals['tax_node']['ram:CalculatedAmount'] = {
            '_text': self._cii_format_monetary(amount_currency if not invoice.currency_id.is_zero(amount_currency) else 0.0, 2),
        }

    def _cii_add_type_code_node(self, vals):
        vals['tax_node']['ram:TypeCode'] = {
            '_text': "VAT",
        }

    def _cii_add_exemption_reason_node(self, vals):
        vals['tax_node']['ram:ExemptionReason'] = {
            '_text': vals['tax_exemption_reason'],
        }

    def _cii_add_basis_amount_node(self, vals):
        currency_suffix = vals['currency_suffix']
        vals['tax_node']['ram:BasisAmount'] = {
            '_text': self._cii_format_monetary(vals[f'base_amount{currency_suffix}'], 2),
        }

    def _cii_add_category_code_node(self, vals):
        vals['tax_node']['ram:CategoryCode'] = {
            '_text': vals['tax_category_code'],
        }

    def _cii_add_exemption_reason_code_node(self, vals):
        vals['tax_node']['ram:ExemptionReasonCode'] = {
            '_text': vals['tax_exemption_reason_code'],
        }

    def _cii_add_due_date_type_code_node(self, vals):
        vals['tax_node']['ram:DueDateTypeCode'] = {
            '_text': 5,
        }

    def _cii_add_rate_applicable_percent_node(self, vals):
        if vals['amount_type'] == 'percent':
            vals['tax_node']['ram:RateApplicablePercent'] = {
                '_text': vals['amount'],
            }

    def _cii_add_billing_period_node(self, vals):
        node = vals['trade_settlement_node']['ram:BillingSpecifiedPeriod'] = {}
        sub_vals = {
            **vals,
            'billing_node': node,
        }
        self._cii_add_billing_specified_start_date_time(sub_vals)
        self._cii_add_billing_specified_end_date_time(sub_vals)

    def _cii_add_specified_trade_payment_terms_node(self, vals):
        node = vals['trade_settlement_node']['ram:SpecifiedTradePaymentTerms'] = {}
        sub_vals = {
            **vals,
            'payment_terms_node': node,
        }
        self._cii_add_payment_term_description_node(sub_vals)
        self._cii_add_payment_term_due_date_time_node(sub_vals)
        self._cii_add_payment_term_discount_terms_node(sub_vals)

    def _cii_add_payment_term_description_node(self, vals):
        invoice = vals['invoice']
        if invoice.invoice_payment_term_id:
            vals['payment_terms_node']['ram:Description'] = {
                '_text': vals['invoice'].invoice_payment_term_id.name,
            }

    def _cii_add_payment_term_due_date_time_node(self, vals):
        invoice = vals['invoice']
        if invoice.invoice_date_due:
            node = vals['payment_terms_node']['ram:DueDateDateTime'] = {}
            sub_vals = {
                **vals,
                'date_time_node': node,
                'date': invoice.invoice_date_due,
            }
            self._cii_add_date_time_string_node(sub_vals)

    def _cii_add_payment_term_discount_terms_node(self, vals):
        invoice = vals['invoice']
        if invoice.invoice_payment_term_id.early_discount:
            node = vals['payment_terms_node']['ram:ApplicableTradePaymentDiscountTerms'] = {}
            sub_vals = {
                **vals,
                'discount_terms_node': node,
            }
            self._cii_add_basis_period_measure_node(sub_vals)
            self._cii_add_calculation_percent_node(sub_vals)

    def _cii_add_basis_period_measure_node(self, vals):
        invoice = vals['invoice']
        vals['discount_terms_node']['ram:BasisPeriodMeasure'] = {
            '_text': invoice.invoice_payment_term_id.discount_days,
            'unitCode': 'DAY',
        }

    def _cii_add_calculation_percent_node(self, vals):
        invoice = vals['invoice']
        vals['discount_terms_node']['ram:CalculationPercent'] = {
            '_text': invoice.invoice_payment_term_id.discount_percentage,
        }

    def _cii_add_specified_trade_monetary_summation_node(self, vals):
        node = vals['trade_settlement_node']['ram:SpecifiedTradeSettlementHeaderMonetarySummation'] = {}
        sub_vals = {
            **vals,
            'monetary_summation_node': node,
        }
        self._cii_add_line_total_amount_node(sub_vals)
        self._cii_add_tax_basis_total_amount_node(sub_vals)
        self._cii_add_tax_total_amount_node(sub_vals)
        self._cii_add_rounding_amount_node(sub_vals)
        self._cii_add_grand_total_amount_node(sub_vals)
        self._cii_add_total_prepaid_amount(sub_vals)
        self._cii_add_due_payable_amount_node(sub_vals)

    def _cii_add_line_total_amount_node(self, vals):
        currency_suffix = vals['currency_suffix']
        vals['monetary_summation_node']['ram:LineTotalAmount'] = {
            '_text': self._cii_format_monetary(vals[f'line_total_amount{currency_suffix}'], 2),
        }

    def _cii_add_tax_basis_total_amount_node(self, vals):
        currency_suffix = vals['currency_suffix']
        vals['monetary_summation_node']['ram:TaxBasisTotalAmount'] = {
            '_text': self._cii_format_monetary(vals[f'line_total_amount{currency_suffix}'], 2),
        }

    def _cii_add_tax_total_amount_node(self, vals):
        currency = vals['currency_id']
        currency_suffix = vals['currency_suffix']
        vals['monetary_summation_node']['ram:TaxTotalAmount'] = {
            'currencyID': currency.name,
            '_text': self._cii_format_monetary(vals[f'tax_total_amount{currency_suffix}'], 2),
        }

    def _cii_add_rounding_amount_node(self, vals):
        currency_suffix = vals['currency_suffix']
        if vals[f'cash_rounding_base_amount{currency_suffix}']:
            vals['monetary_summation_node']['ram:RoundingAmount'] = {
                '_text': self._cii_format_monetary(vals[f'cash_rounding_base_amount{currency_suffix}'], 2),
            }

    def _cii_add_grand_total_amount_node(self, vals):
        currency_suffix = vals['currency_suffix']
        vals['monetary_summation_node']['ram:GrandTotalAmount'] = {
            '_text': self._cii_format_monetary(vals[f'grand_total_amount{currency_suffix}'], 2),
        }

    def _cii_add_total_prepaid_amount(self, vals):
        currency_suffix = vals['currency_suffix']
        vals['monetary_summation_node']['ram:TotalPrepaidAmount'] = {
            '_text': self._cii_format_monetary(vals[f'total_prepaid_amount{currency_suffix}'], 2),
        }

    def _cii_add_due_payable_amount_node(self, vals):
        currency_suffix = vals['currency_suffix']
        vals['monetary_summation_node']['ram:DuePayableAmount'] = {
            '_text': self._cii_format_monetary(vals[f'due_payable_amount{currency_suffix}'], 2),
        }

    def _cii_constraints(self, invoice, vals):
        constraints = {}
        self._cii_check_seller(invoice, vals, constraints)
        self._cii_check_buyer(vals, constraints)
        self._cii_check_one_tax_per_line(invoice, vals, constraints)

        if vals['intracom_delivery']:
            self._cii_check_intracom_delivery(vals, constraints)

        if vals['invoice']['partner_id']['country_id']['code'] == 'ES' \
            and vals['invoice']['partner_id']['zip'] \
            and vals['invoice']['partner_id']['zip'][:2] in ['35', '38']:
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
        constraints.update({
            'seller_postal_address': self._check_required_fields(
            vals['invoice']['company_id']['partner_id']['commercial_partner_id'], 'country_id'
            ),
        })

    def _cii_check_seller_identifier(self, vals, constraints):
        """
        [BR-CO-26]-In order for the buyer to automatically identify a supplier, the Seller identifier (BT-29),
        the Seller legal registration identifier (BT-30) and/or the Seller VAT identifier (BT-31) shall be present.
        """
        constraints.update({
            'seller_identifier': self._check_required_fields(
                vals['invoice']['company_id'], ['vat']
            ),
        })

    def _cii_check_seller_contact(self, vals, constraints):
        """
        [BR-DE-6] The element "Seller contact telephone number" (BT-42) must be transmitted.
        [BR-DE-7] The element "Seller contact email address" (BT-43) must be transmitted.
        """
        constraints.update({
            'seller_phone': self._check_required_fields(
                vals['invoice']['company_id']['partner_id']['commercial_partner_id'], ['phone', 'mobile'],
            ),
            'seller_email': self._check_required_fields(
                vals['invoice']['company_id'], 'email'
            ),
        })

    def _cii_check_buyer_postal_address(self, vals, constraints):
        """
        [BR-10]-An Invoice shall contain the Buyer postal address (BG-8).
        [BR-11]-The Buyer postal address shall contain a Buyer country code (BT-55).
        """
        constraints.update({
            'buyer_postal_address': self._check_required_fields(
                vals['invoice']['commercial_partner_id'], 'country_id'
            ),
        })

    def _cii_check_one_tax_per_line(self, invoice, vals, constraints):
        """
        Element 'ram:ApplicableTradeTax' must occur exactly 1 times
        Each invoice line must have one and only one tax
        """
        for line in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section')):
            if len(line.tax_ids.flatten_taxes_hierarchy().filtered(lambda t: t.amount_type != 'fixed')) != 1:
                constraints.update({
                    'one_tax_per_line': self.env._("Each invoice line shall have one and only one tax."),
                })

    def _cii_check_intracom_delivery(self, vals, constraints):
        """
        [BR-IC-02]-An Invoice that contains an Invoice line (BG-25) where the Invoiced item VAT category code (BT-151)
        is "Intra-community supply" shall contain the Seller VAT Identifier (BT-31) or the Seller tax representative
        VAT identifier (BT-63) and the Buyer VAT identifier (BT-48).
        """
        constraints.update({
            'intracom_seller_vat': self._check_required_fields(
                vals['invoice']['company_id'], 'vat'
            ),
            'intracom_buyer_vat': self._check_required_fields(
                vals['invoice']['commercial_partner_id'], 'vat'
            ),
        })

    def _cii_check_igi_tax_rate(self, invoice, vals, constraints):
        for line in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section')):
            tax_rate_list = line.tax_ids.flatten_taxes_hierarchy().mapped("amount")
            if not any(rate > 0 for rate in tax_rate_list):
                constraints.update({
                    'igic_tax_rate': self.env._("When the Canary Island General Indirect Tax (IGIC) applies, the tax rate on "
                         "each invoice line should be greater than 0."),
                })

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
        if narration := tree.findtext('./{*}ExchangedDocument/{*}IncludedNote/{*}Content'):
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
            line_total_amount
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
                price_unit = (subtotal / quantity) + (price_discount_amount / price_quantity)
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
