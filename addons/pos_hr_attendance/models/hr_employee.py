from odoo import api, models
from odoo.exceptions import AccessError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_pos_attendance_states(self, employee_ids):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(self.env._("Only Point of Sale users can read attendance states."))
        employees = self.sudo().browse(employee_ids).exists()
        return {employee.id: employee.attendance_state for employee in employees}
