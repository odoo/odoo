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
        help='Total annual leave days accrued from joining date to today.',
    )
    leaves_taken = fields.Float(
        string='Leaves Taken', compute='_compute_leave_data',
        store=True, digits=(10, 4),
        help='Total approved annual leave days taken.',
    )
    remaining_balance = fields.Float(
        string='Remaining Balance', compute='_compute_leave_data',
        store=True, digits=(10, 4),
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

    @api.depends('employee_id')
    def _compute_leave_data(self):
        today = fields.Date.context_today(self)
        for rec in self:
            # --- defaults ---
            rec.joining_date = False
            rec.years_of_service = 0.0
            rec.daily_rate = 0.0
            rec.total_accrued_days = 0.0
            rec.leaves_taken = 0.0
            rec.remaining_balance = 0.0

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

            # --- Leaves taken (all validated annual leaves) ---
            annual_leaves = self.env['hr.leave'].sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'validate'),
                ('holiday_status_id.is_annual_leave', '=', True),
            ])
            taken = sum(annual_leaves.mapped('number_of_days'))
            rec.leaves_taken = taken

            # --- Effective service days (exclude annual leave periods) ---
            effective_days = max(calendar_days - int(taken), 0)

            # --- Years of service (based on effective days) ---
            rdelta = relativedelta(today, joining)
            rec.years_of_service = round(
                rdelta.years + rdelta.months / 12.0 + rdelta.days / 365.25, 2
            )

            # --- Two-tier daily accrual on effective days ---
            five_years_days = 5 * 365
            if effective_days <= five_years_days:
                total_accrued = effective_days * (21.0 / 365.0)
            else:
                total_accrued = (
                    five_years_days * (21.0 / 365.0)
                    + (effective_days - five_years_days) * (30.0 / 365.0)
                )

            rec.total_accrued_days = round(total_accrued, 4)

            # --- Current daily rate (based on effective days) ---
            rec.daily_rate = 30.0 / 365.0 if effective_days > five_years_days else 21.0 / 365.0

            # --- Remaining balance ---
            rec.remaining_balance = round(total_accrued - taken, 4)

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

            if rec.allocation_id:
                # Update existing allocation – just update the number of days
                rec.allocation_id.sudo().write({
                    'number_of_days': rec.total_accrued_days,
                })
            else:
                # Create new allocation (state defaults to 'confirm')
                alloc = Allocation.with_context(
                    mail_create_nosubscribe=True,
                    mail_notrack=True,
                ).create({
                    'employee_id': rec.employee_id.id,
                    'holiday_status_id': annual_type.id,
                    'number_of_days': rec.total_accrued_days,
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

        # Force recompute on ALL records by marking the field dirty
        all_records = AnnualLeave.search([])
        if all_records:
            field = self._fields['joining_date']
            self.env.add_to_compute(field, all_records)
            # Flush the compute so stored values are written before syncing
            all_records.flush_recordset()
            # Now sync allocations with the freshly computed values
            all_records._sync_allocations()

    @api.model
    def _cron_refresh(self):
        """Daily cron to auto-create missing records and recompute."""
        self.action_generate_all()


