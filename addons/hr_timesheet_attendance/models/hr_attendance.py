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

    sheet_id_computed = fields.Many2one('hr_timesheet_sheet.sheet', string='Sheet', compute='_compute_sheet', index=True, ondelete='cascade',
        search='_search_sheet')
    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet', compute='_compute_sheet', string='Sheet', store=True)

    @api.depends('employee_id', 'check_in', 'check_out', 'sheet_id_computed.date_to', 'sheet_id_computed.date_from', 'sheet_id_computed.employee_id')
    def _compute_sheet(self):
        """Links the attendance to the corresponding sheet
        """
        for attendance in self:
            corresponding_sheet = self.env['hr_timesheet_sheet.sheet'].search(
                [('date_to', '>=', attendance.check_in), ('date_from', '<=', attendance.check_in),
                 ('employee_id', '=', attendance.employee_id.id),
                 ('state', 'in', ['draft', 'new'])], limit=1)
            if corresponding_sheet:
                attendance.sheet_id_computed = corresponding_sheet[0]
                attendance.sheet_id = corresponding_sheet[0]

    def _search_sheet(self, operator, value):
        assert operator == 'in'
        ids = []
        for ts in self.env['hr_timesheet_sheet.sheet'].browse(value):
            self._cr.execute("""
                    SELECT a.id
                        FROM hr_attendance a
                    WHERE %(date_to)s >= a.check_in
                        AND %(date_from)s <= a.check_in
                        AND %(employee_id)s = a.employee_id
                    GROUP BY a.id""", {'date_from': ts.date_from,
                                       'date_to': ts.date_to,
                                       'employee_id': ts.employee_id.id, })
            ids.extend([row[0] for row in self._cr.fetchall()])
        return [('id', 'in', ids)]

    def _get_attendance_employee_tz(self, employee_id, date):
        """ Simulate timesheet in employee timezone

        Return the attendance date in string format in the employee
        tz converted from utc timezone as we consider date of employee
        timesheet is in employee timezone
        """
        tz = False
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
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

    @api.model
    def create(self, vals):
        if self.env.context.get('sheet_id'):
            sheet = self.env['hr_timesheet_sheet.sheet'].browse(self.env.context.get('sheet_id'))
        else:
            sheet = self._get_current_sheet(vals.get('employee_id'), vals.get('check_in'))
        if sheet:
            att_tz_date_str = self._get_attendance_employee_tz(vals.get('employee_id'), date=vals.get('check_in'))
            if sheet.state not in ('draft', 'new'):
                raise UserError(_('You can not enter an attendance in a submitted timesheet. Ask your manager to reset it before adding attendance.'))
            elif sheet.date_from > att_tz_date_str or sheet.date_to < att_tz_date_str:
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
