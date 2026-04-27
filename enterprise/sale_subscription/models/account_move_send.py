from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_default_mail_template_id(self, move):
        # EXTENDS 'account'
        if move.move_type == 'out_invoice':
            plan_template = move.invoice_line_ids.subscription_id.plan_id.invoice_mail_template_id
            # Several subscriptions can be linked to invoice_line_ids.
            if plan_template and len(plan_template) == 1:
                return plan_template

        return super()._get_default_mail_template_id(move)
