# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends(
        'partner_id', 'currency_id', 'invoice_date',
        'invoice_line_ids.product_id',
        'invoice_line_ids.tax_ids', 'invoice_line_ids.price_unit', 'invoice_line_ids.quantity', 'invoice_line_ids.discount',
    )
    def _compute_withholding_total_amount(self):
        # EXTENDS 'l10n_account_withholding_tax'
        super()._compute_withholding_total_amount()

    def _get_withholding_base_lines(self):
        # EXTENDS 'l10n_account_withholding_tax'
        base_lines = super()._get_withholding_base_lines()
        # SAT withholdings don't apply to POS orders
        is_pos_invoice = 'pos_order_ids' in self._fields and self.sudo().pos_order_ids
        if self.country_code != 'GT' or is_pos_invoice:
            return base_lines

        merged_base_lines = {}
        for base_line in base_lines:
            line = base_line['record']
            if not isinstance(line, models.Model) or line.display_type != 'product':
                continue

            tax_details = base_line['tax_details']
            untaxed_amount = tax_details['total_excluded'] + tax_details['delta_total_excluded']
            for tax in line._l10n_gt_get_withholding_taxes():
                merged = merged_base_lines.setdefault(tax, {'base_line': base_line, 'untaxed_amount': 0.0})
                merged['untaxed_amount'] += untaxed_amount

        AccountTax = self.env['account.tax']
        withholding_base_lines = []
        for tax, merged in merged_base_lines.items():
            base_amount = merged['untaxed_amount']
            base_line = AccountTax._prepare_base_line_for_taxes_computation(
                merged['base_line'],
                tax_ids=tax,
                price_unit=base_amount,
                quantity=1.0,
                discount=0.0,
                currency_id=self.company_currency_id,
                rate=1.0,
            )

            tax_amount = self._l10n_gt_get_withholding_amount(base_line)
            if not tax_amount:
                continue

            if self.currency_id != self.company_currency_id:
                rate = self.invoice_currency_rate
                base_amount_currency = self.currency_id.round(base_amount * rate)
                base_line = {
                    **base_line,
                    'currency_id': self.currency_id,
                    'rate': rate,
                    'price_unit': base_amount_currency,
                    'manual_tax_amounts': {str(tax.id): {
                        'base_amount_currency': base_amount_currency,
                        'base_amount': base_amount,
                        'tax_amount_currency': self.currency_id.round(tax_amount * rate),
                        'tax_amount': tax_amount,
                    }},
                }
            withholding_base_lines.append(base_line)
        return withholding_base_lines

    def _l10n_gt_get_withholding_amount(self, base_line):
        """ Return the sum of the base lines' withholding taxes. """
        self.ensure_one()
        AccountTax = self.env['account.tax']
        evaluated_base_line = {**base_line, 'calculate_withholding_taxes': True}
        AccountTax._add_tax_details_in_base_line(evaluated_base_line, self.company_id)
        AccountTax._round_base_lines_tax_details([evaluated_base_line], self.company_id)
        return sum(
            tax_data['tax_amount_currency']
            for tax_data in evaluated_base_line['tax_details']['taxes_data']
        )
