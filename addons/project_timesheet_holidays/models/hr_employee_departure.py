from odoo import models


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    def action_register(self):
        self._get_future_timesheets().write({
            'holiday_id': False,
            'global_leave_id': False,
        })
        return super().action_register()
