from odoo import models


class AccountEdiXmlUBL20(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_20'

    def _add_document_line_allowance_charge_nodes(self, line_node, vals):
        # EXTEND account_edi_ubl_cii
        super()._add_document_line_allowance_charge_nodes(line_node, {**vals, 'fixed_taxes_as_allowance_charges': False})
        if vals['document_type'] in {'credit_note', 'debit_note'}:
            return
        line = vals['base_line']
        customer = vals['customer']
        supplier = vals['supplier']

        def grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            if not tax:
                return None

            return {
                'tax_category_code': self._get_tax_category_code(customer.commercial_partner_id, supplier, tax),
                **self._get_tax_exemption_reason(customer.commercial_partner_id, supplier, tax),
                'allowance_charge_reason_code': tax.ubl_cii_allowance_reason_code if tax.amount < 0.0 else tax.ubl_cii_charge_reason_code,
                'allowance_charge_reason': tax.ubl_cii_allowance_charge_reason,
                'amount': tax.amount,
                'amount_type': tax.amount_type,
            }

        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(line, grouping_function)
        currency_suffix = vals['currency_suffix']

        for grouping_key, tax_details in aggregated_tax_details.items():
            if grouping_key and grouping_key['amount_type'] != 'percent' and grouping_key['allowance_charge_reason_code']:
                line_node['cac:AllowanceCharge'].append({
                    'cbc:ChargeIndicator': {'_text': 'true' if tax_details[f'tax_amount{currency_suffix}'] > 0 else 'false'},
                    'cbc:AllowanceChargeReasonCode': {'_text': grouping_key['allowance_charge_reason_code']},
                    'cbc:AllowanceChargeReason': {'_text': grouping_key['allowance_charge_reason']},
                    'cbc:Amount': {
                        '_text': self.format_float(
                            abs(tax_details[f'tax_amount{currency_suffix}']),
                            vals['currency_dp'],
                        ),
                        'currencyID': vals['currency_name'],
                    },
                    'cac:TaxCategory': self._get_tax_category_node({**vals, 'grouping_key': grouping_key}) if 'tax_category_code' in grouping_key else None,
                })
