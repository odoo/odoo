# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosCloseSessionWizard(models.TransientModel):
    _name = 'pos.close.session.wizard'
    _description = "Close Session Wizard"

    amount_to_balance = fields.Float("Amount to balance")
    account_id = fields.Many2one("account.account", "Destination account")
    account_readonly = fields.Boolean("Destination account is readonly")
    message = fields.Text("Information message")

    def close_session(self):
        # FIXME: create balance entry and close session
        pass
