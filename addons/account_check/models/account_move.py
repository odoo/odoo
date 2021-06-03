##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        """ this method is called when changing to draft from account_move or account_payment button and do two things:
        1. Remove undone check operation (handed, delivered, etc)
        2. unsplit liquidity lines because with actual implementation of _synchronize_to_moves it won't work any update
        on the payment
        """
        res = super().button_draft()
        if self.payment_id.check_ids and self.payment_id.state != 'cancel':
            self.payment_id._do_checks_operations(cancel=True)
            liq_lines, counterpart_lines, writeoff_lines = self.payment_id._seek_for_lines()
            if len(liq_lines) > 1:
                self.write({'line_ids': [
                    (1, liq_lines[0].id, {
                        'debit': sum(liq_lines.mapped('debit')),
                        'credit': sum(liq_lines.mapped('credit')),
                        'amount_currency': sum(liq_lines.mapped('amount_currency')),
                    })] + [(3, x.id) for x in liq_lines[1:]]})
        return res
