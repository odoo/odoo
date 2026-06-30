from odoo import api, models
from odoo.fields import Domain


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    def _get_attendance_domain(self):
        domain = []

        leaves_time_type_leave = self.filtered(lambda leave: leave.time_type == 'leave')

        resource_leaves = leaves_time_type_leave.filtered(lambda leave: leave.resource_id.employee_id)
        domain.extend([[
            ('check_in', '<=', max(leaves.mapped('date_to'))),
            ('check_out', '>=', min(leaves.mapped('date_from'))),
            ('employee_id', 'in', resource.employee_id.ids),
        ] for resource, leaves in resource_leaves.grouped('resource_id').items()])

        for leave in (leaves_time_type_leave - resource_leaves):
            leave_domain = [
                ('check_in', '<=', leave.date_to),
                ('check_out', '>=', leave.date_from),
            ]
            if leave.company_id:
                leave_domain.append(('employee_id.company_id', '=', leave.company_id.id))
            if leave.calendar_id:
                leave_domain.append(('employee_id.resource_calendar_id', '=', leave.calendar_id.id))
            domain.append(leave_domain)

        return Domain.OR(domain)

    def _update_attendances_overtime(self, domain=None):
        self.env['hr.attendance'].sudo().search(domain or self._get_attendance_domain())._update_overtime()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._update_attendances_overtime()
        return res

    def write(self, vals):
        affects_attendances = bool({'date_from', 'date_to', 'resource_id', 'calendar_id', 'company_id', 'time_type'} & set(vals.keys()))
        if affects_attendances:
            before_domain = self._get_attendance_domain()
        res = super().write(vals)
        if affects_attendances:
            after_domain = self._get_attendance_domain()
            self._update_attendances_overtime(Domain.OR([before_domain, after_domain]))
        return res

    def unlink(self):
        before_domain = self._get_attendance_domain()
        res = super().unlink()
        self._update_attendances_overtime(before_domain)
        return res
