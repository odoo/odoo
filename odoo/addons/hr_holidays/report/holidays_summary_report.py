# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.dates
import calendar

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date, get_lang

COLORS_MAP = {
    0: 'lightgrey',
    1: 'tomato',
    2: 'sandybrown',
    3: 'khaki',
    4: 'skyblue',
    5: 'dimgrey',
    6: 'lightcoral',
    7: 'steelblue',
    8: 'darkslateblue',
    9: 'crimson',
    10: 'mediumseagreen',
    11: 'mediumpurple',
}


class HrHolidaySummaryReport(models.AbstractModel):
    _name = 'report.hr_holidays.report_holidayssummary'
    _description = 'Holidays Summary Report'

    def _get_header_info(self, start_date, holiday_type):
        st_date = fields.Date.from_string(start_date)
        if holiday_type == 'Confirmed':
            holiday_type = _('Confirmed')
        elif holiday_type == 'Approved':
            holiday_type = _('Approved')
        else:
            holiday_type = _('Confirmed and Approved')
        return {
            'start_date': format_date(self.env, st_date),
            'end_date': format_date(self.env, st_date + relativedelta(days=59)),
            'holiday_type': holiday_type
        }

    def _date_is_day_off(self, date):
        return date.weekday() in (calendar.SATURDAY, calendar.SUNDAY,)

    def _get_day(self, start_date):
        res = []
        start_date = fields.Date.from_string(start_date)
        for x in range(0, 60):
            color = '#ababab' if self._date_is_day_off(start_date) else ''
            res.append({'day_str': babel.dates.get_day_names('abbreviated', locale=get_lang(self.env).code)[start_date.weekday()], 'day': start_date.day, 'color': color})
            start_date = start_date + relativedelta(days=1)
        return res

    def _get_months(self, start_date):
        # it works for geting month name between two dates.
        res = []
        start_date = fields.Date.from_string(start_date)
        end_date = start_date + relativedelta(days=59)
        while start_date <= end_date:
            last_date = start_date + relativedelta(day=1, months=+1, days=-1)
            if last_date > end_date:
                last_date = end_date
            month_days = (last_date - start_date).days + 1
            res.append({'month_name': babel.dates.get_month_names(locale=get_lang(self.env).code)[start_date.month], 'days': month_days})
            start_date += relativedelta(day=1, months=+1)
        return res

    def _get_leaves_summary(self, start_date, empid, holiday_type):
        res = []
        count = 0
        start_date = fields.Date.from_string(start_date)
        end_date = start_date + relativedelta(days=59)
        for index in range(0, 60):
            current = start_date + timedelta(index)
            res.append({'day': current.day, 'color': ''})
            if self._date_is_day_off(current) :
                res[index]['color'] = '#ababab'

        holidays = self._get_leaves(start_date, self.env['hr.employee'].browse(empid), holiday_type)

        for holiday in holidays:
            # Convert date to user timezone, otherwise the report will not be consistent with the
            # value displayed in the interface.
            date_from = fields.Datetime.from_string(holiday.date_from)
            date_from = fields.Datetime.context_timestamp(holiday, date_from).date()
            date_to = fields.Datetime.from_string(holiday.date_to)
            date_to = fields.Datetime.context_timestamp(holiday, date_to).date()
            for index in range(0, ((date_to - date_from).days + 1)):
                if date_from >= start_date and date_from <= end_date:
                    res[(date_from-start_date).days]['color'] = COLORS_MAP[holiday.holiday_status_id.color]
                date_from += timedelta(1)
            count += holiday.number_of_days
        employee = self.env['hr.employee'].browse(empid)
        return {'emp': employee.name, 'display': res, 'sum': count}

    def _get_employees(self, data):
        if 'depts' in data:
            return self.env['hr.employee'].search([('department_id', 'in', data['depts'])])
        elif 'emp' in data:
            return self.env['hr.employee'].browse(data['emp'])
        return self.env['hr.employee'].search([])

    def _get_data_from_report(self, data):
        res = []
        if 'depts' in data:
            employees = self._get_employees(data)
            departments = self.env['hr.department'].browse(data['depts'])
            for department in departments:
                res.append({
                    'dept': department.name,
                    'data': [
                        self._get_leaves_summary(data['date_from'], emp.id, data['holiday_type'])
                        for emp in employees.filtered(lambda emp: emp.department_id.id == department.id)
                    ],
                    'color': self._get_day(data['date_from']),
                })
        elif 'emp' in data:
            res.append({'data': [
                self._get_leaves_summary(data['date_from'], emp.id, data['holiday_type'])
                for emp in self._get_employees(data)
            ]})
        return res

    def _get_leaves(self, date_from, employees, holiday_type, date_to=None):
        state = ['confirm', 'validate'] if holiday_type == 'both' else ['confirm'] if holiday_type == 'Confirmed' else ['validate']

        if not date_to:
            date_to = date_from + relativedelta(days=59)

        return self.env['hr.leave'].search([
            ('employee_id', 'in', employees.ids),
            ('state', 'in', state),
            ('date_from', '<=', str(date_to)),
            ('date_to', '>=', str(date_from))
        ])

    def _get_holidays_status(self, data):
        res = []
        employees = self.env['hr.employee']
        if {'depts', 'emp'} & data.keys():
            employees = self._get_employees(data)

        holidays = self._get_leaves(fields.Date.from_string(data['date_from']), employees, data['holiday_type'])

        for leave_type in holidays.holiday_status_id:
            res.append({'color': COLORS_MAP[leave_type.color], 'name': leave_type.name})

        return res

    @api.model
    def _get_report_values(self, docids, data=None):

        holidays_report = self.env['ir.actions.report']._get_report_from_name('hr_holidays.report_holidayssummary')
        holidays = self.env['hr.leave'].browse(self.ids)
        if data and data.get('form'):
            return {
                'doc_ids': self.ids,
                'doc_model': holidays_report.model,
                'docs': holidays,
                'get_header_info': self._get_header_info(data['form']['date_from'], data['form']['holiday_type']),
                'get_day': self._get_day(data['form']['date_from']),
                'get_months': self._get_months(data['form']['date_from']),
                'get_data_from_report': self._get_data_from_report(data['form']),
                'get_holidays_status': self._get_holidays_status(data['form']),
            }

        return {
            'doc_ids': self.ids,
            'doc_model': holidays_report.model,
            'docs': holidays
        }
