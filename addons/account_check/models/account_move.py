from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        """ this method is called when changing to draft from account_move or account_payment button and cancel
        the check operation (handed, delivered, etc) on the payment
        """
        res = super().button_draft()
        for rec in self:
            if rec.payment_id.check_id and rec.payment_id.state != 'cancel':
                rec.payment_id._do_checks_operations(cancel=True)
        return res
