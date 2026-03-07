from odoo import fields, models,api

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    x_late_minutes = fields.Float(
        string='Late Minutes',
        help='Minutes late compared to scheduled start (after grace period)')

    x_early_leave_minutes = fields.Float(
        string='Early Leave Minutes',
        help='Minutes left early compared to scheduled end (after grace period)')

    x_is_absent = fields.Boolean(
        string='Is Absent',
        default=False,
        readonly=True,
        help='Indicates if the employee is considered absent for this attendance record'
    )

    x_day_of_week = fields.Char(
        string="Day",
        compute='_compute_day_of_week',
        store=True,
    )

    @api.depends('check_in')
    def _compute_day_of_week(self):
        for record in self:
            if record.check_in:
                record.x_day_of_week = record.check_in.strftime('%A')
            else:
                record.x_day_of_week = False