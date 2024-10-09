from types import SimpleNamespace

from odoo import models
from odoo.tools import float_repr
from odoo.tools.float_utils import float_round


# There is a need for this dummy currency because:
# 1. In `ubl_20_templates.xml`, the currency name is read from currency like `vals['currency'].name`
# 2. In Jordanian EDI XML documentation, certain locations expect the currency name to be `JO` not `JOD`.
JO_CURRENCY = SimpleNamespace(name='JO')

JO_MAX_DP = 9

PAYMENT_CODES_MAP = {
    'income': {
        'cash': '011',
        'receivable': '021',
    },
    'sales': {
        'cash': '012',
        'receivable': '022',
    },
    'special': {
        'cash': '013',
        'receivable': '023',
    }
}


class AccountEdiXmlUBL21JO(models.AbstractModel):
    _name = "account.edi.xml.ubl_21.jo"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL 2.1 (JoFotara)"

    ####################################################
    # helper functions
    ####################################################

    def _round_max_dp(self, value):
        return float_round(value, JO_MAX_DP)

    def _get_line_amount_before_discount_jod(self, line, taxes_vals):
        amount_after_discount = taxes_vals['base_line']['tax_details']['raw_total_excluded']
        return amount_after_discount / (1 - line.discount / 100)

    def _get_line_discount_jod(self, line, taxes_vals):
        return self._get_line_amount_before_discount_jod(line, taxes_vals) * line.discount / 100

    def _get_unit_price_jod(self, line, taxes_vals):
        return self._get_line_amount_before_discount_jod(line, taxes_vals) / line.quantity

    def _get_payment_method_code(self, invoice):
        return PAYMENT_CODES_MAP[invoice.company_id.l10n_jo_edi_taxpayer_type]['receivable']

    def _aggregate_totals(self, vals):
        """
        This method is needed to ensure that units sum up to total values.
        ===================================================================================================
        Problem statement can be found inside tests/test_jo_edi_precision.py in the docstring of _validate_jo_edi_numbers
        -------------------------------------------------------------------------------
        Solution:
        taxes_vals (calculated from invoice._prepare_invoice_aggregated_taxes() in `account_edi_xml_ubl_20` module)
        is calculated to generate units with no rounding ensuring that these when aggregated sum up to the totals stored in Odoo.
        This method here uses these unit to calculate the totals again so that JoFotara validations don't fail.
        The difference between reported totals and Odoo stored totals in this case is < 0.001 JOD.
        """
        tax_inclusive_amount = 0
        tax_exclusive_amount = 0
        for line_val in vals['line_vals']:
            price_unit = self._round_max_dp(line_val['price_vals']['price_amount'])
            quantity = self._round_max_dp(line_val['line_quantity'])
            discount = self._round_max_dp(line_val['price_vals']['allowance_charge_vals'][0]['amount'])

            line_val['line_extension_amount'] = (price_unit * quantity) - discount

            total_tax_amount = 0
            if line_val['tax_total_vals']:
                for subtotal in line_val['tax_total_vals'][0]['tax_subtotal_vals']:
                    subtotal['taxable_amount'] = line_val['line_extension_amount']

                total_tax_amount = self._round_max_dp(sum(subtotal['tax_amount'] for subtotal in line_val['tax_total_vals'][0]['tax_subtotal_vals']))
                line_val['tax_total_vals'][0]['rounding_amount'] = line_val['line_extension_amount'] + total_tax_amount

            tax_exclusive_amount += (price_unit * quantity)
            tax_inclusive_amount += ((price_unit * quantity) - discount + total_tax_amount)

        vals['monetary_total_vals']['tax_inclusive_amount'] = vals['monetary_total_vals']['payable_amount'] = tax_inclusive_amount
        vals['monetary_total_vals']['tax_exclusive_amount'] = tax_exclusive_amount

    ########################################################
    # overriding vals methods of account_edi_xml_ubl_20 file
    ########################################################

    def _get_country_vals(self, country):
        return {
            'identification_code': country.code,
        }

    def _get_partner_party_identification_vals_list(self, partner):
        return [{
            'id_attrs': {'schemeID': 'TN'},
            'id': partner.vat,
        }]

    def _get_partner_address_vals(self, partner):
        return {
            'postal_zone': partner.zip,
            'country_subentity_code': partner.state_id.code,
            'country_vals': self._get_country_vals(partner.country_id),
        }

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        return [{
            'company_id': partner.vat,
            'tax_scheme_vals': {'id': 'VAT'},
        }]

    def _get_partner_party_legal_entity_vals_list(self, partner):
        return [{
            'registration_name': partner.name,
        }]

    def _get_partner_contact_vals(self, partner):
        return {}

    def _get_empty_party_vals(self):
        return {
            'postal_address_vals': {'country_vals': {'identification_code': 'JO'}},
            'party_tax_scheme_vals': [{'tax_scheme_vals': {'id': 'VAT'}}],
        }

    def _get_partner_party_vals(self, partner, role):
        vals = super()._get_partner_party_vals(partner, role)
        vals['party_name_vals'] = []
        if role == 'supplier':
            vals['party_identification_vals'] = []
        return vals

    def _get_delivery_vals_list(self, invoice):
        return []

    def _get_invoice_payment_means_vals_list(self, invoice):
        if invoice.move_type == 'out_refund':
            return [{
                'payment_means_code': 10,
                'payment_means_code_attrs': {'listID': "UN/ECE 4461"},
                'instruction_note': invoice.ref.replace('/', '_'),
            }]
        else:
            return []

    def _get_invoice_payment_terms_vals_list(self, invoice):
        return []

    def _get_invoice_tax_totals_vals_helper(self, taxes_vals):
        tax_totals_vals = {
            'currency': JO_CURRENCY,
            'currency_dp': self._get_currency_decimal_places(),
            'tax_amount': 0,
            'tax_subtotal_vals': [],
        }
        for grouping_key, vals in taxes_vals['tax_details'].items():
            if grouping_key['tax_amount_type'] != 'fixed':
                subtotal = {
                    'currency': JO_CURRENCY,
                    'currency_dp': self._get_currency_decimal_places(),
                    'taxable_amount': vals['raw_base_amount'],
                    'tax_amount': self._round_max_dp(vals['raw_base_amount']) * vals['tax_category_percent'] / 100,
                    'tax_category_vals': vals['_tax_category_vals_'],
                }
                tax_totals_vals['tax_subtotal_vals'].append(subtotal)
                tax_totals_vals['tax_amount'] += subtotal['tax_amount']

        return tax_totals_vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # Tax unregistered companies should have no tax values
        if invoice.company_id.l10n_jo_edi_taxpayer_type == 'income':
            return []

        vals = self._get_invoice_tax_totals_vals_helper(taxes_vals)
        if not invoice._is_sales_refund():
            vals['tax_subtotal_vals'] = []
        return [vals]

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        product = line.product_id
        description = line.name and line.name.replace('\n', ', ')
        return {
            'name': product.name or description,
        }

    def _get_document_allowance_charge_vals_list(self, invoice, taxes_vals):
        """ For JO UBL the document allowance charge vals needs to be the sum of the line discounts. """
        discount_amount = 0
        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section'))
        for line in invoice_lines:
            line_taxes_vals = taxes_vals['tax_details_per_record'][line]
            discount_amount += self._get_line_discount_jod(line, line_taxes_vals)
        return [{
            'charge_indicator': 'false',
            'allowance_charge_reason': 'discount',
            'currency_name': JO_CURRENCY.name,
            'currency_dp': self._get_currency_decimal_places(),
            'amount': discount_amount,
        }]

    def _get_invoice_line_allowance_vals_list(self, line, taxes_vals):
        return [{
            'charge_indicator': 'false',
            'allowance_charge_reason': 'DISCOUNT',
            'currency_name': JO_CURRENCY.name,
            'currency_dp': self._get_currency_decimal_places(),
            'amount': self._get_line_discount_jod(line, taxes_vals),
        }]

    def _get_invoice_line_price_vals(self, line, taxes_vals):
        return {
            'currency': JO_CURRENCY,
            'currency_dp': self._get_currency_decimal_places(),
            'price_amount': self._get_unit_price_jod(line, taxes_vals),
            'product_price_dp': self._get_currency_decimal_places(),
            'allowance_charge_vals': self._get_invoice_line_allowance_vals_list(line, taxes_vals),
            'base_quantity': None,
            'base_quantity_attrs': {'unitCode': self._get_uom_unece_code()},
        }

    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        # Tax unregistered companies should have no tax values
        if line.move_id.company_id.l10n_jo_edi_taxpayer_type == 'income':
            return []

        vals = self._get_invoice_tax_totals_vals_helper(taxes_vals)
        for grouping_key, tax_details_vals in taxes_vals['tax_details'].items():
            if grouping_key['tax_amount_type'] == 'fixed':
                subtotal = {
                    'currency': JO_CURRENCY,
                    'currency_dp': self._get_currency_decimal_places(),
                    'taxable_amount': tax_details_vals['raw_base_amount'],
                    'tax_amount': tax_details_vals['raw_tax_amount'],
                    'tax_category_vals': tax_details_vals['_tax_category_vals_'],
                }
                vals['tax_subtotal_vals'].insert(0, subtotal)
                vals['tax_subtotal_vals'][1]['taxable_amount'] = tax_details_vals['raw_base_amount']
        return [vals]

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        return {
            'currency': JO_CURRENCY,
            'currency_dp': self._get_currency_decimal_places(),
            'id': line_id + 1,
            'line_quantity': line.quantity,
            'line_quantity_attrs': {'unitCode': self._get_uom_unece_code()},
            'line_extension_amount': taxes_vals['base_line']['tax_details']['raw_total_excluded'],
            'tax_total_vals': self._get_invoice_line_tax_totals_vals_list(line, taxes_vals),
            'item_vals': self._get_invoice_line_item_vals(line, taxes_vals),
            'price_vals': self._get_invoice_line_price_vals(line, taxes_vals),
        }

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        return {
            'currency': JO_CURRENCY,
            'currency_dp': self._get_currency_decimal_places(),
            'allowance_total_amount': allowance_total_amount,
            'prepaid_amount': 0 if invoice._is_sales_refund() else None,
        }

    ####################################################
    # overriding vals methods of account_edi_common file
    ####################################################

    def format_float(self, amount, precision_digits):
        if amount is None:
            return None

        def get_decimal_places(number):
            return len(f'{float(number)}'.split('.')[1])

        rounded_amount = float_repr(self._round_max_dp(amount), JO_MAX_DP).rstrip('0').rstrip('.')
        decimal_places = get_decimal_places(rounded_amount)
        if decimal_places < precision_digits:
            rounded_amount = float_repr(float(rounded_amount), precision_digits)
        return rounded_amount

    def _get_currency_decimal_places(self, currency_id=None):
        # Invoices are always reported in JOD
        return self.env.ref('base.JOD').decimal_places

    def _get_uom_unece_code(self, line=None):
        return "PCE"

    def _get_tax_category_list(self, customer, supplier, tax):
        def get_tax_jo_ubl_code(tax):
            if tax._l10n_jo_is_exempt_tax():
                return "Z"
            if tax.amount:
                return "S"
            return "O"

        def get_jo_tax_type(tax):
            if tax.amount_type == 'percent':
                return 'general'
            elif tax.amount_type == 'fixed':
                return 'special'

        tax_type = get_jo_tax_type(tax)
        tax_code = get_tax_jo_ubl_code(tax)
        return [{
            'id': tax_code,
            'id_attrs': {'schemeAgencyID': '6', 'schemeID': 'UN/ECE 5305'},
            'percent': tax.amount if tax_type == 'general' else '',
            'tax_scheme_vals': {
                'id': 'VAT' if tax_type == 'general' else 'OTH',
                'id_attrs': {
                    'schemeAgencyID': '6',
                    'schemeID': 'UN/ECE 5153',
                },
            },
        }]

    ####################################################
    # vals methods of account.edi.xml.ubl_21.jo
    ####################################################

    def _get_billing_reference_vals(self, invoice):
        if not invoice.reversed_entry_id:
            return {}

        return {
            'id': invoice.reversed_entry_id.name.replace('/', '_'),
            'uuid': invoice.reversed_entry_id.l10n_jo_edi_uuid,
            'document_description': self.format_float(abs(invoice.reversed_entry_id.amount_total_signed), self._get_currency_decimal_places()),
        }

    def _get_additional_document_reference_list(self, invoice):
        return [{
            'id': 'ICV',
            'uuid': invoice.id,
        }]

    def _get_seller_supplier_party_vals(self, invoice):
        return {
            'party_identification_vals': [{'id': invoice.company_id.l10n_jo_edi_sequence_income_source}],
        }

    ####################################################
    # export methods
    ####################################################

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'main_template': 'l10n_jo_edi.ubl_jo_Invoice',
            'InvoiceType_template': 'l10n_jo_edi.ubl_jo_InvoiceType',
            'PaymentMeansType_template': 'l10n_jo_edi.ubl_jo_PaymentMeansType',
            'InvoiceLineType_template': 'l10n_jo_edi.ubl_jo_InvoiceLineType',
            'TaxTotalType_template': 'l10n_jo_edi.ubl_jo_TaxTotalType',
        })

        customer = invoice.partner_id
        is_refund = invoice.move_type == 'out_refund'

        vals['vals'].update({
            'ubl_version_id': '',
            'order_reference': '',
            'sales_order_id': '',
            'profile_id': 'reporting:1.0',
            'id': invoice.name.replace('/', '_'),
            'uuid': invoice.l10n_jo_edi_uuid,
            'document_currency_code': 'JOD',
            'tax_currency_code': 'JOD',
            'document_type_code_attrs': {'name': self._get_payment_method_code(invoice)},
            'document_type_code': "381" if is_refund else "388",
            'accounting_customer_party_vals': {
                'party_vals': self._get_empty_party_vals() if is_refund else self._get_partner_party_vals(customer, role='customer'),
                'accounting_contact': {
                    'telephone': '' if is_refund else invoice.partner_id.phone or invoice.partner_id.mobile,
                },
            },
            'seller_supplier_party_vals': {
                'party_vals': self._get_seller_supplier_party_vals(invoice),
            },
            'billing_reference_vals': self._get_billing_reference_vals(invoice),
            'additional_document_reference_list': self._get_additional_document_reference_list(invoice),
        })

        self._aggregate_totals(vals['vals'])

        return vals
