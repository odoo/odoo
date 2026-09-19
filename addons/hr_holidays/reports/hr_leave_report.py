from odoo import fields, models
from odoo.db.schema import drop_view_if_exists


class HrLeaveReport(models.Model):
    _name = "hr.leave.report"
    _description = "Time Off Summary / Report"
    _inherit = ["mixin.hr.manager.department.report"]
    _auto = False
    _order = "date_from DESC, employee_id"

    leave_id = fields.Many2one(
        comodel_name="hr.leave",
        string="Time Off Request",
        readonly=True,
    )
    allocation_id = fields.Many2one(
        comodel_name="hr.leave.allocation",
        string="Allocation Request",
        readonly=True,
    )
    name = fields.Char(
        string="Description",
        readonly=True,
        groups="hr_holidays.group_hr_holidays_user",
        help="A request's description is its private_name, which hr.leave "
        "itself masks as ***** for anyone but an officer, the employee or "
        "their approver. This view reads that column straight, so the field "
        "carries the restriction the view cannot.",
    )
    number_of_days = fields.Float(
        string="Number of Days",
        readonly=True,
    )
    number_of_hours = fields.Float(
        string="Number of Hours",
        readonly=True,
    )
    leave_type = fields.Selection(
        selection=[("allocation", "Allocation"), ("request", "Time Off")],
        string="Request Type",
        readonly=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        readonly=True,
    )
    holiday_status_id = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Time Off Type",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("cancel", "Cancelled"),
            ("confirm", "To Approve"),
            ("refuse", "Refused"),
            ("validate1", "Second Approval"),
            ("validate", "Approved"),
        ],
        string="Status",
        readonly=True,
    )
    date_from = fields.Datetime(
        string="Start Date",
        readonly=True,
    )
    date_to = fields.Datetime(
        string="End Date",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )

    def init(self):
        drop_view_if_exists(self.env.cr, "hr_leave_report")

        self.env.cr.execute("""
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
                    v.department_id as department_id,
                    allocation.holiday_status_id as holiday_status_id,
                    allocation.state as state,
                    allocation.date_from as date_from,
                    allocation.date_to as date_to,
                    'allocation' as leave_type,
                    employee.company_id as company_id
                from hr_leave_allocation as allocation
                inner join hr_employee as employee on (allocation.employee_id = employee.id)
                LEFT JOIN hr_version v ON v.id = employee.current_version_id
                where employee.active IS True
                union all select
                    -- UNION ALL binds branches by POSITION, and the derived
                    -- table takes its column names from the first branch, so
                    -- these two must stay in the first branch's order.  When
                    -- they were swapped, every request row filed its hr.leave
                    -- id under allocation_id and left leave_id null, which sent
                    -- action_view_record to an unrelated allocation form.
                    request.id as leave_id,
                    null as allocation_id,
                    request.employee_id as employee_id,
                    request.private_name as name,
                    (request.number_of_days * -1) as number_of_days,
                    (request.number_of_hours * -1) as number_of_hours,
                    v.department_id as department_id,
                    request.holiday_status_id as holiday_status_id,
                    request.state as state,
                    request.date_from as date_from,
                    request.date_to as date_to,
                    'request' as leave_type,
                    employee.company_id as company_id
                from hr_leave as request
                inner join hr_employee as employee on (request.employee_id = employee.id)
                LEFT JOIN hr_version v ON v.id = employee.current_version_id
                where employee.active IS True
                ) leaves
            );
        """)

    def action_view_record(self):
        self.check_singleton()

        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_id": self.leave_id.id if self.leave_id else self.allocation_id.id,
            "res_model": "hr.leave" if self.leave_id else "hr.leave.allocation",
        }
