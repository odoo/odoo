# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from pytz import timezone
import pytz

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet', compute='_compute_sheet', string='Sheet', store=True)

    # Same problem as in account.analytic.line for dependance, need to define a search function.
    # No need to migrate correctly, hr.attendance will be removed from this module anyways.

    # def _get_hr_timesheet_sheet(self, cr, uid, ids, context=None):
    #     attendance_ids = []
    #     for ts in self.browse(cr, uid, ids, context=context):
    #         cr.execute("""
    #                     SELECT a.id
    #                       FROM hr_attendance a
    #                      INNER JOIN hr_employee e
    #                            INNER JOIN resource_resource r
    #                                    ON (e.resource_id = r.id)
    #                         ON (a.employee_id = e.id)
    #                      LEFT JOIN res_users u
    #                      ON r.user_id = u.id
    #                      LEFT JOIN res_partner p
    #                      ON u.partner_id = p.id
    #                      WHERE %(date_to)s >= date_trunc('day', a.name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
    #                           AND %(date_from)s <= date_trunc('day', a.name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))
    #                           AND %(user_id)s = r.user_id
    #                      GROUP BY a.id""", {'date_from': ts.date_from,
    #                                         'date_to': ts.date_to,
    #                                         'user_id': ts.employee_id.user_id.id,})
    #         attendance_ids.extend([row[0] for row in cr.fetchall()])
    #     return attendance_ids

    def _get_attendance_employee_tz(self, employee_id, date):
        """ Simulate timesheet in employee timezone

        Return the attendance date in string format in the employee
        tz converted from utc timezone as we consider date of employee
        timesheet is in employee timezone
        """
        employee_obj = self.env['hr.employee']

        tz = False
        if employee_id:
            employee = employee_obj.browse(employee_id)
            tz = employee.user_id.partner_id.tz

        if not date:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        att_tz = timezone(tz or 'utc')

        attendance_dt = datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)
        att_tz_dt = pytz.utc.localize(attendance_dt)
        att_tz_dt = att_tz_dt.astimezone(att_tz)
        # We take only the date omiting the hours as we compare with timesheet
        # date_from which is a date format thus using hours would lead to
        # be out of scope of timesheet
        att_tz_date_str = datetime.strftime(att_tz_dt, DEFAULT_SERVER_DATE_FORMAT)
        return att_tz_date_str

    def _get_current_sheet(self, employee_id, date=False):
        if not date:
            date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        att_tz_date_str = self._get_attendance_employee_tz(employee_id, date=date)
        sheet = self.env['hr_timesheet_sheet.sheet'].search(
            [('date_from', '<=', att_tz_date_str),
             ('date_to', '>=', att_tz_date_str),
             ('employee_id', '=', employee_id)], limit=1)
        return sheet or False

    @api.depends('employee_id', 'name', 'day', 'sheet_id.employee_id', 'sheet_id.date_from', 'sheet_id.date_to')
    def _compute_sheet(self, name, args):
        for attendance in self:
            attendance.sheet_id = self._get_current_sheet(attendance.employee_id.id, attendance.name)

    @api.model
    def create(self, vals):
        sheet_id = self.env.context.get('sheet_id') or self._get_current_sheet(vals.get('employee_id'), vals.get('name'))
        if sheet_id:
            att_tz_date_str = self._get_attendance_employee_tz(vals.get('employee_id'), date=vals.get('name'))
            ts = self.env['hr_timesheet_sheet.sheet'].browse(sheet_id)
            if ts.state not in ('draft', 'new'):
                raise UserError(_('You can not enter an attendance in a submitted timesheet. Ask your manager to reset it before adding attendance.'))
            elif ts.date_from > att_tz_date_str or ts.date_to < att_tz_date_str:
                raise UserError(_('You can not enter an attendance date outside the current timesheet dates.'))
        return super(HrAttendance, self).create(vals)

    @api.multi
    def unlink(self):
        self._check()
        return super(HrAttendance, self).unlink()

    @api.multi
    def write(self, vals):
        self._check()
        res = super(HrAttendance, self).write(vals)
        if 'sheet_id' in self.env.context:
            for attendance in self:
                if self.env.context['sheet_id'] != attendance.sheet_id.id:
                    raise UserError(_('You cannot enter an attendance date outside the current timesheet dates.'))
        return res

    def _check(self):
        for att in self:
            if att.sheet_id and att.sheet_id.state not in ('draft', 'new'):
                raise UserError(_('You cannot modify an entry in a confirmed timesheet'))
        return True
