# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import format_duration
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    overtime_deductible = fields.Boolean(compute='_compute_overtime_deductible', search='_search_overtime_deductible')

    @api.depends_context('company')
    def _compute_overtime_deductible(self):
        company = self.env.company
        for leave_type in self:
            leave_type.overtime_deductible = leave_type == company.extra_hours_leave_type_id

    def _search_overtime_deductible(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))
        company_extra_hours_leave_type_id = self.env.company.extra_hours_leave_type_id.id
        op = '=' if (operator == '=' and value) or (operator == '!=' and not value) else '!='
        return [('id', op, company_extra_hours_leave_type_id)]

    @api.depends('overtime_deductible', 'requires_allocation')
    @api.depends_context('request_type', 'leave', 'holiday_status_display_name', 'employee_id')
    def _compute_display_name(self):
        # Exclude hours available in allocation contexts, it might be confusing otherwise
        if not self.requested_display_name() or self._context.get('request_type', 'leave') == 'allocation':
            return super()._compute_display_name()

        employee = self.env['hr.employee'].browse(self._context.get('employee_id')).sudo()
        if employee.total_overtime <= 0:
            return super()._compute_display_name()

        overtime_leaves = self.filtered(lambda l_type: l_type.overtime_deductible and l_type.requires_allocation == 'no')
        for leave_type in overtime_leaves:
            leave_type.display_name = "%(name)s (%(count)s)" % {
                'name': leave_type.name,
                'count': _('%s hours available',
                    format_duration(employee.total_overtime)),
            }
        super(HrLeaveType, self - overtime_leaves)._compute_display_name()

    def get_allocation_data(self, employees, target_date=None):
        res = super().get_allocation_data(employees, target_date)
        deductible_time_off_types = self.env['hr.leave.type'].search([
            ('overtime_deductible', '=', True),
            ('requires_allocation', '=', 'no')])
        leave_type_names = deductible_time_off_types.mapped('name')
        for employee in res:
            for leave_data in res[employee]:
                if leave_data[0] in leave_type_names:
                    leave_data[1]['virtual_remaining_leaves'] = employee.sudo().total_overtime
                    leave_data[1]['overtime_deductible'] = True
                else:
                    leave_data[1]['overtime_deductible'] = False
        return res
