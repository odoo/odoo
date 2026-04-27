from odoo import models, fields, _


class AccountMove(models.Model):
    _inherit = "account.move"

    generating_loan_line_id = fields.Many2one(
        comodel_name='account.loan.line',
        string='Generating Loan Line',
        help="Line of the loan that generated this entry",
        copy=False,
        readonly=True,
        index=True,
        ondelete='cascade',
    )
    loan_id = fields.Many2one(related='generating_loan_line_id.loan_id')
    is_loan_payment_move = fields.Boolean()

    def _post(self, soft=True):
        posted = super()._post(soft)
        for move in self:
            skip_date = move.loan_id.skip_until_date
            if move.loan_id and all(l.is_payment_move_posted or skip_date and l.date < skip_date for l in move.loan_id.line_ids):
                move.loan_id.state = 'closed'
        return posted

    def open_loan(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _("Original Loan"),
            'views': [(False, 'form')],
            'res_model': 'account.loan',
            'res_id': self.loan_id.id,
        }
        return action
