from odoo import api, fields, models


class AbsentDaysWizardUnpaid(models.TransientModel):
    """Extend Service Days Calculator to include unpaid leave days
    in the FIFO accrual deduction."""
    _inherit = 'absent.days.wizard'

    unpaid_leave_days = fields.Float(
        string='Unpaid Leave Days',
        readonly=True,
        digits=(10, 4),
        help='Total approved unpaid leave calendar days (all time).',
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """After parent computes accrual, re-run with unpaid days added."""
        super()._onchange_employee_id()

        if not self.employee_id or not self.joining_date:
            self.unpaid_leave_days = 0.0
            return

        # Query validated unpaid leaves
        unpaid_leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'validate'),
            ('holiday_status_id.is_unpaid_leave', '=', True),
        ])
        unpaid_days = sum(unpaid_leaves.mapped('number_of_days'))
        self.unpaid_leave_days = unpaid_days

        if unpaid_days <= 0:
            return

        # Re-run the FIFO formula with reduced effective calendar days
        today = fields.Date.context_today(self)
        total_calendar_days = max((today - self.joining_date).days, 0)
        if total_calendar_days <= 0:
            return

        # Reduce effective service days by unpaid leave days
        calendar_days = max(total_calendar_days - unpaid_days, 0)

        # Annual taken (already computed by parent)
        taken = self.annual_leave_taken

        five_years_days = 5 * 365
        tier1_cal = min(calendar_days, five_years_days)
        tier2_cal = max(calendar_days - five_years_days, 0)

        tier1_max = tier1_cal * (21.0 / 365.0)
        tier2_max = tier2_cal * (30.0 / 365.0)

        # FIFO deduction for annual vacation days only
        tier1_deduction = min(taken * (21.0 / 365.0), tier1_max)
        tier1_vac_days = min(taken, tier1_max / (21.0 / 365.0))
        leftover_days = max(taken - tier1_vac_days, 0)
        tier2_deduction = min(leftover_days * (30.0 / 365.0), tier2_max)

        total_accrued = (tier1_max - tier1_deduction) + (tier2_max - tier2_deduction)
        self.total_accrued_days = round(total_accrued, 4)
        self.annual_leave_balance = round(total_accrued - taken, 4)


