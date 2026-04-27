# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools.float_utils import float_round


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_sa_leaves_count_compensable = fields.Float(
        'Number of Time Off Eligible for Compensation',
        compute='_compute_l10n_sa_leaves_count_compensable',
        groups="hr.group_hr_user")

    l10n_sa_employee_code = fields.Char(string="Saudi National / IQAMA ID", groups="hr.group_hr_user")

    def _l10n_sa_get_remaining_leaves_compensable(self):
        """ Copy of _get_remaining_leaves but filtered only to include compensable leave types
        """
        if not self:
            return {}
        self._cr.execute("""
            SELECT
                sum(h.number_of_days) AS days,
                h.employee_id
            FROM
                (
                    SELECT holiday_status_id, number_of_days,
                        state, employee_id
                    FROM hr_leave_allocation
                    UNION ALL
                    SELECT holiday_status_id, (number_of_days * -1) as number_of_days,
                        state, employee_id
                    FROM hr_leave
                ) h
                join hr_leave_type s ON (s.id=h.holiday_status_id AND s.l10n_sa_is_compensable = 'true')
            WHERE
                s.active = true AND h.state='validate' AND
                s.requires_allocation='yes' AND
                h.employee_id in %s
            GROUP BY h.employee_id""", (tuple(self.ids),))
        return {row['employee_id']: row['days'] for row in self._cr.dictfetchall()}

    def _compute_l10n_sa_leaves_count_compensable(self):
        remaining = self._l10n_sa_get_remaining_leaves_compensable()
        for employee in self:
            employee.l10n_sa_leaves_count_compensable = float_round(remaining.get(employee.id, 0.0), precision_digits=2)
