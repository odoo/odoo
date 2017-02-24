# -*- coding: utf-8 -*-
###############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2009-TODAY Tech-Receptives(<http://www.techreceptives.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from datetime import datetime
import time

from openerp import models, pooler
from openerp.report import report_sxw


class TimeTableStudentGenerate(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(TimeTableStudentGenerate, self).__init__(
            cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_object': self.get_object,
        })

    def sort_tt(self, data_list):
        main_list = []
        f = []
        for d in data_list:
            if d['period'] not in f:
                f.append(d['period'])
                main_list.append({
                    'name': d['period'],
                    'line': {d['day']: d}
                })
            else:
                for m in main_list:
                    if m['name'] == d['period']:
                        m['line'][d['day']] = d
        return main_list

    def get_object(self, data):

        dayofWeek = ['Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday', 'Saturday']

        data_list = []
        for timetable_obj in pooler.get_pool(self.cr.dbname).get(
            'op.timetable').browse(
                self.cr, self.uid, data['time_table_ids']):

            oldDate = datetime.strptime(
                timetable_obj.start_datetime, "%Y-%m-%d %H:%M:%S")
            day = dayofWeek[datetime.weekday(oldDate)]

            timetable_data = {
                'period': timetable_obj.period_id.name,
                'sequence': timetable_obj.period_id.sequence,
                'start_datetime': timetable_obj.start_datetime,
                'day': day,
                'subject': timetable_obj.subject_id.name,
            }
            data_list.append(timetable_data)

        ttdl = sorted(data_list, key=lambda k: k['sequence'])
        final_list = self.sort_tt(ttdl)
        return final_list


class ReportTimetableStudentGenerate(models.AbstractModel):
    _name = 'report.openeducat_timetable.report_timetable_student_generate'
    _inherit = 'report.abstract_report'
    _template = 'openeducat_timetable.report_timetable_student_generate'
    _wrapped_report_class = TimeTableStudentGenerate


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
