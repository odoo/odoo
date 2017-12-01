# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.exceptions import UserError


class HrTimesheetSheet(models.Model):
    _inherit = "hr_timesheet_sheet.sheet"

    attendances_ids = fields.One2many('hr.attendance', 'sheet_id', 'Attendances')
    total_attendance = fields.Float(string='Total Attendance', compute='_compute_total')
    total_timesheet = fields.Float(string='Total Timesheet', compute="_compute_total")
    total_difference = fields.Float(string='Difference', compute="_compute_total")
    period_ids = fields.One2many('hr_timesheet_sheet.sheet.day', 'sheet_id', string='Period', readonly=True)
    attendance_count = fields.Integer(compute='_compute_attendances', string="Attendances")

    @api.depends('period_ids.total_attendance', 'period_ids.total_timesheet', 'period_ids.total_difference')
    def _compute_total(self):
        """ Compute the attendances, analytic lines timesheets and differences
            between them for all the days of a timesheet and the current day
        """
        if len(self.ids) == 0:
            return

        self.env.cr.execute("""
            SELECT sheet_id as id,
                   sum(total_attendance) as total_attendance,
                   sum(total_timesheet) as total_timesheet,
                   sum(total_difference) as  total_difference
            FROM hr_timesheet_sheet_sheet_day
            WHERE sheet_id IN %s
            GROUP BY sheet_id
        """, (tuple(self.ids), ))

        for x in self.env.cr.dictfetchall():
            sheet = self.browse(x.pop('id'))
            sheet.total_attendance = x.pop('total_attendance')
            sheet.total_timesheet = x.pop('total_timesheet')
            sheet.total_difference = x.pop('total_difference')

    @api.depends('attendances_ids')
    def _compute_attendances(self):
        for sheet in self:
            sheet.attendance_count = len(sheet.attendances_ids)

    @api.multi
    def unlink(self):
        sheets = self.read(['total_attendance'])
        for sheet in sheets:
            if sheet['total_attendance'] > 0.00:
                raise UserError(_('You cannot delete a timesheet that has attendance entries.'))
        return super(HrTimesheetSheet, self).unlink()

    @api.multi
    def action_sheet_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'HR Timesheet/Attendance Report',
            'res_model': 'hr.timesheet.attendance.report',
            'domain': [('date', '>=', self.date_from), ('date', '<=', self.date_to)],
            'view_mode': 'pivot',
            'context': {'search_default_user_id': self.user_id.id, }
        }

    @api.multi
    def action_timesheet_confirm(self):
        for sheet in self:
            sheet.check_employee_attendance_state()
            di = sheet.user_id.company_id.timesheet_max_difference
            if (abs(sheet.total_difference) <= di) or not di:
                return super(HrTimesheetSheet, self).action_timesheet_confirm()
            else:
                raise UserError(_('Please verify that the total difference of the sheet is lower than %.2f.') % (di,))

    @api.multi
    def check_employee_attendance_state(self):
        """ Checks the attendance records of the timesheet, make sure they are all closed
            (by making sure they have a check_out time)
        """
        self.ensure_one()
        if any(self.attendances_ids.filtered(lambda r: not r.check_out)):
            raise UserError(_("The timesheet cannot be validated as it contains an attendance record with no Check Out)."))
        return True


class hr_timesheet_sheet_sheet_day(models.Model):
    _name = "hr_timesheet_sheet.sheet.day"
    _description = "Timesheets by Period"
    _auto = False
    _order = 'name'

    name = fields.Date('Date', readonly=True)
    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet', 'Sheet', readonly=True, index=True)
    total_timesheet = fields.Float('Total Timesheet', readonly=True)
    total_attendance = fields.Float('Attendance', readonly=True)
    total_difference = fields.Float('Difference', readonly=True)

    _depends = {
        'account.analytic.line': ['date', 'unit_amount'],
        'hr.attendance': ['check_in', 'check_out', 'sheet_id'],
        'hr_timesheet_sheet.sheet': ['attendances_ids', 'timesheet_ids'],
    }

    @api.model_cr
    def init(self):
        self._cr.execute("""create or replace view %s as
            SELECT
                id,
                name,
                sheet_id,
                total_timesheet,
                total_attendance,
                cast(round(cast(total_attendance - total_timesheet as Numeric),2) as Double Precision) AS total_difference
            FROM
                ((
                    SELECT
                        MAX(id) as id,
                        name,
                        sheet_id,
                        timezone,
                        SUM(total_timesheet) as total_timesheet,
                        SUM(total_attendance) /60 as total_attendance
                    FROM
                        ((
                            select
                                min(l.id) as id,
                                p.tz as timezone,
                                l.date::date as name,
                                s.id as sheet_id,
                                sum(l.unit_amount) as total_timesheet,
                                0.0 as total_attendance
                            from
                                account_analytic_line l
                                LEFT JOIN hr_timesheet_sheet_sheet s ON s.id = l.sheet_id
                                JOIN hr_employee e ON s.employee_id = e.id
                                JOIN resource_resource r ON e.resource_id = r.id
                                LEFT JOIN res_users u ON r.user_id = u.id
                                LEFT JOIN res_partner p ON u.partner_id = p.id
                            group by l.date::date, s.id, timezone
                        ) union (
                            select
                                -min(a.id) as id,
                                p.tz as timezone,
                                (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))::date as name,
                                s.id as sheet_id,
                                0.0 as total_timesheet,
                                SUM(DATE_PART('day', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                      - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) ) * 60 * 24
                                    + DATE_PART('hour', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                         - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) ) * 60
                                    + DATE_PART('minute', (a.check_out AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
                                                           - (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')) )) as total_attendance
                            from
                                hr_attendance a
                                LEFT JOIN hr_timesheet_sheet_sheet s
                                ON s.id = a.sheet_id
                                JOIN hr_employee e
                                ON a.employee_id = e.id
                                JOIN resource_resource r
                                ON e.resource_id = r.id
                                LEFT JOIN res_users u
                                ON r.user_id = u.id
                                LEFT JOIN res_partner p
                                ON u.partner_id = p.id
                            WHERE a.check_out IS NOT NULL
                            group by (a.check_in AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))::date, s.id, timezone
                        )) AS foo
                        GROUP BY name, sheet_id, timezone
                )) AS bar""" % self._table)
