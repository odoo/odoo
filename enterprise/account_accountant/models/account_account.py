import ast
from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def action_open_reconcile(self):
        self.ensure_one()
        # Open reconciliation view for this account
        action_values = self.env['ir.actions.act_window']._for_xml_id('account_accountant.action_move_line_posted_unreconciled')
        domain = ast.literal_eval(action_values['domain'])
        domain.append(('account_id', '=', self.id))
        action_values['domain'] = domain
        return action_values
