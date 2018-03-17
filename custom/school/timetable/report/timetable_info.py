# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ReportTimetableInfo(models.AbstractModel):
    _name = 'report.timetable.timetable'

    @api.multi
    def _get_timetable(self, timetable_id):
        timetable_detail = []
        self._cr.execute('''select t.start_time,t.end_time,s.name,week_day,
                        r.name as teacher from time_table_line t,
                        subject_subject s, resource_resource r, hr_employee
                        hr where t.subject_id= s.id and t.teacher_id= hr.id
                        and hr.resource_id = r.id  and table_id = %s
                        group by start_time,end_time,s.name,week_day,r.name
                        order by start_time''', tuple([timetable_id.id]))
        res = self._cr.dictfetchall()
        self._cr.execute('''select start_time,end_time from time_table_line
                        where table_id=%s group by start_time,end_time
                        order by start_time''', tuple([timetable_id.id]))
        time_data = self._cr.dictfetchall()
        for time_detail in time_data:
            for data in res:
                if ((time_detail['start_time'] == data['start_time']) and
                        (time_detail['end_time'] == data['end_time'])):
                    if (data['name'] == 'Recess'):
                        time_detail[data['week_day']] = data['name']
                    else:
                        td = data['name'] + '\n(' + data['teacher'] + ')'
                        time_detail[data['week_day']] = td
            timetable_detail.append(time_detail)
        return timetable_detail

    @api.model
    def render_html(self, docids, data=None):
        docs = self.env['time.table'].browse(docids)
        docargs = {'doc_ids': docids,
                   'doc_model': self.env['time.table'],
                   'docs': docs,
                   'get_timetable': self._get_timetable}
        return self.env['report'].render('timetable.timetable', docargs)
