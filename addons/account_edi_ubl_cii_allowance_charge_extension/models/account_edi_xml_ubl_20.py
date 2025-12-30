from odoo import models


class AccountEdiXmlUBL20(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_20"

    def _get_grouping_key_dict(self, tax, tax_category_vals):
        """Extends grouping key dict to insert tax's ubl_cii_type"""
        return {
            **super()._get_grouping_key_dict(tax, tax_category_vals),
            'ubl_cii_type': tax.ubl_cii_type,
        }

    def _get_eligible_tax_keys(self, taxes_vals):
        """
        Filter out allowance/charge from taxes to avoid any effect on
        taxes explicitly defined as an allowance/charge.
        """
        tax_details = taxes_vals.get('tax_details', {})
        return [
            key
            for key in super()._get_eligible_tax_keys(taxes_vals)
            if tax_details[key].get('ubl_cii_type') != 'allowance_charge'
        ]

    def _remove_allowance_charge_tax_effect(self, taxes_vals):
        """
        Override base logic to remove AllowanceCharge taxes from totals.

        This removes taxes marked as ``ubl_cii_type = 'allowance_charge'``,
        which are modeled as taxes in Odoo but exported separately as AllowanceCharge.
        """

        # remove AllowanceCharge taxes
        allowance_charge_keys = [
            k for k in taxes_vals['tax_details']
            if k.get('ubl_cii_type') == 'allowance_charge'
        ]

        for key in allowance_charge_keys:
            tax_details = taxes_vals['tax_details'].pop(key)
            taxes_vals['tax_amount_currency'] -= tax_details['tax_amount_currency']
            taxes_vals['tax_amount'] -= tax_details['tax_amount']
            taxes_vals['base_amount_currency'] += tax_details['tax_amount_currency']
            taxes_vals['base_amount'] += tax_details['tax_amount']

        return taxes_vals

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list=None):
        """
        Extension of the UBL 2.0 logic to generate AllowanceCharge values from:
        - fixed taxes mapped as charges/allowances
        - taxes explicitly marked with allowance/charge metadata
        - line discounts

        :param line:            An invoice line.
        :param tax_values_list: A dict containing computed tax details for the line
        :return:                A list of python dictionaries.
        """

        allowance_charge_vals_list = []
        for tax_details in (tax_values_list or {}).get('tax_details', {}).values():
            tax_category_vals = tax_details.get('_tax_category_vals_', {})
            if tax_details.get('ubl_cii_type') == 'allowance_charge':
                allowance_charge_vals_list.append({
                    'currency_name': line.currency_id.name,
                    'currency_dp': line.currency_id.decimal_places,
                    'charge_indicator': tax_category_vals.get('charge_indicator'),
                    'allowance_charge_reason_code': tax_category_vals.get('allowance_charge_reason_code'),
                    'allowance_charge_reason': tax_category_vals.get('allowance_charge_reason'),
                    # Allowance/Charge multiplier_factor is required to predict tax during import
                    'multiplier_factor': tax_category_vals.get('percent'),
                    # Only keep base_amount in conjunction with multiplier_factor
                    'base_amount': tax_details.get('base_amount_currency') if (tax_category_vals.get('percent') is not False) else None,
                    # Absolute value because tax_amount_currency might be -ve for allowance
                    'amount': abs(tax_details.get('tax_amount_currency')),
                })

        return super()._get_invoice_line_allowance_vals_list(line, tax_values_list) + allowance_charge_vals_list

    def _get_total_allowance_charge_tax_amount(self, line, allowance_charge_vals_list):
        """
        Extend the base computation of allowance/charge tax amounts.

        Charges are added and allowances are subtracted. Since the result is
        later added to `price_subtotal` (which already includes line discounts),
        the discount impact is removed to avoid double-counting.
        """
        total_allowance_charge_tax_amount = super()._get_total_allowance_charge_tax_amount(line, allowance_charge_vals_list)
        total_allowance_charge_tax_amount -= sum(
            vals['amount']
            for vals in allowance_charge_vals_list
            if vals.get('charge_indicator') == 'false'
        )
        discount = ((line.discount or 0.0) / 100.0)
        if discount:
            gross_price_subtotal = (
                0.0
                if discount == 1.0
                else line.currency_id.round(line.price_subtotal / (1.0 - discount))
            )
            total_allowance_charge_tax_amount += (gross_price_subtotal - line.price_subtotal)
        return total_allowance_charge_tax_amount

    def _get_invoice_line_item_taxes(self, line):
        """Exclude AllowanceCharge taxes from item-level tax classification."""
        return super()._get_invoice_line_item_taxes(line).filtered(lambda t: t.ubl_cii_type != 'allowance_charge')
