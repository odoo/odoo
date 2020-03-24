from odoo import fields, models, api
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Check whether a pos_session is being closed.
    # If it is a pos_session and it is unbalanced
    #   -> rollback operation
    #   -> set unbalanced flag on the session

    def _check_balanced(self):
        try:
            super(AccountMove, self)._check_balanced()
        except UserError:
            if self.env.context.get('pos_session_id'):
                self.env.cr.rollback()
                session = self.env['pos.session'].browse(self.env.context.get('pos_session_id'))
                session._is_unbalanced = True
                self.env.cr.commit()
            raise
