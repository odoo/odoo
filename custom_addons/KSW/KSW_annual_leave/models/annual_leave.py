from odoo import api, fields, models
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
        help='Total annual leave days accrued based on effective days '
             '(calendar days minus approved vacation days).',
    )
    leaves_taken = fields.Float(
        string='Leaves Taken',
        related='allocation_id.leaves_taken',
        digits=(10, 4),
        help='Total approved annual leave days taken (from linked allocation).',
    )
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

    _unique_employee = models.Constraint(
        'UNIQUE(employee_id)',
        'Only one annual leave record per employee is allowed.',
    )

    @api.depends(
        'employee_id',
        'employee_id.version_ids.contract_date_start',
        'employee_id.version_ids.wage',
        'employee_id.version_ids.date_version',
        'employee_id.version_ids.active',
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

            # --- Calendar days since joining ---
            calendar_days = (today - joining).days
            if calendar_days <= 0:
                continue

            # --- Years of service ---
            rdelta = relativedelta(today, joining)
            rec.years_of_service = round(
                rdelta.years + rdelta.months / 12.0 + rdelta.days / 365.25, 2
            )

            # --- Approved annual leave days taken ---
            # Vacation days do NOT generate additional accrual.
            taken = (
                rec.allocation_id.sudo().leaves_taken
                if rec.allocation_id else 0.0
            )

            # --- Two-tier daily accrual (Saudi Labor Law Art. 109) ---
            # FIFO deduction: vacation days consume tier-1 accrued balance
            # first (max 105 days = 21 × 5 years), overflow to tier-2.
            # Each vacation day removes one daily-rate unit of accrual
            # from the relevant tier (21/365 for tier 1, 30/365 for tier 2).
            five_years_days = 5 * 365
            tier1_cal = min(calendar_days, five_years_days)
            tier2_cal = max(calendar_days - five_years_days, 0)

            # Maximum accrued days each tier can produce
            tier1_max = tier1_cal * (21.0 / 365.0)   # up to 105
            tier2_max = tier2_cal * (30.0 / 365.0)

            # Convert vacation days to accrual-equivalent deductions (FIFO).
            # Each vacation day in tier 1 removes 21/365 accrual days;
            # once tier 1 is exhausted, each day in tier 2 removes 30/365.
            tier1_deduction = min(taken * (21.0 / 365.0), tier1_max)
            # How many raw vacation days were NOT covered by tier 1?
            tier1_vac_days = min(taken, tier1_max / (21.0 / 365.0))
            leftover_days = max(taken - tier1_vac_days, 0)
            tier2_deduction = min(leftover_days * (30.0 / 365.0), tier2_max)

            total_accrued = (tier1_max - tier1_deduction) + (tier2_max - tier2_deduction)

            rec.total_accrued_days = round(total_accrued, 4)

            # --- Current daily rate (based on actual calendar service) ---
            rec.daily_rate = 30.0 / 365.0 if calendar_days > five_years_days else 21.0 / 365.0

    # ------------------------------------------------------------------
    # Remaining balance (non-stored, always real-time)
    # ------------------------------------------------------------------
    @api.depends('total_accrued_days', 'leaves_taken')
    def _compute_remaining_balance(self):
        for rec in self:
            rec.remaining_balance = round(rec.total_accrued_days - rec.leaves_taken, 4)

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
        """Create or update hr.leave.allocation so Odoo enforces the balance."""
        LeaveType = self.env['hr.leave.type'].sudo()
        Allocation = self.env['hr.leave.allocation'].sudo()

        # Find the annual-leave type once
        annual_type = LeaveType.search([('is_annual_leave', '=', True)], limit=1)
        if not annual_type:
            return

        for rec in self:
            if not rec.employee_id or rec.total_accrued_days <= 0:
                continue

            # The allocation must start from the joining date so that
            # leaves taken at any point in the employee's service are
            # covered by this allocation.
            joining = rec.joining_date

            if rec.allocation_id:
                # Update existing allocation – days and date_from
                vals = {'number_of_days': rec.total_accrued_days}
                if joining and rec.allocation_id.date_from != joining:
                    vals['date_from'] = joining
                rec.allocation_id.sudo().write(vals)
            else:
                # Create new allocation
                alloc = Allocation.with_context(
                    mail_create_nosubscribe=True,
                    mail_notrack=True,
                ).create({
                    'employee_id': rec.employee_id.id,
                    'holiday_status_id': annual_type.id,
                    'number_of_days': rec.total_accrued_days,
                    'date_from': joining,
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

    def _get_version_accrual_segments(self, employee, as_of_date=None):
        """Build per-version accrual segments with wage rates.

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

        segments = ksw_rec._get_version_accrual_segments(employee) if ksw_rec else []

        if not segments:
            # Fallback: use current wage
            daily_wage = (employee.current_version_id.wage or 0.0) / 30.0
            total = vacation_days * daily_wage
            return {
                'total': total,
                'breakdown': [(vacation_days, daily_wage, total)],
                'label': '%.2f days × %.2f/day' % (vacation_days, daily_wage),
            }

        # Get previously taken vacation days (excluding current leave)
        taken = 0.0
        if ksw_rec and ksw_rec.allocation_id:
            taken = ksw_rec.allocation_id.sudo().leaves_taken or 0.0
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
