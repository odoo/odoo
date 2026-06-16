import pytz

from odoo import api, models


class BiometricScheduleHelperKSW(models.AbstractModel):
    _inherit = 'biometric.schedule.helper'

    @api.model
    def calculate_worked_time(self, check_in, check_out, employee):
        """For check-in-only employees, replace checkout with the scheduled
        end time so that no early-leave penalty is ever computed."""
        if employee and employee.x_check_in_only:
            emp_tz = self.get_employee_tz(employee)
            local_ci = pytz.utc.localize(check_in).astimezone(emp_tz)
            work_date = local_ci.date()
            schedule = self.get_employee_day_schedule(employee, work_date, emp_tz)
            if schedule:
                check_out = schedule['end'].astimezone(pytz.utc).replace(tzinfo=None)

        return super().calculate_worked_time(check_in, check_out, employee)
