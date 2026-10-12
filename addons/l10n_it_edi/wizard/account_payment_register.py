from odoo import api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.depends('payment_type', 'journal_id', 'line_ids.move_id')
    def _compute_payment_method_line_id(self):
        super()._compute_payment_method_line_id()

        for wizard in self.filtered(
            lambda wizard: (
                wizard.journal_id
                and len(wizard.line_ids.move_id) == 1
                and wizard.line_ids.move_id.l10n_it_payment_method
            ),
        ):
            available_lines = wizard.journal_id._get_available_payment_method_lines(wizard.payment_type)

            matched_lines = available_lines.filtered(
                lambda line: line.l10n_it_payment_method == wizard.line_ids.move_id.l10n_it_payment_method,
            )

            if matched_lines:
                wizard.payment_method_line_id = matched_lines[0]
