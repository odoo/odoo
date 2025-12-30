from odoo import models


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = 'account.edi.xml.cii'

    def _get_grouping_key_dict(self, invoice, tax):
        grouping_key_dict = {
            **super()._get_grouping_key_dict(invoice, tax),
            'ubl_cii_type': tax.ubl_cii_type,
        }
        if tax.ubl_cii_type == 'allowance_charge':
            grouping_key_dict['allowance_charge_vals'] = {
                'charge_indicator': 'true' if tax.amount >= 0 else 'false',
                'allowance_charge_reason_code': tax.ubl_cii_allowance_reason_code if tax.amount < 0 else tax.ubl_cii_charge_reason_code,
                'allowance_charge_reason': tax.ubl_cii_allowance_charge_reason,
            }
        return grouping_key_dict

    def _remove_allowance_charge_tax_effect(self, tax_details):
        """
        Remove the effect of fixed taxes and AllowanceCharge taxes from totals.

        Fixed taxes are already handled by the base implementation. This override
        additionally removes taxes marked as ``ubl_cii_type = 'allowance_charge'``,
        which are modeled as taxes in Odoo but exported separately as AllowanceCharge.
        """
        # remove fixed taxes
        tax_details = super()._remove_allowance_charge_tax_effect(tax_details)

        # Remove remaining AllowanceCharge taxes
        allowance_charge_keys = [
            k for k in tax_details['tax_details']
            if k.get('ubl_cii_type') == 'allowance_charge'
        ]

        for key in allowance_charge_keys:
            td = tax_details['tax_details'].pop(key)
            tax_details['tax_amount_currency'] -= td['tax_amount_currency']
            tax_details['tax_amount'] -= td['tax_amount']
            tax_details['base_amount_currency'] += td['tax_amount_currency']
            tax_details['base_amount'] += td['tax_amount']
        return tax_details

    def _add_invoice_line_allowance_charge_vals(self, template_values):
        """Override of base implementation to handle allowance/charge taxes"""
        for line_vals in template_values['invoice_line_vals_list']:
            line_vals['allowance_charge_vals_list'] = []
            tax_details = template_values['tax_details']
            tax_details_per_record = tax_details['tax_details_per_record'][line_vals['line']]['tax_details']
            for grouping_key, tax_detail in tax_details_per_record.items():
                allowance_charge_vals = grouping_key.get('allowance_charge_vals', {})
                if 'charge_indicator' in allowance_charge_vals:
                    line_vals['allowance_charge_vals_list'].append({
                        'indicator': allowance_charge_vals['charge_indicator'],
                        'reason_code': allowance_charge_vals.get('allowance_charge_reason_code'),
                        'reason': allowance_charge_vals.get('allowance_charge_reason'),
                        # Allowance/Charge calculation_percent is required to predict tax during import
                        'calculation_percent': grouping_key.get('amount') if grouping_key.get('amount_type') == 'percent' else None,
                        # Only keep basis_amount in conjunction with calculation_percent
                        'basis_amount': tax_detail.get('base_amount_currency') if grouping_key.get('amount_type') == 'percent' else None,
                        # Absolute value because tax_amount_currency might be -ve for allowance
                        'amount': abs(tax_detail['tax_amount_currency']),
                    })

            # Remove allowance charge taxes from tax_details_per_record, as this will be used to fill <ram:ApplicableTradeTax>
            allowance_charge_keys = [
                key for key in tax_details_per_record
                if key.get('ubl_cii_type') == 'allowance_charge'
            ]
            for key in allowance_charge_keys:
                tax_details_per_record.pop(key)

            sum_charge_taxes = sum(x['amount'] for x in line_vals['allowance_charge_vals_list'] if x['indicator'] == 'true')
            sum_allowance_taxes = sum(x['amount'] for x in line_vals['allowance_charge_vals_list'] if x['indicator'] == 'false')
            line_vals['line_total_amount'] = line_vals['line'].price_subtotal + sum_charge_taxes - sum_allowance_taxes

            line_vals['quantity'] = line_vals['line'].quantity  # /!\ The quantity is the line.quantity since we keep the unece_uom_code!

            # Invert the quantity and the gross_price_total_unit if a line has a negative price total
            if line_vals['line'].currency_id.compare_amounts(line_vals['gross_price_total_unit'], 0) == -1:
                line_vals['quantity'] *= -1
                line_vals['gross_price_total_unit'] *= -1
                line_vals['price_subtotal_unit'] *= -1
        return template_values
