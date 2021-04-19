##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def button_draft(self):
        """ this method is called when changing to draft from account_move or account_payment button 
        """
        if self.payment_id.check_ids and self.payment_id.state != 'cancel':
            self.payment_id.do_checks_operations(cancel=True)
        return super().button_draft()
