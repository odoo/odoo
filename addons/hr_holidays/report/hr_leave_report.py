# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.osv import expression


class LeaveReport(models.Model):
    _name = "hr.leave.report"
    _description = 'Time Off Summary / Report'
    _inherit = "hr.manager.department.report"
    _auto = False
    _order = "date_from DESC, employee_id"

    leave_id = fields.Many2one('hr.leave', string="Time Off Request", readonly=True)
    allocation_id = fields.Many2one('hr.leave.allocation', string="Allocation Request", readonly=True)
    name = fields.Char('Description', readonly=True)
    number_of_days = fields.Float('Number of Days', readonly=True)
    number_of_hours = fields.Float('Number of Hours', readonly=True)
    leave_type = fields.Selection([
        ('allocation', 'Allocation'),
        ('request', 'Time Off')
        ], string='Request Type', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    holiday_status_id = fields.Many2one("hr.leave.type", string="Time Off Type", readonly=True)
    state = fields.Selection([
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True)
    date_from = fields.Datetime('Start Date', readonly=True)
    date_to = fields.Datetime('End Date', readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_report')

        self._cr.execute("""
            CREATE or REPLACE view hr_leave_report as (
                SELECT row_number() over(ORDER BY leaves.employee_id) as id,
                leaves.leave_id as leave_id,
                leaves.allocation_id as allocation_id,
                leaves.employee_id as employee_id, leaves.name as name,
                leaves.number_of_days as number_of_days, leaves.leave_type as leave_type,
                leaves.number_of_hours as number_of_hours,
                leaves.department_id as department_id,
                leaves.holiday_status_id as holiday_status_id, leaves.state as state,
                leaves.date_from as date_from,
                leaves.date_to as date_to, leaves.company_id
                from (select
                    null as leave_id,
                    allocation.id as allocation_id,
                    allocation.employee_id as employee_id,
                    allocation.name as name,
                    allocation.number_of_days as number_of_days,
                    allocation.number_of_hours_display as number_of_hours,
                    allocation.department_id as department_id,
                    allocation.holiday_status_id as holiday_status_id,
                    allocation.state as state,
                    allocation.date_from as date_from,
                    allocation.date_to as date_to,
                    'allocation' as leave_type,
                    allocation.employee_company_id as company_id
                from hr_leave_allocation as allocation
                inner join hr_employee as employee on (allocation.employee_id = employee.id)
                where employee.active IS True
                union all select
                    request.id as leave_id,
                    null as allocation_id,
                    request.employee_id as employee_id,
                    request.private_name as name,
                    (request.number_of_days * -1) as number_of_days,
                    (request.number_of_hours * -1) as number_of_hours,
                    request.department_id as department_id,
                    request.holiday_status_id as holiday_status_id,
                    request.state as state,
                    request.date_from as date_from,
                    request.date_to as date_to,
                    'request' as leave_type,
                    request.employee_company_id as company_id
                from hr_leave as request
                inner join hr_employee as employee on (request.employee_id = employee.id)
                where employee.active IS True
                ) leaves
            );
        """)

    def action_open_record(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.leave_id.id if self.leave_id else self.allocation_id.id,
            'res_model': 'hr.leave' if self.leave_id else 'hr.leave.allocation',
        }
