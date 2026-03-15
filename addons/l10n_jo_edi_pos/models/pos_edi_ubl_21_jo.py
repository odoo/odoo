import functools
import re
from types import SimpleNamespace

from odoo import models
from odoo.tools import float_round, float_is_zero
from odoo.addons.l10n_jo_edi.models.account_edi_xml_ubl_21_jo import JO_MAX_DP
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt


class HashableNamespace(SimpleNamespace):
    """ We need to use a hashable namespace to be able to use it as a key in a dictionary.
    This is because the `SimpleNamespace` class is not hashable by default.
    """

    def __hash__(self):
        return hash(self.name)


class PosEdiXmlUBL21Jo(models.AbstractModel):
    _name = 'pos.edi.xml.ubl_21.jo'
    _inherit = ['pos.edi.xml.ubl_21']
    _description = 'UBL 2.1 (JoFotara) for PoS Orders'

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

    def _get_pos_order_node(self, vals):
        document_node = super()._get_pos_order_node(vals)
        self._add_pos_order_seller_supplier_party_nodes(document_node, vals)
        return document_node

    def _add_pos_order_config_vals(self, vals):
        super()._add_pos_order_config_vals(vals)
        vals.update({
            'document_type': 'invoice',
            'fixed_taxes_as_allowance_charges': False,
            'is_refund': vals['document_type'] == 'credit_note',
            'is_sales': vals['pos_order'].company_id.l10n_jo_edi_taxpayer_type == 'sales',
            'is_income': vals['pos_order'].company_id.l10n_jo_edi_taxpayer_type == 'income',
        })
        # We cannot use a new `res.currency` record to round to 9 decimals, because the
        # `res.currency.rounding` field definition prevents rounding to more than 6 decimal places.
        vals['currency_id'] = HashableNamespace(
            name='JOD',
            round=functools.partial(float_round, precision_digits=JO_MAX_DP),
            is_zero=functools.partial(float_is_zero, precision_digits=JO_MAX_DP),
            rounding=10**-JO_MAX_DP,
            decimal_places=JO_MAX_DP,
        )

    def _add_pos_order_currency_vals(self, vals):
        super()._add_pos_order_currency_vals(vals)
        vals['currency_name'] = 'JO'

    def _add_pos_order_base_lines_vals(self, vals):
        # OVERRIDE account_edi_xml_ubl_20.py
        currency_9_dp = vals['currency_id']
        pos_order = vals['pos_order']

        # Compute values for order lines. In Jordan, because the web-service has absolutely no tolerance,
        # what we do is: use round per line with 9 decimals (yes!)
        base_lines = pos_order._prepare_tax_base_line_values()

        AccountTax = self.env['account.tax']
        for base_line in base_lines:
            base_line['currency_id'] = currency_9_dp
            AccountTax._add_tax_details_in_base_line(base_line, base_line['record'].company_id, 'round_per_line')

        # Round to 9 decimals
        AccountTax._round_base_lines_tax_details(base_lines, company=pos_order.company_id)

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
        self._add_pos_order_discount_vals(vals)

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

    def _add_pos_order_discount_vals(self, vals):
        discount_amount_currency = 0
        for base_line in vals['base_lines']:
            new_vals = {**vals, 'base_line': base_line}
            self._add_document_line_gross_subtotal_and_discount_vals(new_vals)
            discount_amount_currency += abs(new_vals['discount_amount_currency'])
        vals['discount_amount_currency'] = discount_amount_currency

    def _get_payment_method_code(self, order):
        return order._get_order_scope_code() + order._get_order_payment_method_code() + order._get_order_tax_payer_type_code()

    def _add_pos_order_header_nodes(self, document_node, vals):
        pos_order = vals['pos_order']
        document_node.update({
            'cbc:ProfileID': {'_text': 'reporting:1.0'},
            'cbc:ID': {'_text': (pos_order.name or '').replace('/', '_')},
            'cbc:UUID': {'_text': pos_order.l10n_jo_edi_pos_uuid},
            'cbc:IssueDate': {'_text': '2020-01-01' if pos_order.company_id.l10n_jo_edi_pos_testing_mode else pos_order.date_order.date()},
            'cbc:InvoiceTypeCode': {'_text': 381 if vals['is_refund'] else 388, 'name': self._get_payment_method_code(pos_order)},
            'cbc:Note': {'_text': pos_order.general_customer_note},
            'cbc:DocumentCurrencyCode': {'_text': pos_order.currency_id.name},
            'cbc:TaxCurrencyCode': {'_text': pos_order.currency_id.name},
            'cac:BillingReference': {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': (pos_order.refunded_order_id.name or '').replace('/', '_')},
                    'cbc:UUID': {'_text': pos_order.refunded_order_id.l10n_jo_edi_pos_uuid},
                    'cbc:DocumentDescription': {
                        '_text': self.format_float(abs(pos_order.refunded_order_id.amount_total), vals['currency_dp']),
                    },
                },
            } if vals['is_refund'] else None,
            'cac:AdditionalDocumentReference': {
                'cbc:ID': {'_text': 'ICV'},
                'cbc:UUID': {'_text': pos_order.id},
            },
        })

    def _add_pos_order_accounting_customer_party_nodes(self, document_node, vals):
        super()._add_pos_order_accounting_customer_party_nodes(document_node, vals)
        if not vals['is_refund']:
            document_node['cac:AccountingCustomerParty'].update({
                'cac:AccountingContact': {
                    'cbc:Telephone': {'_text': self._sanitize_phone(vals['customer'].phone)}
                },
            })

    def _add_pos_order_seller_supplier_party_nodes(self, document_node, vals):
        document_node['cac:SellerSupplierParty'] = {
            'cac:Party': {
                'cac:PartyIdentification': {
                    'cbc:ID': {'_text': vals['pos_order'].company_id.l10n_jo_edi_sequence_income_source},
                },
            },
        }

    def _add_pos_order_payment_means_nodes(self, document_node, vals):
        if vals['is_refund']:
            document_node['cac:PaymentMeans'] = {
                'cbc:PaymentMeansCode': {'listID': 'UN/ECE 4461', '_text': 10},
                'cbc:InstructionNote': {'_text': vals['pos_order'].l10n_jo_edi_pos_return_reason},
            }

    def _get_party_node(self, vals):
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id
        is_customer = vals['role'] == 'customer'
        return {
            'cac:PartyIdentification': {
                'cbc:ID': {'_text': commercial_partner.vat, 'schemeID': 'TN' if partner.country_code == 'JO' else 'PN'},
            } if not vals['is_refund'] and is_customer else None,
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cbc:CompanyID': {'_text': commercial_partner.vat} if not vals['is_refund'] or not is_customer else None,
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT'}
                },
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
            } if not vals['is_refund'] or not is_customer else None,
        }

    def _get_address_node(self, vals):
        partner = vals['partner']
        country = partner['country_id']
        state = partner['state_id']

        return {
            'cbc:PostalZone': {'_text': partner.zip} if not vals['is_refund'] else None,
            'cbc:CountrySubentityCode': {'_text': state.code} if not vals['is_refund'] else None,
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': country.code},
            },
        }

    def _add_pos_order_allowance_charge_nodes(self, document_node, vals):
        currency_suffix = vals['currency_suffix']

        document_node['cac:AllowanceCharge'] = {
            'cbc:ChargeIndicator': {'_text': 'false'},
            'cbc:AllowanceChargeReason': {'_text': 'discount'},
            'cbc:Amount': {
                '_text': self.format_float(vals[f'discount_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }

    def _add_pos_order_tax_total_nodes(self, document_node, vals):
        # income docs should have no taxes
        if not vals['is_income']:
            super()._add_pos_order_tax_total_nodes(document_node, vals)

    def _add_pos_order_monetary_total_nodes(self, document_node, vals):
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        currency_suffix = vals['currency_suffix']

        document_node[monetary_total_tag] = {
            'cbc:TaxExclusiveAmount': {
                '_text': self.format_float(vals[f'tax_exclusive_amount{currency_suffix}'] + vals[f'discount_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:TaxInclusiveAmount': {
                '_text': self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:AllowanceTotalAmount': {
                '_text': self.format_float(vals[f'discount_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:PrepaidAmount': {
                '_text': self.format_float(0, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals['is_refund'] and vals['is_sales'] else None,
            'cbc:PayableAmount': {
                '_text': self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }

    def _get_pos_order_line_node(self, vals):
        self._add_pos_order_line_vals(vals)

        line_node = {}
        self._add_pos_order_line_id_nodes(line_node, vals)
        self._add_pos_order_line_amount_nodes(line_node, vals)
        self._add_pos_order_line_item_nodes(line_node, vals)
        self._add_pos_order_line_tax_total_nodes(line_node, vals)
        self._add_pos_order_line_price_nodes(line_node, vals)
        self._add_pos_order_line_allowance_charge_nodes(line_node, vals)
        return line_node

    def _get_pos_order_line_id(self, vals):
        if not vals['is_refund']:
            return vals['line_idx']

        line_id = -1
        refund_line = vals['base_line']['record']
        order_lines = vals['pos_order'].refunded_order_id.lines
        for order_line_id, order_line in enumerate(order_lines, 1):
            if refund_line.product_id == order_line.product_id \
                    and refund_line.price_unit == order_line.price_unit \
                    and refund_line.discount == order_line.discount:
                line_id = order_line_id
                break
        if line_id == -1:
            line_id = len(order_lines) + vals['line_idx']

        return line_id

    def _add_pos_order_line_id_nodes(self, line_node, vals):
        line_id = self._get_pos_order_line_id(vals)
        line_node['cbc:ID'] = {'_text': line_id}

    def _add_pos_order_line_amount_nodes(self, line_node, vals):
        super()._add_pos_order_line_amount_nodes(line_node, vals)
        quantity_tag = self._get_tags_for_document_type(vals)['line_quantity']
        line_node[quantity_tag]['unitCode'] = 'PCE'

    def _add_pos_order_line_item_nodes(self, line_node, vals):
        product = vals['base_line']['product_id']
        line_node['cac:Item'] = {
            'cbc:Name': {'_text': product.name},
        }

    def _add_pos_order_line_tax_total_nodes(self, line_node, vals):
        # income docs should have no taxes
        if not vals['is_income']:
            super()._add_pos_order_line_tax_total_nodes(line_node, vals)

    def _sum_tax_details(self, vals, key, include_fixed=False):
        currency_suffix = vals['currency_suffix']

        return sum(
            tax_details[f'{key}{currency_suffix}']
            for grouping_key, tax_details in vals['aggregated_tax_details'].items()
            if grouping_key and (include_fixed or grouping_key['amount_type'] != 'fixed')
        )

    def _get_tax_total_node(self, vals):
        aggregated_tax_details = vals['aggregated_tax_details']
        total_tax_amount = self._sum_tax_details(vals, 'raw_tax_amount')
        rounding_amount = self._sum_tax_details(vals, 'raw_total_excluded') + self._sum_tax_details(vals, 'raw_tax_amount', True)
        return {
            'cbc:TaxAmount': {
                '_text': self.format_float(total_tax_amount, vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:RoundingAmount': {
                '_text': self.format_float(rounding_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals['role'] == 'line' else None,
            'cac:TaxSubtotal': [
                self._get_tax_subtotal_node({
                    **vals,
                    'tax_details': tax_details,
                    'grouping_key': grouping_key,
                })
                for grouping_key, tax_details in aggregated_tax_details.items()
                if grouping_key
            ] if vals['role'] == 'line' or (vals['is_refund'] and vals['is_sales']) else None,
        }

    def _get_tax_subtotal_node(self, vals):
        tax_details = vals['tax_details']
        currency_suffix = vals['currency_suffix']
        return {
            'cbc:TaxableAmount': {
                '_text': self.format_float(tax_details[f'raw_total_excluded{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:TaxAmount': {
                '_text': self.format_float(tax_details[f'raw_tax_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cac:TaxCategory': self._get_tax_category_node(vals)
        }

    def _get_tax_category_node(self, vals):
        grouping_key = vals['grouping_key']
        return {
            'cbc:ID': {'_text': grouping_key['tax_category_code'], 'schemeAgencyID': 6, 'schemeID': 'UN/ECE 5305'},
            'cbc:Percent': {'_text': grouping_key['amount']} if grouping_key['amount_type'] == 'percent' else None,
            'cac:TaxScheme': {
                'cbc:ID': {
                    '_text': 'VAT' if grouping_key['amount_type'] == 'percent' else 'OTH',
                    'schemeAgencyID': 6,
                    'schemeID': 'UN/ECE 5153',
                },
            }
        }

    def _add_pos_order_line_price_nodes(self, line_node, vals):
        currency_suffix = vals['currency_suffix']

        line_node['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': self.format_float(
                    vals[f'gross_price_unit{currency_suffix}'],
                    vals['currency_dp'],
                ),
                'currencyID': vals['currency_name'],
            },
        }

    def _add_pos_order_line_allowance_charge_nodes(self, line_node, vals):
        currency_suffix = vals['currency_suffix']

        line_node['cac:Price']['cac:AllowanceCharge'] = {
            'cbc:ChargeIndicator': {'_text': 'false'},
            'cbc:AllowanceChargeReason': {'_text': 'DISCOUNT'},
            'cbc:Amount': {
                '_text': self.format_float(vals[f'discount_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }
