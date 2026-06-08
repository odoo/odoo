# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.misc import format_duration
from odoo import _, api, fields, models


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    overtime_deductible = fields.Boolean(
        "Deduct Extra Hours", default=False,
        help="Once a time off of this type is approved, extra hours in attendances will be deducted.")

    @api.depends('overtime_deductible', 'requires_allocation')
    @api.depends_context('request_type', 'leave', 'work_entry_type_display_name', 'employee_id')
    def _compute_display_name(self):
        # Exclude hours available in allocation contexts, it might be confusing otherwise
        if not self.requested_display_name() or self.env.context.get('request_type', 'leave') == 'allocation':
            return super()._compute_display_name()

        employee = self.env['hr.employee'].browse(self.env.context.get('employee_id')).sudo()
        unspent_overtime = employee._get_deductible_employee_overtime()[employee]
        if not unspent_overtime:
            return super()._compute_display_name()

        overtime_leaves = self.filtered(lambda l_type: l_type.overtime_deductible and not l_type.requires_allocation)
        for work_entry_type in overtime_leaves:
            work_entry_type.display_name = "%(name)s (%(count)s)" % {
                'name': work_entry_type.name,
                'count': _('%s hours available',
                    format_duration(unspent_overtime)),
            }
        super(HrWorkEntryType, self - overtime_leaves)._compute_display_name()

    def get_allocation_data(self, employees, target_date=None):
        res = super().get_allocation_data(employees, target_date)
        deductible_time_off_types = self.env['hr.work.entry.type'].search([
            ('overtime_deductible', '=', True),
            ('requires_allocation', '=', False)])
        work_entry_type_names = deductible_time_off_types.mapped('name')
        unspent_overtime = employees._get_deductible_employee_overtime()
        for employee in res:
            total_overtime = employee.sudo().total_overtime
            for leave_data in res[employee]:
                if leave_data[0] in work_entry_type_names:
                    leave_data[1]['virtual_remaining_leaves'] = unspent_overtime[employee]
                    leave_data[1]['max_leaves'] += total_overtime
                    leave_data[1]['remaining_leaves'] += total_overtime
                    leave_data[1]['overtime_deductible'] = True
                else:
                    leave_data[1]['overtime_deductible'] = False
        return res
