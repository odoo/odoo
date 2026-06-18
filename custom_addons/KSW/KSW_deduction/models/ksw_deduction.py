from datetime import date
from dateutil.relativedelta import relativedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


LOAN_APPROVAL_STATES = [
    ('pending_dm', 'Pending DM Approval'),
    ('pending_hr', 'Pending HR Approval'),
    ('pending_acc', 'Pending Accounting'),
    ('pending_gm', 'Pending GM Final'),
    ('approved', 'Approved'),
    ('refused', 'Refused'),
]


class KswDeduction(models.Model):
    _name = 'ksw.deduction'
    _description = 'KSW Deduction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        required=True, copy=False, readonly=True, default='New', tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', required=True, tracking=True, ondelete='restrict',
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True, readonly=True,
    )
    manager_id = fields.Many2one(
        related='employee_id.parent_id', store=True, readonly=True,
    )

    # ------------------------------------------------------------------
    # Type & category (drives workflow)
    # ------------------------------------------------------------------
    type_id = fields.Many2one(
        'ksw.deduction.type', required=True, tracking=True,
        ondelete='restrict',
    )
    category = fields.Selection(
        related='type_id.category', store=True, readonly=True,
    )
    is_loan = fields.Boolean(
        related='type_id.is_loan', store=True, readonly=True,
    )

    # ------------------------------------------------------------------
    # Financial details
    # ------------------------------------------------------------------
    amount = fields.Monetary(
        required=True, tracking=True,
        help='Total amount of the deduction.',
    )
    installments = fields.Integer(
        default=1, required=True, tracking=True,
        help='Number of monthly installments. Defaults to the type suggestion.',
    )
    installment_amount = fields.Monetary(
        compute='_compute_installment_amount', store=True,
        help='Base amount per installment (amount / installments). '
             'The last line absorbs the rounding residue.',
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
        required=True,
    )
    start_month = fields.Date(
        required=True, tracking=True,
        default=lambda s: fields.Date.context_today(s).replace(day=1),
        help='Month from which installments start (first day of month).',
    )
    reason = fields.Text()
    description = fields.Text()
    attachment_ids = fields.Many2many(
        'ir.attachment', 'ksw_deduction_attachment_rel',
        'deduction_id', 'attachment_id',
        string='Attachments',
    )

    # ------------------------------------------------------------------
    # State machine (lifecycle)
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, tracking=True, copy=False)

    # Loan approval workflow (in parallel with state='draft')
    approval_state = fields.Selection(
        LOAN_APPROVAL_STATES, copy=False, tracking=True,
        help='Only relevant for loan types. Drives the 5-step approval chain.',
    )

    # ------------------------------------------------------------------
    # Installment schedule
    # ------------------------------------------------------------------
    line_ids = fields.One2many('ksw.deduction.line', 'deduction_id',
                               string='Installment Lines', copy=False)
    total_paid = fields.Monetary(
        compute='_compute_progress', store=True,
    )
    total_pending = fields.Monetary(
        compute='_compute_progress', store=True,
    )
    progress_percent = fields.Float(
        compute='_compute_progress', store=True,
        help='Percentage of the total amount already paid.',
    )

    # ------------------------------------------------------------------
    # Approvers tracking (loan only)
    # ------------------------------------------------------------------
    dm_approved_by = fields.Many2one('hr.employee', readonly=True, copy=False)
    dm_approved_date = fields.Datetime(readonly=True, copy=False)
    hr_approved_by = fields.Many2one('hr.employee', readonly=True, copy=False)
    hr_approved_date = fields.Datetime(readonly=True, copy=False)
    acc_approved_by = fields.Many2one('hr.employee', readonly=True, copy=False)
    acc_approved_date = fields.Datetime(readonly=True, copy=False)
    gm_approved_by = fields.Many2one('hr.employee', readonly=True, copy=False)
    gm_approved_date = fields.Datetime(readonly=True, copy=False)

    # GM modification tracking
    gm_original_amount = fields.Monetary(readonly=True, copy=False)
    gm_original_installments = fields.Integer(readonly=True, copy=False)

    # Accountant modification tracking (mirror of GM snapshot)
    acc_original_amount = fields.Monetary(readonly=True, copy=False)
    acc_original_installments = fields.Integer(readonly=True, copy=False)

    # Approval confirmation checkboxes (shown in Decision Support tab)
    x_hr_no_penalties_confirmed = fields.Boolean(
        string='HR: No pending penalties on this employee',
        tracking=True, copy=False,
        help='HR must tick this before approving. If a penalty is '
             'pending, create it first via "New Penalty" button so the '
             'decision-support values reflect it.',
    )
    x_acc_budget_confirmed = fields.Boolean(
        string='Accounting: Budget confirmed',
        tracking=True, copy=False,
        help='Accounting must tick this before approving — confirms '
             'monthly budget impact and total outstanding are within '
             'the approved envelope.',
    )

    # Submit-button visibility (creator or officer)
    x_can_submit = fields.Boolean(compute='_compute_x_can_submit')

    # Cancel-button visibility.
    # - Loans: only the requesting employee (employee_id.user_id) can
    #   cancel their own request. Approvers must use "Refuse" (with
    #   mandatory reason) instead of cancelling.
    # - Non-loans: Deduction Officer/Manager only.
    x_can_cancel = fields.Boolean(compute='_compute_x_can_cancel')

    # ------------------------------------------------------------------
    # Refusal tracking (loan only — any approval step)
    # ------------------------------------------------------------------
    x_refusal_reason = fields.Text(
        string='Refusal Reason', readonly=True, copy=False, tracking=True,
        help='Reason provided by the approver when refusing the loan '
             'request. Visible to the employee so they know why it was '
             'rejected and can decide whether to modify and resubmit.',
    )
    x_refused_by = fields.Many2one(
        'hr.employee', string='Refused By',
        readonly=True, copy=False, tracking=True,
    )
    x_refused_date = fields.Datetime(readonly=True, copy=False, tracking=True)
    x_refused_at_step = fields.Selection(
        LOAN_APPROVAL_STATES, string='Refused At',
        readonly=True, copy=False, tracking=True,
        help='Which approval step the loan was at when it was refused.',
    )

    # ------------------------------------------------------------------
    # DM approval authorization (derived — no dedicated group)
    # ------------------------------------------------------------------
    # DM approval authority is NOT a separate group; it is conferred by
    # being the employee's direct manager (employee.parent_id.user_id)
    # or by holding Deduction Officer/Manager privileges.
    x_can_dm_approve = fields.Boolean(
        compute='_compute_x_can_dm_approve',
        help="True if the current user can perform the DM approval step "
             "on this deduction — either they are the employee's direct "
             "manager, or they hold the Deduction Officer/Manager role.",
    )

    # ==================================================================
    # Per-user permission mirrors (read-only, driven by the
    # "Loan Modification" privilege on res.groups)
    # ==================================================================
    # These three fields mirror the current user's Loan Modification
    # level (blank / Edit only / Delete only / Edit and Delete) so the
    # form view can use them in ``readonly`` expressions. They are NOT
    # stored — the authoritative state is group membership, set on the
    # user form (Access Rights tab → KSW Deductions → Loan Modification).
    #
    #   x_allow_edit_amount       ↔ has_group('group_loan_edit')
    #   x_allow_edit_installments ↔ has_group('group_loan_edit')
    #   x_allow_delete            ↔ has_group('group_loan_delete')
    #
    # "Edit and Delete" implies both "Edit only" and "Delete only", so a
    # user at that level gets True for all three mirrors. Deduction
    # Managers also get True for all three (Manager implies
    # group_loan_edit_delete).
    x_allow_edit_amount = fields.Boolean(
        string='Current user may edit amount',
        compute='_compute_user_permissions',
        help='True if the current user holds the "Edit only" or '
             '"Edit and Delete" level of the Loan Modification privilege.',
    )
    x_allow_edit_installments = fields.Boolean(
        string='Current user may edit installments',
        compute='_compute_user_permissions',
        help='True if the current user holds the "Edit only" or '
             '"Edit and Delete" level of the Loan Modification privilege.',
    )
    x_allow_delete = fields.Boolean(
        string='Current user may delete',
        compute='_compute_user_permissions',
        help='True if the current user holds the "Delete only" or '
             '"Edit and Delete" level of the Loan Modification privilege.',
    )

    @api.depends_context('uid')
    def _compute_user_permissions(self):
        """Reflect the current user's Loan Modification privilege level.

        Read once (group membership doesn't vary per record) and fan
        out to every record in self.
        """
        user = self.env.user
        can_edit = user.has_group('KSW_deduction.group_loan_edit')
        can_delete = user.has_group('KSW_deduction.group_loan_delete')
        for rec in self:
            rec.x_allow_edit_amount = can_edit
            rec.x_allow_edit_installments = can_edit
            rec.x_allow_delete = can_delete

    # ==================================================================
    # HR Decisions (Pass 2): EOS / Vacation balance / Active deductions
    # ==================================================================

    # --- End-of-Service Benefit (Saudi Articles 84–88) ---
    x_eos_service_years = fields.Float(
        string='Service Years', compute='_compute_eos_fields',
        digits=(5, 2),
        help='Years of service from earliest contract_date_start of '
             'any version to today (calendar days / 365.25).',
    )
    x_eos_last_wage = fields.Monetary(
        string='Last Wage', compute='_compute_eos_fields',
        help='Wage of the current active version.',
    )
    x_eos_force_majeure = fields.Boolean(
        string='Force Majeure (Art. 87)',
        help='If checked, resignation entitlement equals the full '
             'termination amount (Art. 87 — force majeure waives the '
             '2-year minimum and tier reductions).',
    )
    x_eos_termination_amount = fields.Monetary(
        string='EOS — Termination (Art. 84)',
        compute='_compute_eos_fields',
        help='Article 84: ½ month wage × first 5 years + 1 month wage × '
             'years above 5 (pro-rated for fractional years).',
    )
    x_eos_resignation_amount = fields.Monetary(
        string='EOS — Resignation (Art. 85)',
        compute='_compute_eos_fields',
        help='Article 85: tiered fraction of the termination amount — '
             '<2 yrs: nothing, 2–5: 1/3, 5–10: 2/3, ≥10: full. '
             'Force majeure → full termination amount.',
    )

    # --- Translated annual vacation balance ---
    x_vac_balance_days = fields.Float(
        string='Vacation Balance (days)',
        compute='_compute_vacation_balance',
        digits=(10, 4),
        help='Accrued untaken annual leave balance for the employee, '
             'taken from ksw.annual.leave.remaining_balance.',
    )
    x_vac_balance_value = fields.Monetary(
        string='Vacation Balance Value',
        compute='_compute_vacation_balance',
        help='Monetary value of the vacation balance using FIFO '
             'historical wage slicing per hr.version.',
    )
    x_vac_balance_breakdown = fields.Char(
        string='Vacation Balance Breakdown',
        compute='_compute_vacation_balance',
        help='Human-readable per-version daily-rate breakdown.',
    )

    # --- Active deductions summary (other deductions for the same employee) ---
    x_active_deductions_count = fields.Integer(
        string='Other Active Deductions',
        compute='_compute_active_deductions_summary',
    )
    x_active_deductions_total_outstanding = fields.Monetary(
        string='Total Outstanding (other)',
        compute='_compute_active_deductions_summary',
    )
    x_active_deductions_monthly_impact = fields.Monetary(
        string='Monthly Impact (other)',
        compute='_compute_active_deductions_summary',
    )
    x_active_deductions_summary = fields.Html(
        string='Active Deductions Breakdown',
        compute='_compute_active_deductions_summary',
        sanitize=False,
    )

    # Employee's current-month total across ALL active deductions
    # (this record included) — useful on the list view for HR/Accounting.
    x_emp_monthly_total = fields.Monetary(
        string="Employee's Total This Month",
        related='employee_id.x_deduction_monthly_total',
        currency_field='currency_id',
        readonly=True,
    )

    # ==================================================================
    # Computed fields
    # ==================================================================

    @api.depends('amount', 'installments')
    def _compute_installment_amount(self):
        for rec in self:
            if rec.installments and rec.amount:
                rec.installment_amount = rec.amount / rec.installments
            else:
                rec.installment_amount = 0.0

    @api.depends('line_ids.state', 'line_ids.amount', 'amount')
    def _compute_progress(self):
        for rec in self:
            paid = sum(rec.line_ids.filtered(
                lambda l: l.state == 'paid').mapped('amount'))
            pending = sum(rec.line_ids.filtered(
                lambda l: l.state == 'pending').mapped('amount'))
            rec.total_paid = paid
            rec.total_pending = pending
            rec.progress_percent = (
                (paid / rec.amount * 100.0) if rec.amount else 0.0)

    # ------------------------------------------------------------------
    # HR Decisions: End-of-Service computation
    # ------------------------------------------------------------------
    @api.depends(
        'employee_id',
        'employee_id.version_ids.contract_date_start',
        'employee_id.version_ids.active',
        'employee_id.current_version_id.wage',
        'x_eos_force_majeure',
    )
    def _compute_eos_fields(self):
        today = fields.Date.context_today(self)
        for rec in self:
            wage = 0.0
            years = 0.0
            if rec.employee_id:
                emp = rec.employee_id.sudo()
                wage = emp.current_version_id.wage or 0.0
                versions = emp.version_ids.filtered(
                    lambda v: v.contract_date_start)
                if versions:
                    joining = min(versions.mapped('contract_date_start'))
                    days = max((today - joining).days, 0)
                    years = days / 365.25
            rec.x_eos_service_years = years
            rec.x_eos_last_wage = wage
            # Article 84 — termination
            first = min(years, 5.0)
            extra = max(years - 5.0, 0.0)
            term = 0.5 * wage * first + 1.0 * wage * extra
            rec.x_eos_termination_amount = term
            # Article 85 — resignation tiers (or force majeure → full)
            if rec.x_eos_force_majeure:
                resig = term
            elif years < 2.0:
                resig = 0.0
            elif years < 5.0:
                resig = term / 3.0
            elif years < 10.0:
                resig = term * 2.0 / 3.0
            else:
                resig = term
            rec.x_eos_resignation_amount = resig

    # ------------------------------------------------------------------
    # HR Decisions: Vacation balance translated via FIFO historical wage
    # ------------------------------------------------------------------
    @api.depends('employee_id')
    def _compute_vacation_balance(self):
        AnnualLeave = self.env['ksw.annual.leave'].sudo()
        for rec in self:
            days = 0.0
            value = 0.0
            label = ''
            if rec.employee_id:
                ksw_rec = AnnualLeave.search(
                    [('employee_id', '=', rec.employee_id.id)], limit=1)
                if ksw_rec:
                    days = ksw_rec.remaining_balance or 0.0
                if days > 0:
                    result = AnnualLeave._compute_historical_vacation_value(
                        rec.employee_id, days, exclude_days=0.0)
                    value = result.get('total', 0.0)
                    label = result.get('label', '') or ''
            rec.x_vac_balance_days = days
            rec.x_vac_balance_value = value
            rec.x_vac_balance_breakdown = label

    # ------------------------------------------------------------------
    # HR Decisions: Other active deductions for the same employee
    # ------------------------------------------------------------------
    @api.depends('employee_id')
    def _compute_active_deductions_summary(self):
        for rec in self:
            count = 0
            outstanding = 0.0
            monthly = 0.0
            html = ''
            if rec.employee_id:
                self_id = rec.id if isinstance(rec.id, int) else 0
                siblings = self.sudo().search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', self_id),
                ])
                count = len(siblings)
                outstanding = sum(siblings.mapped('total_pending'))
                monthly = sum(siblings.mapped('installment_amount'))
                if siblings:
                    # Group per type for display
                    groups = {}
                    for sib in siblings:
                        key = sib.type_id.name or _('Unknown')
                        g = groups.setdefault(
                            key, {'n': 0, 'out': 0.0, 'mo': 0.0})
                        g['n'] += 1
                        g['out'] += sib.total_pending
                        g['mo'] += sib.installment_amount
                    items = []
                    for name, g in groups.items():
                        items.append(Markup(
                            '<li><b>%s</b>: %d active, '
                            '%.2f outstanding, %.2f/month</li>'
                        ) % (name, g['n'], g['out'], g['mo']))
                    html = Markup('<ul>') + Markup('').join(items) + Markup('</ul>')
            rec.x_active_deductions_count = count
            rec.x_active_deductions_total_outstanding = outstanding
            rec.x_active_deductions_monthly_impact = monthly
            rec.x_active_deductions_summary = html

    # ==================================================================
    # Onchange helpers
    # ==================================================================

    @api.onchange('type_id')
    def _onchange_type_id(self):
        if self.type_id and self.type_id.default_installments:
            self.installments = self.type_id.default_installments

    # ==================================================================
    # UI helpers (smart buttons)
    # ==================================================================

    def action_view_installments(self):
        """Smart-button target. Re-opens the record on the same form
        (scrolls back to the Installments page via `default_tab`).
        Used for the summary stat buttons in the header — clicking
        them simply returns the user to the form, which is the
        expected no-op behaviour of an info-only pill.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ==================================================================
    # CRUD
    # ==================================================================

    @api.model_create_multi
    def create(self, vals_list):
        # Category-scoped reference:
        #   loans                   -> LO00001  (code 'ksw.deduction.loan')
        #   company-paid (penalty)  -> PE00001  (code 'ksw.deduction.penalty')
        #   borrowed non-loan       -> DE00001  (code 'ksw.deduction.regular')
        # Falls back to the legacy 'ksw.deduction' sequence only if
        # type_id is missing at create-time (UI always requires it).
        Seq = self.env['ir.sequence']
        DeductionType = self.env['ksw.deduction.type']
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                code = 'ksw.deduction'
                type_id = vals.get('type_id')
                if type_id:
                    ded_type = DeductionType.browse(type_id)
                    if ded_type.is_loan:
                        code = 'ksw.deduction.loan'
                    elif ded_type.category == 'company_paid':
                        code = 'ksw.deduction.penalty'
                    else:
                        code = 'ksw.deduction.regular'
                vals['name'] = Seq.next_by_code(code) or 'New'
        records = super().create(vals_list)
        return records

    def unlink(self):
        # Block deletion if any installment has been paid (linked to a confirmed payslip)
        # and honour the per-record "Allow deletion" override.
        is_super = self.env.su
        for rec in self:
            paid_lines = rec.line_ids.filtered(lambda l: l.state == 'paid')
            if paid_lines:
                raise UserError(_(
                    "Deduction %(name)s cannot be deleted because %(n)s "
                    "installment(s) have already been paid. "
                    "Cancel it instead.",
                    name=rec.name, n=len(paid_lines),
                ))
            # The Loan Modification privilege only governs LOAN records.
            # Non-loan deductions (penalties, advances, etc.) are gated
            # purely by the model-level ACL (perm_unlink — Manager only),
            # so we don't run the x_allow_delete check here. This keeps
            # Loan Modification orthogonal to Deduction Management:
            # an HR/Admin can be a Deduction Manager (delete any
            # non-loan) without inheriting loan-delete rights, and a
            # non-Manager loan approver can be granted loan-delete via
            # Loan Modification = Delete only / Edit and Delete.
            if rec.is_loan and not rec.x_allow_delete and not is_super:
                raise UserError(_(
                    "You are not allowed to delete loan deduction "
                    "%(name)s. Deleting loans requires the "
                    "\"Delete only\" or \"Edit and Delete\" level of "
                    "the Loan Modification privilege. Ask an "
                    "administrator to set it on your user (Access "
                    "Rights → KSW Deductions → Loan Modification).",
                    name=rec.name,
                ))
        return super().unlink()

    # ==================================================================
    # State transitions
    # ==================================================================

    def action_submit(self):
        """Submit a draft deduction.

        - Non-loan types: draft -> active (instant, with attachments).
        - Loan types:     draft -> pending_dm (starts approval chain).
        """
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft deductions can be submitted."))
            # Guard against re-submitting a loan whose approval chain
            # has already started. `state` stays 'draft' throughout the
            # DM→HR→Acc→GM chain; only `approval_state` advances. The
            # view hides the Submit button in that case, but keep a
            # server-side check in case the method is called from
            # elsewhere (RPC, automation, etc.).
            if rec.is_loan and rec.approval_state:
                raise UserError(_(
                    "This loan request has already been submitted and "
                    "is currently %(s)s. It cannot be submitted again.",
                    s=dict(LOAN_APPROVAL_STATES).get(
                        rec.approval_state, rec.approval_state),
                ))
            if rec.amount <= 0:
                raise ValidationError(_("Amount must be greater than zero."))
            if rec.installments < 1:
                raise ValidationError(
                    _("Installments must be at least 1."))
            if rec.is_loan:
                rec.write({'approval_state': 'pending_dm'})
                rec.message_post(
                    body=Markup(
                        '<strong>📤 Loan Request Submitted</strong><br/>'
                        '<b>Amount:</b> %(amt)s<br/>'
                        '<b>Installments:</b> %(n)s<br/>'
                        '<b>Reason:</b> %(r)s'
                    ) % {
                        'amt': rec.amount,
                        'n': rec.installments,
                        'r': rec.reason or '—',
                    },
                    subtype_xmlid='mail.mt_note',
                )
            else:
                rec._activate_and_generate_lines()
                rec.message_post(
                    body=Markup(
                        '<strong>✅ Deduction Activated (Instant)</strong>'
                    ),
                    subtype_xmlid='mail.mt_note',
                )

    def action_cancel(self):
        """Cancel a deduction.

        Authorization:
          - Loan records: only the employee who requested the loan
            (``employee_id.user_id``) or the superuser may cancel. This
            deliberately excludes approvers — they must use the
            "Refuse" flow (which records a mandatory reason) instead of
            cancelling.
          - Non-loan records: Deduction Officer/Manager (via the
            standard model-level ACL).
        """
        for rec in self:
            if rec.state == 'completed':
                raise UserError(
                    _("Completed deductions cannot be cancelled."))
            is_employee_owner = bool(
                rec.employee_id.user_id
                and rec.employee_id.user_id.id == self.env.uid
            )
            if rec.is_loan and not self.env.su and not is_employee_owner:
                raise UserError(_(
                    "Only the employee who submitted the loan request "
                    "can cancel it. Approvers must use the 'Refuse' "
                    "button, which records a mandatory reason that is "
                    "shown to the employee."
                ))
            # The requesting employee has only read access to
            # ksw.deduction (record rule lets them see their own), so
            # elevate to write the cancel transition.
            target = rec.sudo() if rec.is_loan else rec
            target.line_ids.filtered(
                lambda l: l.state == 'pending').write({'state': 'skipped'})
            target.write({'state': 'cancelled', 'approval_state': False})
            target.message_post(
                body=Markup(
                    '<strong>⛔ Cancelled by %s</strong>'
                ) % self.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_reset_to_draft(self):
        """Reset to draft.

        Allowed when:
          - state is 'active' or 'cancelled' (existing behaviour,
            officer/manager via model ACL), OR
          - approval_state is 'refused' — the requesting employee, an
            officer/manager, or superuser may reset so the employee can
            modify the request and resubmit it. The employee only has
            read access, so we elevate with sudo() after the auth check.

        All refusal / approval snapshots are cleared so the record is
        returned to a clean draft state.
        """
        for rec in self:
            if rec.line_ids.filtered(lambda l: l.state == 'paid'):
                raise UserError(_(
                    "Cannot reset to draft: some installments are already paid."))
            target = rec
            if rec.approval_state == 'refused' and not self.env.su:
                is_employee_owner = bool(
                    rec.employee_id.user_id
                    and rec.employee_id.user_id.id == self.env.uid
                )
                is_officer = self.env.user.has_group(
                    'KSW_deduction.group_deduction_officer')
                if not (is_employee_owner or is_officer):
                    raise UserError(_(
                        "Only the requesting employee or a Deduction "
                        "Officer/Manager can reset a refused loan "
                        "request to draft."
                    ))
                # Employee has read-only access on ksw.deduction; elevate.
                if is_employee_owner and not is_officer:
                    target = rec.sudo()
            target.line_ids.unlink()
            target.write({
                'state': 'draft',
                'approval_state': False,
                'dm_approved_by': False, 'dm_approved_date': False,
                'hr_approved_by': False, 'hr_approved_date': False,
                'acc_approved_by': False, 'acc_approved_date': False,
                'gm_approved_by': False, 'gm_approved_date': False,
                'gm_original_amount': 0.0, 'gm_original_installments': 0,
                'acc_original_amount': 0.0, 'acc_original_installments': 0,
                'x_hr_no_penalties_confirmed': False,
                'x_acc_budget_confirmed': False,
                'x_refusal_reason': False,
                'x_refused_by': False,
                'x_refused_date': False,
                'x_refused_at_step': False,
            })

    # ==================================================================
    # Loan workflow
    # ==================================================================

    def _check_loan(self):
        for rec in self:
            if not rec.is_loan:
                raise UserError(_(
                    "This action is only available for loan-type deductions."))

    def action_dm_approve(self):
        """Step 1: DM (direct manager) approval.

        There is no dedicated 'DM Approver' group. Only one of the
        following may run this action:
          - The employee's direct manager (employee.parent_id.user_id),
          - A Deduction Officer or Manager (fallback when the line
            manager is unavailable),
          - Superuser.
        """
        self._check_loan()
        for rec in self:
            if rec.approval_state != 'pending_dm':
                raise UserError(_("Not pending DM approval."))
            if not rec.x_can_dm_approve:
                raise UserError(_(
                    "Only the employee's direct manager (or a Deduction "
                    "Officer/Manager) can perform the DM approval step."
                ))
            # Plain internal users (the normal case for a line manager)
            # only have read access to ksw.deduction. Since DM authority
            # is derived, we elevate for this specific transition.
            rec.sudo().write({
                'approval_state': 'pending_hr',
                'dm_approved_by': self.env.user.employee_id.id,
                'dm_approved_date': fields.Datetime.now(),
            })
            rec.sudo().message_post(
                body=Markup(
                    '<strong>✅ Step 1 — DM Approval</strong><br/>'
                    '<b>By:</b> %s'
                ) % self.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_hr_approve(self):
        self._check_loan()
        for rec in self:
            if rec.approval_state != 'pending_hr':
                raise UserError(_("Not pending HR approval."))
            if not rec.x_hr_no_penalties_confirmed:
                raise ValidationError(_(
                    "HR cannot approve until the checkbox "
                    "'No pending penalties on this employee' is ticked "
                    "in the Decision Support tab. If a penalty is "
                    "pending, create it first via 'New Penalty'."
                ))
            rec.write({
                'approval_state': 'pending_acc',
                'hr_approved_by': self.env.user.employee_id.id,
                'hr_approved_date': fields.Datetime.now(),
            })
            rec.message_post(
                body=Markup(
                    '<strong>✅ Step 2 — HR Approval</strong><br/>'
                    '<b>By:</b> %s<br/>'
                    '<b>No pending penalties:</b> confirmed'
                ) % self.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    def action_acc_approve(self):
        self._check_loan()
        for rec in self:
            if rec.approval_state != 'pending_acc':
                raise UserError(_("Not pending accounting approval."))
            if not rec.x_acc_budget_confirmed:
                raise ValidationError(_(
                    "Accounting cannot approve until the checkbox "
                    "'Budget confirmed' is ticked in the Decision "
                    "Support tab."
                ))
            # Log any modification done during pending_acc
            modified = []
            if (rec.acc_original_amount
                    and rec.acc_original_amount != rec.amount):
                modified.append(
                    'Amount: %.2f → %.2f' % (
                        rec.acc_original_amount, rec.amount))
            if (rec.acc_original_installments
                    and rec.acc_original_installments != rec.installments):
                modified.append(
                    'Installments: %d → %d' % (
                        rec.acc_original_installments, rec.installments))
            rec.write({
                'approval_state': 'pending_gm',
                'acc_approved_by': self.env.user.employee_id.id,
                'acc_approved_date': fields.Datetime.now(),
            })
            body = [
                '<strong>✅ Step 3 — Accounting Approval</strong><br/>',
                '<b>By:</b> %s<br/>' % self.env.user.name,
                '<b>Budget confirmed:</b> yes<br/>',
                '<b>Installments:</b> %d<br/>' % rec.installments,
                '<b>Installment Amount:</b> %.2f' % rec.installment_amount,
            ]
            if modified:
                body.append('<br/><b>Modifications by Accounting:</b><br/>')
                for m in modified:
                    body.append('&nbsp;&nbsp;• %s<br/>' % m)
            rec.message_post(
                body=Markup(''.join(body)),
                subtype_xmlid='mail.mt_note',
            )


    def action_gm_approve(self):
        """Step 4: GM final approval.

        GM may have modified `amount` and/or `installments` before clicking.
        Any change is logged (gm_original_* was captured when entering the
        pending_gm state via write()). After approval, the deduction moves
        to 'active' and installment lines are generated.
        """
        self._check_loan()
        for rec in self:
            if rec.approval_state != 'pending_gm':
                raise UserError(_("Not pending GM final approval."))
            # Log any modification
            modified = []
            if (rec.gm_original_amount
                    and rec.gm_original_amount != rec.amount):
                modified.append(
                    'Amount: %.2f → %.2f' % (
                        rec.gm_original_amount, rec.amount))
            if (rec.gm_original_installments
                    and rec.gm_original_installments != rec.installments):
                modified.append(
                    'Installments: %d → %d' % (
                        rec.gm_original_installments, rec.installments))
            rec.write({
                'approval_state': 'approved',
                'gm_approved_by': self.env.user.employee_id.id,
                'gm_approved_date': fields.Datetime.now(),
            })
            rec._activate_and_generate_lines()
            body = [
                '<strong>✅ Step 4 — GM Final Approval</strong><br/>',
                '<b>By:</b> %s<br/>' % self.env.user.name,
            ]
            if modified:
                body.append('<b>Modifications:</b><br/>')
                for m in modified:
                    body.append('&nbsp;&nbsp;• %s<br/>' % m)
            rec.message_post(
                body=Markup(''.join(body)),
                subtype_xmlid='mail.mt_note',
            )

    # ==================================================================
    # Loan refusal (any step)
    # ==================================================================
    # Refusal is handled via a wizard that collects a mandatory reason.
    # Each step has a thin action that just opens the wizard with the
    # right context; the wizard calls ``_do_refuse`` which runs the
    # real authorization + state transition. The reason is shown to
    # the employee on the form (refusal banner) and in the chatter.

    def _open_refuse_wizard(self, step):
        self.ensure_one()
        self._check_loan()
        if self.approval_state != step:
            raise UserError(_(
                "This loan is not currently at the %s step.",
            ) % dict(LOAN_APPROVAL_STATES).get(step, step))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refuse Loan Request'),
            'res_model': 'ksw.loan.refuse.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_deduction_id': self.id,
                'default_step': step,
            },
        }

    def action_refuse_dm(self):
        return self._open_refuse_wizard('pending_dm')

    def action_refuse_hr(self):
        return self._open_refuse_wizard('pending_hr')

    def action_refuse_acc(self):
        return self._open_refuse_wizard('pending_acc')

    def action_refuse_gm(self):
        return self._open_refuse_wizard('pending_gm')

    def _do_refuse(self, reason, step):
        """Apply a refusal from the refuse-wizard.

        Performs per-step authorization:
          * pending_dm: current user must qualify via ``x_can_dm_approve``
            (derived — direct manager, or Deduction Officer/Manager).
          * pending_hr/acc/gm: current user must hold the matching
            Loan Approval group.

        Uses ``sudo()`` for the write/message_post because the DM
        approver may only have read access, and mirrors the pattern
        used by ``action_dm_approve``.
        """
        self.ensure_one()
        self._check_loan()
        if self.approval_state != step:
            raise UserError(_(
                "This loan is not currently at the %s step.",
            ) % dict(LOAN_APPROVAL_STATES).get(step, step))
        reason = (reason or '').strip()
        if not reason:
            raise ValidationError(_("A refusal reason is required."))
        user = self.env.user
        if step == 'pending_dm':
            if not self.x_can_dm_approve:
                raise UserError(_(
                    "Only the employee's direct manager (or a Deduction "
                    "Officer/Manager) can refuse at the DM step."
                ))
        elif step == 'pending_hr':
            if not user.has_group('KSW_deduction.group_loan_hr'):
                raise UserError(_(
                    "Only HR Approvers can refuse at the HR step."))
        elif step == 'pending_acc':
            if not user.has_group('KSW_deduction.group_loan_acc'):
                raise UserError(_(
                    "Only Accounting Approvers can refuse at the "
                    "Accounting step."))
        elif step == 'pending_gm':
            if not user.has_group('KSW_deduction.group_loan_gm'):
                raise UserError(_(
                    "Only GM Final Approvers can refuse at the GM "
                    "step."))
        else:
            raise UserError(_("Invalid refusal step."))

        self.sudo().write({
            'approval_state': 'refused',
            'x_refusal_reason': reason,
            'x_refused_by': user.employee_id.id,
            'x_refused_date': fields.Datetime.now(),
            'x_refused_at_step': step,
        })
        self.sudo().message_post(
            body=Markup(
                '<strong>⛔ Refused at %(step)s</strong><br/>'
                '<b>By:</b> %(by)s<br/>'
                '<b>Reason:</b> %(r)s'
            ) % {
                'step': dict(LOAN_APPROVAL_STATES).get(step, step),
                'by': user.name,
                'r': reason,
            },
            subtype_xmlid='mail.mt_note',
        )

    # ==================================================================
    # GM entry hook: snapshot amount/installments
    # ==================================================================

    def write(self, vals):
        # Snapshot original values when moving into pending_acc / pending_gm
        # so we can log any modifications done during those steps.
        if 'approval_state' in vals:
            if vals['approval_state'] == 'pending_acc':
                for rec in self:
                    rec.acc_original_amount = rec.amount
                    rec.acc_original_installments = rec.installments
            elif vals['approval_state'] == 'pending_gm':
                for rec in self:
                    rec.gm_original_amount = rec.amount
                    rec.gm_original_installments = rec.installments

        # ------------------------------------------------------------------
        # Defer the installment-total-consistency check when O2M commands
        # are present in `vals`. Odoo dispatches each (1, id, vals)
        # update as an individual `ksw.deduction.line.write`, and the
        # @api.constrains on the line fires after every one of those
        # calls. If the user balances a decrease on one line with an
        # increase on another (e.g. #5: 200→150, #6: 200→250), the
        # per-line constraint would reject the first write before the
        # compensating second write is applied. We mute the line-level
        # check via `_skip_installment_total_check` in the context and
        # run ONE authoritative check on the fully-updated parent after
        # super().write() returns.
        # ------------------------------------------------------------------
        has_line_commands = bool(vals.get('line_ids'))
        self_for_write = (
            self.with_context(_skip_installment_total_check=True)
            if has_line_commands else self
        )
        res = super(KswDeduction, self_for_write).write(vals)
        if has_line_commands:
            # Run on the originals (without the skip-flag) so any
            # validation errors are raised in the caller's context.
            self._validate_installments_total()
        return res

    # ------------------------------------------------------------------
    # Installment total consistency (shared entry point)
    # ------------------------------------------------------------------
    def _validate_installments_total(self):
        """Assert that the sum of non-skipped installments equals the
        deduction's total `amount`.

        Invoked from two places:
          1. `ksw.deduction.line._check_total_matches_deduction_amount`
             — the @api.constrains that fires on direct line writes
             (outside a parent save).
          2. `ksw.deduction.write()` — the deferred post-batch hook
             that runs ONCE after all O2M line writes have settled,
             bypassing the per-line fire-too-early problem.

        Only 'active' and 'completed' deductions are checked. 'draft'
        has no lines yet, and 'cancelled' lines are marked 'skipped'
        (explicitly excluded from the sum).
        """
        for ded in self:
            if ded.state not in ('active', 'completed'):
                continue
            relevant = ded.line_ids.filtered(
                lambda l: l.state in ('pending', 'paid'))
            total = sum(relevant.mapped('amount'))
            # Use the deduction's currency for float comparison so
            # sub-cent rounding noise does not trigger a false
            # positive.
            if ded.currency_id.compare_amounts(total, ded.amount) != 0:
                diff = ded.amount - total
                raise ValidationError(_(
                    "The sum of the installments on loan %(name)s no "
                    "longer matches the total loan amount.\n\n"
                    "  • Total loan amount : %(amt).2f %(cur)s\n"
                    "  • Sum of installments: %(tot).2f %(cur)s\n"
                    "  • Difference        : %(diff).2f %(cur)s\n\n"
                    "Adjust one or more of the other pending "
                    "installments so the totals match, then save again.",
                    name=ded.name or '',
                    amt=ded.amount,
                    tot=total,
                    diff=diff,
                    cur=ded.currency_id.name or '',
                ))

    # ==================================================================
    # Decision Support helpers
    # ==================================================================

    def _compute_x_can_submit(self):
        """Submit button visible only to the record creator or to
        officers/managers (who can submit on behalf of an employee who
        has no user account)."""
        officer_grp = self.env.ref(
            'KSW_deduction.group_deduction_officer',
            raise_if_not_found=False)
        is_officer = bool(officer_grp and self.env.user in officer_grp.user_ids)
        uid = self.env.uid
        for rec in self:
            rec.x_can_submit = (
                is_officer
                or (rec.create_uid and rec.create_uid.id == uid)
                or not rec.id  # new record being composed
            )

    @api.depends('employee_id', 'employee_id.parent_id.user_id')
    def _compute_x_can_dm_approve(self):
        """True when the current user is entitled to perform the DM
        approval step on this record.

        Authority sources (any one is sufficient):
          1. The current user IS the employee's direct manager
             (employee.parent_id.user_id == env.user).
          2. The current user holds Deduction Officer or Manager role
             (covers admin / HR ops scenarios where the manager is
             unavailable).
          3. Superuser / odoo-bot.
        """
        uid = self.env.uid
        is_officer = self.env.user.has_group(
            'KSW_deduction.group_deduction_officer')
        is_super = self.env.su or uid == self.env.ref('base.user_root').id
        for rec in self:
            mgr_user = rec.employee_id.parent_id.user_id
            rec.x_can_dm_approve = (
                is_super
                or is_officer
                or (mgr_user and mgr_user.id == uid)
            )

    @api.depends_context('uid')
    @api.depends('is_loan', 'state', 'employee_id.user_id')
    def _compute_x_can_cancel(self):
        """Who may click the Cancel button.

        - Loan: only the requesting employee (employee_id.user_id ==
          env.user) or superuser. Approvers must use "Refuse" instead.
        - Non-loan: Deduction Officer/Manager (via
          group_deduction_officer implication) or superuser.
        In both cases, completed/already-cancelled records hide the
        button.
        """
        uid = self.env.uid
        is_officer = self.env.user.has_group(
            'KSW_deduction.group_deduction_officer')
        is_super = self.env.su or uid == self.env.ref('base.user_root').id
        for rec in self:
            if rec.state in ('cancelled', 'completed'):
                rec.x_can_cancel = False
                continue
            if rec.is_loan:
                rec.x_can_cancel = (
                    is_super
                    or (rec.employee_id.user_id
                        and rec.employee_id.user_id.id == uid)
                )
            else:
                rec.x_can_cancel = is_super or is_officer

    def action_create_new_penalty(self):
        """Open the deductions form pre-filled for a new penalty record
        on the same employee. Used by HR from the Decision Support tab
        to log a pending penalty before ticking the confirmation."""
        self.ensure_one()
        penalty_type = self.env.ref(
            'KSW_deduction.type_internal_penalty',
            raise_if_not_found=False)
        ctx = {
            'default_employee_id': self.employee_id.id,
        }
        if penalty_type:
            ctx['default_type_id'] = penalty_type.id
        return {
            'name': _('New Penalty for %s') % (self.employee_id.name or ''),
            'type': 'ir.actions.act_window',
            'res_model': 'ksw.deduction',
            'view_mode': 'form',
            'target': 'current',
            'context': ctx,
        }


    # ==================================================================
    # Installment generation
    # ==================================================================

    def _activate_and_generate_lines(self):
        self.ensure_one()
        if self.line_ids:
            # Already generated (shouldn't happen normally)
            self.line_ids.unlink()
        self._generate_installment_lines()
        self.write({'state': 'active'})

    def _generate_installment_lines(self):
        """Create one ksw.deduction.line per month starting from start_month.

        The base per-line amount is `amount / installments` rounded to 2
        decimals; the last line absorbs any residue so the sum equals the
        total exactly.
        """
        self.ensure_one()
        if not self.start_month or self.installments < 1:
            return
        per = round(self.amount / self.installments, 2)
        lines = []
        start = self.start_month.replace(day=1)
        running_total = 0.0
        for i in range(self.installments):
            period = start + relativedelta(months=i)
            if i < self.installments - 1:
                line_amount = per
                running_total += per
            else:
                # Last line: absorb rounding residue so the sum is exact
                line_amount = round(self.amount - running_total, 2)
            lines.append((0, 0, {
                'sequence': i + 1,
                'year': period.year,
                'month': period.month,
                'amount': line_amount,
            }))
        # `_ksw_auto_generating` tells `ksw.deduction.line.create()`
        # that these are schedule lines, not manual entries — so it
        # skips the manual-entry guards (privilege check, forced
        # is_manual/state=paid stamping, audit post).
        self.with_context(_ksw_auto_generating=True).write(
            {'line_ids': lines})

    # ==================================================================
    # Mark lines paid / unpaid (called by hr.payslip state transitions)
    # ==================================================================

    def _mark_lines_paid(self, line_ids, payslip):
        """Mark the given line ids as paid and attach them to the payslip."""
        if not line_ids:
            return
        self.env['ksw.deduction.line'].browse(line_ids).write({
            'state': 'paid',
            'payslip_id': payslip.id,
        })
        # Auto-complete a deduction when all lines are paid
        for ded in self.env['ksw.deduction.line'].browse(
                line_ids).mapped('deduction_id'):
            if all(l.state == 'paid' for l in ded.line_ids):
                ded.write({'state': 'completed'})
                ded.message_post(
                    body=Markup('<strong>🏁 Completed</strong> — all '
                                'installments paid.'),
                    subtype_xmlid='mail.mt_note',
                )

    def _unmark_lines_paid(self, payslip):
        """Revert lines attached to the given payslip back to pending."""
        lines = self.env['ksw.deduction.line'].search([
            ('payslip_id', '=', payslip.id),
            ('state', '=', 'paid'),
        ])
        if not lines:
            return
        deductions = lines.mapped('deduction_id')
        lines.write({'state': 'pending', 'payslip_id': False})
        # Re-open any deductions that were auto-completed
        deductions.filtered(lambda d: d.state == 'completed').write(
            {'state': 'active'})


