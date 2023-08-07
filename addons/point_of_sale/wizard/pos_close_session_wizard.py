# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosCloseSessionWizard(models.TransientModel):
    _name = "pos.close.session.wizard"
    _description = "Close Session Wizard"

    pos_session_id = fields.Many2one('pos.session', required=True)
    amount_to_balance = fields.Float("Amount to balance", related='pos_session_id.amount_to_balance')
    account_id = fields.Many2one("account.account", "Destination account")
    account_readonly = fields.Boolean("Destination account is readonly")
    message = fields.Text("Information message")

    def close_session(self):
        ## TODO check cron triggered (when _validate_session has its auto trigger)
        self.pos_session_id.action_pos_session_closing_control(
            self.account_id
        )

    def retry_session_processing(self):
        return self.pos_session_id.action_retry_validated_processing()
