# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, models
from odoo.fields import Domain

# the fields that change the hours expected from the employees
_EXPECTED_HOURS_FIELDS = frozenset({'date_from', 'date_to', 'resource_id', 'company_id', 'calendar_id', 'count_as'})


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        leaves._recompute_attendance_issues(leaves._get_attendances_in_period())
        return leaves

    def write(self, vals):
        if not _EXPECTED_HOURS_FIELDS & vals.keys():
            return super().write(vals)
        attendances_before = self._get_attendances_in_period()
        res = super().write(vals)
        self._recompute_attendance_issues(attendances_before | self._get_attendances_in_period())
        return res

    def unlink(self):  # nosemgrep: unlink-override
        # The issues of the attendances can only be recomputed once the time off or public holidays are gone, which
        # an ondelete method cannot do. Only follow-up computations, nothing that could block the uninstall.
        attendances = self._get_attendances_in_period()
        res = super().unlink()
        self._recompute_attendance_issues(attendances.exists())
        return res

    def _get_attendances_in_period(self):
        """Return the attendances whose issues may change with these time off or public holidays.

        A time off changes the shifts that the attendances of its employee are compared with, see
        ``hr.attendance._get_issues``. A public holiday (without resource) applies to all the employees of its
        company, whatever their current schedule, as their past versions may have had another one. The period is
        widened by a day on each side, because the attendances are compared per local day of the employee.

        :rtype: hr.attendance
        """
        domains = []
        # sudo: the domain may read the time off of the leaves
        leaves = self.sudo().filtered_domain(self._get_leave_intervals_domain())
        for leave in leaves.filtered(lambda leave: leave.date_from and leave.date_to):
            if leave.resource_id:
                employee_domain = Domain('employee_id.resource_id', '=', leave.resource_id.id)
            elif leave.company_id:
                employee_domain = Domain('employee_id.company_id', '=', leave.company_id.id)
            else:
                employee_domain = Domain.TRUE
            domains.append(
                employee_domain
                & Domain('check_in', '<', leave.date_to + timedelta(days=1))
                & Domain('check_in', '>', leave.date_from - timedelta(days=1))
            )
        attendances = self.env['hr.attendance'].sudo()
        if not domains:
            return attendances
        return attendances.search(Domain.OR(domains) & attendances._get_worked_time_domain())

    def _recompute_attendance_issues(self, attendances):
        """Recompute the expected hours and the issues of the days of the attendances. The ones that no longer have an
        issue may be reviewed, as after any change of their day, see ``hr.attendance._auto_review``."""
        if attendances:
            # Approving or refusing a time off runs with skip_time_rules, which is meant for the time off. The
            # attendances that get reviewed here still need their time rules.
            had_issue = attendances.with_context(skip_time_rules=False)._recompute_same_day_issues()
            attendances._search_same_day_attendances()._recompute_expected_hours()
            had_issue._auto_review()
