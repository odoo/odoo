"""KSW Commission Sheet — monthly per-employee allowance/commission record.

State machine:

    draft         supervisor edits all fields, lines auto-pulled loans
    confirmed     supervisor done; only the "Commission Accountant" can
                  edit the locked loans amount
    done          accountant finalised; sheet is read-only; pending
                  ksw.deduction.line records flagged
                  ``x_awaiting_commission=True`` for the same
                  (employee, year, month) have been flipped to
                  ``state='paid'`` and stamped with
                  ``x_paid_via_commission_sheet_id = self.id`` (FIFO
                  across loans, with last-line splitting if the locked
                  amount only partially covers them).

Reset-to-draft (Officer or Accountant) unwinds the offset by flipping
the consumed installment lines back to ``state='pending'`` (and
re-merging any split sibling), using the JSON snapshot stored on the
sheet at done time.
"""
import json
from datetime import date

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


SHEET_STATES = [
    ('draft', 'Draft'),
    ('confirmed', 'Awaiting Accountant'),
    ('done', 'Done'),
]


class KswCommissionSheet(models.Model):
    _name = 'ksw.commission.sheet'
    _description = 'KSW Commission & Allowance Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period desc, employee_id'

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------
    name = fields.Char(
        required=True, default='New', copy=False, readonly=True,
        tracking=True,
    )
    employee_id = fields.Many2one(
        'hr.employee', required=True, tracking=True,
        ondelete='restrict',
        domain="[('x_is_attendance_sheet', '=', True)]",
    )
    period = fields.Date(
        required=True, tracking=True,
        default=lambda s: fields.Date.context_today(s).replace(day=1),
        help='First day of the month covered by this sheet.',
    )
    note = fields.Text()

    # Related read-only mirrors that reproduce the paper form header.
    # All declared with sudo via ``compute`` in case the supervisor
    # lacks ``hr.group_hr_user`` (the underlying fields are
    # group-restricted on hr.employee).
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True, readonly=True,
    )
    job_id = fields.Many2one(
        related='employee_id.job_id', store=True, readonly=True,
    )
    identification_id = fields.Char(
        related='employee_id.identification_id',
        readonly=True, groups='hr.group_hr_user',
    )
    vehicle_number = fields.Char(
        compute='_compute_employee_extras', readonly=True,
    )
    wage = fields.Monetary(
        compute='_compute_employee_extras', readonly=True,
    )
    site_id = fields.Many2one(
        'ksw.site', compute='_compute_employee_extras', readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
        required=True,
    )

    # ------------------------------------------------------------------
    # Dynamic lines + computed totals
    # ------------------------------------------------------------------
    line_ids = fields.One2many(
        'ksw.commission.sheet.line', 'sheet_id', copy=True,
    )
    lines_subtotal = fields.Monetary(
        compute='_compute_totals', store=True,
        help='Sum of all entered line amounts (allowances, '
             'commissions, holiday bonuses, etc.).',
    )

    # Driver's commission — read-only. Phase A leaves this at 0; Phase B
    # auto-resolves the matching ksw.driver.commission.line.
    driver_commission_amount = fields.Monetary(
        compute='_compute_driver_commission', store=True, readonly=True,
        help='Auto-resolved from the matching driver-commission line '
             '(per site, per period). Phase A: always 0.',
    )

    # Technician location (meals) allowance — auto-resolved from the
    # confirmed ksw.location.allowance.line for this employee/period.
    location_allowance_amount = fields.Monetary(
        compute='_compute_location_allowance', store=True, readonly=True,
        help='Auto-resolved from the matching technician '
             'location-allowance line (per period). Updated when the '
             'location-allowance sheet is confirmed.',
    )

    # Sales / Collection / Combined commissions — auto-resolved from
    # the confirmed ksw.sales.commission.line for this employee/period.
    sales_commission_amount = fields.Monetary(
        compute='_compute_sales_commission', store=True, readonly=True,
        help='Auto-resolved from the confirmed sales-commission '
             'line for this employee/period.',
    )
    collection_commission_amount = fields.Monetary(
        compute='_compute_sales_commission', store=True, readonly=True,
        help='Auto-resolved from the confirmed sales-commission '
             'line for this employee/period.',
    )
    combined_commission_amount = fields.Monetary(
        compute='_compute_sales_commission', store=True, readonly=True,
        help='Auto-resolved combined sales+collection commission for '
             'hybrid (Salesman & Collector) employees.',
    )

    # Loans — auto-pulled in draft, frozen on confirm, applied on done.
    loans_amount = fields.Monetary(
        compute='_compute_loans_amount',
        help='Sum of pending KSW deduction installments for this '
             'employee/period that the deduction accountant has '
             'flagged "Awaiting Commission" — i.e. slices of '
             "monthly installments routed away from payroll so the "
             'commission sheet can settle them. The supervisor sees '
             'this as read-only; the commission accountant can adjust '
             'it after the supervisor confirms.',
    )
    x_loans_amount_locked = fields.Monetary(
        string='Loans (locked)', readonly=False, copy=False,
        tracking=True,
        help='Editable only by the Commission Accountant while the '
             'sheet is in state "confirmed". Frozen from '
             '``loans_amount`` on supervisor-confirm.',
    )
    # Snapshot used by reset_to_draft to undo the deduction-line
    # mutations applied in action_done. Stored as JSON:
    # ``[{"line_id": <int>, "delta": <float>}, ...]`` plus
    # ``"manual_line_id"``.
    x_unwind_data = fields.Text(
        readonly=True, copy=False,
        help='Internal JSON used to unwind the KSW_deduction mutations '
             'applied at done time. Touched only by the model.',
    )

    total = fields.Monetary(
        compute='_compute_totals', store=True,
        help='Lines + driver commission. Bank-transfer total uses '
             '``total_payable`` instead (which subtracts loans).',
    )
    total_payable = fields.Monetary(
        compute='_compute_totals', store=True,
        help='What the bank should actually transfer = total minus the '
             'loan deductible (locked amount when state is '
             'confirmed/done, otherwise the auto-pulled shortfall).',
    )

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    state = fields.Selection(
        SHEET_STATES, default='draft', required=True,
        copy=False, tracking=True,
    )
    # Stored boolean for view ``readonly`` expressions (AGENTS.md gotcha:
    # never use a non-stored compute inreadonly attributes).
    is_locked = fields.Boolean(
        readonly=True, copy=False,
        help='True when state is "done". Drives readonly in the form '
             'view via a stored Boolean (Odoo 19 does not reliably '
             'evaluate non-stored computes in readonly expressions).',
    )

    confirmed_by = fields.Many2one(
        'res.users', readonly=True, copy=False,
        help='Supervisor who confirmed the sheet (state draft → confirmed).',
    )
    confirmed_date = fields.Datetime(readonly=True, copy=False)
    done_by = fields.Many2one(
        'res.users', readonly=True, copy=False,
        help='Accountant who finalised the sheet (state confirmed → done).',
    )
    done_date = fields.Datetime(readonly=True, copy=False)

    # SQL constraints
    _unique_employee_period = models.Constraint(
        'UNIQUE(employee_id, period)',
        'Only one commission sheet per employee per month.',
    )

    # ==================================================================
    # Computed fields
    # ==================================================================
    @api.depends('employee_id')
    def _compute_employee_extras(self):
        for rec in self:
            emp = rec.employee_id.sudo() if rec.employee_id else False
            # ``vehicle_number`` is a paper-form field that doesn't exist
            # in the standard hr.employee schema. Phase A leaves it
            # blank; a future iteration can add a custom field on
            # hr.employee or pull from a fleet integration.
            rec.vehicle_number = ''
            rec.wage = (emp.current_version_id.wage if emp else 0.0) or 0.0
            rec.site_id = emp.x_site_id if emp else False

    @api.depends('line_ids.amount', 'driver_commission_amount',
                 'location_allowance_amount',
                 'sales_commission_amount',
                 'collection_commission_amount',
                 'combined_commission_amount',
                 'loans_amount', 'x_loans_amount_locked', 'state')
    def _compute_totals(self):
        for rec in self:
            sub = sum(rec.line_ids.mapped('amount'))
            rec.lines_subtotal = sub
            rec.total = (
                sub
                + (rec.driver_commission_amount or 0.0)
                + (rec.location_allowance_amount or 0.0)
                + (rec.sales_commission_amount or 0.0)
                + (rec.collection_commission_amount or 0.0)
                + (rec.combined_commission_amount or 0.0)
            )
            # The "active" loans figure depends on state:
            #   - draft: live shortfall
            #   - confirmed/done: locked figure
            loans = (
                rec.x_loans_amount_locked
                if rec.state in ('confirmed', 'done')
                else rec.loans_amount
            )
            rec.total_payable = rec.total - (loans or 0.0)

    @api.depends('employee_id', 'period', 'state')
    def _compute_loans_amount(self):
        Ded = self.env['ksw.deduction']
        for rec in self:
            if rec.state in ('confirmed', 'done'):
                # Frozen — show the locked figure as the "current"
                # loans value so the form/list stays consistent.
                rec.loans_amount = rec.x_loans_amount_locked
                continue
            if not rec.employee_id or not rec.period:
                rec.loans_amount = 0.0
                continue
            total, _lines = Ded._get_pending_commission_lines_for_period(
                rec.employee_id, rec.period)
            rec.loans_amount = total

    @api.depends('employee_id', 'period')
    def _compute_driver_commission(self):
        """Pull the matching confirmed driver-commission line for this employee/period."""
        Line = self.env['ksw.driver.commission.line'].sudo()
        for rec in self:
            if not rec.employee_id or not rec.period:
                rec.driver_commission_amount = 0.0
                continue
            line = Line.search([
                ('employee_id', '=', rec.employee_id.id),
                ('sheet_id.period', '=', rec.period),
                ('sheet_id.state', '=', 'confirmed'),
            ], limit=1)
            rec.driver_commission_amount = line.total_commission if line else 0.0

    @api.depends('employee_id', 'period')
    def _compute_location_allowance(self):
        """Pull the matching confirmed location-allowance line for this
        employee/period.
        """
        Line = self.env['ksw.location.allowance.line'].sudo()
        for rec in self:
            if not rec.employee_id or not rec.period:
                rec.location_allowance_amount = 0.0
                continue
            line = Line.search([
                ('employee_id', '=', rec.employee_id.id),
                ('sheet_id.period', '=', rec.period),
                ('sheet_id.state', '=', 'confirmed'),
            ], limit=1)
            rec.location_allowance_amount = (
                line.total_allowance if line else 0.0
            )

    @api.depends('employee_id', 'period')
    def _compute_sales_commission(self):
        """Pull the matching confirmed sales/collection commission
        line for this employee/period.
        """
        Line = self.env['ksw.sales.commission.line'].sudo()
        for rec in self:
            if not rec.employee_id or not rec.period:
                rec.sales_commission_amount = 0.0
                rec.collection_commission_amount = 0.0
                rec.combined_commission_amount = 0.0
                continue
            lines = Line.search([
                ('employee_id', '=', rec.employee_id.id),
                ('sheet_id.period', '=', rec.period),
                ('sheet_id.state', '=', 'confirmed'),
            ])
            rec.sales_commission_amount = sum(
                lines.mapped('sales_commission_amount'))
            rec.collection_commission_amount = sum(
                lines.mapped('collection_commission_amount'))
            rec.combined_commission_amount = sum(
                lines.mapped('combined_commission_amount'))

    # ==================================================================
    # CRUD
    # ==================================================================
    @api.model_create_multi
    def create(self, vals_list):
        Seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = (
                    Seq.next_by_code('ksw.commission.sheet') or 'New')
            # Normalise period to first-of-month.
            if vals.get('period'):
                d = fields.Date.to_date(vals['period'])
                vals['period'] = d.replace(day=1)
        sheets = super().create(vals_list)
        # Auto-populate lines from the assigned commission template,
        # but only for sheets created without pre-existing lines (i.e.
        # the cron / toggle path). Sheets created manually with lines
        # already set (e.g. copied from another sheet) are left as-is.
        Template = self.env['ksw.commission.template']
        for sheet in sheets:
            if sheet.line_ids:
                # Lines were already provided (copy or manual creation).
                continue
            if not sheet.employee_id:
                continue
            tmpl = Template._get_template_for_employee(sheet.employee_id)
            if tmpl:
                tmpl._apply_to_sheet(sheet)
        return sheets

    def write(self, vals):
        # ------------------------------------------------------------------
        # State-gated edit guard. Once the sheet is past 'draft' the
        # supervisor can no longer edit any field; only the locked-loans
        # field is editable, and only by users in the Commission
        # Accountant group while state is 'confirmed'.
        # ------------------------------------------------------------------
        if not self.env.su:
            user = self.env.user
            is_accountant = user.has_group(
                'KSW_commissions.group_commission_accountant')
            for rec in self:
                if rec.state == 'done':
                    raise UserError(_(
                        "Sheet '%(n)s' is finalised (Done). Reset it to "
                        "draft to make changes.", n=rec.name,
                    ))
                if rec.state == 'confirmed':
                    # Only x_loans_amount_locked may change, and only
                    # by an accountant.
                    edited = set(vals)
                    allowed = {
                        'x_loans_amount_locked', 'message_follower_ids',
                        'message_ids', 'activity_ids',
                        'message_main_attachment_id',
                    }
                    illegal = edited - allowed
                    if illegal and not is_accountant:
                        raise UserError(_(
                            "Sheet '%(n)s' has been confirmed. Only the "
                            "Commission Accountant can adjust it now "
                            "(via the locked loans field).", n=rec.name,
                        ))
                    if illegal and is_accountant and illegal != {
                            'x_loans_amount_locked'}:
                        raise UserError(_(
                            "Confirmed sheets are read-only except for "
                            "the locked loans amount. Reset to draft if "
                            "broader edits are needed."
                        ))
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state == 'done' and not self.env.su:
                raise UserError(_(
                    "Sheet '%(n)s' is finalised (Done). Reset it to "
                    "draft before deleting.", n=rec.name,
                ))
        return super().unlink()

    # ==================================================================
    # State transitions
    # ==================================================================
    def action_confirm(self):
        """Supervisor confirm: draft → confirmed.

        Freezes the auto-pulled ``loans_amount`` into the locked field
        and posts a chatter trail.
        """
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "Only draft sheets can be confirmed. '%(n)s' is "
                    "%(s)s.", n=rec.name,
                    s=dict(SHEET_STATES).get(rec.state, rec.state),
                ))
            # Re-pull the live awaiting-commission total so we freeze
            # the most up-to-date number.
            total, _lines = self.env['ksw.deduction']._get_pending_commission_lines_for_period(
                rec.employee_id, rec.period)
            rec.write({
                'state': 'confirmed',
                'x_loans_amount_locked': total,
                'confirmed_by': self.env.uid,
                'confirmed_date': fields.Datetime.now(),
            })
            rec.message_post(
                body=Markup(
                    '<strong>📋 Confirmed by Supervisor</strong><br/>'
                    '<b>Loans (frozen):</b> %.2f<br/>'
                    '<b>Lines subtotal:</b> %.2f<br/>'
                    '<b>Driver commission:</b> %.2f<br/>'
                    '<b>Bank transfer (preview):</b> %.2f'
                ) % (
                    total, rec.lines_subtotal,
                    rec.driver_commission_amount,
                    rec.total - total,
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_done(self):
        """Accountant final: confirmed → done.

        Side-effects on KSW_deduction (atomic):
          1. For each FIFO shortfall line up to the locked loans
             amount, raise its ``amount`` by ``portion`` (which closes
             that part of the shortfall — the line is no longer below
             its ``x_original_amount``).
          2. Create a manual paid ``ksw.deduction.line`` of the locked
             amount, tagged ``x_paid_via_commission_sheet_id = self.id``,
             on the *first* deduction touched (FIFO).
          3. Snapshot the (line_id, delta) tuples + manual line id in
             ``x_unwind_data`` so reset can restore exactly.

        Permission: requires ``group_commission_accountant`` (or sudo).
        """
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_(
                    "Only confirmed sheets can be finalised."))
            if not self.env.su and not self.env.user.has_group(
                    'KSW_commissions.group_commission_accountant'):
                raise UserError(_(
                    "Only the Commission Accountant can finalise sheets."))
            rec.sudo()._apply_loan_offset()
            rec.sudo().write({
                'state': 'done',
                'is_locked': True,
                'done_by': self.env.uid,
                'done_date': fields.Datetime.now(),
            })
            rec.message_post(
                body=Markup(
                    '<strong>✅ Finalised by Accountant</strong><br/>'
                    '<b>Loans deducted:</b> %.2f<br/>'
                    '<b>Bank transfer:</b> %.2f'
                ) % (rec.x_loans_amount_locked, rec.total_payable),
                subtype_xmlid='mail.mt_note',
            )

    def action_reset_to_draft(self):
        """Reset to draft. Allowed from confirmed or done.

        From done: unwinds the KSW_deduction mutations using
        ``x_unwind_data``.
        From confirmed: simply clears the locked loans + state.
        """
        for rec in self:
            if rec.state == 'draft':
                continue
            is_accountant = self.env.user.has_group(
                'KSW_commissions.group_commission_accountant')
            is_officer = self.env.user.has_group(
                'KSW_commissions.group_commission_officer')
            if not (self.env.su or is_accountant or is_officer):
                raise UserError(_(
                    "Only a Commission Accountant or Officer can reset "
                    "this sheet."))
            if rec.state == 'done':
                rec._unwind_loan_offset()
            rec.sudo().write({
                'state': 'draft',
                'is_locked': False,
                'x_loans_amount_locked': 0.0,
                'x_unwind_data': False,
                'confirmed_by': False, 'confirmed_date': False,
                'done_by': False, 'done_date': False,
            })
            rec.message_post(
                body=Markup('<strong>↩ Reset to Draft</strong><br/>'
                            '<b>By:</b> %s') % self.env.user.name,
                subtype_xmlid='mail.mt_note',
            )

    # ==================================================================
    # KSW_deduction integration helpers
    # ==================================================================
    def _apply_loan_offset(self):
        """Apply the locked loans amount against pending awaiting-
        commission KSW_deduction lines for (employee, year, month).

        For each FIFO pending line flagged ``x_awaiting_commission``:
          - If ``line.amount <= remaining``, the whole line is
            consumed: flip ``state='paid'`` and stamp
            ``x_paid_via_commission_sheet_id = self.id``.
          - Otherwise the line is split: reduce the original line's
            amount by ``remaining`` and create a new sibling
            (same year/month) for ``remaining``, immediately marked
            ``state='paid'`` + linked to the sheet.

        Snapshots ``paid_ids`` and ``splits`` (list of
        ``{orig, new, taken}``) in ``self.x_unwind_data`` so the
        reset path can undo it.
        """
        self.ensure_one()
        amount = self.x_loans_amount_locked or 0.0
        if amount <= 0.0:
            self.x_unwind_data = False
            return
        Ded = self.env['ksw.deduction'].sudo()
        Line = self.env['ksw.deduction.line'].sudo()
        total, lines = Ded._get_pending_commission_lines_for_period(
            self.employee_id, self.period)
        if amount > total + 1e-6:
            raise UserError(_(
                "The locked loans amount (%(loc).2f) exceeds the "
                "current 'Awaiting Commission' installments "
                "(%(now).2f) for this employee in the sheet's month. "
                "Reset the sheet to draft and reconfirm so it picks "
                "up the latest figure.",
                loc=amount, now=total,
            ))

        paid_ids = []   # whole lines flipped pending → paid
        splits = []     # [{orig, new, taken}]
        remaining = amount
        deductions_touched = self.env['ksw.deduction']

        for line in lines:
            if remaining <= 1e-6:
                break
            line_amt = line.amount or 0.0
            if line_amt <= remaining + 1e-6:
                line.with_context(
                    _skip_installment_total_check=True,
                ).sudo().write({
                    'state': 'paid',
                    'x_paid_via_commission_sheet_id': self.id,
                    # Clear the awaiting flag — the slice has now
                    # actually been settled by the commission.
                    'x_awaiting_commission': False,
                })
                paid_ids.append(line.id)
                deductions_touched |= line.deduction_id
                remaining -= line_amt
            else:
                # Partial — split into two siblings and mark the new
                # one paid via the commission sheet. We are running
                # under sudo (action_done escalates) so the amount
                # write bypasses the group_installment_edit gate.
                take = remaining
                new_line = Line.with_context(
                    _ksw_auto_generating=True,
                    _skip_installment_total_check=True,
                ).create({
                    'deduction_id': line.deduction_id.id,
                    'sequence': line.sequence,
                    'year': line.year,
                    'month': line.month,
                    'amount': take,
                    'state': 'paid',
                    'is_manual': False,
                    'x_awaiting_commission': False,
                    'x_paid_via_commission_sheet_id': self.id,
                    'x_original_amount': take,
                })
                line.with_context(
                    _skip_installment_total_check=True,
                ).sudo().write({'amount': line_amt - take})
                splits.append({
                    'orig': line.id,
                    'new': new_line.id,
                    'taken': take,
                })
                deductions_touched |= line.deduction_id
                remaining = 0.0

        for ded in deductions_touched:
            ded._validate_installments_total()

        self.x_unwind_data = json.dumps({
            'paid_ids': paid_ids,
            'splits': splits,
        })

    def _unwind_loan_offset(self):
        """Reverse the operations recorded in ``x_unwind_data``."""
        self.ensure_one()
        if not self.x_unwind_data:
            return
        try:
            payload = json.loads(self.x_unwind_data)
        except Exception:
            raise UserError(_(
                "Cannot reset: the unwind snapshot for sheet '%(n)s' "
                "is corrupted. Manual cleanup required.", n=self.name,
            ))
        Line = self.env['ksw.deduction.line'].sudo()
        paid_ids = payload.get('paid_ids') or []
        splits = payload.get('splits') or []
        deductions_touched = self.env['ksw.deduction']

        # 1) Whole lines: flip back to pending and re-flag awaiting.
        for line in Line.browse(paid_ids).exists():
            line.with_context(
                _skip_installment_total_check=True,
            ).sudo().write({
                'state': 'pending',
                'x_paid_via_commission_sheet_id': False,
                'x_awaiting_commission': True,
            })
            deductions_touched |= line.deduction_id

        # 2) Splits: restore original amount and unlink the paid sibling.
        for s in splits:
            orig = Line.browse(s.get('orig')).exists()
            new = Line.browse(s.get('new')).exists()
            taken = s.get('taken') or 0.0
            if orig:
                orig.with_context(
                    _skip_installment_total_check=True,
                ).sudo().write({
                    'amount': (orig.amount or 0.0) + taken,
                })
                deductions_touched |= orig.deduction_id
            if new:
                new.with_context(
                    _skip_installment_total_check=True,
                ).sudo().unlink()

        for ded in deductions_touched:
            ded._validate_installments_total()

    # ==================================================================
    # Template integration
    # ==================================================================
    def action_apply_template(self):
        """Apply the employee's assigned template to this draft sheet.

        Idempotent — lines already on the sheet (same category+holiday)
        are never duplicated. Raises if the sheet is not in draft.
        """
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "Templates can only be applied to draft sheets. "
                    "'%(n)s' is %(s)s.", n=rec.name,
                    s=dict(SHEET_STATES).get(rec.state, rec.state),
                ))
            if not rec.employee_id:
                continue
            tmpl = self.env['ksw.commission.template']._get_template_for_employee(
                rec.employee_id)
            if not tmpl:
                raise UserError(_(
                    "No active commission template is assigned to %(emp)s.",
                    emp=rec.employee_id.name,
                ))
            tmpl._apply_to_sheet(rec)

    # ==================================================================
    # Auto-creation helpers (cron + on-toggle)
    # ==================================================================
    @api.model
    def _ensure_current_period_sheets(self, employees=None):
        """Create a draft sheet for the current month for each given
        employee that doesn't already have one.

        When ``employees`` is omitted the scope is ALL employees that
        are assigned to at least one active commission template.
        This is intentionally narrower than "all x_is_attendance_sheet
        employees" — only template-assigned employees have meaningful
        lines to pre-fill, so creating blank sheets for everyone else
        would create unnecessary clutter.
        """
        if employees is None:
            # Collect employees from every active template.
            templates = self.env['ksw.commission.template'].sudo().search([
                ('active', '=', True),
            ])
            employees = templates.mapped('employee_ids')
        if not employees:
            return self.browse()
        period = fields.Date.context_today(self).replace(day=1)
        existing = self.sudo().search([
            ('employee_id', 'in', employees.ids),
            ('period', '=', period),
        ])
        existing_emp_ids = set(existing.mapped('employee_id').ids)
        to_create = [
            {'employee_id': e.id, 'period': period}
            for e in employees if e.id not in existing_emp_ids
        ]
        if not to_create:
            return self.browse()
        return self.sudo().create(to_create)

    @api.model
    def _cron_ensure_monthly_sheets(self):
        """Cron entry-point — runs at month rollover."""
        self._ensure_current_period_sheets()

    # ==================================================================
    # Report helpers — called from QWeb; no lambdas allowed in QWeb
    # safe_eval so all aggregation lives here instead.
    # ==================================================================
    def _report_get_period_labels(self):
        """Return a list of 'Month YYYY' strings for every distinct period
        in this recordset, most-recent first."""
        periods = sorted(
            {o.period for o in self if o.period}, reverse=True)
        return [p.strftime('%B %Y') for p in periods]

    def _report_get_dept_breakdown(self):
        """Return a list of dicts for the department sub-total table.

        Each dict has keys: name, count, lines, driver, gross, bank.
        Named departments first (alpha), then 'No Department' bucket.
        """
        dept_map = {}   # dept.id (or 0) → accumulator dict
        for o in self:
            key = o.department_id.id if o.department_id else 0
            name = o.department_id.name if o.department_id else '— No Department —'
            if key not in dept_map:
                dept_map[key] = {
                    'name': name, 'count': 0,
                    'lines': 0.0, 'driver': 0.0,
                    'gross': 0.0, 'bank': 0.0,
                }
            dept_map[key]['count'] += 1
            dept_map[key]['lines'] += o.lines_subtotal or 0.0
            dept_map[key]['driver'] += o.driver_commission_amount or 0.0
            dept_map[key]['gross'] += o.total or 0.0
            dept_map[key]['bank'] += o.total_payable or 0.0
        named = sorted(
            [v for k, v in dept_map.items() if k != 0],
            key=lambda d: d['name'],
        )
        no_dept = [dept_map[0]] if 0 in dept_map else []
        return named + no_dept

    # ------------------------------------------------------------------
    # "Commissions & Allowances Summary" report helpers
    # ------------------------------------------------------------------
    def _report_get_summary_columns(self):
        """Return the distinct ``ksw.commission.category`` records used by
        any line on this recordset, ordered by (sequence, id).

        Used to build dynamic per-category columns on the
        Commissions & Allowances Summary report so each category /
        commission type appears once across the table.
        """
        cats = self.mapped('line_ids.category_id')
        return cats.sorted(key=lambda c: (c.sequence or 0, c.id))

    def _report_get_summary_cells(self, columns):
        """For *one* sheet, return a list of amounts aligned to ``columns``.

        Multiple lines under the same category (e.g. multiple holiday
        bonus entries) are summed into a single cell.
        """
        self.ensure_one()
        by_cat = {}
        for ln in self.line_ids:
            cid = ln.category_id.id
            by_cat[cid] = by_cat.get(cid, 0.0) + (ln.amount or 0.0)
        return [by_cat.get(c.id, 0.0) for c in columns]

    def _report_get_summary_totals(self, columns):
        """Return per-category column totals across the whole recordset."""
        totals = {c.id: 0.0 for c in columns}
        for o in self:
            for ln in o.line_ids:
                cid = ln.category_id.id
                if cid in totals:
                    totals[cid] += ln.amount or 0.0
        return [totals[c.id] for c in columns]








