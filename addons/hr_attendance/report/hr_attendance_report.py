from odoo import api, fields, models, tools


class HRAttendanceReport(models.Model):
    _name = "hr.attendance.report"
    _description = "Attendance Statistics"
    _auto = False

    department_id = fields.Many2one('hr.department', string="Department", readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    check_in = fields.Datetime("Check In", readonly=True)
    worked_hours = fields.Float("Worked Hours", readonly=True)
    extra_hours = fields.Float("Extra Hours", readonly=True)

    def init(self):
        """
        In DB, extra_hours is the same for all attendances of a same day.
        In the query below, extra_hours value is limited to 1 attendance by day.
        Thus reporting extra_hours per attendance is not relevant since many of them will show 0. It should always
        be at least by day.
        It has been done like this in order to avoid inconsistencies while grouping records.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                (
                    SELECT
                        hra.id AS id,
                        department_id,
                        hra.employee_id AS employee_id,
                        hra.check_in AS check_in,
                        hra.worked_hours AS worked_hours,
                        CASE WHEN ROW_NUMBER() OVER (
                            PARTITION BY employee_id, date_trunc('day', hra.check_in)) = 1 THEN hra.extra_hours ELSE 0 END AS extra_hours
                    FROM
                        hr_attendance hra
                    LEFT JOIN
                        (SELECT id, department_id
                         FROM hr_employee) employee ON employee.id = hra.employee_id
                )
            )
        """ % (self._table))
