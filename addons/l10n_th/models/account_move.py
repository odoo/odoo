from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.company_id.account_fiscal_country_id.code == 'TH':
            return 'l10n_th.report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_th_get_credit_debit_note_amounts(self):
        self.ensure_one()

        if original_move := self.reversed_entry_id:
            related_moves = original_move.reversal_move_ids
            sign = -1
        elif 'debit_origin_id' in self._fields and (original_move := self.debit_origin_id):
            related_moves = original_move.debit_note_ids
            sign = 1
        else:
            return []

        previous_amount = sum(
            related_moves.filtered(
                lambda move: (
                    move.state == 'posted'
                    and (
                        move._get_accounting_date_source() < self._get_accounting_date_source()
                        or (
                            move._get_accounting_date_source() == self._get_accounting_date_source()
                            and (not self.name or self.name == '/' or move.name < self.name)
                        )
                    )
                ),
            ).mapped('amount_untaxed'),
        )

        original_amount = original_move.amount_untaxed + sign * previous_amount
        corrected_amount = original_amount + sign * self.amount_untaxed

        return [
            {
                'label': self.env._("Original Amount"),
                'amount': original_amount,
            },
            {
                'label': self.env._("Correct Amount"),
                'amount': corrected_amount,
            },
        ]
