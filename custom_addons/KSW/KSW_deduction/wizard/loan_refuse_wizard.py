from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class KswLoanRefuseWizard(models.TransientModel):
    """Collect a mandatory refusal reason for a loan request.

    Opened from each approval step (DM / HR / Accounting / GM) via the
    corresponding ``action_refuse_*`` on ``ksw.deduction``. The real
    authorization and state transition are performed by
    ``ksw.deduction._do_refuse`` so the same checks apply regardless of
    how the wizard is invoked.
    """

    _name = 'ksw.loan.refuse.wizard'
    _description = 'KSW Loan Refusal Wizard'

    deduction_id = fields.Many2one(
        'ksw.deduction', string='Loan Request',
        required=True, readonly=True, ondelete='cascade',
    )
    # Mirror the approval step the user is refusing from. Stored so the
    # wizard can show a clear label and the backend can re-validate that
    # the record is still at that step on submit.
    step = fields.Selection([
        ('pending_dm', 'DM Approval'),
        ('pending_hr', 'HR Approval'),
        ('pending_acc', 'Accounting Approval'),
        ('pending_gm', 'GM Final Approval'),
    ], string='Refusing At', required=True, readonly=True)

    employee_id = fields.Many2one(
        related='deduction_id.employee_id', readonly=True,
    )
    amount = fields.Monetary(related='deduction_id.amount', readonly=True)
    installments = fields.Integer(
        related='deduction_id.installments', readonly=True,
    )
    currency_id = fields.Many2one(
        related='deduction_id.currency_id', readonly=True,
    )

    reason = fields.Text(
        string='Refusal Reason', required=True,
        help='A clear, factual explanation of why this loan request is '
             'being refused. This will be visible to the employee on '
             'the loan form and recorded in the chatter history.',
    )

    @api.constrains('reason')
    def _check_reason_not_empty(self):
        for rec in self:
            if not (rec.reason and rec.reason.strip()):
                raise ValidationError(_("A refusal reason is required."))

    def action_confirm(self):
        """Apply the refusal via the deduction's _do_refuse."""
        self.ensure_one()
        if not self.deduction_id:
            raise UserError(_("No loan request selected."))
        self.deduction_id._do_refuse(self.reason, self.step)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Loan Request'),
            'res_model': 'ksw.deduction',
            'res_id': self.deduction_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

