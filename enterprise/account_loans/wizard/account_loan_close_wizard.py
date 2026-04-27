from odoo import models, fields, _
from odoo.tools import format_date


class AccountCloseWizard(models.TransientModel):
    _name = 'account.loan.close.wizard'
    _description = 'Close Loan Wizard'

    loan_id = fields.Many2one(
        comodel_name='account.loan',
        string='Loan',
        required=True,
    )
    date = fields.Date(
        string='Close Date',
        default=fields.Date.context_today,
        required=True,
    )

    def action_save(self):
        self.loan_id.line_ids.generated_move_ids.filtered(lambda m: m.generating_loan_line_id.date > self.date and m.state == 'draft').unlink()
        self.loan_id.state = 'closed'
        self.loan_id.message_post(body=_("Closed on the %(date)s", date=format_date(self.env, self.date)))
        return {'type': 'ir.actions.act_window_close'}
