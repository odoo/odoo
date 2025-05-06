from odoo import models


class AccountEdiXmlUBL20(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_20'

    def _get_tax_grouping_key(self, base_line, tax_data):
        # EXTENDS account_edi_ubl_cii
        grouping_key = super()._get_tax_grouping_key(base_line, tax_data)
        tax = tax_data['tax']

        grouping_key |= {
            'allowance_charge_reason_code': tax.ubl_cii_allowance_charge_reason_code,
            'allowance_charge_reason': tax.ubl_cii_allowance_charge_reason,
        }

        return grouping_key

    def _get_invoice_line_tax_allowance_vals_list(self, grouping_key, tax_details, currency):
        # OVERRIDE account_edi_ubl_cii
        if grouping_key['tax_amount_type'] == 'percent' or not grouping_key['allowance_charge_reason_code']:
            return dict()

        return {
            'currency_name': currency.name,
            'currency_dp': self._get_currency_decimal_places(currency),
            'charge_indicator': 'true',
            'allowance_charge_reason_code': grouping_key['allowance_charge_reason_code'],
            'allowance_charge_reason': grouping_key['allowance_charge_reason'],
            'amount': tax_details['tax_amount_currency'],
        }
