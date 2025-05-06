from odoo import models


class AccountEdiXmlUBL20(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_20'

    def _get_tax_grouping_key(self, base_line, tax_data):
        # OVERRIDE account_edi_ubl_cii
        grouping_key = super()._get_tax_grouping_key(base_line, tax_data)
        tax = tax_data['tax']

        grouping_key |= {
            'allowance_charge_reason_code': tax.ubl_cii_allowance_reason_code,
            'allowance_charge_reason': tax.ubl_cii_charge_reason_code,
        }

        return grouping_key

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list=None):
        # OVERRIDE account_edi_ubl_cii
        allowance_vals_list = []

        for grouping_key, tax_details in tax_values_list['tax_details'].items():
            if grouping_key['tax_amount_type'] != 'percent' and grouping_key['allowance_charge_reason']:
                allowance_vals_list.append({
                    'currency_name': line.currency_id.name,
                    'currency_dp': self._get_currency_decimal_places(line.currency_id),
                    'charge_indicator': 'true',
                    'allowance_charge_reason_code': grouping_key['allowance_charge_reason_code'],
                    'allowance_charge_reason': grouping_key['allowance_charge_reason'],
                    'amount': tax_details['tax_amount_currency'],
                })

            if not line.discount:
                return allowance_vals_list

        return [self._get_invoice_line_discount_allowance_vals(line)] + allowance_vals_list
