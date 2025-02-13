# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from math import copysign


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # ----------------
    # Business methods
    # ----------------

    def _get_withholding_amounts(self):
        """
        Return a dict with the amounts relevant to withholding taxes.
        Amounts are returned in the invoice currency.
        """
        self.ensure_one()
        withholding_amount = 0.0
        withholding_amount_currency = 0.0
        for line in self.move_id.line_ids:
            base_line = self.move_id._prepare_product_base_line_for_taxes_computation(line)
            base_line['tax_ids'] = base_line['tax_ids'].with_context(include_withholding_taxes=True)
            self.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)

            for tax in line.tax_ids:
                if not tax.is_withholding_tax_on_payment:
                    continue

                tax_data = [d for d in base_line['tax_details']['taxes_data'] if d['tax'] == tax][0]
                withholding_amount += tax_data['raw_tax_amount']
                withholding_amount_currency += tax_data['raw_tax_amount_currency']

        # In case of EPD self could be a part of the invoice; so we get the ratio and multiply the withholding by it.
        ratio = self.amount_residual / self.move_id.amount_total_signed
        withholding_amount *= ratio
        withholding_amount_currency *= ratio

        # Ensure that we properly affect the net with the correct sign.
        withholding_amount = copysign(withholding_amount, self.amount_residual)
        withholding_amount_currency = copysign(withholding_amount_currency, self.amount_residual_currency)

        return {
            'withholding': withholding_amount,
            'residual_net': self.currency_id.round(self.amount_residual - withholding_amount),
            'residual_net_currency': self.currency_id.round(self.amount_residual_currency - withholding_amount_currency),
        }
