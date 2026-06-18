from odoo import api, fields, models


class KswAnnualLeaveUnpaid(models.Model):
    """Extend the annual-leave accrual to deduct validated unpaid days.

    Unpaid leave days reduce the *effective service days* (calendar_days)
    used in the two-tier FIFO accrual formula.  This ensures that unpaid
    days after the 5-year mark reduce accrual at the tier-2 rate (30/365)
    rather than being consumed FIFO from tier-1 at 21/365.
    """
    _inherit = 'ksw.annual.leave'

    def _get_unpaid_leave_days(self, employee_id):
        """Return the total number of validated unpaid-leave calendar days
        for the given employee (all time).  Includes the unpaid portion
        of combined annual+unpaid leaves."""
        # Standalone unpaid leaves
        unpaid_leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'validate'),
            ('holiday_status_id.is_unpaid_leave', '=', True),
        ])
        total = sum(unpaid_leaves.mapped('number_of_days'))

        # Unpaid portion of combined annual leaves
        combined_leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'validate'),
            ('holiday_status_id.is_annual_leave', '=', True),
            ('x_excess_days_accepted', '=', True),
            ('x_unpaid_portion_days', '>', 0),
        ])
        total += sum(combined_leaves.mapped('x_unpaid_portion_days'))

        return total

    @api.depends('employee_id')
    def _compute_leave_data(self):
        """Override to subtract unpaid days from effective calendar days.

        The parent computes accrual using calendar_days (today - joining).
        Unpaid leave days should NOT count as service time, so we subtract
        them from calendar_days before running the two-tier formula.
        This ensures days after 5 years reduce at 30/365, not 21/365.
        """
        super()._compute_leave_data()

        today = fields.Date.context_today(self)

        for rec in self:
            if not rec.employee_id or not rec.joining_date:
                continue

            unpaid_days = self._get_unpaid_leave_days(rec.employee_id.id)
            if unpaid_days <= 0:
                continue

            total_calendar_days = (today - rec.joining_date).days
            if total_calendar_days <= 0:
                continue

            # Reduce effective service days by unpaid leave days
            calendar_days = max(total_calendar_days - unpaid_days, 0)

            # Annual leaves taken (from allocation)
            taken = (
                rec.allocation_id.sudo().leaves_taken
                if rec.allocation_id else 0.0
            )

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

            total_accrued = (
                (tier1_max - tier1_deduction)
                + (tier2_max - tier2_deduction)
            )
            rec.total_accrued_days = round(total_accrued, 4)


