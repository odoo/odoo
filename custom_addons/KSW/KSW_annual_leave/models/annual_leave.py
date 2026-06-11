from odoo import api, fields, models
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class KswAnnualLeave(models.Model):
    _name = 'ksw.annual.leave'
    _description = 'Annual Leave Dashboard'
    _order = 'employee_id'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee',
        required=True, ondelete='cascade',
    )
    department_id = fields.Many2one(
        'hr.department', string='Department',
        related='employee_id.department_id', store=True,
    )
    joining_date = fields.Date(
        string='Joining Date', compute='_compute_leave_data', store=True,
    )
    years_of_service = fields.Float(
        string='Years of Service', compute='_compute_leave_data',
        store=True, digits=(5, 2),
    )
    daily_rate = fields.Float(
        string='Daily Rate', compute='_compute_leave_data',
        store=True, digits=(10, 6),
        help='21/365 for the first 5 years, 30/365 after that.',
    )
    total_accrued_days = fields.Float(
        string='Total Accrued', compute='_compute_leave_data',
        store=True, digits=(10, 4),
        help='Total annual leave days accrued since effective start date '
             '(opening reset date if set, otherwise joining date), '
             'adjusted for leaves taken. Opening extra days are included.',
    )
    leaves_taken = fields.Float(
        string='Leaves Taken',
        compute='_compute_leaves_taken',
        digits=(10, 4),
        help='Total approved annual leave days taken (from linked allocation). '
             'When an opening reset date is set, only leaves after that date '
             'are counted (the allocation date_from is set accordingly).',
    )

    @api.depends('allocation_id', 'allocation_id.leaves_taken')
    def _compute_leaves_taken(self):
        for rec in self:
            try:
                # Use exists() to avoid MissingError on deleted allocation
                if rec.allocation_id and rec.allocation_id.exists():
                    rec.leaves_taken = rec.allocation_id.leaves_taken
                else:
                    rec.leaves_taken = 0.0
            except Exception:
                rec.leaves_taken = 0.0
    remaining_balance = fields.Float(
        string='Remaining Balance',
        compute='_compute_remaining_balance',
        digits=(10, 4),
    )
    allocation_id = fields.Many2one(
        'hr.leave.allocation', string='Linked Allocation',
        readonly=True, ondelete='set null',
        help='The auto-managed hr.leave.allocation record.',
    )

    # ------------------------------------------------------------------
    # Opening Balance (Go-Live Deployment)
    # ------------------------------------------------------------------
    x_opening_reset_date = fields.Date(
        string='Opening Reset Date',
        help='Go-live baseline date. Accrual starts from this date '
             '(using the correct service-tier rate based on total employment '
             'duration). Only annual leaves validated on or after this date '
             'are counted against the balance. Leave this blank to track the '
             'full history from the joining date.',
    )
    x_opening_extra_days = fields.Float(
        string='Opening Extra Days',
        digits=(10, 4),
        default=0.0,
        help='One-time manual balance adjustment added at the opening reset '
             'date (e.g. carry-over days from a manual prior system, or a '
             'negative correction). Positive = extra days granted.',
    )
    x_opening_is_locked = fields.Boolean(
        string='Opening Data Locked',
        default=False,
        help='Lock the Opening Reset Date and Opening Extra Days fields after '
             'go-live to prevent accidental changes. A manager can unlock if '
             'corrections are needed.',
    )
    x_effective_start_date = fields.Date(
        string='Effective Start Date',
        compute='_compute_effective_start_date',
        store=True,
        compute_sudo=True,
        help='The date from which accrual and balance counting begins. '
             'This is the Opening Reset Date if set, otherwise the Joining Date.',
    )

    _unique_employee = models.Constraint(
        'UNIQUE(employee_id)',
        'Only one annual leave record per employee is allowed.',
    )

    # ------------------------------------------------------------------
    # Write guard — protect locked opening balance fields
    # ------------------------------------------------------------------
    def write(self, vals):
        opening_keys = {'x_opening_reset_date', 'x_opening_extra_days'}
        if opening_keys & vals.keys():
            for rec in self:
                if rec.x_opening_is_locked:
                    raise UserError(
                        'The opening balance for %s is locked. '
                        'Uncheck "Opening Data Locked" before making changes.'
                        % rec.employee_id.name
                    )
        return super().write(vals)

    def unlink(self):
        """Delete linked allocations when dashboard record is deleted."""
        allocations = self.mapped('allocation_id').sudo()
        result = super().unlink()
        if allocations:
            allocations.unlink()
        return result

    # ------------------------------------------------------------------
    # Effective start date (stored for reliability in views/reports)
    # ------------------------------------------------------------------
    @api.depends('joining_date', 'x_opening_reset_date')
    def _compute_effective_start_date(self):
        for rec in self:
            if rec.x_opening_reset_date and rec.joining_date:
                rec.x_effective_start_date = max(rec.x_opening_reset_date, rec.joining_date)
            else:
                rec.x_effective_start_date = rec.x_opening_reset_date or rec.joining_date

    @api.depends(
        'employee_id',
        'employee_id.version_ids.contract_date_start',
        'employee_id.version_ids.wage',
        'employee_id.version_ids.date_version',
        'employee_id.version_ids.active',
        'x_opening_reset_date',
        'x_opening_extra_days',
    )
    def _compute_leave_data(self):
        today = fields.Date.context_today(self)
        for rec in self:
            # --- defaults ---
            rec.joining_date = False
            rec.years_of_service = 0.0
            rec.daily_rate = 0.0
            rec.total_accrued_days = 0.0

            if not rec.employee_id:
                continue

            # --- Joining date from earliest contract start ---
            versions = rec.employee_id.sudo().version_ids.filtered(
                lambda v: v.contract_date_start
            )
            if not versions:
                continue

            joining = min(versions.mapped('contract_date_start'))
            rec.joining_date = joining

            # --- Effective start date (reset overrides joining) ---
            if rec.x_opening_reset_date:
                effective_start = max(rec.x_opening_reset_date, joining)
            else:
                effective_start = joining
            if effective_start > today:
                # Future reset date — no accrual yet
                continue

            # --- Years of service (full service, not just since reset) ---
            rdelta = relativedelta(today, joining)
            rec.years_of_service = round(
                rdelta.years + rdelta.months / 12.0 + rdelta.days / 365.25, 2
            )

            # --- Calendar days for tier boundary (always from joining) ---
            total_days = (today - joining).days        # joining → today
            reset_days = (effective_start - joining).days  # joining → effective_start
            if total_days <= 0:
                continue

            # --- Approved annual leave days taken (from linked allocation) ---
            # When x_opening_reset_date is set, the allocation's date_from is
            # also set to that date, so allocation.leaves_taken only counts
            # post-reset leaves automatically (Odoo allocation date_from filter).
            taken = rec.leaves_taken

            # --- Two-tier daily accrual (Saudi Labor Law Art. 109) ---
            # We compute tier-1 and tier-2 calendar days in the EFFECTIVE
            # period (effective_start → today), but tier boundaries are based
            # on TOTAL service from the joining date. This ensures an employee
            # already past 5 years at the reset date correctly accrues at
            # the 30/365 rate.
            #
            # tier1_effective = min(total_days, 1825) − min(reset_days, 1825)
            # tier2_effective = max(total_days − 1825, 0) − max(reset_days − 1825, 0)
            five_years_days = 5 * 365

            tier1_effective = (
                min(total_days, five_years_days)
                - min(reset_days, five_years_days)
            )
            tier1_effective = max(tier1_effective, 0)

            tier2_effective = (
                max(total_days - five_years_days, 0)
                - max(reset_days - five_years_days, 0)
            )
            tier2_effective = max(tier2_effective, 0)

            # Maximum accrued days each tier can produce in the effective period
            tier1_max = tier1_effective * (21.0 / 365.0)
            tier2_max = tier2_effective * (30.0 / 365.0)

            # Opening extra days (manual go-live adjustment)
            extra_days = rec.x_opening_extra_days or 0.0

            # --- FIFO deduction of leaves taken ---
            # Each calendar vacation day in tier 1 removes 21/365 accrual days;
            # once tier 1 is exhausted, each day in tier 2 removes 30/365.
            tier1_deduction = min(taken * (21.0 / 365.0), tier1_max)
            tier1_vac_days = min(taken, tier1_max / (21.0 / 365.0)) if tier1_max > 0 else 0
            leftover_days = max(taken - tier1_vac_days, 0)
            tier2_deduction = min(leftover_days * (30.0 / 365.0), tier2_max)

            total_accrued = (
                (tier1_max - tier1_deduction)
                + (tier2_max - tier2_deduction)
                + extra_days
            )

            rec.total_accrued_days = round(total_accrued, 4)

            # --- Current daily rate (based on total service from joining) ---
            rec.daily_rate = (
                30.0 / 365.0 if total_days > five_years_days else 21.0 / 365.0
            )

    # ------------------------------------------------------------------
    # Remaining balance (non-stored, always real-time)
    # ------------------------------------------------------------------
    @api.depends('total_accrued_days', 'leaves_taken')
    def _compute_remaining_balance(self):
        for rec in self:
            # Handle cases where allocation_id was deleted but leaves_taken related field
            # might return a default value (like 0.0) without the warning if accessed carefully,
            # but we explicitly check here to be sure.
            try:
                # Check exists() explicitly to prevent MissingError on related field access
                if rec.allocation_id and rec.allocation_id.exists():
                    taken = rec.leaves_taken
                else:
                    taken = 0.0
            except Exception:
                taken = 0.0
            rec.remaining_balance = round(rec.total_accrued_days - taken, 4)

    # ------------------------------------------------------------------
    # Refresh accrual — called whenever leaves_taken changes
    # ------------------------------------------------------------------
    def _refresh_accrual(self):
        """Force recompute of accrued days and sync the allocation.

        Call this whenever an annual leave is approved, refused, deleted,
        or otherwise changes the leaves_taken value so that
        effective_days (calendar_days - leaves_taken) stays accurate.
        """
        if not self:
            return
        # Clear ORM caches so allocation.leaves_taken is read fresh
        # (it may have just changed in the same transaction).
        self.env.invalidate_all()
        field = self._fields['joining_date']
        self.env.add_to_compute(field, self)
        self.flush_recordset()
        self._sync_allocations()

    @api.model
    def _refresh_accrual_for_employees(self, employee_ids):
        """Convenience: refresh accrual for specific employees by id."""
        if not employee_ids:
            return
        records = self.sudo().search([
            ('employee_id', 'in', list(employee_ids)),
        ])
        records._refresh_accrual()

    # ------------------------------------------------------------------
    # Allocation sync
    # ------------------------------------------------------------------
    def _sync_allocations(self):
        """Create or update hr.leave.allocation so Odoo enforces the balance.

        When an opening reset date is set, the allocation's date_from is set
        to that date.  Odoo's leave-assignment logic only links validated leaves
        to an allocation when the leave date_from >= allocation.date_from, so
        pre-reset leaves are automatically excluded from leaves_taken.
        """
        LeaveType = self.env['hr.leave.type'].sudo()
        Allocation = self.env['hr.leave.allocation'].sudo()

        # Find the annual-leave type once
        annual_type = LeaveType.search([('is_annual_leave', '=', True)], limit=1)
        if not annual_type:
            return

        for rec in self:
            if not rec.employee_id or rec.total_accrued_days <= 0:
                continue

            joining = rec.joining_date
            # Effective start: reset date takes priority over joining date.
            # This determines the allocation's date_from, which in turn controls
            # which validated leaves Odoo counts in leaves_taken.
            if rec.x_opening_reset_date:
                effective_start = max(rec.x_opening_reset_date, joining)
            else:
                effective_start = joining

            if rec.allocation_id and rec.allocation_id.exists():
                # Update existing allocation – days and date_from
                vals = {'number_of_days': rec.total_accrued_days}
                if effective_start and rec.allocation_id.date_from != effective_start:
                    vals['date_from'] = effective_start
                rec.allocation_id.sudo().write(vals)
            else:
                # Create new allocation (or replace missing one)
                alloc = Allocation.with_context(
                    mail_create_nosubscribe=True,
                    mail_notrack=True,
                ).create({
                    'employee_id': rec.employee_id.id,
                    'holiday_status_id': annual_type.id,
                    'number_of_days': rec.total_accrued_days,
                    'date_from': effective_start,
                    'notes': 'Auto-managed by KSW Annual Leave module',
                })
                # Approve the allocation so it becomes active
                alloc.action_approve()
                rec.sudo().write({'allocation_id': alloc.id})

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_generate_all(self):
        """Create or refresh annual leave records for all active employees."""
        AnnualLeave = self.env['ksw.annual.leave']
        employees = self.env['hr.employee'].search([])
        existing = AnnualLeave.search([])
        existing_emp_ids = set(existing.mapped('employee_id').ids)

        # Create missing records
        vals_list = []
        for emp in employees:
            if emp.id not in existing_emp_ids:
                vals_list.append({'employee_id': emp.id})
        if vals_list:
            AnnualLeave.create(vals_list)

        # Force recompute on ALL records
        all_records = AnnualLeave.search([])
        if all_records:
            all_records._refresh_accrual()

    @api.model
    def _cron_refresh(self):
        """Daily cron to auto-create missing records and recompute."""
        self.action_generate_all()

    # ------------------------------------------------------------------
    # FIFO Historical Vacation Value
    # ------------------------------------------------------------------

    def _get_version_accrual_segments(self, employee, as_of_date=None,
                                      from_date=None):
        """Build per-version accrual segments with wage rates.

        Args:
            employee: hr.employee record
            as_of_date: optional upper bound (defaults to today)
            from_date: optional lower bound — segments before this date are
                trimmed or skipped.  Used when an opening reset date is set
                so that FIFO vacation value only prices post-reset accrual.

        Returns a list of dicts sorted oldest-first::

            [
                {
                    'version_id': <id>,
                    'date_from': <date>,
                    'date_to': <date>,
                    'calendar_days': <int>,
                    'accrual_days': <float>,
                    'daily_wage': <float>,      # version.wage / 30
                },
                ...
            ]

        The two-tier accrual logic (21/365 for first 1825 calendar days
        from joining, 30/365 after) is applied across segments in
        chronological order.
        """
        if not as_of_date:
            as_of_date = fields.Date.context_today(self)

        versions = employee.sudo().version_ids.filtered(
            lambda v: v.contract_date_start and v.active
        ).sorted('date_version')

        if not versions:
            return []

        joining = min(versions.mapped('contract_date_start'))
        five_years_days = 5 * 365

        # Normalise from_date: if it is at or before joining, ignore it
        if from_date and from_date <= joining:
            from_date = None

        segments = []
        for i, version in enumerate(versions):
            seg_start = version.date_version
            if seg_start < joining:
                seg_start = joining

            # Segment ends the day before the next version starts,
            # or as_of_date for the last version.
            if i + 1 < len(versions):
                next_start = versions[i + 1].date_version
                seg_end = next_start - relativedelta(days=1)
            else:
                seg_end = as_of_date

            if seg_end < seg_start:
                continue

            # Apply from_date lower bound (opening reset date trimming)
            if from_date:
                if seg_end < from_date:
                    continue          # entire segment is before reset, skip
                if seg_start < from_date:
                    seg_start = from_date   # trim segment to start at reset

            if seg_end < seg_start:
                continue

            cal_days_in_seg = (seg_end - seg_start).days + 1

            # How many calendar days elapsed from joining to the START
            # of this segment — determines tier-1/tier-2 boundary.
            days_before_seg = (seg_start - joining).days

            # Tier-1 calendar days within this segment
            tier1_remaining = max(five_years_days - days_before_seg, 0)
            tier1_in_seg = min(cal_days_in_seg, tier1_remaining)
            tier2_in_seg = cal_days_in_seg - tier1_in_seg

            accrual_days = (
                tier1_in_seg * (21.0 / 365.0)
                + tier2_in_seg * (30.0 / 365.0)
            )

            segments.append({
                'version_id': version.id,
                'date_from': seg_start,
                'date_to': seg_end,
                'calendar_days': cal_days_in_seg,
                'accrual_days': round(accrual_days, 6),
                'daily_wage': (version.wage or 0.0) / 30.0,
            })

        return segments

    @api.model
    def _compute_historical_vacation_value(self, employee, vacation_days,
                                           exclude_days=0.0):
        """Compute the FIFO-weighted vacation balance settlement value.

        Walk through the employee's version history, build accrual
        segments, deduct previously-taken vacation days FIFO from the
        oldest segments, then consume ``vacation_days`` FIFO and sum
        ``segment_days × segment_daily_wage`` for each portion.

        When an opening reset date is set on the employee's
        ``ksw.annual.leave`` record, segments before that date are
        excluded so the FIFO pricing starts from the go-live baseline.
        Any ``x_opening_extra_days`` are prepended as a synthetic first
        segment valued at the earliest post-reset version's daily wage.

        Args:
            employee: hr.employee record
            vacation_days: float — number of accrual days to consume
            exclude_days: float — days to subtract from leaves_taken
                before FIFO deduction.  Use this when the current leave's
                days are already included in ``allocation.leaves_taken``
                (e.g. when recomputing after validation) to avoid
                double-counting.

        Returns:
            dict with:
                'total': float — total monetary value
                'breakdown': list of (days, daily_wage, amount) tuples
                'label': str — human-readable breakdown for payslip name
        """
        ksw_rec = self.sudo().search([
            ('employee_id', '=', employee.id),
        ], limit=1)

        # Determine from_date for segment trimming (opening reset date)
        from_date = ksw_rec.x_opening_reset_date if ksw_rec else None
        extra_days = (ksw_rec.x_opening_extra_days or 0.0) if ksw_rec else 0.0

        segments = (
            ksw_rec._get_version_accrual_segments(employee, from_date=from_date)
            if ksw_rec else []
        )

        if not segments:
            # Fallback: use current wage
            daily_wage = (employee.current_version_id.wage or 0.0) / 30.0
            total = vacation_days * daily_wage
            return {
                'total': total,
                'breakdown': [(vacation_days, daily_wage, total)],
                'label': '%.2f days × %.2f/day' % (vacation_days, daily_wage),
            }

        # Prepend opening extra days as a synthetic segment valued at the
        # earliest post-reset version's daily wage (they represent pre-existing
        # balance carried forward, older than any post-reset accrual).
        if extra_days > 0 and from_date:
            first_wage = segments[0]['daily_wage'] if segments else (
                (employee.current_version_id.wage or 0.0) / 30.0
            )
            segments = [{
                'version_id': False,
                'date_from': from_date,
                'date_to': from_date,
                'calendar_days': 0,
                'accrual_days': round(extra_days, 6),
                'daily_wage': first_wage,
            }] + segments

        # Get previously taken vacation days (excluding current leave)
        taken = 0.0
        try:
            if ksw_rec and ksw_rec.allocation_id and ksw_rec.allocation_id.exists():
                taken = ksw_rec.allocation_id.sudo().leaves_taken or 0.0
        except Exception:
            taken = 0.0
        taken = max(taken - exclude_days, 0.0)

        # Deduct previously-taken days FIFO from oldest segments.
        # Each taken vacation day removes 1 accrual day from the segment.
        remaining_taken = taken
        remaining_segments = []
        for seg in segments:
            if remaining_taken <= 0:
                remaining_segments.append(dict(seg))
                continue

            if remaining_taken >= seg['accrual_days']:
                remaining_taken -= seg['accrual_days']
                continue
            else:
                leftover = seg['accrual_days'] - remaining_taken
                remaining_taken = 0
                new_seg = dict(seg)
                new_seg['accrual_days'] = round(leftover, 6)
                remaining_segments.append(new_seg)

        # Now consume vacation_days FIFO from remaining segments
        to_consume = vacation_days
        breakdown = []
        total = 0.0

        for seg in remaining_segments:
            if to_consume <= 0:
                break

            days_from_seg = min(to_consume, seg['accrual_days'])
            amount = days_from_seg * seg['daily_wage']
            breakdown.append((
                round(days_from_seg, 4),
                round(seg['daily_wage'], 2),
                round(amount, 2),
            ))
            total += amount
            to_consume -= days_from_seg

        # Build label
        parts = []
        for days, rate, _amt in breakdown:
            parts.append('%.2f d × %.2f' % (days, rate))
        label = ' + '.join(parts) if parts else '0 days'

        return {
            'total': round(total, 2),
            'breakdown': breakdown,
            'label': label,
        }
