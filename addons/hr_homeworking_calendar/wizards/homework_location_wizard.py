from odoo import fields, models

from odoo.addons.hr_homeworking.models.hr_homeworking import DAYS


class HomeworkLocationWizard(models.TransientModel):
    _name = "homework.location.wizard"
    _inherit = ["mixin.work.location.assignment"]
    _description = "Set Homework Location Wizard"

    weekly = fields.Boolean(default=False)

    def set_employee_location(self):
        self.check_singleton()
        if not self.date:
            return
        default_employee_id = (
            self.env.context.get("default_employee_id") or self.env.user.employee_id.id
        )
        employee_id = self.env["hr.employee"].browse(
            self.employee_id.id or default_employee_id
        )
        employee_location = self.env["hr.employee.location"].search(
            [("date", "=", self.date), ("employee_id", "=", employee_id.id)]
        )
        weekday = self.date.weekday()
        default_location_for_current_date = DAYS[weekday]
        if self.weekly:
            if employee_location:
                employee_location.unlink()
            employee_id.sudo().write(
                {default_location_for_current_date: self.work_location_id.id}
            )
        elif (
            self.work_location_id.id
            == employee_id[default_location_for_current_date].id
        ):
            employee_location.unlink()
        elif employee_location:
            employee_location.write({"work_location_id": self.work_location_id.id})
        else:
            self.env["hr.employee.location"].create(
                {
                    "date": self.date,
                    "employee_id": employee_id.id,
                    "work_location_id": self.work_location_id.id,
                }
            )
