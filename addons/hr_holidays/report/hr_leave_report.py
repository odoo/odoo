# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, tools
from odoo.tools import SQL


class HrLeaveReport(models.Model):
    _name = 'hr.leave.report'
    _description = 'Time Off Summary / Report'
    _inherit = ["hr.manager.department.report"]
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
    work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Time Type", readonly=True)
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
        tools.drop_view_if_exists(self.env.cr, 'hr_leave_report')

        self.env.cr.execute(SQL("""
            CREATE OR REPLACE VIEW hr_leave_report AS (%(query)s);""", query=self._query()))

    def _query(self):
        select_columns = SQL(",\n").join(map(SQL, self._select()))
        return SQL("""
            SELECT
                %(columns)s
            FROM (
                %(union_queries)s
            ) leaves
        """, columns=select_columns, union_queries=self._get_union_queries())

    def _select(self):
        return [
            "row_number() over(ORDER BY leaves.employee_id) as id",
            "leaves.leave_id as leave_id",
            "leaves.allocation_id as allocation_id",
            "leaves.employee_id as employee_id",
            "leaves.name as name",
            "leaves.number_of_days as number_of_days",
            "leaves.leave_type as leave_type",
            "leaves.number_of_hours as number_of_hours",
            "leaves.department_id as department_id",
            "leaves.work_entry_type_id as work_entry_type_id",
            "leaves.state as state",
            "leaves.date_from as date_from",
            "leaves.date_to as date_to",
            "leaves.company_id as company_id",
        ]

    def _get_union_queries(self):
        leave_allocation_columns = SQL(",\n").join(map(SQL, self._leave_allocation_select_query()))
        leave_request_columns = SQL(",\n").join(map(SQL, self._leave_request_select_query()))

        return SQL("""
            SELECT
                %(allocation_columns)s
            FROM hr_leave_allocation as allocation
            INNER JOIN hr_employee as employee on (allocation.employee_id = employee.id)
            LEFT JOIN hr_version v ON v.id = employee.current_version_id
            WHERE employee.active IS True
            UNION ALL SELECT
                %(request_columns)s
            FROM hr_leave as request
            INNER JOIN hr_employee as employee on (request.employee_id = employee.id)
            LEFT JOIN hr_version v ON v.id = employee.current_version_id
            WHERE employee.active IS True
        """, allocation_columns=leave_allocation_columns, request_columns=leave_request_columns)

    def _leave_allocation_select_query(self):
        return [
            "NULL AS leave_id",
            "allocation.id AS allocation_id",
            "allocation.employee_id AS employee_id",
            "allocation.name AS name",
            "allocation.number_of_days AS number_of_days",
            "allocation.number_of_hours_display AS number_of_hours",
            "v.department_id AS department_id",
            "allocation.work_entry_type_id AS work_entry_type_id",
            "allocation.state AS state",
            "allocation.date_from AS date_from",
            "allocation.date_to AS date_to",
            "'allocation' AS leave_type",
            "allocation.employee_company_id AS company_id",
        ]

    def _leave_request_select_query(self):
        return [
            "request.id AS leave_id",
            "NULL AS allocation_id",
            "request.employee_id AS employee_id",
            "request.private_name AS name",
            "(request.number_of_days * -1) AS number_of_days",
            "(request.number_of_hours * -1) AS number_of_hours",
            "v.department_id AS department_id",
            "request.work_entry_type_id AS work_entry_type_id",
            "request.state AS state",
            "request.date_from AS date_from",
            "request.date_to AS date_to",
            "'request' AS leave_type",
            "request.employee_company_id AS company_id",
        ]

    def action_open_record(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.leave_id.id if self.leave_id else self.allocation_id.id,
            'res_model': 'hr.leave' if self.leave_id else 'hr.leave.allocation',
        }
