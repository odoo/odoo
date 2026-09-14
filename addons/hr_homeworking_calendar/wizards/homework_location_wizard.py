from odoo import fields, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.hr_homeworking.models.hr_homeworking import DAYS

_debug = DebugLog(__name__)


class HomeworkLocationWizard(models.TransientModel):
    _name = "homework.location.wizard"
    _inherit = ["mixin.work.location.assignment"]
    _description = "Set Homework Location Wizard"

    weekly = fields.Boolean(default=False)

    def set_employee_location(self):
        self.check_singleton()
        if not self.date:
            _debug.logic("set_location_skipped", reason="no_date", wizard=self)
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
            _debug.lifecycle(
                "location_set",
                by="weekly",
                employee=employee_id,
                day=default_location_for_current_date,
                location=self.work_location_id,
                cleared_exception=employee_location,
            )
            if employee_location:
                employee_location.unlink()
            employee_id.sudo().write(
                {default_location_for_current_date: self.work_location_id.id}
            )
        elif (
            self.work_location_id.id
            == employee_id[default_location_for_current_date].id
        ):
            _debug.lifecycle(
                "location_set",
                by="matches_weekday_default",
                employee=employee_id,
                cleared_exception=employee_location,
            )
            employee_location.unlink()
        elif employee_location:
            _debug.lifecycle(
                "location_set",
                by="exception_updated",
                employee=employee_id,
                location=self.work_location_id,
            )
            employee_location.write({"work_location_id": self.work_location_id.id})
        else:
            _debug.lifecycle(
                "location_set",
                by="exception_created",
                employee=employee_id,
                location=self.work_location_id,
            )
            self.env["hr.employee.location"].create(
                {
                    "date": self.date,
                    "employee_id": employee_id.id,
                    "work_location_id": self.work_location_id.id,
                }
            )
