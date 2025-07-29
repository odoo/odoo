from collections import defaultdict
from lxml import etree

from odoo import _, models, Command
from odoo.tools import html2plaintext, cleanup_xml_node, float_is_zero, float_repr, float_round
from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.tools import Invoice, CreditNote, DebitNote

UBL_NAMESPACES = {
    'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


class FloatFmt(float):
    """ A float with a given precision.
    The precision is used when formatting the float.
    """
    def __new__(cls, value, min_dp=2, max_dp=None):
        return super().__new__(cls, value)

    def __init__(self, value, min_dp=2, max_dp=None):
        self.min_dp = min_dp
        self.max_dp = max_dp

    def __str__(self):
        if not isinstance(self.min_dp, int) or (self.max_dp is not None and not isinstance(self.max_dp, int)):
            return "<FloatFmt()>"
        self_float = float(self)
        min_dp_int = int(self.min_dp)
        if self.max_dp is None:
            return float_repr(self_float, min_dp_int)
        else:
            # Format the float to between self.min_dp and self.max_dp decimal places.
            # We start by formatting to self.max_dp, and then remove trailing zeros,
            # but always keep at least self.min_dp decimal places.
            max_dp_int = int(self.max_dp)
            amount_max_dp = float_repr(self_float, max_dp_int)
            num_trailing_zeros = len(amount_max_dp) - len(amount_max_dp.rstrip('0'))
            return float_repr(self_float, max(max_dp_int - num_trailing_zeros, min_dp_int))

    def __repr__(self):
        if not isinstance(self.min_dp, int) or (self.max_dp is not None and not isinstance(self.max_dp, int)):
            return "<FloatFmt()>"
        self_float = float(self)
        min_dp_int = int(self.min_dp)
        if self.max_dp is None:
            return f"FloatFmt({self_float!r}, {min_dp_int!r})"
        else:
            max_dp_int = int(self.max_dp)
            return f"FloatFmt({self_float!r}, {min_dp_int!r}, {max_dp_int!r})"


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
        if partner.ref:
            return [{'id': partner.ref}]
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
        if invoice.move_type == 'out_invoice':
            if invoice.partner_bank_id:
                payment_means_code, payment_means_name = (30, 'credit transfer')
            else:
                payment_means_code, payment_means_name = ('ZZZ', 'mutually defined')
        else:
            payment_means_code, payment_means_name = (57, 'standing agreement')

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
            if grouping_key['tax_amount_type'] != 'fixed' or not self._context.get('convert_fixed_taxes'):
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
        taxes = line.tax_ids.flatten_taxes_hierarchy()
        if self._context.get('convert_fixed_taxes'):
            taxes = taxes.filtered(lambda t: t.amount_type != 'fixed')
        customer = line.move_id.commercial_partner_id
        supplier = line.move_id.company_id.partner_id.commercial_partner_id
        tax_category_vals_list = self._get_tax_category_list(customer, supplier, taxes)
        description = line.name and line.name.replace('\n', ' ')
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

    def _get_document_allowance_charge_vals_list(self, invoice, taxes_vals=None):
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
        if self._context.get('convert_fixed_taxes'):
            for grouping_key, tax_details in tax_values_list['tax_details'].items():
                if grouping_key['tax_amount_type'] == 'fixed':
                    fixed_tax_charge_vals_list.append({
                        'currency_name': line.currency_id.name,
                        'currency_dp': self._get_currency_decimal_places(line.currency_id),
                        'charge_indicator': 'true',
                        'allowance_charge_reason_code': 'AEO',
                        'allowance_charge_reason': grouping_key['tax_name'],
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

        uom = self._get_uom_unece_code(line.product_uom_id)

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

        uom = self._get_uom_unece_code(line.product_uom_id)
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

    def _get_tax_grouping_key(self, base_line, tax_data):
        tax = tax_data['tax']
        customer = base_line['record'].move_id.commercial_partner_id
        supplier = base_line['record'].move_id.company_id.partner_id.commercial_partner_id
        tax_category_vals = self._get_tax_category_list(customer, supplier, tax)[0]
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

    def _export_invoice_vals(self, invoice):
        # Validate the structure of the taxes
        self._validate_taxes(invoice.invoice_line_ids.tax_ids)

        # Compute the tax details for the whole invoice and each invoice line separately.
        taxes_vals = invoice._prepare_invoice_aggregated_taxes(
            grouping_key_generator=self._get_tax_grouping_key,
            filter_tax_values_to_apply=self._apply_invoice_tax_filter,
            filter_invl_to_apply=self._apply_invoice_line_filter,
            round_from_tax_lines=True,
        )

        # Fixed Taxes: filter them on the document level, and adapt the totals
        # Fixed taxes are not supposed to be taxes in real live. However, this is the way in Odoo to manage recupel
        # taxes in Belgium. Since only one tax is allowed, the fixed tax is removed from totals of lines but added
        # as an extra charge/allowance.
        if self._context.get('convert_fixed_taxes'):
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
        document_allowance_charge_vals_list = self._get_document_allowance_charge_vals_list(invoice, taxes_vals)
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
            'InvoicePeriodType_template': 'account_edi_ubl_cii.ubl_20_InvoicePeriodType',
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
                'document_currency_code': invoice.currency_id.name,
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

    def _export_invoice(self, invoice, convert_fixed_taxes=True):
        """ Generates an UBL 2.0 xml for a given invoice.
        :param convert_fixed_taxes: whether the fixed taxes are converted into AllowanceCharges on the InvoiceLines
        """
        vals = self \
            .with_context(convert_fixed_taxes=convert_fixed_taxes) \
            ._export_invoice_vals(invoice.with_context(lang=invoice.partner_id.lang))
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
            'vat': self._find_value(f'.//cac:{role}Party/cac:Party//cbc:CompanyID[string-length(text()) > 5]', tree),
            'phone': self._find_value(f'.//cac:{role}Party/cac:Party//cbc:Telephone', tree),
            'email': self._find_value(f'.//cac:{role}Party/cac:Party//cbc:ElectronicMail', tree),
            'name': self._find_value(f'.//cac:{role}Party/cac:Party//cbc:Name', tree) or
                    self._find_value(f'.//cac:{role}Party/cac:Party//cbc:RegistrationName', tree),
            'country_code': self._find_value(f'.//cac:{role}Party/cac:Party//cac:Country//cbc:IdentificationCode', tree),
            'street': self._find_value(f'.//cac:{role}Party/cac:Party//cbc:StreetName', tree),
            'street2': self._find_value(f'.//cac:{role}Party/cac:Party//cbc:AdditionalStreetName', tree),
            'city': self._find_value(f'.//cac:{role}Party/cac:Party//cbc:CityName', tree),
            'zip_code': self._find_value(f'.//cac:{role}Party/cac:Party//cbc:PostalZone', tree),
        }

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        logs = []
        invoice_values = {}
        if qty_factor == -1:
            logs.append(_("The invoice has been converted into a credit note and the quantities have been reverted."))
        role = "AccountingCustomer" if invoice.journal_id.type == 'sale' else "AccountingSupplier"
        partner, partner_logs = self._import_partner(invoice.company_id, **self._import_retrieve_partner_vals(tree, role))
        # Need to set partner before to compute bank and lines properly
        invoice.partner_id = partner.id
        invoice_values['currency_id'], currency_logs = self._import_currency(tree, './/{*}DocumentCurrencyCode')
        invoice_values['invoice_date'] = tree.findtext('./{*}IssueDate')
        invoice_values['invoice_date_due'] = self._find_value(('./cbc:DueDate', './/cbc:PaymentDueDate'), tree)
        # ==== partner_bank_id ====
        bank_detail_nodes = tree.findall('.//{*}PaymentMeans')
        bank_details = [bank_detail_node.findtext('{*}PayeeFinancialAccount/{*}ID') for bank_detail_node in bank_detail_nodes]
        if bank_details:
            self._import_partner_bank(invoice, bank_details)

        # ==== ref, invoice_origin, narration, payment_reference ====
        ref = tree.findtext('./{*}ID')
        if ref and invoice.is_sale_document(include_receipts=True) and invoice.quick_edit_mode:
            invoice_values['name'] = ref
        elif ref:
            invoice_values['ref'] = ref
        invoice_values['invoice_origin'] = tree.findtext('./{*}OrderReference/{*}ID')
        invoice_values['narration'] = self._import_description(tree, xpaths=['./{*}Note', './{*}PaymentTerms/{*}Note'])
        invoice_values['payment_reference'] = tree.findtext('./{*}PaymentMeans/{*}PaymentID')

        # ==== Delivery ====
        delivery_date = tree.find('.//{*}Delivery/{*}ActualDeliveryDate')
        invoice.delivery_date = delivery_date is not None and delivery_date.text

        # ==== invoice_incoterm_id ====
        incoterm_code = tree.findtext('./{*}TransportExecutionTerms/{*}DeliveryTerms/{*}ID')
        if incoterm_code:
            incoterm = self.env['account.incoterms'].search([('code', '=', incoterm_code)], limit=1)
            if incoterm:
                invoice_values['invoice_incoterm_id'] = incoterm.id

        # ==== Document level AllowanceCharge, Prepaid Amounts, Invoice Lines, Payable Rounding Amount ====
        allowance_charges_line_vals, allowance_charges_logs = self._import_document_allowance_charges(tree, invoice, invoice.journal_id.type, qty_factor)
        logs += self._import_prepaid_amount(invoice, tree, './{*}LegalMonetaryTotal/{*}PrepaidAmount', qty_factor)
        line_tag = (
            'InvoiceLine'
            if invoice.move_type in ('in_invoice', 'out_invoice') or qty_factor == -1
            else 'CreditNoteLine'
        )
        invoice_line_vals, line_logs = self._import_invoice_lines(invoice, tree, './{*}' + line_tag, qty_factor)
        rounding_line_vals, rounding_logs = self._import_rounding_amount(invoice, tree, './{*}LegalMonetaryTotal/{*}PayableRoundingAmount', qty_factor)
        line_vals = allowance_charges_line_vals + invoice_line_vals + rounding_line_vals

        invoice_values = {
            **invoice_values,
            'invoice_line_ids': [Command.create(line_value) for line_value in line_vals],
        }
        invoice.write(invoice_values)
        logs += partner_logs + currency_logs + line_logs + allowance_charges_logs + rounding_logs
        return logs

    def _get_tax_nodes(self, tree):
        tax_nodes = tree.findall('.//{*}Item/{*}ClassifiedTaxCategory/{*}Percent')
        if not tax_nodes:
            for elem in tree.findall('.//{*}TaxTotal'):
                percentage_nodes = elem.findall('.//{*}TaxSubtotal/{*}TaxCategory/{*}Percent')
                if not percentage_nodes:
                    percentage_nodes = elem.findall('.//{*}TaxSubtotal/{*}Percent')
                tax_nodes += percentage_nodes
        return tax_nodes

    def _get_document_allowance_charge_xpaths(self):
        return {
            'root': './{*}AllowanceCharge',
            'charge_indicator': './{*}ChargeIndicator',
            'base_amount': './{*}BaseAmount',
            'amount': './{*}Amount',
            'reason': './{*}AllowanceChargeReason',
            'percentage': './{*}MultiplierFactorNumeric',
            'tax_percentage': './{*}TaxCategory/{*}Percent',
        }

    def _get_invoice_line_xpaths(self, document_type=False, qty_factor=1):
        return {
            'deferred_start_date': './{*}InvoicePeriod/{*}StartDate',
            'deferred_end_date': './{*}InvoicePeriod/{*}EndDate',
            'date_format': '%Y-%m-%d',
        }

    def _get_line_xpaths(self, document_type=False, qty_factor=1):
        return {
            'basis_qty': './cac:Price/cbc:BaseQuantity',
            'gross_price_unit': './{*}Price/{*}AllowanceCharge/{*}BaseAmount',
            'rebate': './{*}Price/{*}AllowanceCharge/{*}Amount',
            'net_price_unit': './{*}Price/{*}PriceAmount',
            'delivered_qty': (
                './{*}InvoicedQuantity'
                if document_type and document_type in ('in_invoice', 'out_invoice') or qty_factor == -1
                else './{*}CreditedQuantity'
            ),
            'allowance_charge': './/{*}AllowanceCharge',
            'allowance_charge_indicator': './{*}ChargeIndicator',
            'allowance_charge_amount': './{*}Amount',
            'allowance_charge_reason': './{*}AllowanceChargeReason',
            'allowance_charge_reason_code': './{*}AllowanceChargeReasonCode',
            'line_total_amount': './{*}LineExtensionAmount',
            'name': [
                './cac:Item/cbc:Description',
                './cac:Item/cbc:Name',
            ],
            'product': {
                'default_code': './cac:Item/cac:SellersItemIdentification/cbc:ID',
                'name': './cac:Item/cbc:Name',
                'barcode': './cac:Item/cac:StandardItemIdentification/cbc:ID[@schemeID="0160"]',
            },
        }

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

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _export_invoice_new(self, invoice):
        """ Generates an UBL 2.0 xml for a given invoice, using the new dict_to_xml helpers. """
        # 1. Validate the structure of the taxes
        self._validate_taxes(invoice.invoice_line_ids.tax_ids)

        # 2. Instantiate the XML builder
        vals = {'invoice': invoice.with_context(lang=invoice.partner_id.lang)}
        document_node = self._get_invoice_node(vals)

        # 3. Run constraints
        vals['document_node'] = document_node
        errors = [constraint for constraint in self._export_invoice_constraints_new(invoice, vals).values() if constraint]

        template = self._get_document_template(vals)
        nsmap = self._get_document_nsmap(vals)

        # 4. Render the XML
        xml_content = dict_to_xml(document_node, nsmap=nsmap, template=template)

        # 5. Format the XML
        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8'), set(errors)

    def _get_document_template(self, vals):
        return {
            'invoice': Invoice,
            'credit_note': CreditNote,
            'debit_note': DebitNote,
        }[vals['document_type']]

    def _get_document_nsmap(self, vals):
        return {
            None: {
                'invoice': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
                'credit_note': "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
                'debit_note': "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2",
                'order': "urn:oasis:names:specification:ubl:schema:xsd:Order-2",
            }[vals['document_type']],
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        }

    def _get_tags_for_document_type(self, vals):
        return {
            'document_type_code': {
                'invoice': 'cbc:InvoiceTypeCode',
                'credit_note': 'cbc:CreditNoteTypeCode',
                'debit_note': None,
                'order': 'cbc:OrderTypeCode',
            }[vals['document_type']],
            'monetary_total': {
                'invoice': 'cac:LegalMonetaryTotal',
                'credit_note': 'cac:LegalMonetaryTotal',
                'debit_note': 'cac:RequestedMonetaryTotal',
                'order': 'cac:AnticipatedMonetaryTotal',
            }[vals['document_type']],
            'document_line': {
                'invoice': 'cac:InvoiceLine',
                'credit_note': 'cac:CreditNoteLine',
                'debit_note': 'cac:DebitNoteLine',
                'order': 'cac:OrderLine',
            }[vals['document_type']],
            'line_quantity': {
                'invoice': 'cbc:InvoicedQuantity',
                'credit_note': 'cbc:CreditedQuantity',
                'debit_note': 'cbc:DebitedQuantity',
                'order': 'cbc:Quantity',
            }[vals['document_type']]
        }

    def _is_document_allowance_charge(self, base_line):
        """ Whether the base line should be treated as a document-level AllowanceCharge. """
        return base_line['special_type'] == 'early_payment'

    # -------------------------------------------------------------------------
    # EXPORT: account.move specific templates
    # -------------------------------------------------------------------------

    def _get_invoice_node(self, vals):
        self._add_invoice_config_vals(vals)
        self._add_invoice_base_lines_vals(vals)
        self._add_invoice_currency_vals(vals)
        self._add_invoice_tax_grouping_function_vals(vals)
        self._add_invoice_monetary_totals_vals(vals)

        document_node = {}
        self._add_invoice_header_nodes(document_node, vals)
        self._add_invoice_accounting_supplier_party_nodes(document_node, vals)
        self._add_invoice_accounting_customer_party_nodes(document_node, vals)
        self._add_invoice_seller_supplier_party_nodes(document_node, vals)

        if vals['document_type'] == 'invoice':
            self._add_invoice_delivery_nodes(document_node, vals)
            self._add_invoice_payment_means_nodes(document_node, vals)
            self._add_invoice_payment_terms_nodes(document_node, vals)

        self._add_invoice_allowance_charge_nodes(document_node, vals)
        self._add_invoice_exchange_rate_nodes(document_node, vals)
        self._add_invoice_tax_total_nodes(document_node, vals)
        self._add_invoice_monetary_total_nodes(document_node, vals)
        self._add_invoice_line_nodes(document_node, vals)
        return document_node

    def _add_invoice_config_vals(self, vals):
        invoice = vals['invoice']
        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.partner_id

        vals.update({
            'document_type': 'debit_note' if 'debit_origin_id' in self.env['account.move']._fields and invoice.debit_origin_id
                else 'credit_note' if invoice.move_type == 'out_refund'
                else 'invoice',

            'supplier': supplier,
            'customer': customer,
            'partner_shipping': invoice.partner_shipping_id or invoice.partner_id,

            'currency_id': invoice.currency_id,
            'company_currency_id': invoice.company_id.currency_id,

            'use_company_currency': False,  # If true, use the company currency for the amounts instead of the invoice currency
            'fixed_taxes_as_allowance_charges': True,  # If true, include fixed taxes as AllowanceCharges on lines instead of as taxes
        })

    def _add_invoice_base_lines_vals(self, vals):
        invoice = vals['invoice']
        base_lines, _tax_lines = invoice._get_rounded_base_and_tax_lines()
        vals['base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] != 'cash_rounding']
        vals['cash_rounding_base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] == 'cash_rounding']

    def _add_invoice_currency_vals(self, vals):
        self._add_document_currency_vals(vals)

    def _add_invoice_tax_grouping_function_vals(self, vals):
        self._add_document_tax_grouping_function_vals(vals)

    def _add_invoice_monetary_totals_vals(self, vals):
        self._add_document_monetary_total_vals(vals)

    def _add_invoice_header_nodes(self, document_node, vals):
        invoice = vals['invoice']
        document_node.update({
            'cbc:UBLVersionID': {'_text': '2.0'},
            'cbc:ID': {'_text': invoice.name},
            'cbc:IssueDate': {'_text': invoice.invoice_date},
            'cbc:InvoiceTypeCode': {'_text': 380} if vals['document_type'] == 'invoice' else None,
            'cbc:Note': {'_text': html2plaintext(invoice.narration)} if invoice.narration else None,
            'cbc:DocumentCurrencyCode': {'_text': invoice.currency_id.name},
            'cac:OrderReference': {
                # OrderReference/ID (order_reference) is mandatory inside the OrderReference node
                'cbc:ID': {'_text': invoice.ref or invoice.name},
                # OrderReference/SalesOrderID (sales_order_id) is optional
                'cbc:SalesOrderID': {
                    '_text': ",".join(invoice.invoice_line_ids.sale_line_ids.order_id.mapped('name'))
                } if 'sale_line_ids' in invoice.invoice_line_ids._fields else None,
            }
        })

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        document_node['cac:AccountingSupplierParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['supplier'], 'role': 'supplier'}),
        }

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        document_node['cac:AccountingCustomerParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['customer'], 'role': 'customer'}),
        }

    def _add_invoice_seller_supplier_party_nodes(self, document_node, vals):
        pass

    def _add_invoice_delivery_nodes(self, document_node, vals):
        invoice = vals['invoice']
        document_node['cac:Delivery'] = {
            'cbc:ActualDeliveryDate': {'_text': invoice.delivery_date},
            'cac:DeliveryLocation': {
                'cac:Address': self._get_address_node({'partner': vals['partner_shipping']})
            },
        }

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        invoice = vals['invoice']
        if invoice.move_type == 'out_invoice':
            if invoice.partner_bank_id:
                payment_means_code, payment_means_name = 30, 'credit transfer'
            else:
                payment_means_code, payment_means_name = 'ZZZ', 'mutually defined'
        else:
            payment_means_code, payment_means_name = 57, 'standing agreement'

        # in Denmark payment code 30 is not allowed. we hardcode it to 1 ("unknown") for now
        # as we cannot deduce this information from the invoice
        if invoice.partner_id.country_code == 'DK':
            payment_means_code, payment_means_name = 1, 'unknown'

        document_node['cac:PaymentMeans'] = {
            'cbc:PaymentMeansCode': {
                '_text': payment_means_code,
                'name': payment_means_name,
            },
            'cbc:PaymentDueDate': {'_text': invoice.invoice_date_due or invoice.invoice_date},
            'cbc:InstructionID': {'_text': invoice.payment_reference},
            'cbc:PaymentID': {'_text': invoice.payment_reference or invoice.name},
            'cac:PayeeFinancialAccount': self._get_financial_account_node({
                **vals, 'partner_bank': invoice.partner_bank_id
            }) if invoice.partner_bank_id else None
        }

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        invoice = vals['invoice']
        payment_term = invoice.invoice_payment_term_id
        if payment_term:
            document_node['cac:PaymentTerms'] = {
                # The payment term's note is automatically embedded in a <p> tag in Odoo
                'cbc:Note': {'_text': html2plaintext(payment_term.note)}
            }

    def _add_invoice_allowance_charge_nodes(self, document_node, vals):
        self._add_document_allowance_charge_nodes(document_node, vals)

    def _add_invoice_exchange_rate_nodes(self, document_node, vals):
        pass

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        self._add_document_tax_total_nodes(document_node, vals)

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        self._add_document_monetary_total_nodes(document_node, vals)
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        invoice = vals['invoice']
        document_node[monetary_total_tag].update({
            'cbc:PrepaidAmount': {
                '_text': self.format_float(invoice.amount_total - invoice.amount_residual, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:PayableRoundingAmount': {
                '_text': self.format_float(vals['cash_rounding_base_amount_currency'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals['cash_rounding_base_amount_currency'] else None,
            'cbc:PayableAmount': {
                '_text': self.format_float(invoice.amount_residual, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        })

    def _get_invoice_line_node(self, vals):
        self._add_invoice_line_vals(vals)

        line_node = {}
        self._add_invoice_line_id_nodes(line_node, vals)
        self._add_invoice_line_note_nodes(line_node, vals)
        self._add_invoice_line_amount_nodes(line_node, vals)
        self._add_invoice_line_period_nodes(line_node, vals)
        self._add_invoice_line_allowance_charge_nodes(line_node, vals)
        self._add_invoice_line_tax_total_nodes(line_node, vals)
        self._add_invoice_line_item_nodes(line_node, vals)
        self._add_invoice_line_tax_category_nodes(line_node, vals)
        self._add_invoice_line_price_nodes(line_node, vals)
        self._add_invoice_line_pricing_reference_nodes(line_node, vals)
        return line_node

    def _add_invoice_line_nodes(self, document_node, vals):
        line_idx = 1

        line_tag = self._get_tags_for_document_type(vals)['document_line']
        document_node[line_tag] = line_nodes = []
        for base_line in vals['base_lines']:
            # Only use product lines to generate the UBL InvoiceLines.
            # Other lines should be represented as AllowanceCharges.
            if not self._is_document_allowance_charge(base_line):
                line_vals = {
                    **vals,
                    'line_idx': line_idx,
                    'base_line': base_line,
                }
                line_node = self._get_invoice_line_node(line_vals)
                line_nodes.append(line_node)
                line_idx += 1

    def _add_invoice_line_vals(self, vals):
        self._add_document_line_vals(vals)

    def _add_invoice_line_id_nodes(self, line_node, vals):
        self._add_document_line_id_nodes(line_node, vals)

    def _add_invoice_line_note_nodes(self, line_node, vals):
        self._add_document_line_note_nodes(line_node, vals)

    def _add_invoice_line_amount_nodes(self, line_node, vals):
        self._add_document_line_amount_nodes(line_node, vals)

    def _add_invoice_line_period_nodes(self, line_node, vals):
        pass

    def _add_invoice_line_allowance_charge_nodes(self, line_node, vals):
        self._add_document_line_allowance_charge_nodes(line_node, vals)

    def _add_invoice_line_tax_total_nodes(self, line_node, vals):
        self._add_document_line_tax_total_nodes(line_node, vals)

    def _add_invoice_line_item_nodes(self, line_node, vals):
        self._add_document_line_item_nodes(line_node, vals)

        line = vals['base_line']['record']
        if line_name := line.name and line.name.replace('\n', ' '):
            line_node['cac:Item']['cbc:Description']['_text'] = line_name
            if not line_node['cac:Item']['cbc:Name']['_text']:
                line_node['cac:Item']['cbc:Name']['_text'] = line_name

    def _add_invoice_line_tax_category_nodes(self, line_node, vals):
        self._add_document_line_tax_category_nodes(line_node, vals)

    def _add_invoice_line_price_nodes(self, line_node, vals):
        self._add_document_line_price_nodes(line_node, vals)

    def _add_invoice_line_pricing_reference_nodes(self, line_node, vals):
        pass

    # -------------------------------------------------------------------------
    # EXPORT: Generic templates
    # -------------------------------------------------------------------------

    def _add_document_currency_vals(self, vals):
        """ Add the 'currency_suffix', 'currency_dp' and 'currency_name'. """
        vals['currency_suffix'] = '' if vals['use_company_currency'] else '_currency'

        currency = vals['company_currency_id'] if vals['use_company_currency'] else vals['currency_id']
        vals['currency_dp'] = self._get_currency_decimal_places(currency)
        vals['currency_name'] = currency.name

    def _add_document_tax_grouping_function_vals(self, vals):
        # Add the grouping functions for the monetary totals and tax totals
        customer = vals['customer']
        supplier = vals['supplier']

        # This function will be used when computing the monetary totals on the document level.
        # It should return True for all taxes which should be included in the total.
        def total_grouping_function(base_line, tax_data):
            return True

        # This function will be used when computing the tax totals on the document and line level.
        # It should group taxes together according to the tax catagory with which they will be reported.
        # Any taxes that should be included in the tax totals should be included.
        def tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            # Exclude fixed taxes if 'fixed_taxes_as_allowance_charges' is True
            if vals['fixed_taxes_as_allowance_charges'] and tax and tax.amount_type == 'fixed':
                return None
            return {
                'tax_category_code': self._get_tax_category_code(customer.commercial_partner_id, supplier, tax),
                **self._get_tax_exemption_reason(customer.commercial_partner_id, supplier, tax),
                'amount': tax.amount if tax else 0.0,
                'amount_type': tax.amount_type if tax else 'percent',
            }

        vals['total_grouping_function'] = total_grouping_function
        vals['tax_grouping_function'] = tax_grouping_function

    def _add_document_monetary_total_vals(self, vals):
        # Compute the monetary totals for the document
        def fixed_total_grouping_function(base_line, tax_data):
            if vals['fixed_taxes_as_allowance_charges'] and tax_data and tax_data['tax'].amount_type == 'fixed':
                return vals['total_grouping_function'](base_line, tax_data)

        for currency_suffix in ['', '_currency']:
            for key in ['total_allowance', 'total_charge', 'total_lines']:
                vals[f'{key}{currency_suffix}'] = 0.0

        for base_line in vals['base_lines']:
            aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, fixed_total_grouping_function)

            for currency_suffix in ['', '_currency']:
                base_line_total_excluded = \
                    base_line['tax_details'][f'total_excluded{currency_suffix}'] \
                    + base_line['tax_details'][f'delta_total_excluded{currency_suffix}'] \
                    + sum(
                        tax_details[f'tax_amount{currency_suffix}']
                        for grouping_key, tax_details in aggregated_tax_details.items()
                        if grouping_key
                    )

                if self._is_document_allowance_charge(base_line):
                    if base_line_total_excluded < 0.0:
                        vals[f'total_allowance{currency_suffix}'] += -base_line_total_excluded
                    else:
                        vals[f'total_charge{currency_suffix}'] += base_line_total_excluded
                else:
                    vals[f'total_lines{currency_suffix}'] += base_line_total_excluded

        for currency_suffix in ['', '_currency']:
            vals[f'tax_exclusive_amount{currency_suffix}'] = vals[f'total_lines{currency_suffix}'] \
                + vals[f'total_charge{currency_suffix}'] \
                - vals[f'total_allowance{currency_suffix}']

        def non_fixed_total_grouping_function(base_line, tax_data):
            if vals['fixed_taxes_as_allowance_charges'] and tax_data and tax_data['tax'].amount_type == 'fixed':
                return None
            return vals['total_grouping_function'](base_line, tax_data)

        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], non_fixed_total_grouping_function)
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        for currency_suffix in ['', '_currency']:
            vals[f'tax_inclusive_amount{currency_suffix}'] = vals[f'tax_exclusive_amount{currency_suffix}'] \
                + sum(
                    tax_details[f'tax_amount{currency_suffix}']
                    for grouping_key, tax_details in aggregated_tax_details.items()
                    if grouping_key
                )

        # Cash rounding for 'add_invoice_line' cash rounding strategy
        # (For the 'biggest_tax' strategy the amounts are directly included in the tax amounts.)
        for currency_suffix in ['', '_currency']:
            vals[f'cash_rounding_base_amount{currency_suffix}'] = 0.0
            for base_line in vals.setdefault('cash_rounding_base_lines', []):
                tax_details = base_line['tax_details']
                vals[f'cash_rounding_base_amount{currency_suffix}'] += tax_details[f'total_excluded{currency_suffix}']

    # -------------------------------------------------------------------------
    # EXPORT: Generic templates - partner-related nodes
    # -------------------------------------------------------------------------

    def _get_address_node(self, vals):
        """ Generic helper to generate the Address node for a res.partner or res.bank. """
        partner = vals['partner']
        country_key = 'country' if partner._name == 'res.bank' else 'country_id'
        state_key = 'state' if partner._name == 'res.bank' else 'state_id'
        country = partner[country_key]
        state = partner[state_key]

        return {
            'cbc:StreetName': {'_text': partner.street},
            'cbc:AdditionalStreetName': {'_text': partner.street2},
            'cbc:CityName': {'_text': partner.city},
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentity': {'_text': state.name},
            'cbc:CountrySubentityCode': {'_text': state.code},
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': country.code},
                'cbc:Name': {'_text': country.name},
            },
        }

    def _get_party_node(self, vals):
        """ Generic helper to generate the Party node for a res.partner. """
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id
        return {
            'cac:PartyIdentification': {
                'cbc:ID': {'_text': commercial_partner.ref},
            },
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name},
            },
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
                'cac:RegistrationAddress': self._get_address_node({**vals, 'partner': commercial_partner}),
                'cac:TaxScheme': {
                    'cbc:ID': {
                        '_text': ('NOT_EU_VAT' if commercial_partner.country_id and
                                commercial_partner.vat and
                                not commercial_partner.vat[:2].isalpha() else 'VAT')
                    }
                },
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
                'cac:RegistrationAddress': self._get_address_node({**vals, 'partner': commercial_partner}),
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {'_text': partner.phone},
                'cbc:ElectronicMail': {'_text': partner.email},
            },
        }

    def _get_financial_account_node(self, vals):
        """ Generic helper to generate the FinancialAccount node for a res.partner.bank """
        partner_bank = vals['partner_bank']
        bank = partner_bank.bank_id
        financial_institution_branch = None
        if bank:
            financial_institution_branch = {
                'cbc:ID': {
                    '_text': bank.bic,
                    'schemeID': 'BIC'
                },
                'cac:FinancialInstitution': {
                    'cbc:ID': {
                        '_text': bank.bic,
                        'schemeID': 'BIC'
                    },
                    'cbc:Name': {'_text': bank.name},
                    'cac:Address': self._get_address_node({**vals, 'partner': bank})
                }
            }
        return {
            'cbc:ID': {'_text': partner_bank.acc_number.replace(' ', '')},
            'cac:FinancialInstitutionBranch': financial_institution_branch
        }

    # -------------------------------------------------------------------------
    # EXPORT: Generic templates for tax-related nodes
    # -------------------------------------------------------------------------

    def _add_document_tax_total_nodes(self, document_node, vals):
        """ Generic helper to fill the TaxTotal and WithholdingTaxTotal nodes for a document. """
        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], vals['tax_grouping_function'])
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        document_node['cac:TaxTotal'] = self._get_tax_total_node({**vals, 'aggregated_tax_details': aggregated_tax_details, 'role': 'document'})
        document_node['cac:WithholdingTaxTotal'] = None

    def _add_tax_total_node_in_company_currency(self, document_node, vals):
        """ Generic helper to add a TaxTotal section in the company currency. """
        company_currency = vals['invoice'].company_id.currency_id
        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], vals['tax_grouping_function'])
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        tax_total_node_in_company_currency = self._get_tax_total_node({
            **vals,
            'aggregated_tax_details': aggregated_tax_details,
            'currency_suffix': '',
            'currency_dp': self._get_currency_decimal_places(company_currency),
            'currency_name': company_currency.name,
            'role': 'document'
        })
        document_node['cac:TaxTotal'].append(tax_total_node_in_company_currency)

    def _get_tax_total_node(self, vals):
        """ Generic helper to generate a TaxTotal node given a dict of aggregated tax details. """
        aggregated_tax_details = vals['aggregated_tax_details']
        currency_suffix = vals['currency_suffix']
        sign = vals.get('sign', 1)
        total_tax_amount = sum(
            values[f'tax_amount{currency_suffix}']
            for grouping_key, values in aggregated_tax_details.items()
            if grouping_key
        )
        return {
            'cbc:TaxAmount': {
                '_text': self.format_float(sign * total_tax_amount, vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cac:TaxSubtotal': [
                self._get_tax_subtotal_node({
                    **vals,
                    'tax_details': tax_details,
                    'grouping_key': grouping_key,
                })
                for grouping_key, tax_details in aggregated_tax_details.items()
                if grouping_key
            ]
        }

    def _get_tax_subtotal_node(self, vals):
        """ Generic helper to generate a TaxSubtotal node given a tax grouping key dict and associated tax values. """
        tax_details = vals['tax_details']
        grouping_key = vals['grouping_key']
        sign = vals.get('sign', 1)
        currency_suffix = vals['currency_suffix']
        return {
            'cbc:TaxableAmount': {
                '_text': self.format_float(tax_details[f'base_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:TaxAmount': {
                '_text': self.format_float(sign * tax_details[f'tax_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:Percent': {'_text': grouping_key['amount']} if grouping_key['amount_type'] == 'percent' else None,
            'cac:TaxCategory': self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
        }

    def _get_tax_category_node(self, vals):
        """ Generic helper to generate a TaxCategory node given a tax grouping key dict. """
        grouping_key = vals['grouping_key']
        return {
            'cbc:ID': {'_text': grouping_key['tax_category_code']},
            'cbc:Name': {'_text': grouping_key.get('name')},
            'cbc:Percent': {'_text': grouping_key['amount']} if grouping_key['amount_type'] == 'percent' else None,
            'cbc:TaxExemptionReasonCode': {'_text': grouping_key.get('tax_exemption_reason_code')},
            'cbc:TaxExemptionReason': {'_text': grouping_key.get('tax_exemption_reason')},
            'cac:TaxScheme': {
                'cbc:ID': {'_text': 'VAT'},
            }
        }

    def _add_document_monetary_total_nodes(self, document_node, vals):
        """ Generic helper to fill the MonetaryTotal node for a document given a list of base_lines. """
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        currency_suffix = vals['currency_suffix']

        document_node[monetary_total_tag] = {
            'cbc:LineExtensionAmount': {
                '_text': self.format_float(vals[f'total_lines{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:TaxExclusiveAmount': {
                '_text': self.format_float(vals[f'tax_exclusive_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:TaxInclusiveAmount': {
                '_text': self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:AllowanceTotalAmount': {
                '_text': self.format_float(vals[f'total_allowance{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals[f'total_allowance{currency_suffix}'] else None,
            'cbc:ChargeTotalAmount': {
                '_text': self.format_float(vals[f'total_charge{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals[f'total_charge{currency_suffix}'] else None,
            'cbc:PrepaidAmount': {
                '_text': self.format_float(0.0, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:PayableRoundingAmount': {
                '_text': self.format_float(vals[f'cash_rounding_base_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals[f'cash_rounding_base_amount{currency_suffix}'] else None,
            'cbc:PayableAmount': {
                '_text': self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }

    def _get_document_line_node(self, vals):
        self._add_document_line_vals(vals)

        line_node = {}
        self._add_document_line_id_nodes(line_node, vals)
        self._add_document_line_note_nodes(line_node, vals)
        self._add_document_line_amount_nodes(line_node, vals)
        self._add_document_line_period_nodes(line_node, vals)
        self._add_document_line_allowance_charge_nodes(line_node, vals)
        self._add_document_line_tax_total_nodes(line_node, vals)
        self._add_document_line_item_nodes(line_node, vals)
        self._add_document_line_tax_category_nodes(line_node, vals)
        self._add_document_line_price_nodes(line_node, vals)
        self._add_document_line_pricing_reference_nodes(line_node, vals)
        return line_node

    def _add_document_line_nodes(self, document_node, vals):
        line_idx = 1

        line_tag = self._get_tags_for_document_type(vals)['document_line']
        document_node[line_tag] = line_nodes = []
        for base_line in vals['base_lines']:
            if not self._is_document_allowance_charge(base_line):
                line_vals = {
                    **vals,
                    'line_idx': line_idx,
                    'base_line': base_line,
                }
                line_node = self._get_document_line_node(line_vals)
                line_nodes.append(line_node)
                line_idx += 1

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document-level allowance charge nodes
    # -------------------------------------------------------------------------

    def _add_document_allowance_charge_nodes(self, document_node, vals):
        """ Generic helper to fill the AllowanceCharge nodes for a document given a list of base_lines. """
        # AllowanceCharge doesn't exist in debit notes in UBL 2.0
        if vals['document_type'] != 'debit_note':
            document_node['cac:AllowanceCharge'] = []
            for base_line in vals['base_lines']:
                if self._is_document_allowance_charge(base_line):
                    document_node['cac:AllowanceCharge'].append(
                        self._get_document_allowance_charge_node({**vals, 'base_line': base_line})
                    )

    def _get_document_allowance_charge_node(self, vals):
        """ Generic helper to generate a document-level AllowanceCharge node given a base_line. """
        base_line = vals['base_line']
        currency_suffix = vals['currency_suffix']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])
        base_amount = base_line['tax_details'][f'total_excluded{currency_suffix}']
        return {
            'cbc:ChargeIndicator': {'_text': 'false' if base_amount < 0.0 else 'true'},
            'cbc:AllowanceChargeReasonCode': {'_text': '66' if base_amount < 0.0 else 'ZZZ'},
            'cbc:AllowanceChargeReason': {'_text': _("Conditional cash/payment discount")},
            'cbc:Amount': {
                '_text': self.format_float(abs(base_amount), vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cac:TaxCategory': [
                self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
                for grouping_key in aggregated_tax_details
                if grouping_key
            ]
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for line nodes
    # -------------------------------------------------------------------------

    def _add_document_line_vals(self, vals):
        """ Generic helper to calculate the amounts for a document line. """
        self._add_document_line_total_vals(vals)
        self._add_document_line_gross_subtotal_and_discount_vals(vals)

    def _add_document_line_total_vals(self, vals):
        base_line = vals['base_line']

        def fixed_total_grouping_function(base_line, tax_data):
            if vals['fixed_taxes_as_allowance_charges'] and tax_data and tax_data['tax'].amount_type == 'fixed':
                return vals['total_grouping_function'](base_line, tax_data)

        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, fixed_total_grouping_function)

        for currency_suffix in ['', '_currency']:
            vals[f'total_fixed_taxes{currency_suffix}'] = sum(
                tax_details[f'tax_amount{currency_suffix}']
                for grouping_key, tax_details in aggregated_tax_details.items()
                if grouping_key
            )

            vals[f'total_excluded{currency_suffix}'] = \
                base_line['tax_details'][f'total_excluded{currency_suffix}'] \
                + base_line['tax_details'][f'delta_total_excluded{currency_suffix}'] \
                + vals[f'total_fixed_taxes{currency_suffix}']

    def _add_document_line_gross_subtotal_and_discount_vals(self, vals):
        base_line = vals['base_line']
        company_currency = vals['company_currency_id']

        discount_factor = 1 - (base_line['discount'] / 100.0)

        if discount_factor != 0.0:
            gross_subtotal_currency = base_line['currency_id'].round(base_line['tax_details']['raw_total_excluded_currency'] / discount_factor)
            gross_subtotal = company_currency.round(base_line['tax_details']['raw_total_excluded'] / discount_factor)
        else:
            gross_subtotal_currency = base_line['currency_id'].round(base_line['price_unit'] * base_line['quantity'])
            gross_subtotal = company_currency.round(gross_subtotal_currency / base_line['rate'])

        if base_line['quantity'] == 0.0 or discount_factor == 0.0:
            gross_price_unit_currency = base_line['price_unit']
            gross_price_unit = company_currency.round(base_line['price_unit'] / base_line['rate'])
        else:
            gross_price_unit_currency = gross_subtotal_currency / base_line['quantity']
            gross_price_unit = gross_subtotal / base_line['quantity']

        discount_amount_currency = gross_subtotal_currency - base_line['tax_details']['total_excluded_currency']
        discount_amount = gross_subtotal - base_line['tax_details']['total_excluded']

        vals.update({
            'discount_amount_currency': discount_amount_currency,
            'discount_amount': discount_amount,
            'gross_subtotal_currency': gross_subtotal_currency,
            'gross_subtotal': gross_subtotal,
            'gross_price_unit_currency': gross_price_unit_currency,
            'gross_price_unit': gross_price_unit,
        })

    def _add_document_line_id_nodes(self, line_node, vals):
        line_node['cbc:ID'] = {'_text': vals['line_idx']}

    def _add_document_line_note_nodes(self, line_node, vals):
        pass

    def _add_document_line_amount_nodes(self, line_node, vals):
        currency_suffix = vals['currency_suffix']
        base_line = vals['base_line']

        quantity_tag = self._get_tags_for_document_type(vals)['line_quantity']

        line_node.update({
            quantity_tag: {
                '_text': base_line['quantity'],
                'unitCode': self._get_uom_unece_code(base_line['product_uom_id']),
            },
            'cbc:LineExtensionAmount': {
                '_text': self.format_float(vals[f'total_excluded{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        })

    def _add_document_line_period_nodes(self, line_node, vals):
        pass

    def _add_document_line_item_nodes(self, line_node, vals):
        product = vals['base_line']['product_id']

        line_node['cac:Item'] = {
            'cbc:Description': {'_text': product.description_sale},
            'cbc:Name': {'_text': product.name},
            'cac:SellersItemIdentification': {
                'cbc:ID': {'_text': product.default_code},
            },
            'cac:StandardItemIdentification': {
                'cbc:ID': {
                    '_text': product.barcode,
                    'schemeID': '0160',  # GTIN
                } if product.barcode else None,
            },
            'cac:AdditionalItemProperty': [
                {
                    'cbc:Name': {'_text': value.attribute_id.name},
                    'cbc:Value': {'_text': value.name},
                } for value in product.product_template_attribute_value_ids
            ],
        }

    def _add_document_line_allowance_charge_nodes(self, line_node, vals):
        if vals['document_type'] not in {'credit_note', 'debit_note'}:
            line_node['cac:AllowanceCharge'] = [self._get_line_discount_allowance_charge_node(vals)]
            if vals['fixed_taxes_as_allowance_charges']:
                line_node['cac:AllowanceCharge'].extend(self._get_line_fixed_tax_allowance_charge_nodes(vals))

    def _get_line_discount_allowance_charge_node(self, vals):
        currency_suffix = vals['currency_suffix']
        if float_is_zero(vals[f'discount_amount{currency_suffix}'], precision_digits=vals['currency_dp']):
            return None

        return {
            'cbc:ChargeIndicator': {'_text': 'false' if vals[f'discount_amount{currency_suffix}'] > 0 else 'true'},
            'cbc:AllowanceChargeReasonCode': {'_text': '95'},
            'cbc:Amount': {
                '_text': self.format_float(
                    abs(vals[f'discount_amount{currency_suffix}']),
                    vals['currency_dp'],
                ),
                'currencyID': vals['currency_name'],
            },
        }

    def _get_line_fixed_tax_allowance_charge_nodes(self, vals):
        fixed_tax_aggregated_tax_details = self._get_line_fixed_tax_aggregated_tax_details(vals)
        currency_suffix = vals['currency_suffix']

        allowance_charge_nodes = []
        for grouping_key, tax_details in fixed_tax_aggregated_tax_details.items():
            if grouping_key:
                allowance_charge_nodes.append({
                    'cbc:ChargeIndicator': {'_text': 'true' if tax_details[f'tax_amount{currency_suffix}'] > 0 else 'false'},
                    'cbc:AllowanceChargeReasonCode': {'_text': 'AEO'},
                    'cbc:AllowanceChargeReason': {'_text': grouping_key},
                    'cbc:Amount': {
                        '_text': self.format_float(
                            abs(tax_details[f'tax_amount{currency_suffix}']),
                            vals['currency_dp'],
                        ),
                        'currencyID': vals['currency_name'],
                    },
                })
        return allowance_charge_nodes

    def _get_line_fixed_tax_aggregated_tax_details(self, vals):
        base_line = vals['base_line']

        def fixed_tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            if not tax or tax.amount_type != 'fixed':
                return None
            return tax.name

        return self.env['account.tax']._aggregate_base_line_tax_details(base_line, fixed_tax_grouping_function)

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])
        line_node.setdefault('cac:Item', {})['cac:ClassifiedTaxCategory'] = [
            self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
            for grouping_key in aggregated_tax_details
            if grouping_key
        ]

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])
        line_node['cac:TaxTotal'] = self._get_tax_total_node({**vals, 'aggregated_tax_details': aggregated_tax_details, 'role': 'line'})

    def _add_document_line_price_nodes(self, line_node, vals):
        currency_suffix = vals['currency_suffix']
        product_price_dp = self.env['decimal.precision'].precision_get('Product Price')

        line_node['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': float_round(
                    vals[f'gross_price_unit{currency_suffix}'],
                    precision_digits=product_price_dp,
                ),
                'currencyID': vals['currency_name'],
            },
        }

    def _add_document_line_pricing_reference_nodes(self, line_node, vals):
        pass
