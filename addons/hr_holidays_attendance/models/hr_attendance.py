# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL

# fields that when changed invalidate previously credited allocations
_TIME_FIELDS = frozenset({'check_in', 'check_out', 'employee_id'})


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    has_time_off_conflict = fields.Boolean(
        string="On Time Off", compute='_compute_has_time_off_conflict', search='_search_has_time_off_conflict',
        help="The attendance overlaps an approved time off of the employee.")

    @api.depends('employee_id', 'check_in', 'check_out')
    def _compute_has_time_off_conflict(self):
        """Flag the attendances that overlap an approved time off of the employee. An attendance that is not checked
        out yet counts until the moment it is read as the field is not stored, so it is computed again at each read.
        """
        self.has_time_off_conflict = False
        attendances = self.filtered(lambda a: a.employee_id and a.check_in)
        if not attendances:
            return
        now = fields.Datetime.now()
        leaves_by_employee = self.env['hr.leave'].sudo().search([
            ('state', '=', 'validate'),
            ('employee_id', 'in', attendances.employee_id.ids),
            ('date_from', '<', max(attendances.mapped(lambda a: a.check_out or now))),
            ('date_to', '>', min(attendances.mapped('check_in'))),
        ]).grouped('employee_id')
        for attendance in attendances:
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
        """Overlapping an approved time off is an issue."""
        super()._compute_has_issue()
        self.filtered('has_time_off_conflict').has_issue = True

    def write(self, vals):
        """Reverse the allocation credits of the attendances that are no longer reviewed or whose times change.

        The times are ``check_in``, ``check_out`` and ``employee_id``, unless the context has ``skip_time_rules``.
        Running the time rules again credits the new times. The review state is checked after the write, because
        ``hr_attendance`` may change it there: an employee's edit sends their attendance back to To Review.

        :raise ValidationError: if the allocation was already used beyond its allowed balance
        """
        if not self.env.context.get('skip_time_rules') and _TIME_FIELDS & vals.keys():
            self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', self.ids)
            return super().write(vals)
        reviewed = self.filtered(lambda a: a.state == 'validated')
        result = super().write(vals)
        if no_longer_reviewed := reviewed.filtered(lambda a: a.state != 'validated'):
            self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', no_longer_reviewed.ids)
        return result

    @api.ondelete(at_uninstall=False)
    def _reverse_credits_on_unlink(self):
        """Reverse the allocation credits logged on the deleted attendances."""
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', self.ids)
