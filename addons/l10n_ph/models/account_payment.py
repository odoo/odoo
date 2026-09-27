# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_aggregated_bill_lines_with_totals(self):
        self.ensure_one()

        aggregated = {}
        total_debit = 0.0
        total_credit = 0.0
        currency_round = self.company_id.currency_id.round

        for line in self.reconciled_bill_ids.line_ids:
            key = (line.account_id.id, line.move_name)
            if key not in aggregated:
                aggregated[key] = {
                    'account_id': line.account_id,
                    'move_name': line.move_name,
                    'debit': 0.0,
                    'credit': 0.0,
                }
            aggregated[key]['debit'] = currency_round(aggregated[key]['debit'] + line.debit)
            aggregated[key]['credit'] = currency_round(aggregated[key]['credit'] + line.credit)
            total_debit = currency_round(total_debit + line.debit)
            total_credit = currency_round(total_credit + line.credit)

        return {
            'lines': list(aggregated.values()),
            'total_debit': total_debit,
            'total_credit': total_credit,
        }

    def _get_payment_journal_entries_with_totals(self):
        self.ensure_one()

        if not self.move_id or self.move_id.move_type != 'entry':
            return {'lines': [], 'total_debit': 0.0, 'total_credit': 0.0}

        currency_round = self.company_id.currency_id.round
        lines = self.move_id.line_ids
        total_debit = currency_round(sum(lines.mapped('debit')))
        total_credit = currency_round(sum(lines.mapped('credit')))

        return {
            'lines': lines,
            'total_debit': total_debit,
            'total_credit': total_credit,
        }
