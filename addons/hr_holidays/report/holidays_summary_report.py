# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class HrHolidaySummaryReport(osv.AbstractModel):
    _name = 'report.hr_holidays.report_holidayssummary'

    def _get_header_info(self, start_date, holiday_type):
        return {
            'start_date': datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y-%m-%d'),
            'end_date': (datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=59)).strftime('%Y-%m-%d'),
            'holiday_type': 'Confirmed and Approved' if holiday_type == 'both' else holiday_type
        }

    def _get_day(self, start_date):
        res = []
        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        for x in range(0, 60):
            color = '#ababab' if start_date.strftime('%a') == 'Sat' or start_date.strftime('%a') == 'Sun' else ''
            res.append({'day_str': start_date.strftime('%a'), 'day': start_date.day , 'color': color})
            start_date = start_date + relativedelta(days=1)
        return res

    def _get_months(self, start_date):
        # it works for geting month name between two dates.
        res = []
        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = start_date + relativedelta(days=59)
        while start_date <= end_date:
            last_date = start_date + relativedelta(day=1, months=+1, days=-1)
            if last_date > end_date:
                last_date = end_date
            month_days = (last_date - start_date).days + 1
            res.append({'month_name': start_date.strftime('%B'), 'days': month_days})
            start_date += relativedelta(day=1, months=+1)
        return res

    def _get_leaves_summary(self, cr, uid, ids, start_date, empid, holiday_type, context=None):
        res = []
        count = 0
        start_date = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
        end_date = start_date + relativedelta(days=59)
        for index in range(0, 60):
            current = start_date + timedelta(index)
            res.append({'day': current.day, 'color': ''})
            if current.strftime('%a') == 'Sat' or current.strftime('%a') == 'Sun':
                res[index]['color'] = '#ababab'
        # count and get leave summary details.
        holidays_obj = self.pool['hr.holidays']
        holiday_type = ['confirm','validate'] if holiday_type == 'both' else ['confirm'] if holiday_type == 'Confirmed' else ['validate']
        holidays_ids = holidays_obj.search(cr, uid, [('employee_id', '=', empid), ('state', 'in', holiday_type), ('type', '=', 'remove'), ('date_from', '<=', str(end_date)), ('date_to', '>=', str(start_date))], context=context)
        for holiday in holidays_obj.browse(cr, uid, holidays_ids, context=context):
            date_from = datetime.strptime(holiday.date_from, DEFAULT_SERVER_DATETIME_FORMAT)
            date_to = datetime.strptime(holiday.date_to, DEFAULT_SERVER_DATETIME_FORMAT)
            for index in range(0, ((date_to - date_from).days + 1)):
                if date_from >= start_date and date_from <= end_date:
                    res[(date_from-start_date).days]['color'] = holiday.holiday_status_id.color_name
                    count+=1
                date_from += timedelta(1)
        self.sum = count
        return res

    def _get_data_from_report(self, cr, uid, ids, data, context=None):
        res = []
        emp_obj = self.pool['hr.employee']
        department_obj = self.pool['hr.department']
        if 'depts' in data:
            for department in department_obj.browse(cr, uid, data['depts'], context=context):
                res.append({'dept' : department.name, 'data': [], 'color': self._get_day(data['date_from'])})
                employee_ids = emp_obj.search(cr, uid, [('department_id', '=', department.id)], context=context)
                employees = emp_obj.browse(cr, uid, employee_ids, context=context)
                for emp in employees:
                    res[len(res)-1]['data'].append({
                        'emp': emp.name,
                        'display': self._get_leaves_summary(cr, uid, ids, data['date_from'], emp.id, data['holiday_type'], context=context),
                        'sum': self.sum
                    })
        elif 'emp' in data:
            employees = emp_obj.browse(cr, uid, data['emp'], context=context)
            res.append({'data':[]})
            for emp in employees:
                res[0]['data'].append({
                    'emp': emp.name,
                    'display': self._get_leaves_summary(cr, uid, ids, data['date_from'], emp.id, data['holiday_type'], context=context),
                    'sum': self.sum
                })
        return res

    def _get_holidays_status(self, cr, uid, ids, context=None):
        res = []
        holiday_obj = self.pool['hr.holidays.status']
        holiday_ids = holiday_obj.search(cr, uid, [], context=context)
        holiday_datas = holiday_obj.browse(cr, uid, holiday_ids, context=context)
        for holiday in holiday_datas:
            res.append({'color': holiday.color_name, 'name': holiday.name})
        return res

    def render_html(self, cr, uid, ids, data=None, context=None):
        report_obj = self.pool['report']
        holidays_report = report_obj._get_report_from_name(cr, uid, 'hr_holidays.report_holidayssummary')
        selected_records = self.pool['hr.holidays'].browse(cr, uid, ids, context=context)
        docargs = {
            'doc_ids': ids,
            'doc_model': holidays_report.model,
            'docs': selected_records,
            'get_header_info': self._get_header_info(data['form']['date_from'], data['form']['holiday_type']),
            'get_day': self._get_day(data['form']['date_from']),
            'get_months': self._get_months(data['form']['date_from']),
            'get_data_from_report': self._get_data_from_report(cr, uid, ids, data['form'], context=context),
            'get_holidays_status': self._get_holidays_status(cr, uid, ids, context=context),
        }
        return report_obj.render(cr, uid, ids, 'hr_holidays.report_holidayssummary', docargs, context=context)