from lxml import etree

from odoo import models
from odoo.exceptions import ValidationError
from odoo.tools import float_repr
from odoo.tools.float_utils import float_round


JO_CURRENCY = type('JoCurrency', (), {'name': 'JO'})()


class AccountEdiXmlUBL21JO(models.AbstractModel):
    _name = "account.edi.xml.ubl_21.jo"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL 2.1 (JoFotara)"

    ####################################################
    # overriding vals methods of account.edi.xml.ubl_20
    ####################################################

    def _get_country_vals(self, country):
        return {
            'identification_code': country.code,
        }

    def _get_partner_party_identification_vals_list(self, partner):
        if partner.vat and not partner.vat.isdigit():
            raise ValidationError("JoFotara portal cannot process customer VAT with non-digit characters in it")
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

    def _get_invoice_tax_totals_vals_list_helper(self, invoice, taxes_vals):
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
                    'taxable_amount': sum(record._get_tax_exclusive_amount_jod() - record._get_discount_amount_jod() for record in vals['records']),
                    'tax_amount': sum(record._get_general_tax_amount_jod() for record in vals['records']),
                    'tax_category_vals': vals['_tax_category_vals_'],
                }
                tax_totals_vals['tax_subtotal_vals'].append(subtotal)
                tax_totals_vals['tax_amount'] += subtotal['tax_amount']

        return [tax_totals_vals]

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        if invoice._get_jo_invoice_type_number() in [1, 2]:
            return []

        vals = self._get_invoice_tax_totals_vals_list_helper(invoice, taxes_vals)
        if invoice._get_jo_invoice_type_number() != 4:
            vals[0]['tax_subtotal_vals'] = []
        return vals

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        product = line.product_id
        description = line.name and line.name.replace('\n', ', ')
        return {
            'name': product.name or description,
        }

    def _get_document_allowance_charge_vals_list(self, invoice):
        return [{
            'charge_indicator': 'false',
            'allowance_charge_reason': 'discount',
            'currency_name': JO_CURRENCY.name,
            'currency_dp': self._get_currency_decimal_places(),
            'amount': invoice._get_discount_amount_jod(),
        }]

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list=None):
        return [{
            'charge_indicator': 'false',
            'allowance_charge_reason': 'DISCOUNT',
            'currency_name': JO_CURRENCY.name,
            'currency_dp': self._get_currency_decimal_places(),
            'amount': line._get_discount_amount_jod(),
        }]

    def _get_invoice_line_price_vals(self, line):
        vals = super()._get_invoice_line_price_vals(line)
        return {
            **vals,
            'price_amount': line._get_unit_price_jod(),
            'product_price_dp': self._get_currency_decimal_places(),
            'allowance_charge_vals': self._get_invoice_line_allowance_vals_list(line),
            'currency': JO_CURRENCY,
        }

    def _get_invoice_line_tax_totals_vals_list(self, line, taxes_vals):
        if line.move_id._get_jo_invoice_type_number() in [1, 2]:
            return []

        invoice = line.move_id
        vals = self._get_invoice_tax_totals_vals_list_helper(invoice, taxes_vals)
        val = vals[0]
        val['rounding_amount'] = line._get_tax_inclusive_amount_jod()

        for grouping_key, tax_details_vals in taxes_vals['tax_details'].items():
            if grouping_key['tax_amount_type'] == 'fixed':
                subtotal = {
                    'currency': JO_CURRENCY,
                    'currency_dp': self._get_currency_decimal_places(),
                    'taxable_amount': sum(record._get_tax_exclusive_amount_jod() - record._get_discount_amount_jod() for record in tax_details_vals['records']),
                    'tax_amount': sum(record._get_special_tax_amount_jod() for record in tax_details_vals['records']),
                    'tax_category_vals': tax_details_vals['_tax_category_vals_'],
                }
                val['tax_subtotal_vals'].insert(0, subtotal)
        return vals

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        if line.quantity < 0:
            raise ValidationError("JoFotara portal cannot process negative quantity on invoice line")
        if line.price_unit < 0:
            raise ValidationError("JoFotara portal cannot process negative price on invoice line")
        return {
            **super()._get_invoice_line_vals(line, line_id, taxes_vals),
            'currency': JO_CURRENCY,
            'line_extension_amount': line._get_tax_exclusive_amount_jod() - line._get_discount_amount_jod(),
        }

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        discount = invoice._get_discount_amount_jod()
        return {
            'currency': JO_CURRENCY,
            'currency_dp': self._get_currency_decimal_places(),
            'tax_exclusive_amount': invoice._get_tax_exclusive_amount_jod(),
            'tax_inclusive_amount': invoice._get_tax_inclusive_amount_jod(),
            'allowance_total_amount': discount,
            'payable_amount': invoice._get_tax_inclusive_amount_jod(),
            'prepaid_amount': 0 if invoice._get_jo_invoice_type_number() == 4 else None,
        }

    ####################################################
    # overriding vals methods of account.edi.common
    ####################################################

    def format_float(self, amount, precision_digits):
        if amount is None:
            return None

        def get_decimal_places(number):
            return len(f'{float(number)}'.split('.')[1])

        JO_DP = 9
        rounded_amount = float_repr(float_round(amount, JO_DP), JO_DP).rstrip('0').rstrip('.')

        decimal_places = get_decimal_places(rounded_amount)
        if decimal_places < precision_digits:
            rounded_amount = float_repr(float(rounded_amount), precision_digits)
        return rounded_amount

    def _get_currency_decimal_places(self, currency_id=None):
        return 3

    def _get_uom_unece_code(self, line):
        return "PCE"

    def _get_tax_category_list(self, invoice, taxes):
        res = []
        for tax in taxes:
            tax_type = tax.get_jo_tax_type()
            tax_code = tax.get_tax_jo_ubl_code()
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
            'id': invoice.reversed_entry_id.name.replace('/', '_'),
            'uuid': invoice.reversed_entry_id.l10n_jo_edi_uuid,
            'description': self.format_float(abs(invoice.reversed_entry_id.amount_total_signed), self._get_currency_decimal_places()),
        }

    ####################################################
    # export methods
    ####################################################

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)

        vals.update({
            'main_template': 'account_edi_ubl_cii.ubl_20_Invoice',
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
            'invoice': {
                'id': invoice.id,
                'uuid': invoice.l10n_jo_edi_uuid,
                'sequence_income_source': invoice.company_id.l10n_jo_edi_sequence_income_source,
            },
            'tax_currency_code': 'JOD',
            'document_type_code_attrs': {'name': invoice._get_payment_method()},
            'document_type_code': invoice._get_type_code(),
            'accounting_customer_party_vals': {
                'party_vals': self._get_empty_party_vals() if is_refund else self._get_partner_party_vals(customer, role='customer'),
                'telephone': '' if is_refund else invoice.partner_id.phone or invoice.partner_id.mobile,
            },
            'billing_reference_vals': self._get_billing_reference_vals(invoice)
        })

        return vals

    def _add_name_space(self, xml_string, prefix, namespace):
        root = etree.fromstring(xml_string)
        new_nsmap = root.nsmap.copy()
        new_nsmap[prefix] = namespace
        new_root = etree.Element(root.tag, nsmap=new_nsmap)
        new_root[:] = root[:]
        return etree.tostring(new_root, encoding='UTF-8')

    def _export_invoice(self, invoice):
        xml_file, _ = super()._export_invoice(invoice)
        prefix, namespace = ('ext', 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2')
        return self._add_name_space(xml_file, prefix, namespace)
