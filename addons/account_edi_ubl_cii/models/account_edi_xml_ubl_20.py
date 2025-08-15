# -*- coding: utf-8 -*-
from collections import defaultdict
from lxml import etree

from odoo import models, _
from odoo.tools import html2plaintext, cleanup_xml_node

UBL_NAMESPACES = {
    'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


class AccountEdiXmlUBL20(models.AbstractModel):
    _name = "account.edi.xml.ubl_20"
    _inherit = 'account.edi.common'
    _description = "UBL 2.0"

    def _find_value(self, xpath, tree, nsmap=False):
        # EXTENDS account.edi.common
        return super()._find_value(xpath, tree, UBL_NAMESPACES)

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_20.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'org.oasis-open:invoice:2.0',
            'credit_note': 'org.oasis-open:creditnote:2.0',
        }

    def _get_country_vals(self, country):
        return {
            'country': country,

            'identification_code': country.code,
            'name': country.name,
        }

    def _get_partner_party_identification_vals_list(self, partner):
        return []

    def _get_partner_address_vals(self, partner):
        return {
            'street_name': partner.street,
            'additional_street_name': partner.street2,
            'city_name': partner.city,
            'postal_zone': partner.zip,
            'country_subentity': partner.state_id.name,
            'country_subentity_code': partner.state_id.code,
            'country_vals': self._get_country_vals(partner.country_id),
        }

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # [BR-CO-09] if the PartyTaxScheme/TaxScheme/ID == 'VAT', CompanyID must start with a country code prefix.
        # In some countries however, the CompanyID can be with or without country code prefix and still be perfectly
        # valid (RO, HU, non-EU countries).
        # We have to handle their cases by changing the TaxScheme/ID to 'something other than VAT',
        # preventing the trigger of the rule.
        tax_scheme_id = 'VAT'
        if (
            partner.country_id
            and partner.vat and not partner.vat[:2].isalpha()
        ):
            tax_scheme_id = 'NOT_EU_VAT'
        return [{
            'registration_name': partner.name,
            'company_id': partner.vat,
            'registration_address_vals': self._get_partner_address_vals(partner),
            'tax_scheme_vals': {'id': tax_scheme_id},
        }]

    def _get_partner_party_legal_entity_vals_list(self, partner):
        return [{
            'commercial_partner': partner,
            'registration_name': partner.name,
            'company_id': partner.vat,
            'registration_address_vals': self._get_partner_address_vals(partner),
        }]

    def _get_partner_contact_vals(self, partner):
        return {
            'id': partner.id,
            'name': partner.name,
            'telephone': partner.phone or partner.mobile,
            'electronic_mail': partner.email,
        }

    def _get_partner_person_vals(self, partner):
        """
        This is optional and meant to be overridden when required under the form:
        {
            'first_name': str,
            'family_name': str,
        }.
        Should return a dict.
        """
        return {}

    def _get_partner_party_vals(self, partner, role):
        return {
            'partner': partner,
            'party_identification_vals': self._get_partner_party_identification_vals_list(partner.commercial_partner_id),
            'party_name_vals': [{'name': partner.display_name}],
            'postal_address_vals': self._get_partner_address_vals(partner),
            'party_tax_scheme_vals': self._get_partner_party_tax_scheme_vals_list(partner.commercial_partner_id, role),
            'party_legal_entity_vals': self._get_partner_party_legal_entity_vals_list(partner.commercial_partner_id),
            'contact_vals': self._get_partner_contact_vals(partner),
            'person_vals': self._get_partner_person_vals(partner),
        }

    def _get_invoice_period_vals_list(self, invoice):
        """
        For now, we cannot fill this data from an invoice
        This corresponds to the 'delivery or invoice period'. For UBL Bis 3, in the case of intra-community supply,
        the Actual delivery date (BT-72) or the Invoicing period (BG-14) should be present under the form:
        {
            'start_date': str,
            'end_date': str,
        }.
        """
        return []

    def _get_additional_document_reference_list(self, invoice):
        """
        This is optional and meant to be overridden when required under the form:
        {
            'id': str,
            'issue_date': str,
            'document_type_code': str,
            'document_type': str,
            'document_description': str,
        }.
        Should return a list.
        """
        return []

    def _get_delivery_vals_list(self, invoice):
        # the data is optional, except for ubl bis3 (see the override, where we need to set a default delivery address)
        return [{
            'actual_delivery_date': invoice.delivery_date,
            'delivery_location_vals': {
                'delivery_address_vals': self._get_partner_address_vals(invoice.partner_shipping_id),
            },
            'delivery_party_vals': self._get_partner_party_vals(invoice.partner_shipping_id, 'delivery') if invoice.partner_shipping_id else {},
        }]

    def _get_bank_address_vals(self, bank):
        return {
            'street_name': bank.street,
            'additional_street_name': bank.street2,
            'city_name': bank.city,
            'postal_zone': bank.zip,
            'country_subentity': bank.state.name,
            'country_subentity_code': bank.state.code,
            'country_vals': self._get_country_vals(bank.country),
        }

    def _get_financial_institution_vals(self, bank):
        return {
            'bank': bank,
            'id': bank.bic,
            'id_attrs': {'schemeID': 'BIC'},
            'name': bank.name,
            'address_vals': self._get_bank_address_vals(bank),
        }

    def _get_financial_institution_branch_vals(self, bank):
        return {
            'bank': bank,
            'id': bank.bic,
            'id_attrs': {'schemeID': 'BIC'},
            'financial_institution_vals': self._get_financial_institution_vals(bank),
        }

    def _get_financial_account_vals(self, partner_bank):
        vals = {
            'bank_account': partner_bank,
            'id': partner_bank.acc_number.replace(' ', ''),
        }

        if partner_bank.bank_id:
            vals['financial_institution_branch_vals'] = self._get_financial_institution_branch_vals(partner_bank.bank_id)

        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        payment_means_code, payment_means_name = (30, 'credit transfer') if invoice.move_type == 'out_invoice' else (57, 'standing agreement')
        # in Denmark payment code 30 is not allowed. we hardcode it to 1 ("unknown") for now
        # as we cannot deduce this information from the invoice
        if invoice.partner_id.country_code == 'DK':
            payment_means_code, payment_means_name = 1, 'unknown'

        vals = {
            'payment_means_code': payment_means_code,
            'payment_means_code_attrs': {'name': payment_means_name},
            'payment_due_date': invoice.invoice_date_due or invoice.invoice_date,
            'instruction_id': invoice.payment_reference,
            'payment_id_vals': [invoice.payment_reference or invoice.name],
        }

        if invoice.partner_bank_id:
            vals['payee_financial_account_vals'] = self._get_financial_account_vals(invoice.partner_bank_id)

        return [vals]

    def _get_invoice_payment_terms_vals_list(self, invoice):
        payment_term = invoice.invoice_payment_term_id
        if payment_term:
            # The payment term's note is automatically embedded in a <p> tag in Odoo
            return [{'note_vals': [{'note': html2plaintext(payment_term.note)}]}]
        else:
            return []

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        tax_totals_vals = {
            'currency': invoice.currency_id,
            'currency_dp': self._get_currency_decimal_places(invoice.currency_id),
            'tax_amount': taxes_vals['tax_amount_currency'],
            'tax_subtotal_vals': [],
        }

        # If it's not on the whole invoice, don't manage the EPD.
        epd_tax_to_discount = {}
        if not taxes_vals.get('invoice_line'):
            epd_tax_to_discount = self._get_early_payment_discount_grouped_by_tax_rate(invoice)
            epd_base_tax_amounts = defaultdict(lambda: {
                'base_amount_currency': 0.0,
                'tax_amount_currency': 0.0,
            })
            if epd_tax_to_discount:
                for percentage, base_amount_currency in epd_tax_to_discount.items():
                    epd_base_tax_amounts[percentage]['base_amount_currency'] += base_amount_currency
                epd_accounted_tax_amount = 0.0
                for percentage, amounts in epd_base_tax_amounts.items():
                    amounts['tax_amount_currency'] = invoice.currency_id.round(
                        amounts['base_amount_currency'] * percentage / 100.0)
                    epd_accounted_tax_amount += amounts['tax_amount_currency']

        for grouping_key, vals in taxes_vals['tax_details'].items():
            if grouping_key['tax_amount_type'] != 'fixed':
                subtotal = {
                    'currency': invoice.currency_id,
                    'currency_dp': self._get_currency_decimal_places(invoice.currency_id),
                    'taxable_amount': vals['base_amount_currency'],
                    'tax_amount': vals['tax_amount_currency'],
                    'percent': vals['tax_category_percent'],
                    'tax_category_vals': vals['_tax_category_vals_'],
                }
                if epd_tax_to_discount:
                    # early payment discounts: need to recompute the tax/taxable amounts
                    epd_base_amount = epd_base_tax_amounts.get(subtotal['percent'], {}).get('base_amount_currency', 0.0)
                    taxable_amount_after_epd = subtotal['taxable_amount'] - epd_base_amount
                    subtotal.update({
                        'taxable_amount': taxable_amount_after_epd,
                    })
                tax_totals_vals['tax_subtotal_vals'].append(subtotal)

        if epd_tax_to_discount:
            # early payment discounts: hence, need to add a subtotal section
            tax_totals_vals['tax_subtotal_vals'].append({
                'currency': invoice.currency_id,
                'currency_dp': invoice.currency_id.decimal_places,
                'taxable_amount': sum(epd_tax_to_discount.values()),
                'tax_amount': 0.0,
                'tax_category_vals': {
                    'id': 'E',
                    'percent': 0.0,
                    'tax_scheme_vals': {
                        'id': "VAT",
                    },
                    'tax_exemption_reason': "Exempt from tax",
                },
            })
        return [tax_totals_vals]

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        """ Method used to fill the cac:InvoiceLine/cac:Item node.
        It provides information about what the product you are selling.

        :param line:        An invoice line.
        :param taxes_vals:  The tax details for the current invoice line.
        :return:            A python dictionary.
        """
        product = line.product_id
        taxes = line.tax_ids.flatten_taxes_hierarchy().filtered(lambda t: t.amount_type != 'fixed')
        tax_category_vals_list = self._get_tax_category_list(line.move_id, taxes)
        description = line.name and line.name.replace('\n', ', ')
        return {
            'description': description,
            'name': product.name or description,
            'sellers_item_identification_vals': {'id': product.code},
            'classified_tax_category_vals': tax_category_vals_list,
            'standard_item_identification_vals': {
                'id': product.barcode,
                'id_attrs': {'schemeID': '0160'},  # GTIN
            } if product.barcode else {},
        }

    def _get_document_allowance_charge_vals_list(self, invoice):
        """
        https://docs.peppol.eu/poacc/billing/3.0/bis/#_document_level_allowance_or_charge
        Usage for early payment discounts:
        * Add one document level Allowance per tax rate (VAT included)
        * Add one document level Charge (VAT excluded) with amount = the total sum of the early payment discount
        The difference between these is the cash discount in case of early payment.
        """
        vals_list = []
        # Early Payment Discount
        epd_tax_to_discount = self._get_early_payment_discount_grouped_by_tax_rate(invoice)
        if epd_tax_to_discount:
            # One Allowance per tax rate (VAT included)
            for tax_amount, discount_amount in epd_tax_to_discount.items():
                vals_list.append({
                    'charge_indicator': 'false',
                    'allowance_charge_reason_code': '66',
                    'allowance_charge_reason': _("Conditional cash/payment discount"),
                    'amount': discount_amount,
                    'currency_dp': 2,
                    'currency_name': invoice.currency_id.name,
                    'tax_category_vals': [{
                        'id': 'S',
                        'percent': tax_amount,
                        'tax_scheme_vals': {'id': 'VAT'},
                    }],
                })
            # One global Charge (VAT exempted)
            vals_list.append({
                'charge_indicator': 'true',
                'allowance_charge_reason_code': 'ZZZ',
                'allowance_charge_reason': _("Conditional cash/payment discount"),
                'amount': sum(epd_tax_to_discount.values()),
                'currency_dp': 2,
                'currency_name': invoice.currency_id.name,
                'tax_category_vals': [{
                    'id': 'E',
                    'percent': 0.0,
                    'tax_scheme_vals': {'id': 'VAT'},
                }],
            })
        return vals_list

    def _get_pricing_exchange_rate_vals_list(self, invoice):
        """ To be overridden if needed to fill the PricingExchangeRate node.

        This is used when the currency of the 'Exchange' (e.g.: an invoice) is not the same as the Document currency.

        If used, it should return a list of dict, following this format: [{
            'source_currency_code': str,  (required)
            'target_currency_code': str,  (required)
            'calculation_rate': float,
            'date': date,
        }]
        """
        return []

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list=None):
        """ Method used to fill the cac:{Invoice,CreditNote,DebitNote}Line>cac:AllowanceCharge node.

        Allowances are distinguished from charges using the ChargeIndicator node with 'false' as value.

        Note that allowance charges do not exist for credit notes in UBL 2.0, so if we apply discount in Odoo
        the net price will not be consistent with the unit price, but we cannot do anything about it

        :param line:    An invoice line.
        :return:        A list of python dictionaries.
        """
        fixed_tax_charge_vals_list = []
        for grouping_key, tax_details in tax_values_list['tax_details'].items():
            if grouping_key['tax_amount_type'] == 'fixed':
                fixed_tax_charge_vals_list.append({
                    'currency_name': line.currency_id.name,
                    'currency_dp': self._get_currency_decimal_places(line.currency_id),
                    'charge_indicator': 'true',
                    'allowance_charge_reason_code': 'AEO',
                    'allowance_charge_reason': tax_details['tax_name'],
                    'amount': tax_details['tax_amount_currency'],
                })

        if not line.discount:
            return fixed_tax_charge_vals_list

        # Price subtotal with discount subtracted:
        net_price_subtotal = line.price_subtotal
        # Price subtotal without discount subtracted:
        if line.discount == 100.0:
            gross_price_subtotal = 0.0
        else:
            gross_price_subtotal = line.currency_id.round(net_price_subtotal / (1.0 - (line.discount or 0.0) / 100.0))

        allowance_vals = {
            'currency_name': line.currency_id.name,
            'currency_dp': self._get_currency_decimal_places(line.currency_id),

            # Must be 'false' since this method is for allowances.
            'charge_indicator': 'false',

            # A reason should be provided. In Odoo, we only manage discounts.
            # Full code list is available here:
            # https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5189/
            'allowance_charge_reason_code': 95,

            # The discount should be provided as an amount.
            'amount': gross_price_subtotal - net_price_subtotal,
        }

        return [allowance_vals] + fixed_tax_charge_vals_list

    def _get_invoice_line_price_vals(self, line):
        """ Method used to fill the cac:InvoiceLine/cac:Price node.
        It provides information about the price applied for the goods and services invoiced.

        :param line:    An invoice line.
        :return:        A python dictionary.
        """
        # Price subtotal without discount:
        net_price_subtotal = line.price_subtotal
        # Price subtotal with discount:
        if line.discount == 100.0:
            gross_price_subtotal = 0.0
        else:
            gross_price_subtotal = net_price_subtotal / (1.0 - (line.discount or 0.0) / 100.0)
        # Price subtotal with discount / quantity:
        gross_price_unit = gross_price_subtotal / line.quantity if line.quantity else 0.0

        uom = super()._get_uom_unece_code(line)

        return {
            'currency': line.currency_id,
            'currency_dp': self._get_currency_decimal_places(line.currency_id),

            # The price of an item, exclusive of VAT, after subtracting item price discount.
            'price_amount': round(gross_price_unit, 10),
            'product_price_dp': self.env['decimal.precision'].precision_get('Product Price'),

            # The number of item units to which the price applies.
            # setting to None -> the xml will not comprise the BaseQuantity (it's not mandatory)
            'base_quantity': None,
            'base_quantity_attrs': {'unitCode': uom},
        }

    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        """ Method used to fill the cac:TaxTotal node on a line level.
        Uses the same method as the invoice TaxTotal, but can be overridden in other formats.
        """
        return self._get_invoice_tax_totals_vals_list(line.move_id, taxes_vals)

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        """ Method used to fill the cac:{Invoice,CreditNote,DebitNote}Line node.
        It provides information about the document line.

        :param line:    A document line.
        :return:        A python dictionary.
        """
        allowance_charge_vals_list = self._get_invoice_line_allowance_vals_list(line, tax_values_list=taxes_vals)

        uom = super()._get_uom_unece_code(line)
        total_fixed_tax_amount = sum(
            vals['amount']
            for vals in allowance_charge_vals_list
            if vals.get('charge_indicator') == 'true'
        )
        period_vals = {}
        # deferred_start_date & deferred_end_date are enterprise-only fields
        if line._fields.get('deferred_start_date') and (line.deferred_start_date or line.deferred_end_date):
            period_vals.update({'start_date': line.deferred_start_date})
            period_vals.update({'end_date': line.deferred_end_date})
        return {
            'currency': line.currency_id,
            'currency_dp': self._get_currency_decimal_places(line.currency_id),
            'id': line_id + 1,
            'line_quantity': line.quantity,
            'line_quantity_attrs': {'unitCode': uom},
            'line_extension_amount': line.price_subtotal + total_fixed_tax_amount,
            'allowance_charge_vals': allowance_charge_vals_list,
            'tax_total_vals': self._get_invoice_line_tax_totals_vals_list(line, taxes_vals),
            'item_vals': self._get_invoice_line_item_vals(line, taxes_vals),
            'price_vals': self._get_invoice_line_price_vals(line),
            'invoice_period_vals_list': [period_vals] if period_vals else []
        }

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        """ Method used to fill the cac:{Legal,Requested}MonetaryTotal node"""
        # We only handle rounding amounts that do not belong to any tax ('add_invoice_line' cash rounding strategy).
        # Rounding amounts belonging to a tax ('biggest_tax' strategy) are included already in the tax amounts.
        rounding_amls = invoice.line_ids.filtered(lambda line: line.display_type == 'rounding' and not line.tax_line_id)
        payable_rounding_amount = invoice.direction_sign * sum(rounding_amls.mapped('amount_currency'))
        return {
            'currency': invoice.currency_id,
            'currency_dp': self._get_currency_decimal_places(invoice.currency_id),
            'line_extension_amount': line_extension_amount,
            'tax_exclusive_amount': taxes_vals['base_amount_currency'],
            'tax_inclusive_amount': invoice.amount_total - payable_rounding_amount,
            'allowance_total_amount': allowance_total_amount or None,
            'charge_total_amount': charge_total_amount or None,
            'prepaid_amount': invoice.amount_total - invoice.amount_residual,
            'payable_rounding_amount': payable_rounding_amount or None,
            'payable_amount': invoice.amount_residual,
        }

    def _apply_invoice_tax_filter(self, base_line, tax_values):
        """
            To be overridden to apply a specific tax filter
        """
        return True

    def _apply_invoice_line_filter(self, invoice_line):
        """
            To be overridden to apply a specific invoice line filter
        """
        return True

    def _get_early_payment_discount_grouped_by_tax_rate(self, invoice):
        """
        Get the early payment discounts grouped by the tax rate of the product it is linked to
        :returns {float: float}: mapping tax amounts to early payment discount amounts
        """
        if invoice.invoice_payment_term_id.early_pay_discount_computation != 'mixed':
            return {}
        tax_to_discount = defaultdict(lambda: 0)
        for line in invoice.line_ids.filtered(lambda l: l.display_type == 'epd'):
            for tax in line.tax_ids:
                tax_to_discount[tax.amount] += line.amount_currency
        return tax_to_discount

    def _export_invoice_vals(self, invoice):
        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id
            tax_category_vals = self._get_tax_category_list(invoice, tax)[0]
            grouping_key = {
                'tax_category_id': tax_category_vals['id'],
                'tax_category_percent': tax_category_vals['percent'],
                '_tax_category_vals_': tax_category_vals,
                'tax_amount_type': tax.amount_type,
            }
            # If the tax is fixed, we want to have one group per tax
            # s.t. when the invoice is imported, we can try to guess the fixed taxes
            if tax.amount_type == 'fixed':
                grouping_key['tax_name'] = tax.name
            return grouping_key

        # Validate the structure of the taxes
        self._validate_taxes(invoice)

        # Compute the tax details for the whole invoice and each invoice line separately.
        taxes_vals = invoice._prepare_invoice_aggregated_taxes(
            grouping_key_generator=grouping_key_generator,
            filter_tax_values_to_apply=self._apply_invoice_tax_filter,
            filter_invl_to_apply=self._apply_invoice_line_filter,
        )

        # Fixed Taxes: filter them on the document level, and adapt the totals
        # Fixed taxes are not supposed to be taxes in real live. However, this is the way in Odoo to manage recupel
        # taxes in Belgium. Since only one tax is allowed, the fixed tax is removed from totals of lines but added
        # as an extra charge/allowance.
        fixed_taxes_keys = [k for k in taxes_vals['tax_details'] if k['tax_amount_type'] == 'fixed']
        for key in fixed_taxes_keys:
            fixed_tax_details = taxes_vals['tax_details'].pop(key)
            taxes_vals['tax_amount_currency'] -= fixed_tax_details['tax_amount_currency']
            taxes_vals['tax_amount'] -= fixed_tax_details['tax_amount']
            taxes_vals['base_amount_currency'] += fixed_tax_details['tax_amount_currency']
            taxes_vals['base_amount'] += fixed_tax_details['tax_amount']

        # Compute values for invoice lines.
        line_extension_amount = 0.0

        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section') and line._check_edi_line_tax_required())
        document_allowance_charge_vals_list = self._get_document_allowance_charge_vals_list(invoice)
        invoice_line_vals_list = []
        for line_id, line in enumerate(invoice_lines):
            line_taxes_vals = taxes_vals['tax_details_per_record'][line]
            line_vals = self._get_invoice_line_vals(line, line_id, {**line_taxes_vals, 'invoice_line': line})
            invoice_line_vals_list.append(line_vals)

            line_extension_amount += line_vals['line_extension_amount']

        # Compute the total allowance/charge amounts.
        allowance_total_amount = 0.0
        charge_total_amount = 0.0
        for allowance_charge_vals in document_allowance_charge_vals_list:
            if allowance_charge_vals['charge_indicator'] == 'false':
                allowance_total_amount += allowance_charge_vals['amount']
            else:
                charge_total_amount += allowance_charge_vals['amount']

        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.partner_id

        # OrderReference/SalesOrderID (sales_order_id) is optional
        sales_order_id = 'sale_line_ids' in invoice.invoice_line_ids._fields \
                         and ",".join(invoice.invoice_line_ids.sale_line_ids.order_id.mapped('name'))
        # OrderReference/ID (order_reference) is mandatory inside the OrderReference node !
        order_reference = invoice.ref or invoice.name

        vals = {
            'builder': self,
            'invoice': invoice,
            'supplier': supplier,
            'customer': customer,

            'taxes_vals': taxes_vals,

            'format_float': self.format_float,
            'AddressType_template': 'account_edi_ubl_cii.ubl_20_AddressType',
            'ContactType_template': 'account_edi_ubl_cii.ubl_20_ContactType',
            'PartyType_template': 'account_edi_ubl_cii.ubl_20_PartyType',
            'PaymentMeansType_template': 'account_edi_ubl_cii.ubl_20_PaymentMeansType',
            'PaymentTermsType_template': 'account_edi_ubl_cii.ubl_20_PaymentTermsType',
            'TaxCategoryType_template': 'account_edi_ubl_cii.ubl_20_TaxCategoryType',
            'TaxTotalType_template': 'account_edi_ubl_cii.ubl_20_TaxTotalType',
            'AllowanceChargeType_template': 'account_edi_ubl_cii.ubl_20_AllowanceChargeType',
            'SignatureType_template': 'account_edi_ubl_cii.ubl_20_SignatureType',
            'ResponseType_template': 'account_edi_ubl_cii.ubl_20_ResponseType',
            'DeliveryType_template': 'account_edi_ubl_cii.ubl_20_DeliveryType',
            'MonetaryTotalType_template': 'account_edi_ubl_cii.ubl_20_MonetaryTotalType',
            'InvoiceLineType_template': 'account_edi_ubl_cii.ubl_20_InvoiceLineType',
            'CreditNoteLineType_template': 'account_edi_ubl_cii.ubl_20_CreditNoteLineType',
            'DebitNoteLineType_template': 'account_edi_ubl_cii.ubl_20_DebitNoteLineType',
            'InvoiceType_template': 'account_edi_ubl_cii.ubl_20_InvoiceType',
            'CreditNoteType_template': 'account_edi_ubl_cii.ubl_20_CreditNoteType',
            'DebitNoteType_template': 'account_edi_ubl_cii.ubl_20_DebitNoteType',
            'ExchangeRateType_template': 'account_edi_ubl_cii.ubl_20_ExchangeRateType',

            'vals': {
                'ubl_version_id': 2.0,
                'id': invoice.name,
                'issue_date': invoice.invoice_date,
                'due_date': invoice.invoice_date_due,
                'note_vals': self._get_note_vals_list(invoice),
                'order_reference': order_reference,
                'sales_order_id': sales_order_id,
                'accounting_supplier_party_vals': {
                    'party_vals': self._get_partner_party_vals(supplier, role='supplier'),
                },
                'accounting_customer_party_vals': {
                    'party_vals': self._get_partner_party_vals(customer, role='customer'),
                },
                'invoice_period_vals_list': self._get_invoice_period_vals_list(invoice),
                'additional_document_reference_list': self._get_additional_document_reference_list(invoice),
                'delivery_vals_list': self._get_delivery_vals_list(invoice),
                'payment_means_vals_list': self._get_invoice_payment_means_vals_list(invoice),
                'payment_terms_vals': self._get_invoice_payment_terms_vals_list(invoice),
                # allowances at the document level, the allowances on invoices (eg. discount) are on line_vals
                'allowance_charge_vals': document_allowance_charge_vals_list,
                'tax_total_vals': self._get_invoice_tax_totals_vals_list(invoice, taxes_vals),
                'monetary_total_vals': self._get_invoice_monetary_total_vals(
                    invoice,
                    taxes_vals,
                    line_extension_amount,
                    allowance_total_amount,
                    charge_total_amount,
                ),
                'line_vals': invoice_line_vals_list,
                'currency_dp': self._get_currency_decimal_places(invoice.currency_id),  # currency decimal places
                'pricing_exchange_rate_vals_list': self._get_pricing_exchange_rate_vals_list(invoice),
            },
        }

        # Document type specific settings
        if 'debit_origin_id' in self.env['account.move']._fields and invoice.debit_origin_id:
            vals['document_type'] = 'debit_note'
            vals['main_template'] = 'account_edi_ubl_cii.ubl_20_DebitNote'
            vals['vals']['document_type_code'] = 383
        elif invoice.move_type == 'out_refund':
            vals['document_type'] = 'credit_note'
            vals['main_template'] = 'account_edi_ubl_cii.ubl_20_CreditNote'
            vals['vals']['document_type_code'] = 381
        else: # invoice.move_type == 'out_invoice'
            vals['document_type'] = 'invoice'
            vals['main_template'] = 'account_edi_ubl_cii.ubl_20_Invoice'
            vals['vals']['document_type_code'] = 380

        return vals

    def _get_note_vals_list(self, invoice):
        return [{'note': html2plaintext(invoice.narration)}] if invoice.narration else []

    def _export_invoice_constraints(self, invoice, vals):
        constraints = self._invoice_constraints_common(invoice)
        constraints.update({
            'ubl20_supplier_name_required': self._check_required_fields(vals['supplier'], 'name'),
            'ubl20_customer_name_required': self._check_required_fields(vals['customer'].commercial_partner_id, 'name'),
            'ubl20_invoice_name_required': self._check_required_fields(invoice, 'name'),
            'ubl20_invoice_date_required': self._check_required_fields(invoice, 'invoice_date'),
        })
        return constraints

    def _export_invoice(self, invoice):
        vals = self._export_invoice_vals(invoice.with_context(lang=invoice.partner_id.lang))
        errors = [constraint for constraint in self._export_invoice_constraints(invoice, vals).values() if constraint]
        xml_content = self.env['ir.qweb']._render(vals['main_template'], vals)
        return etree.tostring(cleanup_xml_node(xml_content), xml_declaration=True, encoding='UTF-8'), set(errors)

    def _get_document_type_code_vals(self, invoice, invoice_data):
        """Returns the values used for the `DocumentTypeCode` node"""
        # To be overriden by custom format if required
        return {'attrs': {}, 'value': None}

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_vals(self, tree, role):
        """ Returns a dict of values that will be used to retrieve the partner """
        return {
            'vat': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:CompanyID[string-length(text()) > 5]', tree),
            'phone': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:Telephone', tree),
            'mail': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:ElectronicMail', tree),
            'name': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:Name', tree) or
                    self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:RegistrationName', tree),
            'country_code': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cac:Country//cbc:IdentificationCode', tree),
            'street': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:StreetName', tree),
            'street2': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:AdditionalStreetName', tree),
            'city': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:CityName', tree),
            'zip_code': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cbc:PostalZone', tree),
        }

    def _import_fill_invoice_form(self, invoice, tree, qty_factor):
        logs = []

        if qty_factor == -1:
            logs.append(_("The invoice has been converted into a credit note and the quantities have been reverted."))

        # ==== partner_id ====

        role = "Customer" if invoice.journal_id.type == 'sale' else "Supplier"
        partner_vals = self._import_retrieve_partner_vals(tree, role)
        self._import_retrieve_and_fill_partner(invoice, **partner_vals)

        # ==== currency_id ====

        currency_code_node = tree.find('.//{*}DocumentCurrencyCode')
        if currency_code_node is not None:
            currency = self.env['res.currency'].with_context(active_test=False).search([
                ('name', '=', currency_code_node.text),
            ], limit=1)
            if currency:
                if not currency.active:
                    logs.append(_("The currency '%s' is not active.", currency.name))
                invoice.currency_id = currency
            else:
                logs.append(_("Could not retrieve currency: %s. Did you enable the multicurrency option "
                              "and activate the currency?", currency_code_node.text))

        # ==== invoice_date ====

        invoice_date_node = tree.find('./{*}IssueDate')
        if invoice_date_node is not None and invoice_date_node.text:
            invoice.invoice_date = invoice_date_node.text

        # ==== invoice_date_due ====

        for xpath in ('./{*}DueDate', './/{*}PaymentDueDate'):
            invoice_date_due_node = tree.find(xpath)
            if invoice_date_due_node is not None and invoice_date_due_node.text:
                invoice.invoice_date_due = invoice_date_due_node.text
                break

        # ==== Bank Details ====

        bank_detail_nodes = tree.findall('.//{*}PaymentMeans')
        bank_details = [bank_detail_node.findtext('{*}PayeeFinancialAccount/{*}ID') for bank_detail_node in bank_detail_nodes]

        if bank_details:
            self._import_retrieve_and_fill_partner_bank_details(invoice, bank_details=bank_details)

        # ==== Delivery ====
        delivery_date = tree.find('.//{*}Delivery/{*}ActualDeliveryDate')
        invoice.delivery_date = delivery_date is not None and delivery_date.text

        # ==== Reference ====

        ref_node = tree.find('./{*}ID')
        if ref_node is not None:
            if invoice.is_sale_document(include_receipts=True) and invoice.quick_edit_mode:
                invoice.name = ref_node.text
            else:
                invoice.ref = ref_node.text

        # ==== Invoice origin ====

        invoice_origin_node = tree.find('./{*}OrderReference/{*}ID')
        if invoice_origin_node is not None:
            invoice.invoice_origin = invoice_origin_node.text

        # === Note/narration ====

        narration = ""
        note_node = tree.find('./{*}Note')
        if note_node is not None and note_node.text:
            narration += f"<p>{note_node.text}</p>"

        payment_terms_node = tree.find('./{*}PaymentTerms/{*}Note')  # e.g. 'Payment within 10 days, 2% discount'
        if payment_terms_node is not None and payment_terms_node.text:
            narration += f"<p>{payment_terms_node.text}</p>"

        invoice.narration = narration

        # ==== payment_reference ====

        payment_reference_node = tree.find('./{*}PaymentMeans/{*}PaymentID')
        if payment_reference_node is not None:
            invoice.payment_reference = payment_reference_node.text

        # ==== invoice_incoterm_id ====

        incoterm_code_node = tree.find('./{*}TransportExecutionTerms/{*}DeliveryTerms/{*}ID')
        if incoterm_code_node is not None:
            incoterm = self.env['account.incoterms'].search([('code', '=', incoterm_code_node.text)], limit=1)
            if incoterm:
                invoice.invoice_incoterm_id = incoterm

        # ==== invoice_line_ids: AllowanceCharge (document level) ====

        logs += self._import_fill_invoice_allowance_charge(tree, invoice, qty_factor)

        # ==== Prepaid amount ====

        prepaid_node = tree.find('./{*}LegalMonetaryTotal/{*}PrepaidAmount')
        logs += self._import_log_prepaid_amount(invoice, prepaid_node, qty_factor)

        # ==== invoice_line_ids: InvoiceLine/CreditNoteLine ====

        invoice_line_tag = 'InvoiceLine' if invoice.move_type in ('in_invoice', 'out_invoice') or qty_factor == -1 else 'CreditNoteLine'
        for i, invl_el in enumerate(tree.findall('./{*}' + invoice_line_tag)):
            invoice_line = invoice.invoice_line_ids.create({'move_id': invoice.id})
            invl_logs = self._import_fill_invoice_line_form(invl_el, invoice_line, qty_factor)
            logs += invl_logs

        # ==== Payable Rounding amount ====

        payable_rounding_node = tree.find('./{*}LegalMonetaryTotal/{*}PayableRoundingAmount')
        logs += self._import_rounding_amount(invoice, payable_rounding_node, qty_factor)

        return logs

    def _import_fill_invoice_line_form(self, tree, invoice_line, qty_factor):
        logs = []

        # Product.
        invoice_line.product_id = self.env['product.product']._retrieve_product(
            default_code=self._find_value('./cac:Item/cac:SellersItemIdentification/cbc:ID', tree),
            name=self._find_value('./cac:Item/cbc:Name', tree),
            barcode=self._find_value("./cac:Item/cac:StandardItemIdentification/cbc:ID[@schemeID='0160']", tree),
            company=invoice_line.company_id
        )
        # Description
        description_node = tree.find('./{*}Item/{*}Description')
        name_node = tree.find('./{*}Item/{*}Name')
        if description_node is not None:
            invoice_line.name = description_node.text
        elif name_node is not None:
            invoice_line.name = name_node.text  # Fallback on Name if Description is not found.

        # Start and End date (enterprise fields)
        if invoice_line._fields.get('deferred_start_date'):
            start_date = tree.find('./{*}InvoicePeriod/{*}StartDate')
            end_date = tree.find('./{*}InvoicePeriod/{*}EndDate')
            if start_date is not None and end_date is not None:  # there is a constraint forcing none or the two to be set
                invoice_line.write({
                    'deferred_start_date': start_date.text,
                    'deferred_end_date': end_date.text,
                })
        xpath_dict = {
            'basis_qty': [
                './{*}Price/{*}BaseQuantity',
            ],
            'gross_price_unit': './{*}Price/{*}AllowanceCharge/{*}BaseAmount',
            'rebate': './{*}Price/{*}AllowanceCharge/{*}Amount',
            'net_price_unit': './{*}Price/{*}PriceAmount',
            'billed_qty':  './{*}InvoicedQuantity' if invoice_line.move_id.move_type in ('in_invoice', 'out_invoice') or qty_factor == -1 else './{*}CreditedQuantity',
            'allowance_charge': './/{*}AllowanceCharge',
            'allowance_charge_indicator': './{*}ChargeIndicator',
            'allowance_charge_amount': './{*}Amount',
            'allowance_charge_reason': './{*}AllowanceChargeReason',
            'allowance_charge_reason_code': './{*}AllowanceChargeReasonCode',
            'line_total_amount': './{*}LineExtensionAmount',
        }

        # Taxes
        inv_line_vals = self._import_fill_invoice_line_values(tree, xpath_dict, invoice_line, qty_factor)
        # retrieve tax nodes
        tax_nodes = tree.findall('.//{*}Item/{*}ClassifiedTaxCategory/{*}Percent')
        if not tax_nodes:
            for elem in tree.findall('.//{*}TaxTotal'):
                percentage_nodes = elem.findall('.//{*}TaxSubtotal/{*}TaxCategory/{*}Percent')
                if not percentage_nodes:
                    percentage_nodes = elem.findall('.//{*}TaxSubtotal/{*}Percent')
                tax_nodes += percentage_nodes
        return self._import_fill_invoice_line_taxes(tax_nodes, invoice_line, inv_line_vals, logs)

    def _correct_invoice_tax_amount(self, tree, invoice):
        """ The tax total may have been modified for rounding purpose, if so we should use the imported tax and not
         the computed one """
        currency = invoice.currency_id
        # For each tax in our tax total, get the amount as well as the total in the xml.
        # Negative tax amounts may appear in invoices; they have to be inverted (since they are credit notes).
        document_amount_sign = self._get_import_document_amount_sign(tree)[1] or 1
        # We only search for `TaxTotal/TaxSubtotal` in the "root" element (i.e. not in `InvoiceLine` elements).
        for elem in tree.findall('./{*}TaxTotal/{*}TaxSubtotal'):
            percentage = elem.find('.//{*}TaxCategory/{*}Percent')
            if percentage is None:
                percentage = elem.find('.//{*}Percent')
            amount = elem.find('.//{*}TaxAmount')
            if (percentage is not None and percentage.text is not None) and (amount is not None and amount.text is not None):
                tax_percent = float(percentage.text)
                # Compare the result with our tax total on the invoice, and apply correction if needed.
                # First look for taxes matching the percentage in the xml.
                taxes = invoice.line_ids.tax_line_id.filtered(lambda tax: tax.amount == tax_percent)
                # If we found taxes with the correct amount, look for a tax line using it, and correct it as needed.
                if taxes:
                    tax_total = document_amount_sign * float(amount.text)
                    # Sometimes we have multiple lines for the same tax.
                    tax_lines = invoice.line_ids.filtered(lambda line: line.tax_line_id in taxes)
                    if tax_lines:
                        sign = -1 if invoice.is_inbound(include_receipts=True) else 1
                        tax_lines_total = currency.round(sign * sum(tax_lines.mapped('amount_currency')))
                        difference = currency.round(tax_total - tax_lines_total)
                        if not currency.is_zero(difference):
                            tax_lines[0].amount_currency += sign * difference

    # -------------------------------------------------------------------------
    # IMPORT : helpers
    # -------------------------------------------------------------------------

    def _get_import_document_amount_sign(self, tree):
        """
        In UBL, an invoice has tag 'Invoice' and a credit note has tag 'CreditNote'. However, a credit note can be
        expressed as an invoice with negative amounts. For this case, we need a factor to take the opposite
        of each quantity in the invoice.
        """
        if tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice':
            amount_node = tree.find('.//{*}LegalMonetaryTotal/{*}TaxExclusiveAmount')
            if amount_node is not None and float(amount_node.text) < 0:
                return 'refund', -1
            return 'invoice', 1
        if tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote':
            return 'refund', 1
        return None, None
