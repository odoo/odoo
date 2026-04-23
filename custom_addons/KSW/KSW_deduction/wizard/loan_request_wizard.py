# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class KswLoanRequestWizard(models.TransientModel):
    """Self-service loan-request wizard for plain employees.

    Plain employees (`group_deduction_user` only, no officer / approver
    role) have read-only access to `ksw.deduction`. They cannot create
    deduction records directly — creating any deduction is a privileged
    action reserved for officers. This wizard is the ONLY route they
    have to submit a loan request for themselves.

    Flow:
      1. User opens the wizard via the "Request a Loan" menu (visible
         to every internal user).
      2. Wizard is pre-filled with the user's own employee record.
         The employee field is hidden (not editable).
      3. Type dropdown is filtered to `is_loan=True` types only, so the
         user can never submit a "penalty" or "company-paid" deduction.
      4. On confirm, the wizard creates a ksw.deduction via `sudo()`,
         then calls `action_submit()` which transitions the deduction
         into `approval_state='pending_dm'` — identical to what happens
         when an officer submits on the full form.

    Security note: the wizard runs as the user (no sudo on the wizard
    itself), but all writes to ksw.deduction use sudo because plain
    users have no write/create ACL on that model. The safety is that
    the wizard only exposes fields the user is allowed to set and
    pins `employee_id` to their own employee in `default_get` AND
    re-validates it in `action_submit`.
    """
    _name = 'ksw.loan.request.wizard'
    _description = 'KSW Loan Request (Self-Service)'

    employee_id = fields.Many2one(
        'hr.employee', required=True, readonly=True,
        help='Automatically set to the current user\'s employee. '
             'A user can only request a loan for themselves.',
    )
    type_id = fields.Many2one(
        'ksw.deduction.type', string='Loan Type', required=True,
        domain="[('is_loan', '=', True), ('active', '=', True)]",
        help='Loan-category deduction type. Non-loan types are hidden.',
    )
    amount = fields.Monetary(required=True)
    installments = fields.Integer(
        required=True, default=1,
        help='Number of monthly installments.',
    )
    start_month = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
        help='Month from which the first installment is deducted.',
    )
    reason = fields.Text(
        required=True,
        help='Brief justification for the loan. Helps the DM / HR / '
             'Accounting / GM approvers make an informed decision.',
    )
    description = fields.Text(
        help='Optional extra notes — repayment preferences, urgency, etc.',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Supporting Documents',
        help='Optional supporting documents (ID, proof of expense, etc.).',
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
        required=True,
    )

    # Live summary recap — shown read-only on the wizard so the user
    # can sanity-check their request before clicking Submit.
    installment_amount = fields.Monetary(
        compute='_compute_installment_amount',
        help='Estimated amount deducted each month '
             '(loan amount / number of installments).',
    )

    @api.depends('amount', 'installments')
    def _compute_installment_amount(self):
        for w in self:
            w.installment_amount = (
                w.amount / w.installments if w.installments else 0.0
            )

    # ------------------------------------------------------------------
    # Default setup
    # ------------------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        """Pin employee_id to the current user's employee.

        If the user has no linked employee record, the wizard cannot
        proceed (a loan must tie to an hr.employee). We surface a
        clear error rather than letting the save crash with a vague
        required-field message.
        """
        vals = super().default_get(fields_list)
        emp = self.env.user.employee_id
        if not emp:
            raise UserError(_(
                "You cannot request a loan because your user account "
                "is not linked to an employee record. Please contact "
                "HR to link your account before requesting a loan."
            ))
        vals['employee_id'] = emp.id
        # Pre-select the first available loan type so the form is
        # ready to submit in one click if the user has no preference.
        if 'type_id' in fields_list and not vals.get('type_id'):
            default_type = self.env['ksw.deduction.type'].sudo().search(
                [('is_loan', '=', True), ('active', '=', True)],
                order='sequence, id', limit=1,
            )
            if default_type:
                vals['type_id'] = default_type.id
                if default_type.default_installments:
                    vals['installments'] = default_type.default_installments
        return vals

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id and self.type_id.default_installments:
            self.installments = self.type_id.default_installments

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------
    def action_submit(self):
        """Create the ksw.deduction record and start the approval chain.

        Uses sudo() because plain users have no create/write ACL on
        ksw.deduction. Safety is enforced by (a) pinning employee_id
        to env.user.employee_id, not trusting form input, and (b)
        forcing type_id to a loan type (re-checked here even though
        the UI domain already filters it).
        """
        self.ensure_one()

        # Re-validate invariants (defence-in-depth; UI already enforces these)
        if self.employee_id != self.env.user.employee_id:
            raise UserError(_(
                "You can only request a loan for yourself."
            ))
        if not self.type_id.is_loan:
            raise UserError(_(
                "Only loan-type deductions can be submitted through "
                "this form. Chosen type %(t)s is not a loan.",
                t=self.type_id.name,
            ))
        if self.amount <= 0:
            raise ValidationError(_("Amount must be greater than zero."))
        if self.installments < 1:
            raise ValidationError(_("Installments must be at least 1."))

        Deduction = self.env['ksw.deduction'].sudo()
        deduction = Deduction.create({
            'employee_id': self.employee_id.id,
            'type_id': self.type_id.id,
            'amount': self.amount,
            'installments': self.installments,
            'start_month': self.start_month,
            'reason': self.reason,
            'description': self.description or False,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
            'currency_id': self.currency_id.id,
        })

        # Kick off the approval chain (draft -> pending_dm)
        deduction.action_submit()

        # Return an action that opens the just-created record in
        # read-only mode so the requester can see the approval state
        # progress on their "My Loans" list. They inherit read access
        # via the existing user record rule (own records).
        return {
            'type': 'ir.actions.act_window',
            'name': _('Loan Request #%s') % deduction.name,
            'res_model': 'ksw.deduction',
            'res_id': deduction.id,
            'view_mode': 'form',
            'target': 'current',
        }

