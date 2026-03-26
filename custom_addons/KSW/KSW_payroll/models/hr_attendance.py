from odoo import api, fields, models

# Hardcoded constants: all employees are required 30 days/month, 8 hours/day
DAILY_MINUTES = 480.0   # 8 hours
DAYS_PER_MONTH = 30.0


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    x_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='employee_id.company_id.currency_id',
    )

    x_deductible_base = fields.Monetary(
        string='Deductible Base',
        compute='_compute_deduction',
        store=True,
        currency_field='x_currency_id',
        groups='hr.group_hr_user',
        help='Monthly wage + allowances (excl. housing) used as deduction base.',
    )

    x_daily_rate = fields.Monetary(
        string='Daily Rate',
        compute='_compute_deduction',
        store=True,
        currency_field='x_currency_id',
        groups='hr.group_hr_user',
        help='Deductible base / 30.',
    )

    x_hourly_rate = fields.Monetary(
        string='Hourly Rate',
        compute='_compute_deduction',
        store=True,
        currency_field='x_currency_id',
        groups='hr.group_hr_user',
        help='Daily rate / 8 hours.',
    )

    x_scheduled_minutes = fields.Float(
        string='Scheduled Minutes',
        compute='_compute_deduction',
        store=True,
        help='Required work minutes per day (hardcoded 480 = 8 hours).',
    )

    x_deduction_amount = fields.Monetary(
        string='Deduction',
        compute='_compute_deduction',
        store=True,
        currency_field='x_currency_id',
        groups='hr.group_hr_user',
        help='Salary deduction amount for this attendance record.',
    )

    # ------------------------------------------------------------------
    # Compute deduction
    # ------------------------------------------------------------------

    @api.depends(
        'employee_id.current_version_id.wage',
        'employee_id.current_version_id.da',
        'employee_id.current_version_id.travel_allowance',
        'employee_id.current_version_id.meal_allowance',
        'employee_id.current_version_id.medical_allowance',
        'employee_id.current_version_id.other_allowance',
        'x_net_late_minutes',
        'x_net_early_leave_minutes',
        'x_net_is_absent',
        'check_in',
    )
    def _compute_deduction(self):
        for att in self:
            att.x_deductible_base = 0.0
            att.x_daily_rate = 0.0
            att.x_hourly_rate = 0.0
            att.x_scheduled_minutes = 0.0
            att.x_deduction_amount = 0.0

            if not att.employee_id or not att.check_in:
                continue

            # Get current version (contract) for wage + allowances
            version = att.employee_id.sudo().current_version_id
            if not version:
                continue

            # Deductible base: wage + allowances excluding housing (HRA)
            base = (
                (version.wage or 0.0)
                + (version.da or 0.0)
                + (version.travel_allowance or 0.0)
                + (version.meal_allowance or 0.0)
                + (version.medical_allowance or 0.0)
                + (version.other_allowance or 0.0)
            )
            att.x_deductible_base = base
            daily_rate = base / DAYS_PER_MONTH
            att.x_daily_rate = daily_rate
            att.x_hourly_rate = daily_rate / (DAILY_MINUTES / 60.0)

            # All employees: 8 hours/day = 480 minutes
            att.x_scheduled_minutes = DAILY_MINUTES

            # Calculate deduction
            if att.x_net_is_absent:
                # Full day absence -> deduct one daily rate
                att.x_deduction_amount = daily_rate
            else:
                # Partial day: late + early leave minutes
                deductible_minutes = (
                    (att.x_net_late_minutes or 0.0)
                    + (att.x_net_early_leave_minutes or 0.0)
                )
                if deductible_minutes > 0:
                    # Cap at daily_rate: penalty cannot exceed a full absence
                    att.x_deduction_amount = min(
                        (deductible_minutes / DAILY_MINUTES) * daily_rate,
                        daily_rate,
                    )
