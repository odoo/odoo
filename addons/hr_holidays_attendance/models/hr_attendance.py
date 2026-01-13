from odoo import models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_attendance_check_in_check_out_employee_id ON hr_attendance (check_in, check_out, employee_id);
        """)
