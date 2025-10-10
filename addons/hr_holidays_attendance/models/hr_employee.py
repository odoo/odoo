# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.fields import Domain


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model
    def get_overtime_data(self, domain=None, employee_id=None):
        overtime_data = super().get_overtime_data(domain, employee_id)
        domain = [] if domain is None else domain

        # Given domain will use attendance fields
        # We have to convert the dates to the allocation's fields name
        def attendance_to_allocation_domain(d):
            if d[0] == 'check_in':
                return ['date_from', *d[1:]]
            elif d[0] == 'check_out':
                return ['date_to', *d[1:]]
            else:
                return d

        domain = [attendance_to_allocation_domain(d) for d in domain]

        combined_domain = Domain.AND(
            [
                domain,
                [
                    ('holiday_status_id.overtime_deductible', '=', True),
                    ('state', '=', 'confirm'),
                ],
            ]
        )
        overtime_adjustments = {
            allocation[0].id: allocation[1]
            for allocation in self.env["hr.leave.allocation"]._read_group(
                domain=combined_domain,
                groupby=['employee_id'],
                aggregates=['number_of_hours_display:sum']
            )
        }
        overtime_data.update({
            'overtime_adjustments': overtime_adjustments
        })
        return overtime_data
