# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

from odoo.addons.base.models.res_partner import _tz_get


class LeaveReportCalendar(models.Model):
    _name = "hr.leave.report.calendar"
    _description = 'Time Off Calendar'
    _auto = False
    _order = "start_datetime DESC, employee_id"

    name = fields.Char(string='Name', readonly=True)
    start_datetime = fields.Datetime(string='From', readonly=True)
    stop_datetime = fields.Datetime(string='To', readonly=True)
    tz = fields.Selection(_tz_get, string="Timezone", readonly=True)
    duration = fields.Float(string='Duration', readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    state = fields.Selection([
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], readonly=True)
    description = fields.Char("Description", readonly=True, groups='hr_holidays.group_hr_holidays_user')
    holiday_status_id = fields.Many2one('hr.leave.type', readonly=True, string="Time Off Type")

    is_hatched = fields.Boolean('Hatched', readonly=True)
    is_striked = fields.Boolean('Striked', readonly=True)

    is_absent = fields.Boolean(related='employee_id.is_absent')
    leave_manager_id = fields.Many2one(related='employee_id.leave_manager_id')
    leave_id = fields.Many2one(comodel_name='hr.leave', readonly=True)
    is_manager = fields.Boolean("Manager", compute="_compute_is_manager")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_report_calendar')
        self._cr.execute("""CREATE OR REPLACE VIEW hr_leave_report_calendar AS
        (SELECT
            hl.id AS id,
            hl.id AS leave_id,
            CONCAT(em.name, ': ', hl.duration_display) AS name,
            hl.date_from AS start_datetime,
            hl.date_to AS stop_datetime,
            hl.employee_id AS employee_id,
            hl.state AS state,
            hl.department_id AS department_id,
            hl.number_of_days as duration,
            hl.private_name AS description,
            hl.holiday_status_id AS holiday_status_id,
            em.company_id AS company_id,
            em.job_id AS job_id,
            COALESCE(
                rr.tz,
                rc.tz,
                cc.tz,
                'UTC'
            ) AS tz,
            hl.state = 'refuse' as is_striked,
            hl.state not in ('validate', 'refuse') as is_hatched
        FROM hr_leave hl
            LEFT JOIN hr_employee em
                ON em.id = hl.employee_id
            LEFT JOIN resource_resource rr
                ON rr.id = em.resource_id
            LEFT JOIN resource_calendar rc
                ON rc.id = em.resource_calendar_id
            LEFT JOIN res_company co
                ON co.id = em.company_id
            LEFT JOIN resource_calendar cc
                ON cc.id = co.resource_calendar_id
        WHERE
            hl.state IN ('confirm', 'validate', 'validate1', 'refuse')
        );
        """)

    def _compute_display_name(self):
        if self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
            for record in self:
                record.display_name = record.name.removeprefix(f"{record.employee_id.name}: ")
        else:
            super()._compute_display_name()

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    @api.depends('leave_manager_id')
    def _compute_is_manager(self):
        for leave in self:
            leave.is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or leave.leave_manager_id == self.env.user

    def action_approve(self):
        self.leave_id.action_approve(check_state=False)

    def action_validate(self):
        self.leave_id.action_validate()

    def action_refuse(self):
        self.leave_id.action_refuse()
