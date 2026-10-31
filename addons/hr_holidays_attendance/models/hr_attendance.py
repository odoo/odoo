# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

# fields that when changed invalidate previously credited allocations
_TIME_FIELDS = frozenset({'check_in', 'check_out', 'employee_id'})

# states in which an attendance no longer counts as valid source material
_INVALID_STATES = frozenset({'refused', 'draft'})


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    has_time_off_conflict = fields.Boolean(
        string="On Time Off", compute='_compute_has_time_off_conflict', search='_search_has_time_off_conflict',
        help="The attendance overlaps an approved time off of the employee.")

    def _get_time_off_conflicts(self):
        """Return the approved time off of the employees overlapping the attendances.

        An open attendance is considered until now.

        :rtype: hr.leave
        """
        attendances = self.filtered(lambda a: a.employee_id and a.check_in)
        if not attendances:
            return self.env['hr.leave']
        now = fields.Datetime.now()
        return self.env['hr.leave'].sudo().search([
            ('state', '=', 'validate'),
            ('employee_id', 'in', attendances.employee_id.ids),
            ('date_from', '<', max(attendances.mapped(lambda a: a.check_out or now))),
            ('date_to', '>', min(attendances.mapped('check_in'))),
        ])

    @api.depends('employee_id', 'check_in', 'check_out')
    def _compute_has_time_off_conflict(self):
        leaves_by_employee = self._get_time_off_conflicts().grouped('employee_id')
        now = fields.Datetime.now()
        for attendance in self:
            check_out = attendance.check_out or now
            attendance.has_time_off_conflict = any(
                leave.date_from < check_out and leave.date_to > attendance.check_in
                for leave in leaves_by_employee.get(attendance.employee_id, [])
            )

    def _search_has_time_off_conflict(self, operator, value):
        if operator != 'in':
            return NotImplemented
        if True in value and False in value:
            return Domain.TRUE
        # an overlap between two tables cannot be expressed as a domain
        conflicts = SQL("""(
            SELECT attendance.id
              FROM hr_attendance attendance
              JOIN hr_leave leave
                ON leave.employee_id = attendance.employee_id
               AND leave.state = 'validate'
               AND leave.date_from < COALESCE(attendance.check_out, NOW() AT TIME ZONE 'UTC')
               AND leave.date_to > attendance.check_in
        )""")
        return Domain('id', 'in' if True in value else 'not in', conflicts)

    @api.depends('has_time_off_conflict')
    def _compute_has_issue(self):
        super()._compute_has_issue()

    def _has_issue(self):
        """Overlapping an approved time off is an issue."""
        return super()._has_issue() or self.has_time_off_conflict

    def write(self, vals):
        """Reverse the allocation credits logged on the attendances before an invalidating
        write.

        Credits are reversed when ``check_in``, ``check_out`` or ``employee_id`` change (unless
        the context has ``skip_time_rules``), or when a validated attendance goes back to
        ``draft`` or is ``refused``. Re-running the rules credits the new values again.

        :raise ValidationError: if the allocation was already used beyond its allowed balance
        """
        to_reverse = set()
        if not self.env.context.get('skip_time_rules') and _TIME_FIELDS & vals.keys():
            to_reverse.update(self.ids)
        if vals.get('state') in _INVALID_STATES:
            to_reverse.update(self.filtered(lambda a: a.state == 'validated').ids)
        if to_reverse:
            self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', to_reverse)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _reverse_credits_on_unlink(self):
        """Reverse the allocation credits logged on the deleted attendances."""
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', self.ids)
