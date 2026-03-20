# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)

        if self.company_id.country_id.code == 'IN':
            base_lines = self.lines._prepare_tax_base_line_values()
            self.env['account.tax']._add_tax_details_in_base_lines(base_lines, self.company_id)
            self.env['account.tax']._round_base_lines_tax_details(base_lines, self.company_id)
            l10n_in_hsn_summary = self.env['account.tax']._l10n_in_get_hsn_summary_table(base_lines, False)
            data['extra_data']['l10n_in_hsn_summary'] = l10n_in_hsn_summary
            data['conditions']['code_in'] = self.company_id.country_id.code == 'IN'

            for summary in data['extra_data']['l10n_in_hsn_summary'].get('items'):
                if summary.get('tax_amount_igst') is not None:
                    summary['tax_amount_igst'] = self._order_receipt_format_currency(summary['tax_amount_igst'])
                if summary.get('tax_amount_cgst') is not None:
                    summary['tax_amount_cgst'] = self._order_receipt_format_currency(summary['tax_amount_cgst'])
                if summary.get('tax_amount_sgst') is not None:
                    summary['tax_amount_sgst'] = self._order_receipt_format_currency(summary['tax_amount_sgst'])
                if summary.get('tax_amount_cess') is not None:
                    summary['tax_amount_cess'] = self._order_receipt_format_currency(summary['tax_amount_cess'])

        return data
