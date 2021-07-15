# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, SUPERUSER_ID

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
    company_id = fields.Many2one('res.company', readonly=True)
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),  # YTI This state seems to be unused. To remove
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_report_calendar')
        self._cr.execute("""CREATE OR REPLACE VIEW hr_leave_report_calendar AS
        (SELECT 
            row_number() OVER() AS id,
            CONCAT(em.name, ': ', hl.duration_display) AS name,
            hl.date_from AS start_datetime,
            hl.date_to AS stop_datetime,
            hl.employee_id AS employee_id,
            hl.state AS state,
            em.company_id AS company_id,
            CASE
                WHEN hl.holiday_type = 'employee' THEN rr.tz
                ELSE %s
            END AS tz
        FROM hr_leave hl
            LEFT JOIN hr_employee em
                ON em.id = hl.employee_id
            LEFT JOIN resource_resource rr
                ON rr.id = em.resource_id
        WHERE 
            hl.state IN ('confirm', 'validate', 'validate1')
        ORDER BY id);
        """, [self.env.company.resource_calendar_id.tz or self.env.user.tz or 'UTC'])

    def _read(self, fields):
        res = super()._read(fields)
        if self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
            name_field = self._fields['name']
            for record in self.with_user(SUPERUSER_ID):
                self.env.cache.set(record, name_field, record.name.split(':')[-1].strip())
        return res

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        # Checking the calendar directly allows to not grey out the leaves taken
        # by the employee
        return self.env['hr.leave'].get_unusual_days(date_from, date_to=date_to)
