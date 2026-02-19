from odoo import api, models
from odoo.fields import Domain


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    def _get_attendance_domain(self):
        domain = []

        resource_leaves = self.filtered(lambda l: l.resource_id.employee_id)
        domain.extend([[
            ('employee_id', 'in', resource.employee_id.ids),
            ('check_in', '<=', max(leaves.mapped('date_to'))),
            ('check_out', '>=', min(leaves.mapped('date_from'))),
        ] for resource, leaves in resource_leaves.grouped('resource_id').items()])

        for leave in (self - resource_leaves):
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
        before_domain = self._get_attendance_domain()
        res = super().write(vals)
        after_domain = self._get_attendance_domain()
        self._update_attendances_overtime(Domain.OR([before_domain, after_domain]))
        return res

    def unlink(self):
        before_domain = self._get_attendance_domain()
        res = super().unlink()
        self._update_attendances_overtime(before_domain)
        return res
