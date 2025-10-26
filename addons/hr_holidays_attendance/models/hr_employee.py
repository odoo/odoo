# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def get_overtime_data(self, domain=None, employee_id=None):
        overtime_data = super().get_overtime_data(domain, employee_id)
        allocation_domain = [
            ('holiday_status_id.overtime_deductible', '=', True),
            ('state', '=', 'confirm'),
        ]
        if employee_id:
            allocation_domain.append(('employee_id', '=', employee_id))
        overtime_adjustments = {
            allocation[0].id: allocation[1]
            for allocation in self.env["hr.leave.allocation"]._read_group(
                domain=allocation_domain,
                groupby=['employee_id'],
                aggregates=['number_of_hours_display:sum']
            )
        }
        overtime_data.update({
            'overtime_adjustments': overtime_adjustments
        })
        return overtime_data
