import time

from odoo import fields, models


class HrHolidaysSummaryEmployee(models.TransientModel):
    _name = "hr.holidays.summary.employee"

    _description = "HR Time Off Summary Report By Employee"

    date_from = fields.Date(
        string="From",
        default=lambda *a: time.strftime("%Y-%m-01"),
        required=True,
    )
    emp = fields.Many2many(
        comodel_name="hr.employee",
        relation="summary_emp_rel",
        column1="sum_id",
        column2="emp_id",
        string="Employee(s)",
    )
    holiday_type = fields.Selection(
        selection=[
            ("Approved", "Approved"),
            ("Confirmed", "Confirmed"),
            ("both", "Both Approved and Confirmed"),
        ],
        string="Select Time Off Type",
        default="Approved",
        required=True,
    )

    def print_report(self):
        self.check_singleton()
        [data] = self.read()
        data["emp"] = self.emp.ids or self.env.context.get("active_ids", [])
        employees = self.env["hr.employee"].browse(data["emp"])
        datas = {"ids": [], "model": "hr.employee", "form": data}
        return self.env.ref("hr_holidays.action_report_holidayssummary").report_action(
            employees, data=datas
        )
