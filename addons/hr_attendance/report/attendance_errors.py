# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import time
from odoo import api, fields, models


class ReportHrAttendanceErrors(models.AbstractModel):
    _name = 'report.hr_attendance.report_attendanceerrors'
    _inherit = 'report.abstract_report'
    _template = 'hr_attendance.report_attendanceerrors'

    def _delay(self, employee_id, dt_from, dt_to):
        delay_list = []
        attendances = self.env['hr.attendance'].search([('employee_id', '=', employee_id), ('name', '<=', dt_to), ('name', '>=', dt_from), ('action', 'in', ('sign_in', 'sign_out'))], order="name")
        lang = self.env['res.lang'].search([('code', '=', self.env.context.get('lang', 'en_US'))])
        format_date = lang.date_format.encode('utf-8')
        format_time = lang.time_format.encode('utf-8')
        date_time_format = "%s %s" % (format_date, format_time)
        for attend in attendances:
            name = fields.Datetime.from_string(attend.name).strftime(date_time_format)
            create_date = fields.Datetime.from_string(attend.create_date).strftime(date_time_format)
            delay_time = (fields.Datetime.from_string(attend.name) - fields.Datetime.from_string(attend.create_date))
            res = {'action': attend.action, 'create_date': create_date, 'date': name, 'delay': delay_time}
            if attend.action == 'sign_out':
                res['delay'] = -delay_time
            delay_list.append(res)
        return delay_list

    def _lst(self, employee_id, dt_from, dt_to, max_delay):
        att_lst = []
        for res in self._delay(employee_id, dt_from, dt_to):
            temp = res['delay'].seconds
            res['delay'] = str(res['delay']).split('.')[0]
            if abs(temp) < max_delay*60:
                res['delay2'] = res['delay']
            else:
                res['delay2'] = '/'
            att_lst.append(res)
        return att_lst

    def _lst_total(self, employee_id, dt_from, dt_to, max_delay):
        total2 = datetime.timedelta(seconds=0, minutes=0, hours=0)
        total = datetime.timedelta(seconds=0, minutes=0, hours=0)
        for res in self._delay(employee_id, dt_from, dt_to):
            total += res['delay']
            if abs(res['delay'].seconds) < max_delay*60:
                total2 += res['delay']

            result_dict = {'total': total and str(total).split('.')[0],
                           'total2': total2 and str(total2).split('.')[0]}
        return [result_dict]

    @api.multi
    def render_html(self, data):
        Report = self.env['report']
        report = Report._get_report_from_name('hr_attendance.report_attendanceerrors')
        employees = self.env['hr.employee'].browse(data.get('emp_ids'))
        total_attend = dict.fromkeys(data.get('emp_ids'), [])
        attend_list = dict.fromkeys(data.get('emp_ids'), [])
        for emp in employees:
            attend_list[emp.id] = self._lst(emp.id, data.get('init_date'), data.get('end_date'), data.get('max_delay'))
            total_attend[emp.id] = self._lst_total(emp.id, data.get('init_date'), data.get('end_date'), data.get('max_delay'))
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self,
            'data': data,
            'time': time,
            'attend_list': attend_list,
            'total': total_attend,
            'employees': employees,
        }
        return Report.render('hr_attendance.report_attendanceerrors', docargs)
