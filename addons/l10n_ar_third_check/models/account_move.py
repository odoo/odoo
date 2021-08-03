from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        """ this method is called when changing to draft from account_move or account_payment button and cancel
        the check operation (handed, delivered, etc) on the payment
        """
        res = super().button_draft()
        for rec in self.filtered(
                lambda x: x.payment_id and x.payment_id.state != 'cancel' and
                x.payment_id.payment_method_line_id.code in ['new_third_checks', 'in_third_checks', 'out_third_checks']):
            rec.payment_id._cancel_third_check_operation()
        return res
