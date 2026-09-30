from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _compute_presence_icon(self):
        super()._compute_presence_icon()
        dayfield = self._get_current_day_location_field()
        for employee in self:
            today_employee_location_id = employee.sudo().exceptional_location_id or employee[dayfield]
            if employee.is_absent:
                employee.hr_icon_display = f'presence_holiday_{"absent" if employee.hr_presence_state != "present" else "present"}'
                employee.show_hr_icon_display = True
            elif today_employee_location_id:
                employee.hr_icon_display = f'presence_{today_employee_location_id.location_type}'
                employee.show_hr_icon_display = True
