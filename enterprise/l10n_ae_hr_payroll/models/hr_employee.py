# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_ae_annual_leave_days_taken = fields.Float(
        string="Annual Leave Days Taken",
        groups="hr.group_hr_user",
        compute="_compute_l10n_ae_annual_leave_days")
    l10n_ae_annual_leave_days_total = fields.Float(
        string="Annual Leave Days Total",
        groups="hr.group_hr_user",
        compute="_compute_l10n_ae_annual_leave_days")
    l10n_ae_total_unpaid_days = fields.Float(
        string="Total Unpaid Days",
        groups="hr.group_hr_user",
        compute="_compute_l10n_ae_total_unpaid_days",
    )

    def _l10n_ae_get_worked_duration(self):
        """ Return the PAID duration that the employee has worked as (years, months, days)"""
        self.ensure_one()
        if self.first_contract_date and self.contract_id.date_end:
            unpaid_days = int(self.l10n_ae_total_unpaid_days)
            unpaid_hours = int((self.l10n_ae_total_unpaid_days % 1) * 24)
            adjustment_values = relativedelta(days=unpaid_days + (1 if unpaid_hours else 0)) + relativedelta(hours=unpaid_hours)
            diff = relativedelta(self.contract_id.date_end - adjustment_values, self.first_contract_date)
            return diff.years, diff.months, (diff.days + (diff.hours / 24))
        return 0, 0, 0

    def _l10n_ae_get_worked_years(self):
        years, months, days = self._l10n_ae_get_worked_duration()
        return years + (months / 12) + (days / 365)

    def _compute_l10n_ae_total_unpaid_days(self):
        employee_duration_sums = dict(self.env['hr.work.entry']._read_group(
            domain=[
                ('employee_id', 'in', self.ids),
                ('code', 'in', ('SICKLEAVE0', 'LEAVE90', 'OUT')),
            ],
            groupby=['employee_id'],
            aggregates=['duration:sum'],
        ))
        for employee in self:
            employee.l10n_ae_total_unpaid_days = employee_duration_sums.get(employee, 0) / (employee._get_hours_per_day(employee.contract_id.date_start) or 8)

    def _compute_l10n_ae_annual_leave_days(self):
        self._cr.execute("""
            SELECT
                sum(h.number_of_days) AS days,
                sum(CASE WHEN h.type = 'allocation' THEN h.number_of_days ELSE 0 END) AS total_days_allocated,
                h.employee_id
            FROM
                (
                    SELECT holiday_status_id, number_of_days,
                        state, employee_id, 'allocation' as type
                    FROM hr_leave_allocation
                    UNION ALL
                    SELECT holiday_status_id, (number_of_days * -1) as number_of_days,
                        state, employee_id, 'leave' as type
                    FROM hr_leave
                ) h
                join hr_leave_type s ON (s.id=h.holiday_status_id)
            WHERE
                s.active = true AND h.state='validate' AND
                s.requires_allocation='yes' AND
                h.employee_id in %s AND
                s.l10n_ae_is_annual_leave = TRUE
            GROUP BY h.employee_id""", (tuple(self.ids),))

        employees_remaining_annual_leaves = {row['employee_id']: (row['total_days_allocated'], row['days']) for row in self._cr.dictfetchall()}
        for record in self:
            record.l10n_ae_annual_leave_days_taken = 0
            record.l10n_ae_annual_leave_days_total = 0
            if record.id in employees_remaining_annual_leaves:
                total_days_allocated, remaining_days = employees_remaining_annual_leaves[record.id]
                record.l10n_ae_annual_leave_days_total = total_days_allocated
                record.l10n_ae_annual_leave_days_taken = total_days_allocated - remaining_days
