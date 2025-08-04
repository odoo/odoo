from lxml import etree
import re
from types import SimpleNamespace

from odoo import models
from odoo.tools import float_repr
from odoo.tools.float_utils import float_round


# There is a need for this dummy currency because:
# 1. In `ubl_20_templates.xml`, the currency name is read from currency like `vals['currency'].name`
# 2. In Jordanian EDI XML documentation, certain locations expect the currency name to be `JO` not `JOD`.
JO_CURRENCY = SimpleNamespace(name='JO')

JO_MAX_DP = 9


class AccountEdiXmlUBL21JO(models.AbstractModel):
    _name = "account.edi.xml.ubl_21.jo"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL 2.1 (JoFotara)"

    ####################################################
    # helper functions
    ####################################################

    def _round_max_dp(self, value):
        return float_round(value, JO_MAX_DP)

    def _get_line_amount_before_discount_jod(self, line):
        if line.discount < 100 and line.tax_ids:
            taxes_res = line.tax_ids.with_context({'round_base': False}).compute_all(
                line.price_unit,
                quantity=line.quantity,
                currency=line.currency_id,
                product=line.product_id,
                partner=line.partner_id,
                is_refund=line.is_refund,
            )
            return taxes_res['total_excluded']
        else:
            # reported numbers won't matter if discount is 100%
            return line.price_unit * line.quantity

    def _get_line_discount_jod(self, line):
        return self._get_line_amount_before_discount_jod(line) * line.discount / 100

    def _get_unit_price_jod(self, line):
        return self._get_line_amount_before_discount_jod(line) / line.quantity

    def _get_line_taxable_amount(self, line):
        return self._round_max_dp(self._get_unit_price_jod(line)) * self._round_max_dp(line.quantity) - self._round_max_dp(self._get_line_discount_jod(line))

    def _get_payment_method_code(self, invoice):
        return invoice._get_invoice_scope_code() + invoice._get_invoice_payment_method_code() + invoice._get_invoice_tax_payer_type_code()

    def _get_line_edi_id(self, line, default_id):
        if not line.is_refund:  # in case it's invoice not credit note
            return default_id

        refund_move = line.move_id
        invoice_move = refund_move.reversed_entry_id
        invoice_lines = invoice_move.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section'))
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

            total_tax_amount = 0
            if line_val['tax_total_vals']:
                total_tax_amount = self._round_max_dp(sum(self._round_max_dp(subtotal['tax_amount']) for subtotal in line_val['tax_total_vals'][0]['tax_subtotal_vals']))
                line_val['tax_total_vals'][0]['rounding_amount'] = self._round_max_dp(line_val['line_extension_amount']) + total_tax_amount

            tax_exclusive_amount += self._round_max_dp(price_unit * quantity)
            tax_inclusive_amount += self._round_max_dp((price_unit * quantity) - discount + total_tax_amount)

        vals['monetary_total_vals']['tax_inclusive_amount'] = vals['monetary_total_vals']['payable_amount'] = tax_inclusive_amount
        vals['monetary_total_vals']['tax_exclusive_amount'] = tax_exclusive_amount

    def _sanitize_phone(self, raw):
        return re.sub(r'[^0-9]', '', raw or '')[:15]

    ########################################################
    # overriding vals methods of account_edi_xml_ubl_20 file
    ########################################################

    def _get_country_vals(self, country):
        return {
            'identification_code': country.code,
        }

    def _get_partner_party_identification_vals_list(self, partner):
        return [{
            'id_attrs': {'schemeID': 'TN' if partner.country_code == 'JO' else 'PN'},
            'id': partner.vat if partner.vat and partner.vat != '/' else 'NO_VAT',
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
                'instruction_note': (invoice.ref or '').replace('/', '_'),
            }]
        else:
            return []

    def _get_invoice_payment_terms_vals_list(self, invoice):
        return []

    def _get_invoice_tax_totals_vals_helper(self, taxes_vals, special_tax_amount_per_line):
        tax_totals_vals = {
            'currency': JO_CURRENCY,
            'currency_dp': self._get_currency_decimal_places(),
            'tax_amount': 0,
            'tax_subtotal_vals': [],
        }
        for grouping_key, vals in taxes_vals['tax_details'].items():
            if grouping_key['tax_amount_type'] != 'fixed':
                special_tax_amount = sum(special_tax_amount_per_line.get(line, 0) for line in vals['records'])
                taxable_amount = sum(self._round_max_dp(self._get_line_taxable_amount(line)) for line in vals['records']) + special_tax_amount
                subtotal = {
                    'currency': JO_CURRENCY,
                    'currency_dp': self._get_currency_decimal_places(),
                    'taxable_amount': taxable_amount,
                    'tax_amount': self._round_max_dp(taxable_amount) * vals['tax_category_percent'] / 100,
                    'tax_category_vals': vals['_tax_category_vals_'],
                }
                tax_totals_vals['tax_subtotal_vals'].append(subtotal)
                tax_totals_vals['tax_amount'] += subtotal['tax_amount']

        return tax_totals_vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # Tax unregistered companies should have no tax values
        if invoice.company_id.l10n_jo_edi_taxpayer_type == 'income':
            return []

        special_tax_amount_per_line = {
            line: line_tax['tax_amount_currency']
            for line, line_vals in taxes_vals['tax_details_per_record'].items()
            for line_tax in line_vals['tax_details'].values()
            if 'tax_amount_type' in line_tax and line_tax['tax_amount_type'] == 'fixed'
        }
        vals = self._get_invoice_tax_totals_vals_helper(taxes_vals, special_tax_amount_per_line)
        if not invoice._is_sales_refund():
            vals['tax_subtotal_vals'] = []
        return [vals]

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        product = line.product_id
        description = (line.name or '').replace('\n', ', ')
        return {
            'name': product.name or description,
        }

    def _get_document_allowance_charge_vals_list(self, invoice):
        """ For JO UBL the document allowance charge vals needs to be the sum of the line discounts. """
        discount_amount = 0
        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section'))
        for line in invoice_lines:
            discount_amount += self._round_max_dp(self._get_line_discount_jod(line))
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
            'amount': self._get_line_discount_jod(line),
        }]

    def _get_invoice_line_price_vals(self, line, taxes_vals):
        return {
            'currency': JO_CURRENCY,
            'currency_dp': self._get_currency_decimal_places(),
            'price_amount': self._get_unit_price_jod(line),
            'product_price_dp': self._get_currency_decimal_places(),
            'allowance_charge_vals': self._get_invoice_line_allowance_vals_list(line, taxes_vals),
            'base_quantity': None,
            'base_quantity_attrs': {'unitCode': self._get_uom_unece_code()},
        }

    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        # Tax unregistered companies should have no tax values
        if line.move_id.company_id.l10n_jo_edi_taxpayer_type == 'income':
            return []

        special_tax_amount = 0
        special_tax_subtotal = None
        taxable_amount = 0
        for grouping_key, tax_details_vals in taxes_vals['tax_details'].items():
            if grouping_key['tax_amount_type'] == 'fixed':
                taxable_amount = sum(self._round_max_dp(self._get_line_taxable_amount(line)) for line in tax_details_vals['records'])
                special_tax_amount = tax_details_vals['tax_amount_currency']
                special_tax_subtotal = {
                    'currency': JO_CURRENCY,
                    'currency_dp': self._get_currency_decimal_places(),
                    'taxable_amount': taxable_amount,
                    'tax_amount': special_tax_amount,
                    'tax_category_vals': tax_details_vals['_tax_category_vals_'],
                }
        vals = self._get_invoice_tax_totals_vals_helper(taxes_vals, special_tax_amount_per_line={line: special_tax_amount})
        if special_tax_subtotal:
            vals['tax_subtotal_vals'].insert(0, special_tax_subtotal)
            vals['tax_subtotal_vals'][1]['taxable_amount'] = taxable_amount
        return [vals]

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        return {
            'currency': JO_CURRENCY,
            'currency_dp': self._get_currency_decimal_places(),
            'id': self._get_line_edi_id(line, default_id=line_id + 1),
            'line_quantity': line.quantity,
            'line_quantity_attrs': {'unitCode': self._get_uom_unece_code()},
            'line_extension_amount': self._get_line_taxable_amount(line),
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

        rounded_amount = float_repr(self._round_max_dp(amount), JO_MAX_DP).rstrip('0').rstrip('.')
        decimal_places = len(rounded_amount.split('.')[1]) if '.' in rounded_amount else 0
        if decimal_places < precision_digits:
            rounded_amount = float_repr(float(rounded_amount), precision_digits)
        return rounded_amount

    def _get_currency_decimal_places(self, currency_id=None):
        # Invoices are always reported in JOD
        return self.env.ref('base.JOD').decimal_places

    def _get_uom_unece_code(self, line=None):
        return "PCE"

    def _get_tax_category_list(self, invoice, taxes):
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

        res = []
        for tax in taxes:
            tax_type = get_jo_tax_type(tax)
            tax_code = get_tax_jo_ubl_code(tax)
            res.append({
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
            })
        return res

    ####################################################
    # vals methods of account.edi.xml.ubl_21.jo
    ####################################################

    def _get_billing_reference_vals(self, invoice):
        if not invoice.reversed_entry_id:
            return {}

        return {
            'id': (invoice.reversed_entry_id.name or '').replace('/', '_'),
            'uuid': invoice.reversed_entry_id.l10n_jo_edi_uuid,
            'document_description': self.format_float(abs(invoice.reversed_entry_id.amount_total), self._get_currency_decimal_places()),
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
            'document_currency_code': invoice.currency_id.name,
            'tax_currency_code': invoice.currency_id.name,
            'document_type_code_attrs': {'name': self._get_payment_method_code(invoice)},
            'document_type_code': "381" if is_refund else "388",
            'accounting_customer_party_vals': {
                'party_vals': self._get_empty_party_vals() if is_refund else self._get_partner_party_vals(customer, role='customer'),
                'accounting_contact': {
                    'telephone': '' if is_refund else self._sanitize_phone(invoice.partner_id.phone or invoice.partner_id.mobile),
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

    def _export_invoice(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # _export_invoice normally cleans up the xml to remove empty nodes.
        # However, in the JO UBL version, we always want the PartyIdentification with ID nodes, even if empty.
        # We'll replace the empty value by a dummy one so that the node doesn't get cleaned up and remove its content after the file generation.
        xml, errors = super()._export_invoice(invoice)
        xml_root = etree.fromstring(xml)
        party_identification_id_elements = xml_root.findall('.//cac:PartyIdentification/cbc:ID', namespaces=xml_root.nsmap)
        for element in party_identification_id_elements:
            if element.text == 'NO_VAT':
                element.text = ''
        # method='html' is used to keep the element un-shortened ("<a></a>" instead of <a/>)
        return etree.tostring(xml_root, method='html'), errors
